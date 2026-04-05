from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["asteroidtrack"]

users_collection = db["users"]
observations_collection = db["observations"]