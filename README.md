# Beyblade X Tracker

A mobile-first web app for tracking Beyblade X battles, combos, and stats.

## Features

- **User accounts** — register, log in, log out; all data is per-user
- **Combo management** — build combos from your Blade / Ratchet / Bit parts database; view win/loss record for each combo
- **Battle recording** — record battles with both combos, the winner, and the win type (Spin/Stamina, Over, Burst, or Extreme Finish)
- **Points system** — Spin/Stamina Finish = 1 pt, Over/Burst Finish = 2 pts, Extreme Finish = 3 pts
- **Stats dashboard** — per-combo stats with win rate, total points, average points per round, win-type breakdown, matchup breakdown, and full battle history
- **Part filtering** — filter any combo's stats by the opponent's Blade, Ratchet, or Bit
- **Parts database** — searchable and filterable grid of all known Beyblade X parts with images
- **Mobile-first design** — works great on iPhone SE (375 px) and up; bottom tab navigation

## Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/your-username/beyblade-x-tracker.git
cd beyblade-x-tracker

# 2. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set the DATABASE_URL environment variable
# Windows (PowerShell)
$env:DATABASE_URL = "postgresql://user:password@host:5432/dbname"
# macOS / Linux
export DATABASE_URL="postgresql://user:password@host:5432/dbname"

# 5. (Optional) Set a secret key
$env:SECRET_KEY = "your-random-secret-key"

# 6. Run the app
python app.py
```

Then open http://localhost:5000 in your browser.

## Deployment: Railway + Supabase

### 1. Create a Supabase database

1. Go to [supabase.com](https://supabase.com) and create a new project.
2. In **Project Settings → Database**, copy the **Connection string (URI)** (the `postgresql://` one, not `postgres://`).

### 2. Deploy to Railway

1. Go to [railway.app](https://railway.app) and create a new project.
2. Choose **Deploy from GitHub repo** and select this repository.
3. In your Railway service settings, add the following environment variables:
   - `DATABASE_URL` — paste the Supabase connection string
   - `SECRET_KEY` — a long random string (e.g., output of `python -c "import secrets; print(secrets.token_hex(32))"`)
4. Railway will detect the `Procfile` and deploy automatically.
5. The tables are created automatically on first startup via `init_db()`.

### 3. Custom domain (optional)

In Railway → your service → Settings → Domains, you can add a custom domain or use the auto-generated `.up.railway.app` URL.

## Project Structure

```
BeybladeXWeb/
├── app.py              # Flask backend
├── parts_db.json       # Parts database (blades, ratchets, bits)
├── requirements.txt
├── Procfile
├── runtime.txt
├── .gitignore
├── images/             # Part images (served at /images/...)
│   ├── blades/
│   ├── ratchets/
│   └── bits/
├── static/
│   ├── css/style.css
│   └── js/app.js
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── combos.html
    ├── battle.html
    ├── stats.html
    └── parts.html
```
