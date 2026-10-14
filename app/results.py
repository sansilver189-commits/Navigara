"""The call results you can pick. Key (stored in the database) -> label (what you see)."""
RESULTS = {
    "no_answer": "No Answer",
    "left_voicemail": "Left Voicemail",
    "gatekeeper": "Gatekeeper",
    "not_interested": "Not Interested",
    "call_later": "Call Later",
    "send_info": "Send Info",
    "booked": "Booked",
    "wrong_number": "Wrong Number",
    "showed": "Showed",      # logged later from the Leads page
    "signed": "Signed",      # logged later from the Leads page
}

# Shown on the Dialer's result picker.
DIALER_RESULTS = [k for k in RESULTS if k not in ("showed", "signed")]

# Didn't reach the person: the lead comes back the next day, once.
RETRY_ONCE = {"no_answer", "left_voicemail", "gatekeeper"}

# A human picked up (counts toward answer rate).
ANSWERED = {"gatekeeper", "not_interested", "call_later", "send_info", "booked", "wrong_number"}
