"""
Used to preview the rows that will be upserted upon server start.
"""
import os

from paissadb import gamedata

if __name__ == '__main__':
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gamedata")
    for world in gamedata.generate_worlds(d):
        print(world.__dict__)
