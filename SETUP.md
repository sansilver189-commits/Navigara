# Navigara cold-calling dashboard - getting started

Everything runs on your own computer. Your data is one file: `data/navigara.db`.

## One-time setup

1. **Install Python** (free): https://www.python.org/downloads/
   *Windows:* on the first installer screen, tick **"Add python.exe to PATH"**.
2. **Install Git** (free): https://git-scm.com/downloads
   *Mac:* it is usually already there; if a box pops up asking to install "command line developer tools", click Install.
3. **Get the project** in VS Code: press `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`), type `Git: Clone`, press Enter,
   choose **Clone from GitHub**, sign in if asked, pick **Navigara**, and choose a folder (e.g. Documents).
   Click **Open** when VS Code asks.
4. **Switch to the dashboard branch**: in VS Code open the terminal (menu **Terminal → New Terminal**) and paste:
   ```
   git checkout claude/cold-calling-dashboard-f3k06x
   ```

## Starting it

| What | Mac | Windows |
|---|---|---|
| Your real dashboard | double-click `start.command` | double-click `start.bat` |
| Practice mode (fake leads, pretend calls) | double-click `practice.command` | double-click `practice.bat` |

The first start takes a minute (it installs what it needs). Your browser then opens
http://localhost:8000 (practice mode: http://localhost:8001). Keep the black window open while you use it;
close it to stop.

Or from the VS Code terminal: `python run.py` (Mac: `python3 run.py`), add `--practice` for practice mode.

## Getting the latest version

In the VS Code terminal:
```
git pull
```

## Settings

Copy `.env.example` to a new file named `.env` in the same folder and fill it in. That file holds your
password, time zone and (later) your Twilio keys. It is never uploaded to GitHub.

## Backups

Click **Back up database** in the sidebar. A copy downloads, and another is kept in `data/backups/`.

## Adding leads from Apollo

1. In Apollo, search **People**: job titles like CTO / VP Engineering / Head of AI, your target industries,
   1,000+ employees, United States.
2. Tick the people you want and click **Export → CSV**.
3. In the dashboard, open **Leads**, click **Upload CSV** and pick the file.
   People already in the system are recognised and not added twice.

Making a list by hand (e.g. from LinkedIn)? Click **CSV template** on the Leads page, fill it in, upload it.

## Changing how leads are scored

Open `scoring.toml` in VS Code. Every number and word list is there with a note explaining it.
Save the file, then click **Re-score all** on the Leads page.
