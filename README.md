# GitHub Star Crawler - Complete Technical Assessment Guide

## Understanding the Assignment

### What We're Building

This is a **GitHub Repository Crawler** that:
1. Uses GitHub's GraphQL API to fetch data about repositories
2. Collects star counts and metadata for 100,000 GitHub repositories
3. Stores this data efficiently in PostgreSQL
4. Runs continuously (designed for daily execution via GitHub Actions)
5. Exports data to CSV and JSON formats

### Key Requirements

| Requirement | What It Means | Why It Matters |
|---|---|---|
| **100,000 repos** | Fetch star data from 100k GitHub repositories | Testing scalability and API efficiency |
| **Rate Limiting** | GitHub limits API calls to 5,000 points/hour | Must respect limits or risk being blocked |
| **Retry Mechanisms** | Automatically retry failed requests | Network issues are common; must be resilient |
| **PostgreSQL Database** | Store data in relational database | For efficient querying and historical tracking |
| **Efficient Updates** | Minimal database changes when re-crawling | Crawling daily means many updates |
| **GitHub Actions** | Automated pipeline in CI/CD | Zero-trust deployment; no private secrets |
| **Code Quality** | Clean architecture, separation of concerns | Required for professional engineering |

---

## Project Overview

### What This Project Does

┌─────────────────┐
│ GitHub API │ ← Queries for repository data
└────────┬────────┘
│
↓
┌─────────────────┐
│ Crawler Module │ ← Handles GraphQL requests,
│ (crawler.py) │ rate limiting, retries
└────────┬────────┘
│
↓
┌─────────────────┐
│ Database Layer │ ← Stores/updates repositories
│ (database.py) │ efficiently in PostgreSQL
└────────┬────────┘
│
↓
┌─────────────────┐
│ PostgreSQL DB │ ← Persists repository data
│ (Docker) │
└────────┬────────┘
│
↓
┌─────────────────┐
│ Export Module │ ← Exports to CSV/JSON
│ (export_data.py)│
└─────────────────┘

### Project Structure

github-star-crawler/
├── src/
│ ├── crawler.py # Main crawler logic - fetches from GitHub API
│ ├── database.py # Database connection & operations
│ ├── models.py # SQLAlchemy ORM models (database schema)
│ └── config.py # Configuration (tokens, URLs, limits)
├── scripts/
│ ├── setup_db.py # Creates database tables
│ └── export_data.py # Exports data to CSV/JSON
├── docker/
│ └── postgres/
│ └── init.sql # Initial SQL schema
├── docker-compose.yml # Docker Compose for local development
├── Dockerfile # Python application container
├── requirements.txt # Python dependencies
├── .gitignore # Git ignore rules
├── .env.example # Example environment file
└── .github/
└── workflows/
└── crawl.yml # GitHub Actions CI/CD pipeline

## Architecture & Design

### Design Principles Used

#### 1. **Anti-Corruption Layer**
The crawler doesn't directly expose GitHub API responses. Instead:
- Raw API responses → Crawler module → Models → Database
- Each layer validates and transforms data
- Database layer doesn't know about API details

```python
# ✓ GOOD: Anti-corruption layer
def fetch_repo(repo_id):
    raw_response = github_api.query(repo_id)  # Raw GitHub data
    repo = Repository.from_graphql(raw_response)  # Transform to model
    db.save(repo)  # Save to database

# ❌ BAD: No layer
def fetch_repo(repo_id):
    raw_response = github_api.query(repo_id)
    db.save(raw_response)  # Saves raw data directly

    2. Separation of Concerns
    Each file has one responsibility:

    crawler.py → API communication only
    database.py → Database operations only
    models.py → Data structure definitions only
    config.py → Configuration only
    
    3. Immutability
    Data from API is transformed once and stored
    Updates only modify changed fields
    Historical data preserved with last_crawled timestamp
    
    4. Database Efficiency
    Using indexes strategically:

    CREATE INDEX idx_repos_github_id ON repositories(github_id);
    CREATE INDEX idx_repos_last_crawled ON repositories(last_crawled);
    CREATE INDEX idx_repos_stars ON repositories(stargazers_count DESC);

    github_id - Fast lookup when updating existing repos
    last_crawled - Find repos needing updates
    stargazers_count - Sort by popularity
    Prerequisites & Installation
    
    What You Need Installed
    
    1. GitHub Personal Access Token (Required)
        Go to: https://github.com/settings/tokens
        Click "Generate new token (classic)"
        Select scopes: repo (optional), read:user, public_repo
        Copy the token (you won't see it again!)
        Never commit this token to GitHub
    
    2. Docker & Docker Compose (For local development)
    # Verify installation
        docker --version
        docker-compose --version

    3. Python 3.11+ (For running without Docker)
        python --version

    4. Git (For GitHub repository)
        git --version

        Step 1: Clone or Create the Repository
        # Option A: If you have an existing repo
            git clone https://github.com/YOUR_USERNAME/github-star-crawler.git
            cd github-star-crawler

        # Option B: Create a new one
            mkdir github-star-crawler
            cd github-star-crawler
            git init

        Step 2: Create Environment File
        Create a .env file in the project root:
            # .env file
            GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
            DATABASE_URL=postgresql://postgres:postgres@localhost:5432/github_crawler
            TOTAL_REPOS=100000

        Important:

        Add .env to .gitignore so tokens aren't committed
        Keep your GitHub token secret!

        Create .gitignore:
            .env
            __pycache__/
            *.pyc
            .venv/
            venv/
            .DS_Store
            exports/
            data/
            .pytest_cache/

        Step 3: Install Dependencies (Local Development)
            # Create virtual environment
                python -m venv venv

            # Activate it
            # On Windows:
                venv\Scripts\activate
            # On Linux/Mac:
                source venv/bin/activate

            # Install packages
                pip install -r requirements.txt
        
        Step 4: Verify File Structure
        Ensure your project has: 
            ✓ src/
            ✓ scripts/
            ✓ docker/
            ✓ docker-compose.yml
            ✓ Dockerfile
            ✓ requirements.txt
            ✓ .env (locally only, not in git)
            ✓ .gitignore

### Design Principles Used
Option 1: Using Docker Compose (Recommended for Local Dev)
This runs everything in isolated containers - closest to GitHub Actions environment.

    # 1. Start PostgreSQL and Python services
        docker-compose up -d

    # 2. Setup database (create tables)
        docker exec github_crawler_app python scripts/setup_db.py

    # 3. Run the crawler
        docker exec github_crawler_app python src/crawler.py

    # 4. Export data
        docker exec github_crawler_app python scripts/export_data.py

    # 5. View exported files
        ls exports/

    # 6. Stop services
        docker-compose down


Database Schema & Design:

    repositories table:
    ├── id (auto-increment) ─────────── Primary key
    ├── github_id (unique, indexed) ─── GitHub's internal ID
    ├── name ────────────────────────── Repository name
    ├── full_name (indexed) ─────────── owner/repo format
    ├── owner_login ─────────────────── Repository owner
    ├── stargazers_count (indexed) ──── Number of stars
    ├── language ────────────────────── Programming language
    ├── forks_count ─────────────────── Number of forks
    ├── open_issues_count ───────────── Open issues
    ├── size_kb ─────────────────────── Repository size
    ├── created_at ──────────────────── When repo was created
    ├── updated_at ──────────────────── Last update time
    ├── archived ────────────────────── Is it archived?
    └── last_crawled (indexed) ──────── When we last fetched it

API Rate Limiting & Retry Logic:
    Understanding GitHub's Rate Limits
    GitHub allows 5,000 GraphQL points per hour:

        Request 1: 1 point  ├─ Cumulative: 1
        Request 2: 5 points ├─ Cumulative: 6
        Request 3: 3 points ├─ Cumulative: 9
        ...
        Request N: ? points └─ Cumulative: 5000 (limit hit!)

    Each GraphQL query costs points based on complexity:

        Simple query: 1-5 points
        Fetching 100 repos: ~50-100 points
        Fetching with all fields: ~150+ points

Scaling Considerations:

    Question: What If We Had 500 Million Repos?

    From 100k to 500M repos is 5,000x larger. Current approach would take:

        100,000 repos ÷ 5,000 points/hour = 20 hours worst case
        500,000,000 repos ÷ 5,000 points/hour = 100,000 hours = 11.4 years!


Complete Example: Running Everything:
        Scenario: You just cloned the project

        # Step 1: Setup environment
            git clone https://github.com/YOUR_USERNAME/github-star-crawler.git
            cd github-star-crawler

        # Step 2: Create .env file
            cat > .env << EOF
            GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
            DATABASE_URL=postgresql://postgres:postgres@localhost:5432/github_crawler
            TOTAL_REPOS=100000
            EOF

        # Step 3: Run with Docker Compose
            docker-compose up -d                          # Start services
            docker exec github_crawler_app python scripts/setup_db.py  # Create tables
            docker exec github_crawler_app python src/crawler.py        # Crawl 100k repos
            docker exec github_crawler_app python scripts/export_data.py # Export CSV/JSON

       # Step 4: Check results
            ls -lah exports/
            docker-compose logs -f github_crawler_app     # View logs
            docker-compose down                           # Stop services