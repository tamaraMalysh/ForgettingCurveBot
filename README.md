# Spaced Repetition Telegram Bot

An Anki-style flashcard system for learning algorithms and data structures, built as a Telegram bot with AI-powered natural language processing.

## Features

- **Natural Language Card Creation** - Just type "add Two Sum, uses hashmap" and the bot creates a flashcard
- **AI-Powered** - Uses local LLM (Ollama) to parse messages and auto-generate explanations
- **SM-2 Spaced Repetition** - Same algorithm as Anki for optimal memory retention
- **Interactive Reviews** - Anki-style 4-button rating system (Again, Hard, Good, Easy)
- **Calendar Export** - Export reviews to Google Calendar, Apple Calendar, etc.
- **Smart Tagging** - AI automatically tags cards by data structure, algorithm type, and difficulty
- **Q&A During Review** - Ask questions about cards and get AI-powered explanations

## Quick Start

### Prerequisites

1. **Python 3.11+**
2. **MongoDB** - For storing flashcards
3. **Ollama** - Local LLM for natural language processing
   - Install: https://ollama.com/download
   - Pull a model: `ollama pull llama2`
4. **Telegram Bot Token** - Create bot via [@BotFather](https://t.me/BotFather)

### Installation

```bash
# Clone the repository
git clone https://github.com/tamaramalysh5991/IntervalRepetition.git
cd IntervalRepetition

# Install dependencies
poetry install
# Or with pip:
# pip install -r requirements.txt

# Set up environment variables
cp .env.template .env
# Edit .env with your credentials
```

### Configuration

Edit `.env` file:

```env
BOT_TOKEN=your_telegram_bot_token_here
MONGODB_URI=mongodb://localhost:27017/
MONGO_INITDB_ROOT_USERNAME=your_username
MONGO_INITDB_ROOT_PASSWORD=your_password
```

### Running

```bash
# Start Ollama (in a separate terminal)
ollama serve

# Pull an LLM model (first time only)
ollama pull llama2

# Run the bot
python bot/main.py
```

### Docker Setup

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d
```

## Usage

### Creating Flashcards

Just send a message to the bot in natural language:

```
add Two Sum problem, solved with hashmap for O(n) time
```

```
Binary Search algorithm, divide and conquer approach
```

Include code in triple backticks:
````
add DFS traversal

```python
def dfs(node, visited):
    if node in visited:
        return
    visited.add(node)
    for neighbor in node.neighbors:
        dfs(neighbor, visited)
```

Uses recursion and a visited set
````

The AI will automatically:
- Extract the problem name
- Save your code
- Parse notes and explanations
- Add relevant tags (e.g., "graph", "dfs", "recursion")
- Generate helpful notes if missing

### Reviewing Cards

1. Send `/review` to start a review session
2. Read the question (problem/algorithm name)
3. Think about the solution
4. Click **"Show Answer"** to reveal code and notes
5. Rate yourself:
   - **Again** - Completely forgot (<1 day)
   - **Hard** - Difficult to recall (~1 day)
   - **Good** - Recalled with effort (~4 days)
   - **Easy** - Remembered easily (~7+ days)

The bot uses the SM-2 algorithm to schedule your next review optimally.

### Other Commands

- `/cards` - List all your flashcards with due dates
- `/stats` - View learning statistics (retention rate, review counts)
- `/delete <name>` - Remove a card
- `/export` - Download calendar file (.ics) for next 30 days
- `/help` - Show detailed help

### Asking Questions During Review

During a review session, click **"Ask Question"** and type your question:

```
What's the time complexity of this approach?
```

```
Why use a hashmap instead of sorting?
```

The AI will provide explanations and hints based on the card content.

## How It Works

### Spaced Repetition (SM-2 Algorithm)

The bot uses the SuperMemo-2 algorithm, the same one powering Anki:

1. **New cards** start with 1-day interval
2. **Rating affects next interval**:
   - Again: Reset to 0 days
   - Hard: ~1 day
   - Good: ~4 days
   - Easy: ~7 days
3. **Easiness factor** adjusts based on your performance
4. **Intervals grow exponentially** for cards you remember well

This ensures you review cards just before you forget them, maximizing retention with minimal time.

### AI Integration

The bot uses **Ollama** to run large language models locally:

- **Card parsing**: Extracts problem name, code, notes, links from natural language
- **Content generation**: Auto-generates explanations if you don't provide any
- **Smart tagging**: Automatically categorizes by data structure, algorithm, difficulty
- **Q&A**: Answers questions during review to help you understand concepts

**Privacy**: All AI processing happens locally on your machine. Nothing is sent to external APIs.

## Development

### Project Structure

```
bot/
├── main.py              # Main bot logic and handlers
├── models.py            # Data models (Card, Review)
├── sm2.py               # SM-2 algorithm implementation
├── llm_service.py       # Ollama LLM integration
├── db_service.py        # MongoDB database layer
├── calendar_export.py   # iCalendar generation
├── config.py            # Configuration
└── tests/               # Unit tests
```

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=bot

# Run specific test
pytest bot/tests/test_create_user.py
```

### Code Formatting

```bash
# Format with Black
black bot/

# Check formatting
black --check bot/
```

## Configuration Options

### Changing LLM Model

Edit `bot/llm_service.py` line 16:

```python
ollama_service = OllamaService(model="mistral")  # or phi, codellama, etc.
```

Recommended models:
- **llama2**: General purpose, good balance
- **mistral**: Faster, more concise responses
- **codellama**: Better for understanding code
- **phi**: Lightweight, faster inference

### SM-2 Parameters

Modify `bot/sm2.py` to adjust review intervals:

- Line 69: First review interval (default 1 day)
- Line 71: Second review interval (default 6 days)
- Lines 76-81: Rating multipliers

## Troubleshooting

### Bot doesn't respond

- Check bot token in `.env`
- Verify MongoDB is running
- Check bot is started: `python bot/main.py`

### "Error calling Ollama"

- Ensure Ollama is running: `ollama serve`
- Check model is installed: `ollama list`
- Try pulling model again: `ollama pull llama2`

### No cards showing in /review

- Use `/cards` to check due dates
- Cards may not be due yet
- Use `/stats` to verify cards exist

### AI generates poor tags/notes

- Try a different model (codellama is good for algorithms)
- Provide more context in your card creation message
- Manually add notes and tags in your message

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)

## Acknowledgments

- **SuperMemo** for the SM-2 algorithm
- **Anki** for inspiration
- **Ollama** for making local LLMs accessible
- **aiogram** for the excellent Telegram bot framework
