# CLAUDE.md - AI Assistant Guide for ForgettingCurveBot

This document provides essential context for AI assistants working with the ForgettingCurveBot codebase.

## Project Overview

**ForgettingCurveBot** is an AI-powered Anki-style flashcard learning system for algorithms and data structures, built as a Telegram bot with local LLM (Ollama) integration.

**Key Features:**
- Natural language flashcard creation ("add Two Sum, uses hashmap")
- SM-2 spaced repetition algorithm (same as Anki)
- AI-powered content parsing and auto-generation via Ollama
- Smart tagging based on algorithm difficulty and type
- Interactive review sessions with 4-button rating system
- Q&A support during reviews with LLM explanations
- Calendar export (.ics format)
- Adaptive scheduling based on problem acceptance rate and algorithm rarity

## Technology Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.11+ |
| Bot Framework | aiogram 3.4.1 |
| Database | MongoDB 4.x |
| LLM Engine | Ollama (gemma3, llama2, mistral, phi, codellama) |
| Package Management | Poetry |
| Testing | pytest 8.0.2, pytest-mock 3.12.0 |
| Code Formatting | Black (line-length: 120) |
| Container | Docker + Docker Compose |

## Project Structure

```
ForgettingCurveBot/
├── bot/                           # Main application code
│   ├── main.py                   # Core bot logic (handlers, commands, review flow)
│   ├── models.py                 # Card and Review dataclasses
│   ├── config.py                 # Configuration management
│   ├── sm2.py                    # SM-2 algorithm implementation
│   ├── llm_service.py            # Ollama LLM integration
│   ├── db_service.py             # MongoDB database layer
│   ├── calendar_export.py        # iCalendar generation
│   ├── algorithm_config.py       # Adaptive scheduling config
│   ├── handlers.py               # Additional message handlers
│   ├── callbacks.py              # Callback handlers (stub)
│   ├── commands.py               # Command definitions (stub)
│   ├── utils/                    # Utility modules
│   └── tests/                    # Test suite
│       ├── test_create_user.py   # User creation tests
│       └── test_update_user.py   # User update tests
├── tasks/                         # Reference data
│   └── neetcode.json             # LeetCode problems by category
├── .env.template                 # Environment template
├── Dockerfile                    # Docker image definition
├── docker-compose.yml            # Multi-container setup
├── pyproject.toml               # Poetry configuration
└── README.md                    # Project documentation
```

## Key Modules

### `main.py` - Core Bot Logic
- State management using aiogram FSM (CardCreation, ReviewSession states)
- Command handlers: `/start`, `/help`, `/add`, `/review`, `/cards`, `/delete`, `/stats`, `/export`
- Natural language card creation parsing
- Review session flow with rating system

### `sm2.py` - Spaced Repetition Algorithm
- SuperMemo-2 algorithm (same as Anki)
- Adaptive difficulty multipliers based on acceptance rate and algorithm rarity
- Interval calculation: first=1 day, second=6 days, then interval × easiness_factor

### `llm_service.py` - Ollama Integration
- `parse_card_command(text)` - Extract card details from natural language
- `generate_flashcard_content(name, code)` - Auto-generate notes
- `smart_tag(name, code, notes)` - Categorize by data structure/pattern/difficulty
- `answer_question(card_name, code, notes, question)` - Q&A during reviews

### `db_service.py` - MongoDB Layer
- Card CRUD: `add_card()`, `get_card()`, `update_card()`, `delete_card()`
- Query helpers: `get_all_cards()`, `get_due_cards()`, `get_cards_count()`
- Review tracking: `add_review()`, `get_review_stats()`
- User management: `add_user()`, `update_user()`, `get_user()`

### `algorithm_config.py` - Adaptive Scheduling
- Algorithm rarity: rare (×0.7), common (×1.0), basic (×1.2)
- Difficulty multipliers based on acceptance rate (0.7 to 1.3)

## Database Schema

### `cards` Collection
```python
{
    "user_id": int,              # Telegram user ID
    "chat_id": int,              # Telegram chat ID
    "name": str,                 # Problem name (unique per user)
    "code": str | None,          # Code solution
    "notes": str | None,         # Explanation/intuition
    "links": list[str],          # Resource URLs
    "tags": list[str],           # Auto-generated tags
    "easiness_factor": float,    # SM-2 EF (default: 2.5)
    "interval": int,             # Days until next review
    "repetitions": int,          # Successful review count
    "next_review_date": datetime,
    "acceptance_rate": float,    # 0.0-1.0 (problem difficulty)
    "difficulty_multiplier": float,
    "created_at": datetime,
    "last_reviewed_at": datetime | None
}
```

### `reviews` Collection
```python
{
    "user_id": int,
    "card_name": str,
    "rating": int,               # 0=Again, 1=Hard, 2=Good, 3=Easy
    "reviewed_at": datetime,
    "easiness_factor_before": float,
    "easiness_factor_after": float,
    "interval_before": int,
    "interval_after": int
}
```

### `users` Collection
```python
{
    "user_id": int,              # Primary key
    "username": str,
    "first_name": str,
    "last_name": str,
    "chat_id": int,
    "state": str,                # Default: "start"
    "status": str,               # Default: "active"
    "language": str,             # Default: "en"
    "reminder": str,             # Default: "off"
    "reminder_time": str         # HH:MM format
}
```

## Development Commands

```bash
# Install dependencies
poetry install

# Run bot locally
python -m bot.main

# Start Ollama (in separate terminal)
ollama serve
ollama pull gemma3

# Run tests
pytest
pytest --cov=bot

# Format code
black bot/
black --check bot/

# Docker deployment
docker-compose up --build
docker-compose up -d
```

## Environment Variables

```env
BOT_TOKEN=<telegram-bot-token>     # Required
MONGODB_URI=mongodb://localhost:27017/
MONGO_INITDB_ROOT_USERNAME=
MONGO_INITDB_ROOT_PASSWORD=
MODEL=gemma3                        # Ollama model name
LOG_LEVEL=INFO
```

## Code Conventions

### Naming
- **Functions:** snake_case
- **Classes:** PascalCase
- **Constants:** UPPER_SNAKE_CASE
- **MongoDB Collections:** snake_case
- **Card names:** Title Case ("Two Sum")
- **Tags:** lowercase ("array", "hashmap")

### Patterns
- **Async/Await:** All bot handlers are async
- **FSM States:** CardCreation.waiting_for_details, ReviewSession.reviewing, ReviewSession.asking_question
- **Dataclasses:** Card and Review with `to_dict()`/`from_dict()` serialization
- **Singleton Services:** `ollama_service` instance in llm_service.py

### Error Handling
- Try-except blocks for database operations
- Fallback regex parsing if LLM JSON extraction fails
- User-friendly error messages in Telegram replies

### Formatting
- Black formatter with 120 character line length
- Python 3.11 target version

## SM-2 Algorithm Reference

```
Rating values: 0=Again, 1=Hard, 2=Good, 3=Easy

For rating 0 (Again):
  - Reset: repetitions = 0, interval = 0

For rating 1-3:
  - EF' = max(1.3, EF + (0.1 - (3 - rating) * (0.08 + (3 - rating) * 0.02)))
  - First review: interval = 1 day
  - Second review: interval = 6 days
  - Subsequent: interval = previous_interval × EF
  - Rating adjustments: Hard (×0.85), Easy (×1.3)
  - Apply difficulty multiplier (acceptance_rate + algorithm_rarity)
```

## Testing

### Current Test Coverage
- `test_create_user.py` - User creation with various field combinations
- `test_update_user.py` - User update operations

### Running Tests
```bash
pytest                              # All tests
pytest bot/tests/test_create_user.py  # Specific file
pytest -v                           # Verbose output
pytest --cov=bot --cov-report=html  # Coverage report
```

## Common Tasks for AI Assistants

### Adding a New Bot Command
1. Add handler function in `bot/main.py` with `@router.message(Command("command_name"))`
2. Register in appropriate section (with other command handlers)
3. Update `/help` command message to document new command

### Modifying SM-2 Algorithm
1. Edit `bot/sm2.py`
2. Key parameters: line 101 (first interval), line 103 (second interval), lines 111-114 (rating adjustments)
3. Run tests to verify calculations

### Adding New LLM Functionality
1. Add method to `OllamaService` class in `bot/llm_service.py`
2. Define system prompt for the task
3. Handle JSON parsing with fallback for reliability

### Database Schema Changes
1. Update dataclass in `bot/models.py`
2. Update `to_dict()` and `from_dict()` methods
3. Update relevant functions in `bot/db_service.py`
4. Consider backwards compatibility for existing documents

### Adding Tests
1. Create test file in `bot/tests/`
2. Use pytest-mock for mocking MongoDB operations
3. Follow existing patterns in `test_create_user.py`

## Known Limitations

1. **State Storage:** In-memory FSM (not persistent across restarts)
2. **Reminder Feature:** Schema exists but not fully implemented
3. **Stub Files:** `commands.py` and `callbacks.py` are placeholders
4. **MongoDB Indexes:** No explicit indexes defined
5. **Logging:** Uses print() statements; no centralized logging
6. **Test Coverage:** Limited to user CRUD operations

## Architecture Notes

- Main bot logic is concentrated in `main.py` (~619 lines)
- Separation of concerns: handlers (main.py), models (models.py), database (db_service.py), LLM (llm_service.py), algorithm (sm2.py)
- FSM for conversation state management
- Ollama API calls are synchronous (timeout: 30s)
- MongoDB operations use PyMongo directly (no ODM)

## Quick Reference

| Action | Location |
|--------|----------|
| Bot commands | `bot/main.py` |
| Data models | `bot/models.py` |
| Database queries | `bot/db_service.py` |
| LLM prompts | `bot/llm_service.py` |
| SM-2 algorithm | `bot/sm2.py` |
| Adaptive scheduling | `bot/algorithm_config.py` |
| Calendar export | `bot/calendar_export.py` |
| Tests | `bot/tests/` |
| LeetCode problems | `tasks/neetcode.json` |
