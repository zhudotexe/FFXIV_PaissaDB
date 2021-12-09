"""
Used to preview the rows that will be upserted upon server start.
"""
import os

from common import gamedata


def print_orm_model(o):
    dd = o.__dict__.copy()
    dd.pop('_sa_instance_state')
    print(dd)


if __name__ == '__main__':
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gamedata")
    print("===== Worlds =====")
    for world in gamedata.generate_worlds(d):
        print_orm_model(world)

    print("===== Districts =====")
    districts = gamedata.generate_districts(d)
    for district in districts:
        print_orm_model(district)

    print("===== PlotInfo =====")
    for plotinfo in gamedata.generate_plotinfo(districts, d):
        print_orm_model(plotinfo)
