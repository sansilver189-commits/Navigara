"""Start the dashboard.  python run.py            -> your real dashboard
                        python run.py --practice -> practice mode (made-up leads, pretend calls)"""
import argparse
import os
import threading
import webbrowser

parser = argparse.ArgumentParser()
parser.add_argument("--practice", action="store_true", help="made-up leads in a throwaway database")
parser.add_argument("--no-browser", action="store_true")
args = parser.parse_args()
if args.practice:
    os.environ["NAVIGARA_PRACTICE"] = "1"

import uvicorn  # noqa: E402

from app.config import HOST, PORT  # noqa: E402

url = f"http://localhost:{PORT}"
print(f"\n  Navigara dashboard {'(PRACTICE MODE) ' if args.practice else ''}is running at {url}")
print("  Leave this window open. Close it (or press Ctrl+C) to stop.\n")
if not args.no_browser:
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="warning")
