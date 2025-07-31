from pymongo import MongoClient
from config import Config

client = MongoClient(Config.MONGO_URI)
db = client.get_database("telegram_forwarder")

# You can define your collections here
users_collection = db.get_collection("users")
sessions_collection = db.get_collection("sessions")
rules_collection = db.get_collection("rules")
authorized_users_collection = db.get_collection("authorized_users")
blocked_content_collection = db.get_collection("blocked_content")