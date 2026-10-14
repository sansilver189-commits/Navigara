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

## Connecting Twilio (real calls)

Do this once. Everything you copy goes into the `.env` file on your computer, never into a chat.

**0. Make your settings file** (if you haven't yet). In the VS Code terminal:
```
cp .env.example .env
```
Then click `.env` in VS Code's file list on the left to open it.

**1. Create an account** at https://www.twilio.com/try-twilio and verify your email and phone.
Then **upgrade** (top bar: *Upgrade account*) and add about $20. A trial account can only call
your own verified numbers and plays a "trial account" message.

**2. Buy your numbers.** Left menu: *Phone Numbers → Manage → Buy a number*. Country: United States,
type `415` in the number search, tick *Voice*, click *Search*, then *Buy* on one result.
Repeat for a Southern number (e.g. `404` Atlanta or `214` Dallas).
Put them in `.env`, separated by commas:
`TWILIO_NUMBERS=+14155550123,+14045550123`

**3. Account SID.** On the Console home page, under *Account Info*, copy **Account SID** (starts `AC`)
into `TWILIO_ACCOUNT_SID=`.

**4. API key.** Top-right *Admin → Account management → API keys & tokens → Create API key*.
Name it `navigara`, type *Standard*, click *Create*. Copy the **SID** (starts `SK`) into
`TWILIO_API_KEY=` and the **Secret** into `TWILIO_API_SECRET=`. The secret is shown only once.

**5. Dial secret.** In the VS Code terminal run:
```
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```
Copy the line it prints into `DIAL_SECRET=` in `.env`. You'll paste the same text in step 6.

**6. The call Function** (it places calls, and only ones your dashboard signed).
Left menu: *Functions and Assets → Services → Create Service*, name `navigara-dialer`, *Next*.
- Click *Add + → Add Function*, name the path `/dial`.
- Delete the sample code and paste everything from `twilio/dial-function.js` in this project.
- Next to `/dial`, set visibility to **Protected**. Click *Save*.
- Under *Settings & More → Environment Variables*, add key `DIAL_SECRET` with the value from step 5.
- Click **Deploy All**. When it's done, click the `/dial` function and *Copy URL*.

**7. The TwiML App** (tells Twilio where to ask "who should I call?").
Left menu: *Phone Numbers → Manage → TwiML apps → Create new TwiML App*. Name `Navigara Dialer`.
Under *Voice Configuration*, paste the URL from step 6 into *Request URL* (method POST). *Save*.
Open the app again and copy its **SID** (starts `AP`) into `TWILIO_TWIML_APP_SID=`.

**8. Restart the dashboard** (Ctrl+C in the terminal, then `./start.command`).
The Dialer now shows green **Call** buttons. Your browser asks to use the microphone the first time: click Allow.
Use a headset.

**9. Help calls get through (strongly recommended).** In Twilio: *Trust Hub → Customer Profiles*,
create your business profile (Navigara), then register your numbers for **SHAKEN/STIR** and
**Voice Integrity**. This tells phone carriers you're a real business, so your calls are less
likely to show as "Spam Likely". It takes a few days to approve.
