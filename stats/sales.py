"""
Saves a CSV of all plot sales to an output folder.

Methodology:

To reduce the amount of plots in memory at any one point, this script iterates over each district in each world
independently. It first begins by getting the latest state of all plots (1,440 per district). For each individual plot,
it then iterates over the plot's history in reverse chronological order searching for state transitions.

When it encounters a state transition, it uses PaissaDB methods to estimate the earliest and latest time the transition
could have happened. If the transition was a sale, it determines whether the sale was a relocation using two methods:
1. If the plot does not have a house built, it's likely not a relocation.
2. Otherwise, search for any plot on the same world owned by the new owner up to one week prior to the earliest sell
   time. If any is found, it is likely a relocation. Otherwise, assume it's a first-time buyer.

If the transition was an opening, pair it with the next chronological sale. Use these pairs to emit PlotSale records.

* Note: This script was able to lock all 8 cores of an i9-9900K at 100% for ~20 minutes. I recommend running this on
  a very capable computer.
"""
import csv
import datetime
import multiprocessing
import os
import sys
import time
from contextlib import contextmanager

from common import models
from common.database import SessionLocal
from paissadb import calc, crud
from stats.utils import PlotSale

# threading: setting this to 1 on slower systems and (num cpus) on faster systems is generally fine
NUM_THREADS = 8
district_q = multiprocessing.JoinableQueue()
sale_q = multiprocessing.JoinableQueue()


# ==== helpers ====
@contextmanager
def timer(prefix, name, indent=0):
    start = time.monotonic()
    print(f"{' ' * indent}[{prefix}] started {name}")
    yield
    end = time.monotonic()
    print(f"{' ' * indent}[{prefix}] finished {name} in {end - start:.2f}s")


def is_new_owner(db, plot, sale_details):
    """
    Returns whether the current owner of the given plot is a new owner, i.e. if they have not owned another house within
    the last week.
    """
    # if not plot.has_built_house:  # there are cases of people buying a plot and reloing before building a house
    #     return True

    # time to make a chonky query (~1500ms cold)
    owned = db.query(models.Plot) \
        .filter(models.Plot.world_id == plot.world_id) \
        .filter(
        models.Plot.timestamp < sale_details.est_time_sold_min,
        models.Plot.timestamp >= sale_details.est_time_sold_min - datetime.timedelta(days=7)
    ) \
        .filter(models.Plot.owner_name == plot.owner_name) \
        .count()

    return owned == 0


# ==== stats ====
class SaleStatGenerator:
    def __init__(self, db, plot: models.Plot):
        self.db = db
        self.plot = plot

    # main entrypoint
    def do_stats(self):
        last = self.plot  # technically next chronologically
        for current in crud.plot_history(self.db, self.plot):
            if last.is_owned and not current.is_owned:
                yield self._on_sale(last, current)
            last = current

    # helpers
    def _on_sale(self, last, current):
        """
        Called when *last* is the first datapoint after a plot sells, and *current* is the last datapoint before a plot
        sells.
        """
        sale_details = calc.sold_plot_detail(self.db, last)
        opening_details = calc.open_plot_detail(self.db, current, now=current.timestamp)
        sale_is_relo = not is_new_owner(self.db, last, sale_details)

        return PlotSale(
            world_id=self.plot.world_id,
            territory_type_id=self.plot.territory_type_id,
            ward_number=self.plot.ward_number,
            plot_number=self.plot.plot_number,
            time_open_min=opening_details.est_time_open_min,
            time_open_max=opening_details.est_time_open_max,
            time_sold_min=sale_details.est_time_sold_min,
            time_sold_max=sale_details.est_time_sold_max,
            is_relo=sale_is_relo,
            known_price=opening_details.known_price,
            last_presale_data_id=current.id
        )


def queue_processing():
    with SessionLocal() as db:
        for world in crud.get_worlds(db):
            for district in crud.get_districts(db):
                district_q.put((world.id, district.id))


def t_processor(dq, sq):
    process = multiprocessing.current_process()
    while True:
        world_id, district_id = dq.get()
        with SessionLocal() as db:
            district = crud.get_district_by_id(db, district_id)
            world = crud.get_world_by_id(db, world_id)
            with timer(f'{process.name}', f'{world_id}-{district_id} ({world.name}, {district.name})'):
                latest_plots = crud.get_latest_plots_in_district(db, world_id, district_id)
                for plot in latest_plots:
                    statter = SaleStatGenerator(db, plot)
                    for result in statter.do_stats():
                        sq.put(result)
        dq.task_done()


def t_writer(sq):
    with open('sales.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=PlotSale.__fields__.keys())
        writer.writeheader()
        while True:
            plot_sale = sq.get()
            writer.writerow(plot_sale.dict())
            sq.task_done()


def run():
    # set working tz to UTC, if on Windows you should do this system-wide in time settings
    if sys.platform != 'win32':
        os.environ['TZ'] = 'Etc/UTC'
        time.tzset()
    else:
        input("Make sure your system clock is set to UTC! (Press enter to continue)")

    threads = []
    queue_processing()

    # launch worker threads
    for _ in range(NUM_THREADS):
        t = multiprocessing.Process(target=t_processor, args=(district_q, sale_q), daemon=True)
        t.start()
        threads.append(t)

    # launch writer thread
    t = multiprocessing.Process(target=t_writer, args=(sale_q,), daemon=True)
    t.start()
    threads.append(t)

    # wait for all tasks to complete before returning
    district_q.join()
    sale_q.join()


if __name__ == '__main__':
    with timer('MAIN', 'all'):
        run()
