from common import models, schemas


def plot_state_matches_history(state_event: schemas.paissa.PlotStateEntry, historical_state: models.PlotState):
    """
    Returns whether the state event matches the historical state.

    If owner_name is None for either state, the key is ignored. Ignores lotto_entry.
    """
    if state_event.is_owned != historical_state.is_owned:
        return False
    if (state_event.owner_name is not None
            and historical_state.owner_name is not None
            and state_event.owner_name != historical_state.owner_name):
        return False
    return (state_event.world_id == historical_state.world_id
            and state_event.district_id == historical_state.territory_type_id
            and state_event.ward_num == historical_state.ward_number
            and state_event.plot_num == historical_state.plot_number)


def update_historical_state_from(historical_state: models.PlotState, state_event: schemas.paissa.PlotStateEntry):
    """
    Updates the historical state's keys from the newly seen state in place.

    Updated keys:
    - last_seen_price if latest
    - lotto_entries if latest
    - last_seen if latest
    - owner_name if was None
    """
    if state_event.timestamp > historical_state.last_seen:
        if state_event.price is not None:
            historical_state.last_seen_price = state_event.price
        if state_event.lotto_entries is not None:
            historical_state.lotto_entries = state_event.lotto_entries
        historical_state.last_seen = state_event.timestamp

    if historical_state.owner_name is None and state_event.owner_name is not None:
        historical_state.owner_name = state_event.owner_name


def new_state_from_event(state_event: schemas.paissa.PlotStateEntry) -> models.PlotState:
    return models.PlotState(
        world_id=state_event.world_id,
        territory_type_id=state_event.district_id,
        ward_number=state_event.ward_num,
        plot_number=state_event.plot_num,
        last_seen=state_event.timestamp,
        first_seen=state_event.timestamp,
        is_owned=state_event.is_owned,
        last_seen_price=state_event.price,
        owner_name=state_event.owner_name,
        is_fcfs=state_event.is_fcfs,
        lotto_entries=state_event.lotto_entries
    )
