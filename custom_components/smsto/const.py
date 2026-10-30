"""Constante pentru integrarea SMS.to."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "smsto"
NAME = "SMS.to"

# ── Config entry ──
CONF_API_KEY = "api_key"
CONF_SENDER_ID = "sender_id"
# Numărul folosit pentru calculul costului unui SMS (estimare, nu se trimite nimic).
# Lipsește când expeditorul e un număr de telefon — atunci se folosește expeditorul.
CONF_COST_NUMBER = "cost_number"

# ── API ──
URL_BALANCE = "https://auth.sms.to/api/balance"
URL_SEND = "https://api.sms.to/sms/send"
URL_ESTIMATE = "https://api.sms.to/sms/estimate"
URL_LAST_MESSAGE = "https://api.sms.to/v2/last/message"
URL_MESSAGES = "https://api.sms.to/v2/messages"
URL_LAST_CAMPAIGN = "https://api.sms.to/v2/last/campaign"
URL_CAMPAIGNS = "https://api.sms.to/v2/campaigns"
URL_MONTHLY_USAGE = "https://api.sms.to/v1/reports/monthly-usage"
URL_INBOUND = "https://app.sms.to/v1/recent/inbound-sms"
URL_OPTOUTS = "https://app.sms.to/v1/recent/optouts"

TIMEOUT = 20

# ── Actualizare ──
UPDATE_INTERVAL = timedelta(minutes=10)
# Cheia API se cere din nou abia dacă SMS.to o refuză (la sold, endpoint-ul care o validează) fără
# întrerupere atâta timp: un 401 izolat (eroare trecătoare la SMS.to) nu mai deconectează contul.
AUTH_REFUSAL_GRACE = timedelta(minutes=15)
# Un refuz al soldului se reîncearcă o dată, după atâtea secunde
AUTH_RETRY_DELAY = 2
# Se schimbă rar: costul per SMS și raportul lunii trecute se recitesc o dată pe oră
SLOW_REFRESH = timedelta(hours=1)
# API-ul de mesaje întoarce cel mult 31 de zile; cerem 30, cu cel mult atâtea mesaje
MESSAGES_DAYS = 30
MESSAGES_LIMIT = 1000
CAMPAIGNS_LIMIT = 100

# ── Stări (chei de traducere, litere mici) ──
# Statusurile mesajelor SMS.to (support.sms.to, „SMS Statuses")
MESSAGE_STATUSES = [
    "delivered",
    "sent",
    "sending",
    "queued",
    "scheduled",
    "failed",
    "expired",
    "rejected",
    "unsubscribed",
    "unknown",
]
# Statusuri finale nereușite (pentru „eșuate" în statistici)
FAILED_STATUSES = {"failed", "expired", "rejected", "unsubscribed"}
PENDING_STATUSES = {"sent", "sending", "queued", "scheduled"}

CAMPAIGN_STATUSES = ["done", "scheduled", "sending", "canceled", "unknown"]
CAMPAIGN_STATUS_ALIASES = {
    "done": "done",
    "completed": "done",
    "scheduled": "scheduled",
    "sending": "sending",
    "ongoing": "sending",
    "in_progress": "sending",
    "processing": "sending",
    "canceled": "canceled",
    "cancelled": "canceled",
}

# Mesajul special care nu se trimite (pentru testarea automatizărilor)
TEST_MESSAGE = "TEST_MESSAGE"
