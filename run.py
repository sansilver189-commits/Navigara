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

from app import config  # noqa: E402
from app.util import normalize_phone, pretty_phone  # noqa: E402

url = f"http://localhost:{PORT}"
print(f"\n  Navigara dashboard {'(PRACTICE MODE) ' if args.practice else ''}is running at {url}")
if not args.practice:
    # Shows what's set up, never the secret values themselves.
    needed = {"TWILIO_ACCOUNT_SID": config.TWILIO_ACCOUNT_SID, "TWILIO_API_KEY": config.TWILIO_API_KEY,
              "TWILIO_API_SECRET": config.TWILIO_API_SECRET, "TWILIO_TWIML_APP_SID": config.TWILIO_TWIML_APP_SID,
              "DIAL_SECRET": config.DIAL_SECRET, "TWILIO_NUMBERS": config.TWILIO_NUMBERS}
    missing = [k for k, v in needed.items() if not v]
    if missing:
        print("  Calling: OFF - missing in .env: " + ", ".join(missing))
    else:
        nums = [pretty_phone(normalize_phone(n)) or f"'{n}' (not a valid number!)" for n in config.TWILIO_NUMBERS]
        print("  Calling: ON - calling from " + ", ".join(nums))
    print(f"  Calling hours: {config.CALL_HOURS[0]}:00-{config.CALL_HOURS[1]}:00 in each lead's time zone")
print("  Leave this window open. Close it (or press Ctrl+C) to stop.\n")
if not args.no_browser:
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="warning")
