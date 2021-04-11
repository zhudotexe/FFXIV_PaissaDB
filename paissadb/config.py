import os

GAMEDATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../gamedata")
JWT_SECRET_PAISSAHOUSE = os.getenv("JWT_SECRET_PAISSAHOUSE")
JWT_ISSUER = 'PaissaDB'
JWT_AUDIENCES = ['PaissaHouse']
