from pymongo import MongoClient
from bot.config import Config
from aiogram.types import Message


DEFAULT_LANGUAGE = "ru"
DEFAULT_REMINDER_TIME = "12:00"
DEFAULT_STATE = "start"
DEFAULT_STATUS = "active"

client = MongoClient(
    Config.MONGODB_URI,
    username=Config.MONGO_INITDB_ROOT_USERNAME,
    password=Config.MONGO_INITDB_ROOT_PASSWORD,
)
db = client["telegram_bot_db"]
users_collection = db["users"]
tasks_collection = db["tasks"]
archived_tasks_collection = db["archived_tasks"]


def add_user(user_id: int, message: Message):
    user = {
        "user_id": user_id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "chat_id": message.chat.id,
        "state": DEFAULT_STATE,
        "status": DEFAULT_STATUS,
        "language": DEFAULT_LANGUAGE,
    }
    users_collection.insert_one(user)


def update_user(user_id: int, message: Message):
    if not user_id:
        return None

    try:
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
    except AttributeError:
        # need logging
        return None
    
    user = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "chat_id": message.chat.id,
        "state": DEFAULT_STATE,
        "status": DEFAULT_STATUS,
        "language": DEFAULT_LANGUAGE,
        "reminder": "off",
        "reminder_time": DEFAULT_REMINDER_TIME,
    }
    users_collection.update_one({"user_id": user_id}, {"$set": user})
    return user


def get_user(user_id: int) -> dict:
    return users_collection.find_one({"user_id": user_id})
