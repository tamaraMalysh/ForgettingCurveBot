from datetime import datetime
from typing import Optional
from pymongo import MongoClient
from bot.config import Config
from bot.models import Card, Review
from aiogram.types import Message


DEFAULT_LANGUAGE = "en"
DEFAULT_REMINDER_TIME = "12:00"
DEFAULT_STATE = "start"
DEFAULT_STATUS = "active"

client = MongoClient(
    Config.MONGODB_URI,
    username=Config.MONGO_INITDB_ROOT_USERNAME,
    password=Config.MONGO_INITDB_ROOT_PASSWORD,
)
db = client["spaced_repetition_db"]
users_collection = db["users"]
cards_collection = db["cards"]
reviews_collection = db["reviews"]


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


# ==============================================================================
# Card Management Functions
# ==============================================================================


def add_card(card: Card) -> bool:
    """
    Add a new flashcard to the database.

    Args:
        card: Card object to add

    Returns:
        bool: True if successful
    """
    try:
        cards_collection.insert_one(card.to_dict())
        return True
    except Exception as e:
        print(f"Error adding card: {e}")
        return False


def get_card(user_id: int, card_name: str) -> Optional[Card]:
    """
    Get a specific card by name for a user.

    Args:
        user_id: User's ID
        card_name: Name of the card

    Returns:
        Card object or None if not found
    """
    doc = cards_collection.find_one({"user_id": user_id, "name": card_name})
    if doc:
        return Card.from_dict(doc)
    return None


def update_card(card: Card) -> bool:
    """
    Update an existing card in the database.

    Args:
        card: Card object with updated fields

    Returns:
        bool: True if successful
    """
    try:
        result = cards_collection.update_one({"user_id": card.user_id, "name": card.name}, {"$set": card.to_dict()})
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating card: {e}")
        return False


def delete_card(user_id: int, card_name: str) -> bool:
    """
    Delete a card from the database.

    Args:
        user_id: User's ID
        card_name: Name of the card to delete

    Returns:
        bool: True if successful
    """
    try:
        result = cards_collection.delete_one({"user_id": user_id, "name": card_name})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting card: {e}")
        return False


def get_all_cards(user_id: int) -> list[Card]:
    """
    Get all cards for a user.

    Args:
        user_id: User's ID

    Returns:
        List of Card objects
    """
    docs = cards_collection.find({"user_id": user_id})
    return [Card.from_dict(doc) for doc in docs]


def get_due_cards(user_id: int, current_time: datetime = None) -> list[Card]:
    """
    Get all cards due for review.

    Args:
        user_id: User's ID
        current_time: Current datetime (defaults to now)

    Returns:
        List of Card objects due for review
    """
    if current_time is None:
        current_time = datetime.now()

    docs = cards_collection.find({"user_id": user_id, "next_review_date": {"$lte": current_time}}).sort(
        "next_review_date", 1
    )  # Sort by oldest first

    return [Card.from_dict(doc) for doc in docs]


def get_cards_count(user_id: int) -> dict:
    """
    Get card statistics for a user.

    Args:
        user_id: User's ID

    Returns:
        dict with counts: total, due_today, new (never reviewed)
    """
    now = datetime.now()
    total = cards_collection.count_documents({"user_id": user_id})
    due_today = cards_collection.count_documents({"user_id": user_id, "next_review_date": {"$lte": now}})
    new = cards_collection.count_documents({"user_id": user_id, "repetitions": 0})

    return {"total": total, "due_today": due_today, "new": new}


# ==============================================================================
# Review Management Functions
# ==============================================================================


def add_review(review: Review) -> bool:
    """
    Add a review record to the database.

    Args:
        review: Review object to add

    Returns:
        bool: True if successful
    """
    try:
        reviews_collection.insert_one(review.to_dict())
        return True
    except Exception as e:
        print(f"Error adding review: {e}")
        return False


def get_review_stats(user_id: int, days: int = 30) -> dict:
    """
    Get review statistics for a user.

    Args:
        user_id: User's ID
        days: Number of days to look back (default 30)

    Returns:
        dict with review statistics
    """
    from datetime import timedelta

    start_date = datetime.now() - timedelta(days=days)

    # Get all reviews in time period
    reviews = list(reviews_collection.find({"user_id": user_id, "reviewed_at": {"$gte": start_date}}))

    if not reviews:
        return {
            "total_reviews": 0,
            "again_count": 0,
            "hard_count": 0,
            "good_count": 0,
            "easy_count": 0,
            "retention_rate": 0.0,
        }

    total = len(reviews)
    again_count = sum(1 for r in reviews if r["rating"] == 0)
    hard_count = sum(1 for r in reviews if r["rating"] == 1)
    good_count = sum(1 for r in reviews if r["rating"] == 2)
    easy_count = sum(1 for r in reviews if r["rating"] == 3)

    # Retention rate: percentage of reviews that weren't "Again"
    retention_rate = ((total - again_count) / total * 100) if total > 0 else 0.0

    return {
        "total_reviews": total,
        "again_count": again_count,
        "hard_count": hard_count,
        "good_count": good_count,
        "easy_count": easy_count,
        "retention_rate": round(retention_rate, 1),
    }
