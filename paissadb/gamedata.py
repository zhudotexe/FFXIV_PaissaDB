import csv
import os

from . import models


def upsert_all(gamedata_dir, db):
    """
    Given the path to the directory where gamedata files are, upserts the necessary rows into worlds, districts,
    and plotinfo.
    """
    pass


# ==== Transient Gen ====
def generate_worlds(gamedata_dir):
    worlds = []
    for world in read_csv(os.path.join(gamedata_dir, 'World.csv')):
        db_world = models.World(id=int(world['#']), name=world['Name'])
        worlds.append(db_world)
    return worlds


def generate_districts(gamedata_dir):
    """
    As of patch 5.35, the districts have the following useful properties:
    339/s1h1/mist -> landset 0
    340/f1h1/lav beds -> landset 1
    341/w1h1/goblet -> landset 2
    641/e1h1/shiro -> landset 3
    886/r1hx/firmament? -> landset 4?
    territoryintendeduse=13
    resident=78
    """
    return


def generate_plotinfo(gamedata_dir):
    return


# ==== utils ====
def read_csv(csv_path):
    with open(csv_path, newline='') as csvfile:
        # skip header rows
        next(csvfile)
        headers = next(csvfile).strip().split(',')
        next(csvfile)

        for row in csv.DictReader(csvfile, fieldnames=headers):
            yield row
