import datetime
import logging

from sqlalchemy.orm import Session

from . import models, crud, schemas

# 2am JST
DEVALUE_TIME = datetime.time(hour=2, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))

log = logging.getLogger(__name__)


def plot_detail(db: Session, plot: models.Plot):
    log.debug(plot.district.name, plot.ward_number, plot.plot_number)

    last_known_price_i = (plot.house_price, plot.timestamp)
    last_known_devals_i = (plot.num_devals, plot.timestamp)
    est_time_open_min = est_time_open_max = plot.timestamp

    for ph in crud.plot_history(db, plot):
        log.debug(ph.timestamp)
        last_known_price, _ = last_known_price_i
        # fill in any attrs that we don't know yet
        if last_known_price is None:
            last_known_price_i = (ph.house_price, ph.timestamp)
            last_known_devals_i = (ph.num_devals, ph.timestamp)

        # if the house was owned then, the earliest it could be open is instantaneously after then
        # also if the price decreases going back in history, there was a relo
        price_decreased = last_known_price is not None \
                          and ph.house_price is not None \
                          and ph.house_price < last_known_price
        if ph.is_owned or price_decreased:
            est_time_open_min = ph.timestamp
            break

        # otherwise the latest it could have opened was the instant before the last time it was closed
        est_time_open_max = ph.timestamp

    last_known_price, last_known_price_time = last_known_price_i
    last_known_devals, last_known_devals_time = last_known_devals_i

    return schemas.paissa.PlotDetail(
        world_id=plot.world_id,
        district_id=plot.territory_type_id,
        ward_number=plot.ward_number,
        plot_number=plot.plot_number,
        size=plot.plot_info.house_size,
        price=last_known_price or plot.plot_info.house_base_price,
        last_updated_time=plot.timestamp,
        est_time_open_min=est_time_open_min,
        est_time_open_max=est_time_open_max,
        est_num_devals=last_known_devals or 0
    )
