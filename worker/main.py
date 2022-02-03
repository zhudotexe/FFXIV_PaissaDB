import asyncio
import logging

import sentry_sdk
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sqlalchemy.orm import Session

from common import calc, config, crud, gamedata, models, schemas
from common.database import EVENT_QUEUE_KEY, PUBSUB_WS_CHANNEL, SessionLocal, engine, redis
from . import utils

log = logging.getLogger("worker")
logging.basicConfig(level=config.LOGLEVEL)


class Worker:
    def __init__(self):
        self.redis = redis
        self.db: Session = SessionLocal()

    async def init(self):
        models.Base.metadata.create_all(bind=engine)
        gamedata.upsert_all(gamedata_dir=config.GAMEDATA_DIR, db=self.db)
        if config.SENTRY_DSN is not None:
            sentry_sdk.init(
                dsn=config.SENTRY_DSN,
                environment=config.SENTRY_ENV,
                integrations=[SqlalchemyIntegration()]
            )

    async def main_loop(self):
        while True:
            try:
                _, data_key, score = await self.redis.bzpopmin(EVENT_QUEUE_KEY)
                log.debug(f"Got {data_key} off the event PQ with score {score}")
                await self.process_plot_from_key(data_key)
            except (asyncio.CancelledError, KeyboardInterrupt):
                break
            except Exception:
                log.exception(f"Error processing event:")
                self.db.rollback()

    async def process_plot_from_key(self, key: str):
        data = await self.redis.execute_command("GETDEL", key)  # aioredis doesn't have this yet
        if data is None:
            log.warning(f"Data in key {key} is nil, skipping")
            return 
        plot_state_event: schemas.paissa.PlotStateEntry = schemas.paissa.PlotStateEntry.parse_raw(data)
        world_id = plot_state_event.world_id
        district_id = plot_state_event.district_id
        ward_num = plot_state_event.ward_num
        plot_num = plot_state_event.plot_num

        # get the latest state of the plot
        for state in crud.historical_plot_state(
                self.db,
                plot_state_event.world_id,
                plot_state_event.district_id,
                plot_state_event.ward_num,
                plot_state_event.plot_num,
                yield_per=1
        ):
            # if event's timestamp  > state's last_seen:
            if plot_state_event.timestamp > state.last_seen:
                log.debug(f"Event {key} updates state {state.id} with new time")
                # if it matches, update last_seen (and possibly owner name, lotto_entries) and return
                if utils.plot_state_matches_history(plot_state_event, state):
                    utils.update_historical_state_from(state, plot_state_event)
                # else create a new state, broadcast state changes, and return
                else:
                    new_state = utils.new_state_from_event(plot_state_event)
                    self.db.add(new_state)
                    self.db.enable_relationship_loading(new_state)

                    if new_state.is_owned != state.is_owned:
                        if not new_state.is_owned:
                            transition_detail = schemas.paissa.WSPlotOpened(
                                data=calc.open_plot_detail(new_state, state)
                            )
                        else:
                            transition_detail = schemas.paissa.WSPlotSold(
                                data=calc.sold_plot_detail(new_state, state)
                            )
                        await self.broadcast(transition_detail.json())
                break
            # elif state's last_seen  > event's timestamp > state's first_seen:
            elif state.last_seen >= plot_state_event.timestamp >= state.first_seen:
                log.debug(f"Event {key} falls within {state.id}")
                # if it matches, update owner name (if it's None) and return
                if utils.plot_state_matches_history(plot_state_event, state):
                    utils.update_historical_state_from(state, plot_state_event)
                # otherwise cry (create 2 new states, I guess)
                else:
                    log.warning(
                        f"Event falls within state history but does not match state: "
                        f"event={plot_state_event!r}, history={state!r}"
                    )
                break
            # else state's first_seen > event's timestamp
            # get the previous state and do this again (continue loop)
        else:
            log.debug(f"Event {key} is the first state for its plot")
            log.info(f"Found new state for world {world_id} district {district_id}: {ward_num}-{plot_num}")
            # if there is no previous state (we have exhausted all history)
            # we must be the very first state, create a state
            new_state = utils.new_state_from_event(plot_state_event)
            self.db.add(new_state)

        # whatever changes we made, they're good here
        self.db.commit()

    async def broadcast(self, data: str):
        """Sends some string data to the web workers to broadcast to all connected websockets."""
        await self.redis.publish(PUBSUB_WS_CHANNEL, data)


async def run():
    """Primary entrypoint for a worker instance. Sets up the loop that processes anything in the event PQ."""
    worker = Worker()
    await worker.init()
    log.info("Hello world, worker is listening...")
    await worker.main_loop()
    log.info("Worker is shutting down...")
