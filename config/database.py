from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

client = MongoClient(os.getenv("DB_CONNECTION_STRING"))

db = client.smc_db

collection_name = db["sites_collection"]