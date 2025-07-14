# Telegram Bot for Monitoring TikTok and Instagram Accounts

This is a full production-ready Telegram Bot designed to monitor users’ TikTok and Instagram accounts and notify them of follower changes (new followers, unfollows, and potential blocks). The system is fully automated, user-friendly, stealthy, and scalable, built with Python and Playwright.

## 🚀 Features

- **Dual Platform Support:** Monitors both TikTok and Instagram public profiles.
- **Multi-user Support:** Each user can register and link multiple profiles for monitoring.
- **Automated Monitoring:** Uses pre-created monitoring accounts to follow target accounts and collect data periodically (every 6 hours by default).
- **Follower Change Detection:** Detects new followers, unfollowers, and potential blockers by comparing snapshots.
- **Telegram Notifications:** Users receive scheduled daily/periodic reports and can request on-demand reports.
- **Fully Button-Based Interface:** All interactions are via Inline Keyboard Buttons, no typing required.
- **Language Localization:** Auto-detects user's Telegram language (Arabic or English) and provides a fully localized interface.
- **Dynamic Monitoring Account Management:** Admins can add/remove monitoring accounts directly via the bot, which handles Playwright login and cookie saving.
- **Anti-Detection Techniques:** Implements various strategies to avoid bot detection (rotating proxies, random delays, user-agent rotation, etc.).

## 🔧 Technical Stack

- **Programming Language:** Python 3.10+
- **Headless Browser Automation:** Playwright (Python) with stealth and proxy support.
- **Telegram Bot Framework:** `python-telegram-bot` v20+.
- **Data Storage:** SQLite (default) or Supabase (if configured). Managed with SQLAlchemy.
- **Scheduler:** APScheduler for periodic tasks.
- **Environment Management:** `python-dotenv` for configuration.
- **Deployment:** Designed for Docker-based platforms like Railway.

## 📂 Project Structure

```
account-monitor-bot/
├── bot/                     # Telegram Bot logic and handlers
│   ├── main.py              # Telegram bot entrypoint
│   ├── handlers.py          # Button callbacks and conversation flows
│   ├── states.py            # FSM for managing user state
│   ├── localization.py      # Arabic/English message templates
│   ├── keyboards.py         # InlineKeyboardButtons factory
│   └── utils.py             # Utilities for formatting, URL validation, etc.
│
├── monitor/                 # Web scraping logic with Playwright
│   ├── base_monitor.py      # Base class for Playwright operations (login, cookies, browser management)
│   ├── tiktok_monitor.py    # Playwright bot to scrape TikTok profiles
│   ├── instagram_monitor.py # Playwright bot to scrape Instagram profiles
│   ├── cookies/             # Directory to save session cookies per monitoring account (requires persistent storage)
│   └── diff_checker.py      # Logic to compare snapshots and find changes
│
├── db/                      # Database models and utilities
│   ├── models.py            # SQLAlchemy ORM models (User, TargetAccount, FollowerSnapshot, MonitoringAccount)
│   └── db_utils.py          # Functions for database interactions (add, get, update, delete)
│
├── scheduler/               # Scheduled tasks and job runner
│   └── job_runner.py        # APScheduler jobs for periodic scanning and reporting
│
├── config/                  # Configuration files
│   ├── settings.py          # Configuration variables (API keys, intervals, paths)
│   └── proxies.txt          # List of proxies for rotating IPs (one per line)
│
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation (this file)
├── .env                     # Environment variables (sensitive data)
├── Dockerfile               # Docker configuration for deployment
└── Procfile                 # Process definition for deployment platforms (e.g., Railway)
```

## ⚙️ Setup and Deployment on Railway

This project is designed for easy deployment on Railway, leveraging Docker for environment setup.

### 1. Clone the Repository

```bash
git clone https://github.com/your-repo/account-monitor-bot.git
cd account-monitor-bot
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory of the project and add the following. **Crucially, replace placeholders with your actual values.**

```env
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
# Your Telegram User ID(s) who will have admin privileges to add/manage monitoring accounts.
# Example: ADMIN_TELEGRAM_IDS=\'[123456789, 987654321]\'
ADMIN_TELEGRAM_IDS=\'[]\'

# Optional: Override default settings
# DATABASE_URL="sqlite:///./db/bot.db" # Default uses SQLite in a persistent volume
# LOG_LEVEL="INFO" # DEBUG, INFO, WARNING, ERROR, CRITICAL
# MONITORING_INTERVAL_HOURS=6 # How often to run full monitoring job
# PROXY_LIST_PATH="config/proxies.txt" # Path to your proxy list file
# HEADLESS_MODE="true" # Set to "false" for debugging Playwright in development
# USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
```
- **`TELEGRAM_BOT_TOKEN`**: Obtain this from BotFather on Telegram.
- **`ADMIN_TELEGRAM_IDS`**: This is a JSON string of a list of Telegram User IDs. Only users with these IDs can access the "Admin Menu" to add/manage monitoring accounts. **Replace `[]` with your actual Telegram User ID(s) in a JSON array format.**

### 3. Prepare Proxies (Optional but Recommended for Anti-Detection)

If you plan to use proxies, populate `config/proxies.txt` with one proxy per line:

```
# Example: http://user:pass@ip:port
http://myuser:mypass@192.168.1.1:8080
socks5://anotheruser:anotherpass@10.0.0.1:9050
```

### 4. Deploy to Railway

1.  **Create a new project on Railway.**
2.  **Connect your GitHub repository** where this project code is hosted.
3.  Railway will detect the `Dockerfile` and `Procfile` and automatically build and deploy your application.
4.  **Persistent Volume:** For SQLite database and Playwright cookies to persist across deployments and restarts, you **must** attach a Persistent Volume to your Railway service.
    *   Go to your service settings on Railway.
    *   Under "Volumes", add a new volume.
    *   Mount path: `/app/db` (for SQLite database)
    *   Mount path: `/app/monitor/cookies` (for Playwright cookies)
    *   This ensures `db/bot.db` and files in `monitor/cookies/` are saved.

### 5. Initial Setup and Monitoring Account Management (Via Telegram Bot)

Once the bot is deployed and running on Railway:

1.  **Start the bot** in Telegram by sending `/start`.
2.  **Admin Access:** If your Telegram User ID is in `ADMIN_TELEGRAM_IDS` in the `.env` file, you will see an "Admin Menu" button.
3.  **Add Monitoring Accounts:**
    *   Go to "Admin Menu" -> "Add Monitoring Account".
    *   The bot will guide you through entering the platform (TikTok/Instagram), username, and password for the monitoring account.
    *   The bot will then attempt to log in to the platform using Playwright in headless mode and save the session cookies to `monitor/cookies/`. These accounts are what the bot uses to scrape data.
    *   **Important:** Ensure the monitoring accounts you add are valid and can log in. If login fails, the bot will notify you.
4.  **Add Target Accounts (for any user):**
    *   Any user can use the "Add Profile" button to add a public TikTok or Instagram profile URL they wish to monitor. The bot will then periodically check these profiles.

## ⚠️ Important Considerations

-   **Playwright Stability:** Web scraping, especially on platforms like TikTok and Instagram, is inherently fragile. UI changes on these platforms can break Playwright selectors, requiring updates to `monitor/tiktok_monitor.py` and `monitor/instagram_monitor.py`.
-   **Anti-Detection:** While basic anti-detection measures are included, advanced techniques (e.g., sophisticated CAPTCHA solving, more realistic human emulation) might be necessary for high-volume or long-term scraping to avoid bans.
-   **Resource Usage:** Playwright can be resource-intensive. Monitor your Railway resource usage (CPU, RAM) and scale up if necessary.
-   **Error Handling:** The bot includes basic error handling, but for production, robust logging and alerting (e.g., sending error messages to an admin channel) are recommended.

---
Developed by Manus AI Agent.


