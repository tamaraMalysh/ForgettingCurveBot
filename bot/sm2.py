"""
SM-2 Spaced Repetition Algorithm (SuperMemo 2)

This is the same algorithm used by Anki.
Reference: https://www.supermemo.com/en/archives1990-2015/english/ol/sm2

Enhanced with adaptive intervals based on:
- Problem acceptance rate (difficulty)
- Algorithm rarity (how often used in practice)
"""
from datetime import datetime, timedelta
from bot.models import Card, Review
from bot.algorithm_config import (
    ALGORITHM_RARITY,
    DIFFICULTY_MULTIPLIERS,
    get_difficulty_from_acceptance_rate,
    get_rarity_category,
)


class SM2Algorithm:
    """Implements the SM-2 spaced repetition algorithm."""

    # Rating constants
    AGAIN = 0  # Completely forgot
    HARD = 1  # Remembered with difficulty
    GOOD = 2  # Remembered with some effort
    EASY = 3  # Remembered easily

    @staticmethod
    def calculate_difficulty_multiplier(card: Card) -> float:
        """
        Calculate adaptive interval multiplier based on problem difficulty and algorithm rarity.

        The multiplier adjusts review intervals based on:
        1. Acceptance rate (lower = harder = more frequent reviews)
        2. Algorithm rarity (rare algorithms like graphs need more practice)

        Args:
            card: The flashcard being reviewed

        Returns:
            float: Multiplier for interval (< 1.0 = more frequent, > 1.0 = less frequent)
        """
        multiplier = 1.0

        # 1. Apply acceptance rate multiplier (problem difficulty)
        if card.acceptance_rate is not None:
            difficulty = get_difficulty_from_acceptance_rate(card.acceptance_rate)
            multiplier *= DIFFICULTY_MULTIPLIERS[difficulty]["multiplier"]

        # 2. Apply algorithm rarity multiplier
        if card.tags:
            rarity = get_rarity_category(card.tags)
            multiplier *= ALGORITHM_RARITY[rarity]["interval_multiplier"]

        # Store the calculated multiplier in the card for analytics
        card.difficulty_multiplier = multiplier

        return multiplier

    @staticmethod
    def calculate_next_review(
        card: Card, rating: int, current_time: datetime = None
    ) -> tuple[Card, Review]:
        """
        Calculate the next review date and update card based on rating.

        Args:
            card: The flashcard being reviewed
            rating: User's rating (0=Again, 1=Hard, 2=Good, 3=Easy)
            current_time: Current datetime (defaults to now)

        Returns:
            tuple: (updated_card, review_record)
        """
        if current_time is None:
            current_time = datetime.now()

        # Store original values for review record
        ef_before = card.easiness_factor
        interval_before = card.interval

        # SM-2 algorithm
        if rating == SM2Algorithm.AGAIN:
            # Reset the card
            card.repetitions = 0
            card.interval = 0
        else:
            # Update easiness factor
            # EF' = EF + (0.1 - (3 - rating) * (0.08 + (3 - rating) * 0.02))
            quality = rating  # 1, 2, or 3
            card.easiness_factor = max(
                1.3,  # Minimum EF
                card.easiness_factor
                + (0.1 - (3 - quality) * (0.08 + (3 - quality) * 0.02)),
            )

            # Update interval based on repetition number
            if card.repetitions == 0:
                card.interval = 1  # 1 day
            elif card.repetitions == 1:
                card.interval = 6  # 6 days
            else:
                # I(n) = I(n-1) * EF
                card.interval = round(card.interval * card.easiness_factor)

            # Modify interval based on rating
            if rating == SM2Algorithm.HARD:
                # Make interval 1.2x shorter for "Hard"
                card.interval = max(1, round(card.interval * 0.85))
            elif rating == SM2Algorithm.EASY:
                # Make interval 1.3x longer for "Easy"
                card.interval = round(card.interval * 1.3)

            card.repetitions += 1

        # Apply adaptive difficulty multiplier (based on acceptance rate + algorithm rarity)
        # This happens after rating-based adjustment but before setting the date
        if card.interval > 0:  # Only apply to non-zero intervals
            difficulty_mult = SM2Algorithm.calculate_difficulty_multiplier(card)
            card.interval = max(1, round(card.interval * difficulty_mult))

        # Calculate next review date
        card.next_review_date = current_time + timedelta(days=card.interval)
        card.last_reviewed_at = current_time

        # Create review record
        review = Review(
            user_id=card.user_id,
            card_name=card.name,
            rating=rating,
            reviewed_at=current_time,
            easiness_factor_before=ef_before,
            easiness_factor_after=card.easiness_factor,
            interval_before=interval_before,
            interval_after=card.interval,
        )

        return card, review

    @staticmethod
    def get_interval_preview(card: Card) -> dict[str, int]:
        """
        Get preview of intervals for each rating option.

        Args:
            card: The flashcard to preview

        Returns:
            dict: Intervals in days for each rating
        """
        intervals = {}

        for rating_name, rating_value in [
            ("again", SM2Algorithm.AGAIN),
            ("hard", SM2Algorithm.HARD),
            ("good", SM2Algorithm.GOOD),
            ("easy", SM2Algorithm.EASY),
        ]:
            # Create a temporary copy to calculate
            temp_card = Card(
                user_id=card.user_id,
                chat_id=card.chat_id,
                name=card.name,
                easiness_factor=card.easiness_factor,
                interval=card.interval,
                repetitions=card.repetitions,
            )
            updated_card, _ = SM2Algorithm.calculate_next_review(
                temp_card, rating_value
            )
            intervals[rating_name] = updated_card.interval

        return intervals
