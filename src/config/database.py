import env
from pymongo import MongoClient

client = MongoClient(env.DB_CONNECTION_STRING)

db = client.smc_db

sites_collection = db["sites_collection"]
reports_collection = db["reports_collection"]
