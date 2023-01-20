import collections
import logging
from typing import Optional

from sqlalchemy.orm import Session

from . import crud, models, schemas

log = logging.getLogger(__name__)


def get_world_detail(db: Session, world: models.World, include_time_estimates=False) -> schemas.paissa.WorldDetail:
    """Gets the district detail for a given district in a world."""
    latest_plots = crud.latest_plot_states_in_world(db, world.id)
    district_open_plots = collections.defaultdict(list)

    for plot in latest_plots:
        if plot.is_owned:
            continue
        if include_time_estimates and plot.is_fcfs:
            # we found a plot that was last known as open, iterate over its history to find the details
            first_open_state, last_sold_state = crud.last_state_transition(db, plot)
            district_open_plots[plot.territory_type_id].append(
                open_plot_detail(plot, first_open_state, last_sold_state)
            )
        else:
            district_open_plots[plot.territory_type_id].append(open_plot_detail(plot))

    districts = crud.get_districts(db)
    district_details = []
    for district in districts:
        num_open_plots = len(district_open_plots[district.id])
        oldest_plot_time = min(p.last_seen for p in latest_plots if p.territory_type_id == district.id)
        district_details.append(
            schemas.paissa.DistrictDetail(
                id=district.id,
                name=district.name,
                num_open_plots=num_open_plots,
                oldest_plot_time=oldest_plot_time,
                open_plots=district_open_plots[district.id],
            )
        )

    return schemas.paissa.WorldDetail(
        id=world.id,
        name=world.name,
        districts=district_details,
        num_open_plots=sum(d.num_open_plots for d in district_details),
        oldest_plot_time=min(d.oldest_plot_time for d in district_details),
    )


def get_district_detail(
    db: Session, world: models.World, district: models.District, include_time_estimates=False
) -> schemas.paissa.DistrictDetail:
    """Gets the district detail for a given district in a world."""
    latest_plots = crud.latest_plot_states_in_district(db, world.id, district.id)
    num_open_plots = sum(1 for p in latest_plots if not p.is_owned)
    oldest_plot_time = min(p.last_seen for p in latest_plots) if latest_plots else 0
    open_plots = []

    for plot in latest_plots:
        if plot.is_owned:
            continue
        if include_time_estimates and plot.is_fcfs:
            # we found a plot that was last known as open, iterate over its history to find the details
            first_open_state, last_sold_state = crud.last_state_transition(db, plot)
            open_plots.append(open_plot_detail(plot, first_open_state, last_sold_state))
        else:
            open_plots.append(open_plot_detail(plot))

    return schemas.paissa.DistrictDetail(
        id=district.id,
        name=district.name,
        num_open_plots=num_open_plots,
        oldest_plot_time=oldest_plot_time,
        open_plots=open_plots,
    )


def open_plot_detail(
    latest_state: models.PlotState,
    first_open_state: models.PlotState = None,
    last_sold_state: Optional[models.PlotState] = None,
) -> schemas.paissa.OpenPlotDetail:
    """
    Gets the details of a plot's opening given the transition pair of states.
    """
    est_time_open_max = first_open_state.first_seen if first_open_state is not None else 0

    if last_sold_state is not None:
        est_time_open_min = last_sold_state.last_seen
    else:
        # the plot has been open for as long as we've known it, so could be whenever
        est_time_open_min = 0

    # sometimes it shows there being entries on unavailable plots
    if latest_state.lotto_phase == schemas.ffxiv.LotteryPhase.Unavailable:
        lotto_entries = 0
    else:
        lotto_entries = latest_state.lotto_entries

    return schemas.paissa.OpenPlotDetail(
        world_id=latest_state.world_id,
        district_id=latest_state.territory_type_id,
        ward_number=latest_state.ward_number,
        plot_number=latest_state.plot_number,
        size=latest_state.plot_info.house_size,
        price=latest_state.last_seen_price or latest_state.plot_info.house_base_price,
        last_updated_time=latest_state.last_seen,
        est_time_open_min=est_time_open_min,
        est_time_open_max=est_time_open_max,
        purchase_system=latest_state.purchase_system,
        lotto_entries=lotto_entries,
        lotto_phase=latest_state.lotto_phase,
        lotto_phase_until=latest_state.lotto_phase_until,
    )


def sold_plot_detail(
    first_sold_state: models.PlotState, last_open_state: Optional[models.PlotState]
) -> schemas.paissa.SoldPlotDetail:
    """
    Gets the details of a plot's sale given the transition pair of states.
    """
    est_time_sold_max = first_sold_state.first_seen
    if last_open_state is not None:
        est_time_sold_min = last_open_state.last_seen
    else:
        # the plot has been sold for as long as we've known it, so could be whenever
        est_time_sold_min = 0

    return schemas.paissa.SoldPlotDetail(
        world_id=first_sold_state.world_id,
        district_id=first_sold_state.territory_type_id,
        ward_number=first_sold_state.ward_number,
        plot_number=first_sold_state.plot_number,
        size=first_sold_state.plot_info.house_size,
        last_updated_time=first_sold_state.last_seen,
        est_time_sold_min=est_time_sold_min,
        est_time_sold_max=est_time_sold_max,
    )


def plot_update(plot_state_event: schemas.paissa.PlotStateEntry, old_state: models.PlotState):
    """
    Gets the update information for a plot.
    """
    # sometimes it shows there being entries on unavailable plots
    if plot_state_event.lotto_phase == schemas.ffxiv.LotteryPhase.Unavailable:
        lotto_entries = 0
    else:
        lotto_entries = plot_state_event.lotto_entries

    return schemas.paissa.PlotUpdate(
        world_id=plot_state_event.world_id,
        district_id=plot_state_event.district_id,
        ward_number=plot_state_event.ward_num,
        plot_number=plot_state_event.plot_num,
        size=old_state.plot_info.house_size,
        price=old_state.plot_info.house_base_price,
        last_updated_time=plot_state_event.timestamp,
        purchase_system=plot_state_event.purchase_system,
        lotto_entries=lotto_entries,
        lotto_phase=plot_state_event.lotto_phase,
        previous_lotto_phase=old_state.lotto_phase,
        lotto_phase_until=plot_state_event.lotto_phase_until,
    )
