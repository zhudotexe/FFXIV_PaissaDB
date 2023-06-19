from common import models, schemas


def should_create_new_state(state_event: schemas.paissa.PlotStateEntry, historical_state: models.PlotState):
    """
    Returns whether a new state should be created because of differences between the latest state and the last state.

    Returns True if the ownership state changed, the owner changed, the purchase system changed,
    or the allowed tenant type changed.
    """
    # ownership state changed
    if state_event.is_owned != historical_state.is_owned:
        return True
    # purchase system changed
    if state_event.purchase_system != historical_state.purchase_system:
        return True
    # owner changed (and both populated)
    if (
        state_event.owner_name is not None
        and historical_state.owner_name is not None
        and state_event.owner_name != historical_state.owner_name
    ):
        return True
    return False


def update_historical_state_from(historical_state: models.PlotState, state_event: schemas.paissa.PlotStateEntry):
    """
    Updates the historical state's keys from the newly seen state in place.

    Updated keys:
    - last_seen_price if latest
    - lotto_entries if latest and greater
    - lotto_phase_until if latest
    - last_seen if latest
    - purchase_system if latest
    - lotto_phase if was None or latest
    - lotto_phase_until if latest
    - owner_name if was None
    """
    if did_update_owner := historical_state.owner_name is None and state_event.owner_name is not None:
        historical_state.owner_name = state_event.owner_name
    if historical_state.lotto_phase is None and state_event.lotto_phase is not None:
        historical_state.lotto_phase = state_event.lotto_phase

    if state_event.timestamp > historical_state.last_seen:
        if state_event.price is not None:
            historical_state.last_seen_price = state_event.price
        if state_event.lotto_entries is not None and state_event.lotto_entries > (historical_state.lotto_entries or 0):
            historical_state.lotto_entries = state_event.lotto_entries
        if state_event.lotto_phase_until is not None:
            historical_state.lotto_phase_until = state_event.lotto_phase_until
        if state_event.lotto_phase is not None:
            historical_state.lotto_phase = state_event.lotto_phase
        historical_state.purchase_system = state_event.purchase_system

        # only update timestamp for placard events
        # aetheryte events only change purchase system (creates new state) or owner
        # or if the update occurs after the old lotto_end_time (or we didn't/don't know the old lotto_end_time)
        update_lotto_timestamp = historical_state.lotto_phase_until is None or (
            state_event.timestamp > historical_state.lotto_phase_until
        )
        if (state_event.lotto_phase is not None) or did_update_owner or update_lotto_timestamp:
            historical_state.last_seen = state_event.timestamp


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
        purchase_system=state_event.purchase_system.value,
        lotto_entries=state_event.lotto_entries,
        lotto_phase=state_event.lotto_phase,
        lotto_phase_until=state_event.lotto_phase_until,
    )
