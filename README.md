# API of Life

A self-evolving Web API that grows new features daily through Claude Code.

## Overview

This project demonstrates autonomous code evolution. Every day, Claude Code:
1. Reviews the current codebase
2. Suggests a new feature to implement
3. Implements the feature
4. Runs tests to verify it works
5. Commits the changes

Over time, the API evolves from a simple CRUD application into something more sophisticated.

## Project Structure

```
api-of-life/
├── src/                    # The evolving Web API
│   ├── main.py            # FastAPI application
│   ├── requirements.txt   # Dependencies
│   └── tests/             # Test files (grows with features)
├── evolution/             # Evolution system
│   ├── evolve.sh          # Main evolution script
│   ├── logs/              # Daily evolution logs
│   └── history.md         # Human-readable evolution history
└── README.md              # This file
```

## Current API Endpoints

- `GET /health` - Health check endpoint
- `GET /items` - List all items
- `POST /items` - Create a new item
- `GET /items/{id}` - Get a single item by ID

See the [Evolution History](evolution/history.md) for a complete list of added features.

## Getting Started

### Prerequisites

- Python 3.11+
- Claude Code CLI (`claude`)

### Installation

```bash
cd api-of-life/src
pip install -r requirements.txt
```

### Running the API

```bash
cd api-of-life/src
uvicorn main:app --reload
```

The API will be available at http://localhost:8000

API documentation is auto-generated at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Running Tests

```bash
cd api-of-life/src
python -m pytest tests/ -v
```

## Evolution System

### Manual Evolution

To trigger an evolution cycle manually:

```bash
cd api-of-life/evolution
./evolve.sh
```

### Automated Daily Evolution

Set up a cron job to run the evolution daily:

```bash
crontab -e
```

Add the following line (adjust the path):

```
0 2 * * * /path/to/api-of-life/evolution/evolve.sh >> /path/to/api-of-life/evolution/logs/cron.log 2>&1
```

This runs the evolution at 2:00 AM every day.

### Monitoring Evolution

- **Daily logs:** Check `evolution/logs/YYYY-MM-DD.log` for detailed output
- **History:** Read `evolution/history.md` for a summary of all features
- **Git log:** Use `git log` to see all evolution commits

## Safety Measures

- Tests must pass before any commit is made
- Git provides rollback capability if needed
- All changes are logged for review
- The evolution script can be paused by removing the cron job

## License

MIT
