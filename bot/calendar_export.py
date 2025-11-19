"""
Calendar export functionality for spaced repetition reviews.
Generates .ics files that can be imported into Google Calendar, Apple Calendar, etc.
"""
from datetime import datetime, timedelta
from typing import List
from bot.models import Card


def generate_ical(cards: List[Card], user_id: int) -> str:
    """
    Generate iCalendar (.ics) format string for card reviews.

    Args:
        cards: List of Card objects
        user_id: User's ID

    Returns:
        iCalendar format string
    """
    ical_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Spaced Repetition Bot//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Spaced Repetition Reviews",
        "X-WR-TIMEZONE:UTC",
    ]

    for card in cards:
        event = _create_event(card)
        ical_lines.extend(event)

    ical_lines.append("END:VCALENDAR")

    return "\r\n".join(ical_lines)


def _create_event(card: Card) -> List[str]:
    """
    Create an iCalendar event for a card review.

    Args:
        card: Card object

    Returns:
        List of iCalendar event lines
    """
    # Format datetime for iCalendar (YYYYMMDDTHHMMSSZ)
    dtstart = card.next_review_date.strftime("%Y%m%dT%H%M%SZ")

    # Event lasts 30 minutes by default
    dtend = (card.next_review_date + timedelta(minutes=30)).strftime("%Y%m%dT%H%M%SZ")

    # Create unique ID
    uid = f"{card.name.replace(' ', '-')}-{card.user_id}-{int(card.next_review_date.timestamp())}@spacedrepbot"

    # Current timestamp for DTSTAMP
    dtstamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")

    # Build description
    description = f"Review flashcard: {card.name}"
    if card.tags:
        description += f"\\nTags: {', '.join(card.tags)}"
    if card.notes:
        # Escape special characters
        notes_escaped = card.notes.replace("\n", "\\n").replace(",", "\\,")
        description += f"\\n\\nNotes: {notes_escaped[:200]}"

    event_lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:Review: {card.name}",
        f"DESCRIPTION:{description}",
        "STATUS:CONFIRMED",
        "TRANSP:OPAQUE",
        # Add reminder 30 minutes before
        "BEGIN:VALARM",
        "TRIGGER:-PT30M",
        "ACTION:DISPLAY",
        f"DESCRIPTION:Time to review: {card.name}",
        "END:VALARM",
        "END:VEVENT",
    ]

    return event_lines


def get_upcoming_reviews(cards: List[Card], days: int = 30) -> List[Card]:
    """
    Filter cards to only include those due within the next N days.

    Args:
        cards: List of all cards
        days: Number of days to look ahead (default 30)

    Returns:
        List of cards due within the timeframe
    """
    cutoff_date = datetime.now() + timedelta(days=days)
    upcoming = [card for card in cards if card.next_review_date <= cutoff_date]

    # Sort by review date
    upcoming.sort(key=lambda c: c.next_review_date)

    return upcoming
