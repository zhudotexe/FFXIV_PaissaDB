import datetime
import logging
import time
from math import ceil

from sqlalchemy.orm import Session

from . import crud, models, schemas

# 2am JST
DEVALUE_TIME = datetime.time(hour=2, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
DEVALUE_TIME_NAIVE = datetime.datetime.combine(datetime.date.today(), DEVALUE_TIME).astimezone(None).time()
HOURS_PER_DEVAL = 6  # after 1st deval, 1 deval every 6 hours

log = logging.getLogger(__name__)


def get_district_detail(db: Session, world: models.World, district: models.District) -> schemas.paissa.DistrictDetail:
    """Gets the district detail for a given district in a world."""
    latest_plots = crud.get_latest_plot_states_in_district(db, world.id, district.id)
    num_open_plots = sum(1 for p in latest_plots if not p.is_owned)
    oldest_plot_time = min(p.timestamp for p in latest_plots) if latest_plots else 0
    open_plots = []

    for plot in latest_plots:
        if plot.is_owned:
            continue
        # we found a plot that was last known as open, iterate over its history to find the details
        open_plots.append(open_plot_detail(db, plot))

    return schemas.paissa.DistrictDetail(
        id=district.id,
        name=district.name,
        num_open_plots=num_open_plots,
        oldest_plot_time=oldest_plot_time,
        open_plots=open_plots
    )


def open_plot_detail(
    db: Session,
    plot: models.PlotState,
    now: datetime.datetime = None
) -> schemas.paissa.OpenPlotDetail:
    """
    Gets the current plot detail for a plot given the current state of the plot (assumed to be open).
    """
    log.debug(f"Calculating open plot detail for {plot.district.name} {plot.ward_number}-{plot.plot_number}")

    last_known_price_i = (plot.house_price, plot.timestamp)
    last_known_devals_i = (plot.num_devals, plot.timestamp)
    est_time_open_max = plot.timestamp
    if now is None:
        now = time.time()

    for ph in crud.plot_history(db, plot, before=plot.timestamp):
        log.debug(ph.timestamp)
        last_known_price, _ = last_known_price_i
        # fill in any attrs that we don't know yet
        if last_known_price is None:
            last_known_price_i = (ph.house_price, ph.timestamp)
            last_known_devals_i = (ph.num_devals, ph.timestamp)

        # if the house was owned then, the earliest it could be open is instantaneously after then
        # also if the price decreases going back in history, there was a relo
        # or if the price should have increased but didn't (some relo happened between sweeps)
        price_decreased = last_known_price is not None \
                          and ph.house_price is not None \
                          and ph.house_price < last_known_price
        price_did_not_increase = last_known_price is not None \
                                 and ph.house_price is not None \
                                 and ph.house_price == last_known_price \
                                 and dt_range_contains_time(ph.timestamp, est_time_open_max, DEVALUE_TIME_NAIVE)
        if ph.is_owned or price_decreased or price_did_not_increase:
            est_time_open_min = ph.timestamp
            break

        # otherwise the latest it could have opened was the instant before the last time it was closed
        est_time_open_max = ph.timestamp
    else:
        # the plot has been open for as long as we've known it, so could be whenever, the devalue calc will get it
        est_time_open_min = datetime.datetime.fromtimestamp(0)

    # add any devalues we know happened since we last got data on this plot, but haven't confirmed
    last_known_price, _ = last_known_price_i
    last_known_devals, last_known_devals_time = last_known_devals_i
    est_num_devals = (last_known_devals or 0) + num_missed_devals(last_known_devals, last_known_devals_time, when=now)

    # ensure that the min open time/max open time is sane for the number of devals
    early = earliest_possible_open_time(est_num_devals, now)
    late = early + datetime.timedelta(days=1)
    est_time_open_min = max(est_time_open_min, early)
    est_time_open_max = min(est_time_open_max, late)

    return schemas.paissa.OpenPlotDetail(
        world_id=plot.world_id,
        district_id=plot.territory_type_id,
        ward_number=plot.ward_number,
        plot_number=plot.plot_number,
        size=plot.plot_info.house_size,
        known_price=last_known_price or plot.plot_info.house_base_price,
        last_updated_time=plot.timestamp,
        est_time_open_min=est_time_open_min,
        est_time_open_max=est_time_open_max,
        est_num_devals=est_num_devals
    )


def dt_range_contains_time(start: float, end: float, the_time: datetime.time) -> bool:
    """Returns whether the datetime range defined by [start, end) contains at least one instance of the given time."""
    if end <= start:
        return False

    start = datetime.datetime.fromtimestamp(start)
    end = datetime.datetime.fromtimestamp(end)

    # end is after target and start is before it
    if start.time() <= the_time < end.time():
        return True

    # at least 24 hours has passed
    if end - start >= datetime.timedelta(days=1):
        return True

    # the start is before the time and the end is on the next day
    if start.time() <= the_time and start.date() < end.date():
        return True
    return False


def num_missed_devals(num_devals, known_at, when=None, devalue_time=DEVALUE_TIME_NAIVE) -> int:
    """
    Given a known number of devalues and the time it was known, calculates the number of known devals
    (if *when* is passed, at *when*, otherwise at current time).
    """
    if when is None:
        when = datetime.datetime.now()

    if num_devals == 0:
        # if the last known devals time is before the deval time,
        # and it's after the deval time now, add (num_hours_since_deval_time / 6) to devals
        if known_at.time() < devalue_time:
            devalue_date = known_at.date()
        else:
            devalue_date = known_at.date() + datetime.timedelta(days=1)
        next_deval_datetime = datetime.datetime.combine(devalue_date, devalue_time)
    else:
        # add num_hours_since_deval_time / 6 to devals
        hours_to_skip = (devalue_time.hour - known_at.hour) % HOURS_PER_DEVAL
        next_deval_datetime = known_at.replace(minute=0, second=0, microsecond=0) \
                              + datetime.timedelta(hours=hours_to_skip)
        if next_deval_datetime < known_at:  # edge case if known_at happens immediately after a devalue
            next_deval_datetime += datetime.timedelta(hours=HOURS_PER_DEVAL)

    time_since_last_deval = when - next_deval_datetime
    n = max(ceil(time_since_last_deval / datetime.timedelta(hours=HOURS_PER_DEVAL)), 0)
    return n


def earliest_possible_open_time(num_devals, known_at=None, devalue_time=DEVALUE_TIME_NAIVE) -> float:
    """Given the number of devals at *known_at*, returns the earliest datetime the plot could have opened."""
    if known_at is None:
        known_at = datetime.datetime.now()
    else:
        known_at = datetime.datetime.fromtimestamp(known_at)

    # 0 devals: the most recent devalue time
    # 1+ devals: the most recent devalue time to n * 6 hours ago
    t0 = known_at - datetime.timedelta(hours=HOURS_PER_DEVAL * num_devals)  # some time when it had 0 devals

    if t0.time() >= devalue_time:
        return datetime.datetime.combine(t0.date(), devalue_time).timestamp()
    else:
        return datetime.datetime.combine(t0.date() - datetime.timedelta(days=1), devalue_time).timestamp()


def sold_plot_detail(db: Session, plot: models.Plot):
    """
    Gets the current plot detail for a plot given the *latest* data point on the plot (assumed to be sold).
    """
    log.debug(f"Calculating sold plot detail for {plot.district.name} {plot.ward_number}-{plot.plot_number}")

    est_time_sold_max = plot.timestamp

    for ph in crud.plot_history(db, plot, before=plot.timestamp):
        log.debug(ph.timestamp)
        if not ph.is_owned:
            est_time_sold_min = ph.timestamp
            break
        # otherwise the latest it could have sold was the instant before the last time it was closed
        est_time_sold_max = ph.timestamp
    else:
        # the plot has been sold for as long as we've known it, so could be whenever, the devalue calc will get it
        est_time_sold_min = datetime.datetime.fromtimestamp(0)

    return schemas.paissa.SoldPlotDetail(
        world_id=plot.world_id,
        district_id=plot.territory_type_id,
        ward_number=plot.ward_number,
        plot_number=plot.plot_number,
        size=plot.plot_info.house_size,
        last_updated_time=plot.timestamp,
        est_time_sold_min=est_time_sold_min,
        est_time_sold_max=est_time_sold_max
    )
