import os
import urllib.parse

GAMEDATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../gamedata")
JWT_ISSUER = 'PaissaDB'
JWT_AUDIENCES = ['PaissaHouse']

JWT_SECRET_PAISSAHOUSE = os.getenv("JWT_SECRET_PAISSAHOUSE")
DB_URI = os.getenv("DB_URI", "sqlite:///./sql_app.db")
DB_TYPE = urllib.parse.urlparse(DB_URI).scheme.split('+')[0]
WS_BACKEND_URI = os.getenv("WS_BACKEND_URI", "memory://")
