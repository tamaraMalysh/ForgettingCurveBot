"""
Data models for the spaced repetition system.
"""
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class Card:
    """Represents a flashcard for spaced repetition."""

    user_id: int
    chat_id: int
    name: str  # Problem/algorithm name
    code: Optional[str] = None  # Code solution
    notes: Optional[str] = None  # Explanation/intuition
    links: Optional[list[str]] = None  # URLs to resources
    tags: Optional[list[str]] = None  # e.g., ["graph", "bfs", "medium"]

    # SM-2 algorithm fields
    easiness_factor: float = 2.5  # Default EF
    interval: int = 0  # Days until next review
    repetitions: int = 0  # Number of successful reviews
    next_review_date: datetime = None  # When to review next

    # Adaptive scheduling fields
    acceptance_rate: Optional[float] = None  # LeetCode acceptance rate (0.0-1.0)
    difficulty_multiplier: float = 1.0  # Calculated from acceptance_rate + tags

    # Metadata
    created_at: datetime = None
    last_reviewed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.next_review_date is None:
            self.next_review_date = datetime.now()
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.links is None:
            self.links = []
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> dict:
        """Convert card to dictionary for MongoDB storage."""
        return {
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "name": self.name,
            "code": self.code,
            "notes": self.notes,
            "links": self.links,
            "tags": self.tags,
            "easiness_factor": self.easiness_factor,
            "interval": self.interval,
            "repetitions": self.repetitions,
            "next_review_date": self.next_review_date,
            "acceptance_rate": self.acceptance_rate,
            "difficulty_multiplier": self.difficulty_multiplier,
            "created_at": self.created_at,
            "last_reviewed_at": self.last_reviewed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Card":
        """Create card from MongoDB document."""
        return cls(
            user_id=data["user_id"],
            chat_id=data["chat_id"],
            name=data["name"],
            code=data.get("code"),
            notes=data.get("notes"),
            links=data.get("links", []),
            tags=data.get("tags", []),
            easiness_factor=data.get("easiness_factor", 2.5),
            interval=data.get("interval", 0),
            repetitions=data.get("repetitions", 0),
            next_review_date=data.get("next_review_date", datetime.now()),
            acceptance_rate=data.get("acceptance_rate"),
            difficulty_multiplier=data.get("difficulty_multiplier", 1.0),
            created_at=data.get("created_at", datetime.now()),
            last_reviewed_at=data.get("last_reviewed_at"),
        )


@dataclass
class Review:
    """Represents a review session for a card."""

    user_id: int
    card_name: str
    rating: int  # 0=Again, 1=Hard, 2=Good, 3=Easy
    reviewed_at: datetime = None

    # Before/after SM-2 values for analytics
    easiness_factor_before: float = 2.5
    easiness_factor_after: float = 2.5
    interval_before: int = 0
    interval_after: int = 0

    def __post_init__(self):
        if self.reviewed_at is None:
            self.reviewed_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert review to dictionary for MongoDB storage."""
        return {
            "user_id": self.user_id,
            "card_name": self.card_name,
            "rating": self.rating,
            "reviewed_at": self.reviewed_at,
            "easiness_factor_before": self.easiness_factor_before,
            "easiness_factor_after": self.easiness_factor_after,
            "interval_before": self.interval_before,
            "interval_after": self.interval_after,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Review":
        """Create review from MongoDB document."""
        return cls(
            user_id=data["user_id"],
            card_name=data["card_name"],
            rating=data["rating"],
            reviewed_at=data.get("reviewed_at", datetime.now()),
            easiness_factor_before=data.get("easiness_factor_before", 2.5),
            easiness_factor_after=data.get("easiness_factor_after", 2.5),
            interval_before=data.get("interval_before", 0),
            interval_after=data.get("interval_after", 0),
        )
