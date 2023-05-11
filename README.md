# Simple time tracker telegram bot

Personal time tracker bot. Tracked time by messages.

## Installation

1. Install PostgreSQL and import file `db_scheme.sql`
2. Create some user with directory in `/home`
3. Execute commands:
```
su - [YOUR_USER]
git clone https://github.com/grspectre/time_tracker_bot.git
cd ./time_tracker_bot/
python -m venv --clear venv
./venv/bin/pip install -r ./requirements.txt
```