# SQL Database Query Assistant

An application that lets you query SQLite databases using natural language.

## Features

- 🔍 Query databases in plain English - no SQL knowledge needed
- 📊 AI translates your questions into SQL
- 📋 View database structure and sample data
- 🧠 Powered by Groq LLM, LangChain, and LangGraph

## Requirements

- Python 3.8+
- Groq API key
- SQLite database (.db file)

## Installation

```bash
git clone https://github.com/RishabhRSingh/SQL_AGENT.git
cd sql-query-assistant
pip install -r requirements.txt
```

## Usage

1. Enter your Groq API key in the sidebar or set it as an environment variable:
   ```bash
   export GROQ_API_KEY="your_groq_api_key_here"
   ```
2. Run the application:
   ```bash
   python run.py
   ```

3. Open http://localhost:8501 in your browser


4. Upload a SQLite database and ask questions!


## Architecture

- Frontend: Streamlit
- Backend: FastAPI
- AI: LangChain, LangGraph, Groq
- Database: SQLite with SQLAlchemy

