"""
Spaced Repetition Telegram Bot - Anki-style flashcard system with LLM integration.
"""
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import Config
from bot.models import Card
from bot.sm2 import SM2Algorithm
from bot.llm_service import ollama_service
from bot.calendar_export import generate_ical, get_upcoming_reviews
import bot.db_service as db


# Initialize bot
bot = Bot(token=Config.TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# States for conversation flow
class CardCreation(StatesGroup):
    waiting_for_details = State()


class ReviewSession(StatesGroup):
    reviewing = State()
    asking_question = State()


# User session data for review queue
user_review_queues = {}


# ==============================================================================
# Start and Help Commands
# ==============================================================================


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Welcome message."""
    text = """🎴 **Welcome to Spaced Repetition Bot!**

I'm like Anki, but in Telegram. I help you remember algorithms and data structures using spaced repetition.

**Quick Start:**
Just send me a message like:
• "add Two Sum problem, I solved it using hashmap"
• "add Binary Search algorithm"
• Or send code with ```code blocks```

**Commands:**
/review - Start reviewing due cards
/cards - List all your flashcards
/stats - View your learning statistics
/help - Show detailed help

The bot uses AI to parse your messages and organize information!"""

    await message.reply(text, parse_mode="Markdown")


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Show help information."""
    text = """📚 **How to Use This Bot**

**Adding Cards (Natural Language):**
Just type naturally! Examples:
• "add Two Sum, uses hashmap for O(n)"
• "Create card for DFS, here's my code: ```python..."
• "Binary Search algorithm, divide and conquer"
• "add Kruskal's Algorithm, 50% acceptance" (include acceptance rate for adaptive scheduling)

**Reviewing Cards:**
1. Use /review to start a review session
2. Read the question (problem name)
3. Click "Show Answer" to reveal solution
4. Rate yourself:
   • Again - Forgot completely (<1 day)
   • Hard - Difficult to recall (~1 day)
   • Good - Recalled with effort (~4 days)
   • Easy - Recalled easily (~7+ days)

**During Review:**
• You can ask questions! Just type your question and I'll help explain.

**Other Commands:**
/cards - See all your cards and due dates
/delete <name> - Remove a card
/stats - View statistics (retention rate, reviews, etc.)
/export - Export calendar of upcoming reviews

**Card Content:**
Each card can store:
• Problem/algorithm name
• Code solution
• Notes and explanations
• Links to resources
• Auto-generated tags

The AI will help organize and tag everything automatically!"""

    await message.reply(text, parse_mode="Markdown")


# ==============================================================================
# Card Creation (Natural Language + LLM)
# ==============================================================================


@dp.message(Command("add"))
async def cmd_add_explicit(message: types.Message):
    """Handle explicit /add command."""
    # Remove the /add prefix and process as natural language
    text = message.text.replace("/add", "", 1).strip()
    await handle_card_creation(message, text)


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_natural_language(message: types.Message, state: FSMContext):
    """Handle natural language messages for card creation."""
    current_state = await state.get_state()

    # If in review session, handle as question
    if current_state == ReviewSession.asking_question:
        await handle_review_question(message, state)
        return

    # Otherwise, treat as card creation
    await handle_card_creation(message, message.text)


async def handle_card_creation(message: types.Message, text: str):
    """
    Parse natural language and create a flashcard.

    Args:
        message: Telegram message
        text: Text to parse
    """
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Show typing indicator
    await bot.send_chat_action(chat_id, "typing")

    # Parse with LLM
    parsed = ollama_service.parse_card_command(text)

    if not parsed.get("name"):
        await message.reply(
            "❌ I couldn't find a card name. Please include a problem or algorithm name.\n\n"
            "Example: 'add Two Sum problem, uses hashmap'"
        )
        return

    # Check if card already exists
    existing_card = db.get_card(user_id, parsed["name"])
    if existing_card:
        await message.reply(f"⚠️ Card '{parsed['name']}' already exists. Use /delete to remove it first.")
        return

    # Generate content if needed
    if not parsed.get("notes") or not parsed.get("tags"):
        generated = ollama_service.generate_flashcard_content(
            parsed["name"], parsed.get("code")
        )
        if not parsed.get("notes"):
            parsed["notes"] = generated.get("notes", "")
        if not parsed.get("tags"):
            parsed["tags"] = generated.get("tags", [])

    # Create card
    card = Card(
        user_id=user_id,
        chat_id=chat_id,
        name=parsed["name"],
        code=parsed.get("code"),
        notes=parsed.get("notes"),
        links=parsed.get("links", []),
        tags=parsed.get("tags", []),
        acceptance_rate=parsed.get("acceptance_rate"),
    )

    # Save to database
    success = db.add_card(card)

    if success:
        tags_str = ", ".join(card.tags) if card.tags else "none"
        response = f"""✅ **Card Created!**

📝 **{card.name}**
🏷️ Tags: {tags_str}
📅 Next review: {card.next_review_date.strftime('%Y-%m-%d %H:%M')}"""

        # Show acceptance rate if provided
        if card.acceptance_rate is not None:
            response += f"\n📊 Acceptance rate: {card.acceptance_rate:.1%}"

        # Show difficulty multiplier if different from 1.0
        if card.difficulty_multiplier != 1.0:
            if card.difficulty_multiplier < 1.0:
                response += f"\n⚡ This card will be reviewed more frequently (×{card.difficulty_multiplier:.2f})"
            else:
                response += f"\n😊 This card will be reviewed less frequently (×{card.difficulty_multiplier:.2f})"

        response += "\n\nThe card is ready for review!"

        if card.notes:
            response += f"\n\n💡 Notes: {card.notes[:100]}..."

        await message.reply(response, parse_mode="Markdown")
    else:
        await message.reply("❌ Failed to create card. Please try again.")


# ==============================================================================
# Review Session (Anki-style)
# ==============================================================================


@dp.message(Command("review"))
async def cmd_review(message: types.Message, state: FSMContext):
    """Start a review session."""
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Get due cards
    due_cards = db.get_due_cards(user_id)

    if not due_cards:
        stats = db.get_cards_count(user_id)
        await message.reply(
            f"🎉 No cards due for review!\n\n"
            f"📊 Total cards: {stats['total']}\n"
            f"📅 Come back later when cards are due."
        )
        return

    # Store queue in session
    user_review_queues[user_id] = due_cards
    await state.set_state(ReviewSession.reviewing)

    # Show first card
    await show_review_card(chat_id, user_id, state)


async def show_review_card(chat_id: int, user_id: int, state: FSMContext):
    """Show the current card in review queue."""
    queue = user_review_queues.get(user_id, [])

    if not queue:
        # Session complete
        await finish_review_session(chat_id, user_id, state)
        return

    card = queue[0]

    # Store current card in state
    await state.update_data(current_card=card.name)

    # Create inline keyboard with "Show Answer" button
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👁️ Show Answer", callback_data=f"show_answer:{card.name}")],
            [InlineKeyboardButton(text="💬 Ask Question", callback_data=f"ask_question:{card.name}")],
        ]
    )

    tags_str = ", ".join(card.tags) if card.tags else "none"
    remaining = len(queue)

    text = f"""🎴 **Review Time!**

**Question:** {card.name}

🏷️ Tags: {tags_str}
📅 Last reviewed: {card.last_reviewed_at.strftime('%Y-%m-%d') if card.last_reviewed_at else 'Never'}

🔢 Remaining: {remaining} card(s)

Think about the solution, then click "Show Answer"."""

    await bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("show_answer:"))
async def callback_show_answer(callback: CallbackQuery, state: FSMContext):
    """Show the answer and rating buttons."""
    card_name = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id

    card = db.get_card(user_id, card_name)
    if not card:
        await callback.answer("Card not found!")
        return

    # Get interval preview
    intervals = SM2Algorithm.get_interval_preview(card)

    # Create rating keyboard
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Again (<1d)", callback_data=f"rate:0:{card_name}"
                ),
                InlineKeyboardButton(
                    text=f"Hard (~{intervals['hard']}d)", callback_data=f"rate:1:{card_name}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"Good (~{intervals['good']}d)", callback_data=f"rate:2:{card_name}"
                ),
                InlineKeyboardButton(
                    text=f"Easy (~{intervals['easy']}d)", callback_data=f"rate:3:{card_name}"
                ),
            ],
        ]
    )

    # Build answer text
    answer_text = f"""**Answer:**

{card.name}

"""

    if card.code:
        answer_text += f"**Code:**\n```\n{card.code}\n```\n\n"

    if card.notes:
        answer_text += f"**Notes:**\n{card.notes}\n\n"

    if card.links:
        links_text = "\n".join(f"• {link}" for link in card.links)
        answer_text += f"**Links:**\n{links_text}\n\n"

    answer_text += "**How well did you remember?**"

    await callback.message.edit_text(answer_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data.startswith("ask_question:"))
async def callback_ask_question(callback: CallbackQuery, state: FSMContext):
    """Allow user to ask a question about the card."""
    card_name = callback.data.split(":", 1)[1]
    await state.update_data(current_card=card_name)
    await state.set_state(ReviewSession.asking_question)

    await callback.message.reply(
        "💬 Ask your question about this card. I'll help explain!\n\n"
        "(Send your question as a message, or type 'cancel' to go back)"
    )
    await callback.answer()


async def handle_review_question(message: types.Message, state: FSMContext):
    """Answer user's question during review."""
    if message.text.lower() == "cancel":
        await state.set_state(ReviewSession.reviewing)
        await message.reply("Returning to review...")
        return

    data = await state.get_data()
    card_name = data.get("current_card")

    if not card_name:
        await message.reply("Error: No active card.")
        return

    user_id = message.from_user.id
    card = db.get_card(user_id, card_name)

    if not card:
        await message.reply("Error: Card not found.")
        return

    # Get answer from LLM
    await bot.send_chat_action(message.chat.id, "typing")
    answer = ollama_service.answer_question(
        card.name, card.code or "", card.notes or "", message.text
    )

    await message.reply(f"💡 **Answer:**\n\n{answer}", parse_mode="Markdown")
    await state.set_state(ReviewSession.reviewing)


@dp.callback_query(F.data.startswith("rate:"))
async def callback_rate_card(callback: CallbackQuery, state: FSMContext):
    """Handle card rating and update with SM-2 algorithm."""
    parts = callback.data.split(":")
    rating = int(parts[1])
    card_name = parts[2]

    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    # Get card
    card = db.get_card(user_id, card_name)
    if not card:
        await callback.answer("Card not found!")
        return

    # Calculate next review with SM-2
    updated_card, review = SM2Algorithm.calculate_next_review(card, rating)

    # Save updates
    db.update_card(updated_card)
    db.add_review(review)

    # Remove from queue
    queue = user_review_queues.get(user_id, [])
    if queue and queue[0].name == card_name:
        queue.pop(0)

    # Show feedback
    rating_names = ["Again", "Hard", "Good", "Easy"]
    await callback.message.edit_text(
        f"✅ Rated as **{rating_names[rating]}**\n\n"
        f"📅 Next review: {updated_card.next_review_date.strftime('%Y-%m-%d')}\n"
        f"⏱️ Interval: {updated_card.interval} day(s)",
        parse_mode="Markdown",
    )
    await callback.answer()

    # Show next card
    await asyncio.sleep(1)
    await show_review_card(chat_id, user_id, state)


async def finish_review_session(chat_id: int, user_id: int, state: FSMContext):
    """Finish the review session and show stats."""
    await state.clear()

    if user_id in user_review_queues:
        del user_review_queues[user_id]

    stats = db.get_review_stats(user_id, days=1)

    text = f"""🎉 **Review Session Complete!**

📊 **Today's Stats:**
• Reviews: {stats['total_reviews']}
• Again: {stats['again_count']}
• Hard: {stats['hard_count']}
• Good: {stats['good_count']}
• Easy: {stats['easy_count']}
• Retention: {stats['retention_rate']}%

Great work! Come back tomorrow for more reviews."""

    await bot.send_message(chat_id, text, parse_mode="Markdown")


# ==============================================================================
# Card Management Commands
# ==============================================================================


@dp.message(Command("cards"))
async def cmd_cards(message: types.Message):
    """List all user's cards."""
    user_id = message.from_user.id
    cards = db.get_all_cards(user_id)

    if not cards:
        await message.reply("📭 You don't have any cards yet.\n\nCreate one by sending a message like:\n'add Two Sum problem'")
        return

    # Sort by next review date
    cards.sort(key=lambda c: c.next_review_date)

    text = "📚 **Your Flashcards:**\n\n"

    for card in cards:
        due_date = card.next_review_date.strftime("%Y-%m-%d")
        is_due = card.next_review_date <= datetime.now()
        status = "🔴 DUE" if is_due else "✅"

        text += f"{status} **{card.name}**\n"
        text += f"   📅 Next: {due_date} | 🔁 Reviews: {card.repetitions}\n\n"

    stats = db.get_cards_count(user_id)
    text += f"\n📊 Total: {stats['total']} | Due: {stats['due_today']} | New: {stats['new']}"

    await message.reply(text, parse_mode="Markdown")


@dp.message(Command("delete"))
async def cmd_delete(message: types.Message):
    """Delete a card."""
    user_id = message.from_user.id
    args = message.text.split(" ", 1)

    if len(args) < 2:
        await message.reply("Usage: /delete <card name>\n\nExample: /delete Two Sum")
        return

    card_name = args[1].strip()
    success = db.delete_card(user_id, card_name)

    if success:
        await message.reply(f"✅ Card '{card_name}' has been deleted.")
    else:
        await message.reply(f"❌ Card '{card_name}' not found.")


# ==============================================================================
# Statistics
# ==============================================================================


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Show learning statistics."""
    user_id = message.from_user.id

    # Card stats
    card_stats = db.get_cards_count(user_id)

    # Review stats (last 30 days)
    review_stats = db.get_review_stats(user_id, days=30)

    text = f"""📊 **Your Learning Statistics**

**Cards:**
• Total cards: {card_stats['total']}
• Due today: {card_stats['due_today']}
• New (never reviewed): {card_stats['new']}

**Reviews (Last 30 days):**
• Total reviews: {review_stats['total_reviews']}
• Again: {review_stats['again_count']}
• Hard: {review_stats['hard_count']}
• Good: {review_stats['good_count']}
• Easy: {review_stats['easy_count']}
• **Retention rate: {review_stats['retention_rate']}%**

Keep up the great work! 🚀"""

    await message.reply(text, parse_mode="Markdown")


# ==============================================================================
# Calendar Export
# ==============================================================================


@dp.message(Command("export"))
async def cmd_export(message: types.Message):
    """Export upcoming reviews as iCalendar file."""
    user_id = message.from_user.id

    # Get all user's cards
    all_cards = db.get_all_cards(user_id)

    if not all_cards:
        await message.reply("📭 You don't have any cards to export.")
        return

    # Filter to upcoming reviews (next 30 days)
    upcoming = get_upcoming_reviews(all_cards, days=30)

    if not upcoming:
        await message.reply(
            "📅 No reviews scheduled in the next 30 days.\n\n"
            "All your cards are scheduled further in the future."
        )
        return

    # Generate iCalendar file
    ical_content = generate_ical(upcoming, user_id)

    # Create file
    from aiogram.types import BufferedInputFile

    file = BufferedInputFile(
        ical_content.encode("utf-8"), filename="spaced_repetition_reviews.ics"
    )

    caption = f"""📅 **Calendar Export**

Exported {len(upcoming)} upcoming review(s) for the next 30 days.

**How to import:**
1. Download the .ics file
2. Import to Google Calendar, Apple Calendar, Outlook, etc.
3. Reviews will appear as calendar events with reminders!

Each review is scheduled for 30 minutes with a 30-minute advance reminder."""

    await message.reply_document(file, caption=caption, parse_mode="Markdown")


# ==============================================================================
# Main Entry Point
# ==============================================================================


async def main():
    """Start the bot."""
    print("🤖 Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
