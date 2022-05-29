import csv
import logging
import os

from sqlalchemy.orm import Session

from . import models

log = logging.getLogger(__name__)

PLOTS_PER_WARD = 60


def upsert_all(gamedata_dir, db: Session):
    """
    Given the path to the directory where gamedata files are, upserts the necessary rows into worlds, districts,
    and plotinfo.
    """
    worlds = generate_worlds(gamedata_dir)
    districts = generate_districts(gamedata_dir)
    plotinfo = generate_plotinfo(districts, gamedata_dir)
    for world in worlds:
        db.merge(world)
    for district in districts:
        db.merge(district)
    for pi in plotinfo:
        db.merge(pi)
    db.commit()


# ==== Transient Gen ====
def generate_worlds(gamedata_dir):
    datacenters = {}
    for datacenter in read_csv(os.path.join(gamedata_dir, "WorldDCGroupType.csv")):
        datacenters[datacenter["#"]] = datacenter

    worlds = []
    for world in read_csv(os.path.join(gamedata_dir, "World.csv")):
        if world["IsPublic"] != "True" or world["DataCenter"] == "0":
            continue
        datacenter_name = datacenters[world["DataCenter"]]["Name"]
        db_world = models.World(
            id=int(world["#"]),
            name=world["Name"],
            datacenter_id=int(world["DataCenter"]),
            datacenter_name=datacenter_name,
        )
        worlds.append(db_world)
    return worlds


def generate_districts(gamedata_dir):
    """
    As of patch 5.35, the districts have the following useful properties:
    339/s1h1/mist -> landset 0
    340/f1h1/lav beds -> landset 1
    341/w1h1/goblet -> landset 2
    641/e1h1/shiro -> landset 3
    886/r1h1/empyreum -> landset 4
    territoryintendeduse=13
    resident=78
    """
    territory_to_land_set_map = {
        339: 0,  # Mist
        340: 1,  # Lavender Beds
        341: 2,  # Goblet
        641: 3,  # Shirogane
        979: 4,  # Empyreum
    }
    place_names = {int(p["#"]): p["Name"] for p in read_csv(os.path.join(gamedata_dir, "PlaceName.csv"))}

    def is_housing(t):
        # any of these should work below
        return int(t["TerritoryIntendedUse"]) == 13
        # return int(t['Resident']) == 78
        # return '/hou/' in t['Bg']
        # return int(t['#']) in territory_to_land_set_map

    districts = []
    for territory in read_csv(os.path.join(gamedata_dir, "TerritoryType.csv")):
        if not is_housing(territory):
            continue
        if (tid := int(territory["#"])) not in territory_to_land_set_map:
            log.warning(f"TerritoryType ID {tid} not found in map! Skipping...")
            continue
        name = place_names[int(territory["PlaceName"])]
        db_district = models.District(id=tid, name=name, land_set_id=territory_to_land_set_map[tid])
        districts.append(db_district)
    return districts


def generate_plotinfo(districts, gamedata_dir):
    plotinfo = []
    landsets = {int(ls["#"]): ls for ls in read_csv(os.path.join(gamedata_dir, "HousingLandSet.csv"))}
    for district in districts:
        landset = landsets[district.land_set_id]
        for plotnum in range(PLOTS_PER_WARD):
            db_plotinfo = models.PlotInfo(
                territory_type_id=district.id,
                plot_number=plotnum,
                house_size=int(landset[f"PlotSize[{plotnum}]"]),
                house_base_price=int(landset[f"InitialPrice[{plotnum}]"]),
            )
            plotinfo.append(db_plotinfo)
    return plotinfo


# ==== utils ====
def read_csv(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        # skip header rows
        next(csvfile)
        headers = next(csvfile).strip().split(",")
        next(csvfile)

        for row in csv.DictReader(csvfile, fieldnames=headers):
            yield row
