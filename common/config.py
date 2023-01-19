import os
import urllib.parse

GAMEDATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../gamedata")
SQLITE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")
JWT_ISSUER = "PaissaDB"
JWT_AUDIENCES = ["PaissaHouse"]

JWT_SECRET_PAISSAHOUSE = os.getenv("JWT_SECRET_PAISSAHOUSE")
DB_URI = os.getenv("DB_URI", f"sqlite:///{SQLITE_DIR}sql_app.db")
DB_TYPE = urllib.parse.urlparse(DB_URI).scheme.split("+")[0]
REDIS_URI = os.getenv("REDIS_URI", "redis://localhost")
SENTRY_DSN = os.getenv("SENTRY_DSN")
SENTRY_ENV = os.getenv("SENTRY_ENV", "development")

LOGLEVEL = os.getenv("LOGLEVEL", "INFO")
EMERGENCY_LOAD_PREVENTION = True
