import datetime
import logging
import time
from math import ceil
from typing import Optional

from sqlalchemy.orm import Session

from . import crud, models, schemas

# 2am JST
DEVALUE_TIME = datetime.time(hour=2, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
DEVALUE_TIME_NAIVE = datetime.datetime.combine(datetime.date.today(), DEVALUE_TIME).astimezone(None).time()
HOURS_PER_DEVAL = 6  # after 1st deval, 1 deval every 6 hours
SECONDS_IN_DAY = 60 * 60 * 24

log = logging.getLogger(__name__)


def get_district_detail(db: Session, world: models.World, district: models.District) -> schemas.paissa.DistrictDetail:
    """Gets the district detail for a given district in a world."""
    latest_plots = crud.latest_plot_states_in_district(db, world.id, district.id)
    num_open_plots = sum(1 for p in latest_plots if not p.is_owned)
    oldest_plot_time = min(p.last_seen for p in latest_plots) if latest_plots else 0
    open_plots = []

    for plot in latest_plots:
        if plot.is_owned:
            continue
        # we found a plot that was last known as open, iterate over its history to find the details
        first_open_state, last_sold_state = crud.last_state_transition(db, plot)
        open_plots.append(open_plot_detail(first_open_state, last_sold_state))

    return schemas.paissa.DistrictDetail(
        id=district.id,
        name=district.name,
        num_open_plots=num_open_plots,
        oldest_plot_time=oldest_plot_time,
        open_plots=open_plots
    )


def open_plot_detail(
    first_open_state: models.PlotState,
    last_sold_state: Optional[models.PlotState],
    devalue_aware=True
) -> schemas.paissa.OpenPlotDetail:
    """
    Gets the details of a plot's opening given the transition pair of states.
    """
    est_time_open_max = first_open_state.first_seen

    if last_sold_state is not None:
        est_time_open_min = last_sold_state.last_seen
    else:
        # the plot has been open for as long as we've known it, so could be whenever
        est_time_open_min = 0

    if devalue_aware and first_open_state.num_devals is not None:
        # ensure that the min open time/max open time is sane for the number of devals
        early = earliest_possible_open_time(first_open_state.num_devals, first_open_state.last_seen)
        late = early + SECONDS_IN_DAY
        est_time_open_min = max(est_time_open_min, early)
        est_time_open_max = min(est_time_open_max, late)

    return schemas.paissa.OpenPlotDetail(
        world_id=first_open_state.world_id,
        district_id=first_open_state.territory_type_id,
        ward_number=first_open_state.ward_number,
        plot_number=first_open_state.plot_number,
        size=first_open_state.plot_info.house_size,
        last_seen_price=first_open_state.last_seen_price or first_open_state.plot_info.house_base_price,
        last_updated_time=first_open_state.last_seen,
        est_time_open_min=est_time_open_min,
        est_time_open_max=est_time_open_max,
    )


def earliest_possible_open_time(
    num_devals: int,
    known_at: float = None,
    devalue_time: datetime.time = DEVALUE_TIME_NAIVE
) -> float:
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


def sold_plot_detail(
    first_sold_state: models.PlotState,
    last_open_state: Optional[models.PlotState]
) -> schemas.paissa.SoldPlotDetail:
    """
    Gets the details of a plot's sale given the transition pair of states.
    """
    est_time_sold_max = first_sold_state.first_seen
    if last_open_state is not None:
        est_time_sold_min = last_open_state.last_seen
    else:
        # the plot has been sold for as long as we've known it, so could be whenever, the devalue calc will get it
        est_time_sold_min = 0

    return schemas.paissa.SoldPlotDetail(
        world_id=first_sold_state.world_id,
        district_id=first_sold_state.territory_type_id,
        ward_number=first_sold_state.ward_number,
        plot_number=first_sold_state.plot_number,
        size=first_sold_state.plot_info.house_size,
        last_updated_time=first_sold_state.last_seen,
        est_time_sold_min=est_time_sold_min,
        est_time_sold_max=est_time_sold_max
    )


# ==== pre-endwalker ====
# todo(6.1) yeet me
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


def num_missed_devals(num_devals: int, known_at: float, when: float = None, devalue_time=DEVALUE_TIME_NAIVE) -> int:
    """
    Given a known number of devalues and the time it was known, calculates the number of known devals
    (if *when* is passed, at *when*, otherwise at current time).
    """
    if when is None:
        when = datetime.datetime.now()
    else:
        when = datetime.datetime.fromtimestamp(when)
    known_at = datetime.datetime.fromtimestamp(known_at)

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
