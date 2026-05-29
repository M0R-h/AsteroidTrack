from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["asteroidtrack"]

users_collection = db["users"]
observations_collection = db["observations"]
orbital_elements_collection = db["orbital_elements"]
predictions_collection = db["predictions"]
processing_logs_collection = db["processing_logs"]