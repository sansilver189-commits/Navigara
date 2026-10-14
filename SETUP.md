# Navigara cold-calling dashboard - your guide

A private sales tool that runs on your own Mac. Your data never leaves your computer
(except the calls themselves, which go through Twilio).

**Contents:** Starting it · Daily routine · Backups · Where each setting lives ·
When something goes wrong · Connecting Twilio · **Cold-calling rules (read this)**

---

## Starting it

**First time only** - install Python from https://www.python.org/downloads/ and get the project into
VS Code (`Cmd+Shift+P` → `Git: Clone` → Clone from GitHub → Navigara → Documents → Open). Then, in
VS Code's terminal (*Terminal → New Terminal*):
```
git checkout claude/cold-calling-dashboard-f3k06x
```

**Every time** - in VS Code's terminal, paste one of these:

| What | Command |
|---|---|
| Your real dashboard | `./start.command` |
| Practice mode (made-up people, pretend calls) | `./practice.command` |

Your browser opens it (real: http://localhost:8000, practice: http://localhost:8001).
Keep the terminal open while you use it. To stop: click the terminal and press `Ctrl + C`.

**Getting the newest version** (after I change something): stop it, then `git pull`, then start again.

---

## Daily routine

1. **Leads** → *Upload CSV* with your Apollo export. Check who is *Ready to call*.
2. **Dialer** → put your headset on → *Start dialing*. Pick a result after every call -
   that is the only thing that moves on to the next person.
3. After a meeting happens, open that person on **Leads** and log *Showed* (and later *Signed*).
4. **Analytics** once a week: best hours, best industries, whether a number has stopped getting answers.
5. **Back up** (see below).

---

## Backups

Click **Back up database** at the bottom of the sidebar (or *Settings → Back up now*).
A copy downloads, and another is kept in the `data/backups` folder. Once a week, copy the downloaded
file somewhere safe (iCloud Drive, Google Drive, a USB stick).

**To restore:** stop the dashboard, rename the backup file to `navigara.db`, put it in the `data` folder
(replacing the old one), start again.

Everything lives in one file: `data/navigara.db`. It is **not** uploaded to GitHub (on purpose -
it holds people's phone numbers).

---

## Where each setting lives

| Setting | Where |
|---|---|
| Password, time zone, calling hours, "Call Later" days, Twilio keys | `.env` file in the project folder (make it with `cp .env.example .env`, then click it in VS Code's file list). Restart after changing. |
| Scoring: points, cut-off score, industries, job titles, Big Tech list | `scoring.toml` - every line has a note. Save, then click *Re-score all* on Leads. No restart. |
| Daily dial goal | Type it into the *goal* box on the Dialer. |
| Scripts and objection answers | The **Scripts** page. |
| Text size and high-contrast look for scripts | The *A- / A+* buttons and the look menu on the script. |

**Never** paste the contents of `.env` into a chat, email or GitHub. It is excluded from git automatically.

---

## When something goes wrong

**The dashboard won't start**
- "python3: command not found" → install Python (link above), close and reopen VS Code.
- "Address already in use" → it's already running in another terminal tab. Use that one, or close it.
- Still stuck: copy the red error text from the terminal and send it to Claude.

**A CSV upload fails or adds nobody**
- Make sure it's a `.csv` (in Excel/Numbers: *Export → CSV*), not `.xlsx`.
- "0 added, X already in the system" means everyone in the file is already there - that's working as intended.
- Lots of *Skipped*? Click *Skipped* on Leads to see the reasons (no phone, too small, wrong title...).

**A call fails**
- No green *Call* buttons → Twilio isn't set up, or a value in `.env` is missing. Re-check steps 3-8 below, restart.
- Says "too late/early" → it's outside 8am-8pm in that person's time zone. That's the safety rule working.
- "Could not connect to Twilio" → a key in `.env` is wrong (often a space at the end), or your Twilio balance is $0.
- Call rings but you hear nothing / they can't hear you → your browser blocked the microphone. Click the
  lock icon left of the address bar → Microphone → Allow, reload. Use Chrome.
- You hear "This call is not allowed" → `DIAL_SECRET` in `.env` and in the Twilio Function don't match exactly.
  Fix, *Deploy All* again in Twilio, restart the dashboard.
- Calls connect but nobody ever answers → your number may be flagged as spam. Check the *By phone number*
  table on Analytics, finish Twilio step 9 (business registration), and rest that number for a few days.
- Anything else → Twilio Console → *Monitor → Logs → Calls* shows each call and why it failed.

**I set the wrong result** → on the Dialer just pick the right one (the old one is kept but ignored).
On the Leads page, open the person → *History* → *mark as mistake*.

---

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

---

## Cold-calling rules (read this)

*This is a plain-English summary for US business-to-business calling, not legal advice. Before you scale
up (more callers, thousands of calls a month, or calling outside the US), spend an hour with a lawyer who
knows the TCPA. These rules change - the FCC updates them often.*

### What the dashboard already does for you
- **Calling hours:** it won't ring anyone outside **8am-8pm in their own time zone**
  (federal rule for personal phones is 8am-9pm; some states are stricter, so 8pm is the safe line).
- **No harassment by design:** a miss gets **one** more try the next day, then the person drops off.
  *Not Interested* and *Do Not Call* are final - they never come back on the list.
- **Do Not Call result:** if anyone says "don't call me again", pick **Do Not Call**. You are required to
  honour it, and the dashboard will never show them again (and re-importing the same person is caught as a duplicate).
- **A human on every call:** one call at a time, started by you, no recorded messages. That keeps it out of
  "robocall" territory.
- **Honest caller ID:** calls come from numbers you own and paid for. Local area codes are fine; faking
  someone else's number is illegal.

### What you must do yourself
1. **Say who you are** at the start: your name and "from Navigara". Never pretend to be someone else or
   imply you already have a relationship with them.
2. **Mobile numbers are the risky ones.** Apollo often gives personal cell phones. A cell phone is usually treated as a
   *personal* line even when it's an executive's, so:
   - Prefer direct office lines when you have them (the dashboard already gives these extra points).
   - Before calling a batch of mobile numbers, check them against the **National Do Not Call Registry**
     (https://telemarketing.donotcall.gov - registering is free for up to 5 area codes). Mark anyone on
     it as *Do Not Call*.
3. **Never use recorded or AI voices** to call or to leave voicemails. Since 2024 the FCC treats AI-generated
   voices as "artificial", which needs the person's written consent first - something Navigara, as an AI
   company, should be extra careful about. Always speak yourself, and leave voicemails live.
4. **Don't record calls** unless you tell the other person first. California (Bay Area!) and several other
   states require *everyone* on the call to agree. The dashboard does not record.
5. **Register your numbers** (Twilio step 9: Trust Hub business profile + SHAKEN/STIR). It's not optional in
   practice: unregistered numbers get labelled "Spam Likely" and blocked.
6. **Follow-up emails** ("Send Info") must follow CAN-SPAM: your real name and company, a working way to
   unsubscribe, and Navigara's postal address in the footer. Honour unsubscribes within 10 business days.
7. **Personal data:** the names and numbers you import are personal information. Keep the laptop locked,
   don't share exports, and if someone (especially in California) asks you to delete their details, do it -
   ask Claude to add a "forget this person" button when you need it.
8. **Stay in your lane:** this setup is for calling businesses in the US only (the dashboard skips other
   countries). Calling consumers, or other countries (UK, EU, Canada), comes with different, stricter rules.

### Good habits that also make calls work better
- Ask early: *"Is now a bad time?"* - and if it is, offer to call back.
- If they say no twice, thank them and end the call.
- Keep notes honest and keep your promises (if you said "I'll email you", do it that day).
- Twilio's own rules (Acceptable Use Policy) also apply - breaking the rules above can get your account
  and numbers shut down.
