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
"""
import os
import time

os.environ['TZ'] = 'Etc/UTC'
time.tzset()

import csv
import datetime
from contextlib import contextmanager

from pydantic import BaseModel

from paissadb import calc, crud, models
from paissadb.database import SessionLocal


# ==== helpers ====
class PlotSale(BaseModel):
    world_id: int
    territory_type_id: int
    ward_number: int  # 0-indexed
    plot_number: int  # 0-indexed
    time_open_min: datetime.datetime
    time_open_max: datetime.datetime
    time_sold_min: datetime.datetime
    time_sold_max: datetime.datetime
    is_relo: bool
    known_price: int


@contextmanager
def timer(prefix, name, indent=0):
    start = time.monotonic()
    print(f"{' ' * indent}[{prefix}] started {name}")
    yield
    end = time.monotonic()
    print(f"{' ' * indent}[{prefix}] finished {name} in {end - start:.2f}s")


def is_new_owner(db, plot, sale_details):
    """
    Returns whether the current owner of the given plot is a new owner, or if they have owned another house within
    the last week.
    """
    if not plot.has_built_house:
        return True

    # oh boy
    # time to make a chonky query (~1500ms cold)
    owned = db.query(models.Plot) \
        .filter(models.Plot.world_id == plot.world_id) \
        .filter(models.Plot.timestamp < sale_details.est_time_sold_min,
                models.Plot.timestamp >= sale_details.est_time_sold_min - datetime.timedelta(days=7)) \
        .filter(models.Plot.owner_name == plot.owner_name) \
        .first()

    return owned is None


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
            known_price=opening_details.known_price
        )


def do_all_sale_stats(db):
    for world in crud.get_worlds(db):
        with timer('WRLD', f'{world.id} ({world.name})'):
            for district in crud.get_districts(db):
                with timer('DIST', f'{district.id} ({district.name})', indent=2):
                    latest_plots = crud.get_latest_plots_in_district(db, world.id, district.id)
                    for plot in latest_plots:
                        statter = SaleStatGenerator(db, plot)
                        # with timer('PLOT', f'{plot.ward_number + 1}-{plot.plot_number + 1}', indent=4):
                        yield from statter.do_stats()
        db.expunge_all()  # stop memory use from going wild
        db.rollback()


def run(db):
    with open('sales.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=PlotSale.__fields__.keys())
        writer.writeheader()
        with timer('MAIN', 'all'):
            for plot_sale in do_all_sale_stats(db):
                writer.writerow(plot_sale.dict())


if __name__ == '__main__':
    with SessionLocal() as sess:
        sess.execute("SET LOCAL work_mem = '256MB'")
        run(sess)
