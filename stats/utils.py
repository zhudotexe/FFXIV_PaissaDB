import datetime

from pydantic import BaseModel


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
    last_presale_data_id: int

    @property
    def open_dur_min(self) -> float:
        """The minimum number of hours the house could have been up for sale for"""
        return (self.time_sold_min - self.time_open_max) / datetime.timedelta(hours=1)

    @property
    def open_dur_max(self) -> float:
        """The maximum number of hours the house could have been up for sale for"""
        return (self.time_sold_max - self.time_open_min) / datetime.timedelta(hours=1)

    @property
    def open_precision(self) -> float:
        return abs((self.time_open_max - self.time_open_min) / datetime.timedelta(hours=1))

    @property
    def close_precision(self) -> float:
        return abs((self.time_sold_max - self.time_sold_min) / datetime.timedelta(hours=1))

    @property
    def precision(self) -> float:
        """The number of hours of this sale's imprecision"""
        return self.open_precision + self.close_precision
