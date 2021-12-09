def sweep_processer_entrypoint():
    asyncio.run(process_wardsweeps())


async def process_wardsweeps():
    while True:
        try:
            sweep_id = broadcast_process_queue.get(block=True)
            with SessionLocal() as db:
                wardsweep = await utils.executor(crud.get_wardsweep_by_id, db, sweep_id)
                await broadcast_changes_in_wardsweep(db, wardsweep)
        except (asyncio.CancelledError, KeyboardInterrupt):
            break
        except Exception:
            log.exception("Failed to process wardsweep:")
        finally:
            # small delay to prevent task from hogging system resources
            await asyncio.sleep(0.05)


async def broadcast(message: str):
    await redis.publish(CHANNEL, message)


async def broadcast_changes_in_wardsweep(db: Session, wardsweep: models.WardSweep):
    plot_history = await utils.executor(
        crud.get_plot_states_before,
        db, wardsweep.world_id, wardsweep.territory_type_id, wardsweep.ward_number, wardsweep.timestamp
    )
    history_map = {p.plot_number: p for p in plot_history}
    for plot in wardsweep.plots:
        before = history_map.get(plot.plot_number)
        # seen for first time, and is open
        if before is None and not plot.is_owned:
            await broadcast_plot_open(db, plot)
        # owned -> open
        elif before is not None and before.is_owned and not plot.is_owned:
            await broadcast_plot_open(db, plot)
        # open -> sold
        elif before is not None and not before.is_owned and plot.is_owned:
            await broadcast_plot_sold(db, plot)


async def broadcast_plot_open(db: Session, plot: models.Plot):
    detail = await utils.executor(calc.open_plot_detail, db, plot)
    data = schemas.paissa.WSPlotOpened(data=detail)
    await broadcast(data.json())


async def broadcast_plot_sold(db: Session, plot: models.Plot):
    detail = await utils.executor(calc.sold_plot_detail, db, plot)
    data = schemas.paissa.WSPlotSold(data=detail)
    await broadcast(data.json())