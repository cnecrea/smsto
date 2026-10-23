# SMS Notifications via SMS.to — Integrare Home Assistant

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.11%2B-41BDF5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/cnecrea/smsto)](https://github.com/cnecrea/smsto/releases)
[![GitHub Stars](https://img.shields.io/github/stars/cnecrea/smsto?style=flat&logo=github)](https://github.com/cnecrea/smsto/stargazers)
[![Instalări](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/cnecrea/smsto/main/statistici/shields/descarcari.json)](https://github.com/cnecrea/smsto)
[![Ultima versiune](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/cnecrea/smsto/main/statistici/shields/ultima_release.json)](https://github.com/cnecrea/smsto/releases/latest)


**SMS Notifications via SMS.to** is a custom integration for [Home Assistant](https://www.home-assistant.io/) that sends SMS notifications through **[SMS.to](https://sms.to)** and shows the state of your SMS.to account: balance, how many SMS you can still send, what you spent this month and how your messages were delivered.

The account data is read-only. The integration sends an SMS only when you call `notify.smsto` — setup and reconfiguration never send anything.

---

## 🔧 Features

✅ **Send SMS** from automations and scripts with `notify.smsto` — one or more recipients, optional title.  
✅ **Setup without a test SMS** — the API key is checked by reading your balance, and the cost of an SMS by SMS.to's free estimate.  
✅ **Sender as phone number or name** — a number (`+40712345678`) or an alphanumeric name of up to 11 characters (`HomeAssist`).  
✅ **10 sensors per account** — balance, available SMS, cost per SMS, last SMS, SMS and cost this month, messages in the last 30 days, last campaign, received SMS, opt-outs.  
✅ **Monthly statistics** — "SMS sent this month" and "Cost this month" reset on the 1st of the month and show correctly in Home Assistant's long-term statistics.  
✅ **Several SMS.to accounts** — each sender is a separate entry with its own device; `notify.smsto` can pick the account per call.  
✅ **Reconfigure** the API key, sender or cost number at any time, from the **Configure** button or **⋮ → Reconfigure**.  
✅ **Re-authentication** — if SMS.to rejects the API key, Home Assistant asks for a new one; no need to delete the integration.  
✅ **Keeps working through hiccups** — if one SMS.to endpoint doesn't answer, the other sensors keep their last values.  
✅ **Privacy** — phone numbers in attributes, diagnostics and logs are masked (`+40742•••070`); the API key and message text never appear.  
✅ **Translations** — English and Romanian.  

---

## 📡 Data source

All data comes from the official [SMS.to API](https://developers.sms.to/), authenticated with your API key:

| Endpoint | Used for | Refresh |
|----------|----------|---------|
| `auth.sms.to/api/balance` | Balance and currency | every 10 minutes |
| `api.sms.to/sms/estimate` | Cost of one SMS (free, nothing is sent) | every hour |
| `api.sms.to/v1/reports/monthly-usage` | SMS and cost this month / last month | 10 minutes / every hour |
| `api.sms.to/v2/last/message` | Last SMS | every 10 minutes |
| `api.sms.to/v2/messages` | Messages in the last 30 days | every 10 minutes |
| `api.sms.to/v2/last/campaign`, `v2/campaigns` | Last campaign, total campaigns | every 10 minutes |
| `app.sms.to/v1/recent/inbound-sms` | Received SMS | every 10 minutes |
| `app.sms.to/v1/recent/optouts` | Recent opt-outs | every 10 minutes |
| `api.sms.to/sms/send` | Sending — only from `notify.smsto` | on demand |

After every SMS sent with `notify.smsto`, the sensors refresh immediately.

---

## 🚀 Installation

### Via HACS (recommended)

1. Open **HACS** in Home Assistant.  
2. Click the three-dot menu → **Custom repositories**.  
3. Add `https://github.com/cnecrea/smsto` with the type **Integration**.  
4. Search for **SMS Notifications via SMS.to** and click **Download**.  
5. Restart Home Assistant.  

### Manual installation

1. Download this repository as a ZIP file.  
2. Copy the `custom_components/smsto` folder into `config/custom_components/`.  
3. Restart Home Assistant.  

---

## ⚙️ Configuration

### Step 1 — API key and sender

1. Go to **Settings** → **Devices & services** → **Add integration**.  
2. Search for **SMS Notifications via SMS.to**.  
3. Fill in:  
   - **API key** — from [app.sms.to](https://app.sms.to) → **Settings** → **API keys**.  
   - **Sender** — the sender your messages are sent from:  
     - a **phone number** in international format (`+40712345678`), or  
     - a **name** of up to 11 letters and digits (`HomeAssist`), if your SMS.to account allows alphanumeric senders.  

The API key is checked by reading your balance. If the sender is a phone number, it is also used to calculate the cost of an SMS (SMS.to's estimate is free and sends nothing).

### Step 2 — Number for the SMS cost (only for a name sender)

A name can't be used to calculate the cost of an SMS, so the integration asks for a phone number in the country you usually send to. **Nothing is sent to it.** You can leave it empty — then **Cost per SMS** and **Available SMS** stay unknown.

### Reconfiguration

To change the API key, the sender or the number for the cost:

- **Settings** → **Devices & services** → **SMS.to** → **Configure**, or  
- the **⋮** menu of the entry → **Reconfigure**.  

The new values are checked the same way (nothing is sent) and the integration reloads.

### Re-authentication

If you revoke or regenerate the API key in SMS.to, Home Assistant asks you to re-authenticate the entry (**Settings** → **Devices & services**). Enter the new key and the integration continues with the same sensors and history.

### Several accounts

Add the integration again with another sender. Each entry gets its own device (named **SMS.to**, with the sender as model) and its own sensors. A sender can be configured only once.

---

## 🛠️ Sending SMS — `notify.smsto`

| Field | Required | Description |
|-------|----------|-------------|
| `message` | yes | The SMS text. |
| `target` | yes | One or more phone numbers in international format. |
| `title` | no | Added above the message, followed by an empty line. |
| `data` | no | Extra options, see below. |

Options in `data`:

| Key | Description |
|-----|-------------|
| `sender_id` | Send from this sender. If one of your SMS.to entries uses it, that entry's API key is used; otherwise the first entry sends with this sender (it must be allowed in your SMS.to account). |
| `callback_url` | SMS.to calls this URL with the delivery status. |
| other keys | Passed unchanged to the SMS.to send API. |

### Basic example

```yaml
action: notify.smsto
data:
  title: "Garage"
  message: "The garage door is open!"
  target:
    - "+40712345678"
    - "+40787654321"
```

### Choosing the account

```yaml
action: notify.smsto
data:
  message: "Alarm triggered"
  target: "+40712345678"
  data:
    sender_id: "HomeAssist"
```

### Testing an automation without sending

If `message` is exactly `TEST_MESSAGE`, the call is accepted but nothing is sent (only an info line is logged). Useful for testing automations without paying for an SMS.

```yaml
action: notify.smsto
data:
  message: "TEST_MESSAGE"
  target: "+40712345678"
```

You can also try it from **Developer tools** → **Actions** → `notify.smsto`.

---

## 📊 Sensors

Each account has a device **SMS.to** with these sensors:

| Sensor | State | Unit | Enabled by default |
|--------|-------|------|:------------------:|
| **Balance** | Account balance | account currency (EUR) | ✅ |
| **Available SMS** | How many SMS the balance still covers | — | ✅ |
| **Cost per SMS** | Price of one SMS to the cost number | account currency | ✅ |
| **Last SMS** | Status of the last message | — | ✅ |
| **SMS sent this month** | Messages billed this month | — | ✅ |
| **Cost this month** | Amount billed this month | account currency | ✅ |
| **Messages in the last 30 days** | Number of messages | — | ✅ |
| **Last campaign** | Status of the last campaign | — | ✅ |
| **SMS received (last hour)** | Inbound SMS | — | ❌ |
| **Recent opt-outs** | Numbers that unsubscribed | — | ❌ |

The last two are disabled by default: inbound SMS needs a number rented from SMS.to, and opt-outs matter only for marketing campaigns. Enable them from the entity settings if you need them.

### Balance

The current balance of the SMS.to account, in the account currency.

### Available SMS

`balance ÷ cost per SMS`, rounded down — how many single-part SMS you can still send to the country of the cost number.

| Attribute | Description |
|-----------|-------------|
| Cost per SMS | Price of one SMS part |
| Parts per message | Parts of the test estimate (1) |
| Calculated for | The cost number (masked) |
| Balance | Current balance |

### Cost per SMS

The price of one SMS part to the cost number (the sender, if it is a phone number, or the number from step 2), from SMS.to's free estimate. Recalculated every hour. Unknown if there is no cost number.

### Last SMS

The status of the last message sent from the account, from the API or from the SMS.to website.

**States:** Delivered, Sent, Sending, Queued, Scheduled, Failed, Expired, Rejected, Unsubscribed, Unknown.

| Attribute | Description |
|-----------|-------------|
| Sent at | Date and time |
| Recipient | Masked number (`+40742•••070`) |
| Cost | Cost of the message |
| Channel | SMS, Flash SMS, Viber, WhatsApp, Telegram |
| Parts | Number of SMS parts |
| Sent via | API or Web |
| Failure reason | Only when SMS.to gives one |
| Status from SMS.to | Only for a status the integration doesn't know |

### SMS sent this month

The number of messages billed this month, from the SMS.to monthly usage report. Resets on the 1st of the month and works with long-term statistics.

| Attribute | Description |
|-----------|-------------|
| Month | Billing month (`2026-10`) |
| By channel | For example `{"SMS": 3}` |
| By country | For example `{"RO": 3}` |
| Last month | Messages last month |
| Cost last month | Amount billed last month |

### Cost this month

The amount billed this month, in the report's currency. Resets on the 1st of the month. Attribute: **Cost last month**.

### Messages in the last 30 days

The number of messages from the last 30 days.

| Attribute | Description |
|-----------|-------------|
| Delivered | Delivered messages |
| Failed | Failed, expired, rejected or unsubscribed |
| Pending | Sent, sending, queued or scheduled |
| Delivery rate (%) | Delivered out of messages with a final status |
| Cost | Total cost |
| Parts | Total SMS parts |
| Via API / Via web | Where the messages were sent from |
| List truncated | Appears only above 1000 messages |

### Last campaign

The status of the last campaign in your SMS.to account.

**States:** Done, Scheduled, Sending, Canceled, Unknown.

| Attribute | Description |
|-----------|-------------|
| Total campaigns | Number of campaigns (`100+` above the first page) |
| Created at | Date and time |
| Sent / Delivered / Failed / Pending | Messages in the campaign |
| Cost | Cost of the campaign |

### SMS received (last hour)

The number of SMS received on a number rented from SMS.to. Attributes: **Last sender** (masked) and **Last received**.

### Recent opt-outs

The number of numbers that recently unsubscribed from your messages.

---

## 🤖 Automation examples

### Warning when the SMS credit runs low

```yaml
alias: SMS.to — low credit
triggers:
  - trigger: numeric_state
    entity_id: sensor.sms_to_available_sms
    below: 50
actions:
  - action: persistent_notification.create
    data:
      title: "SMS.to"
      message: >
        Only {{ states('sensor.sms_to_available_sms') }} SMS left
        ({{ states('sensor.sms_to_balance') }} {{ state_attr('sensor.sms_to_balance', 'unit_of_measurement') }}).
```

### Warning when an SMS wasn't delivered

```yaml
alias: SMS.to — SMS not delivered
triggers:
  - trigger: state
    entity_id: sensor.sms_to_last_sms
    to:
      - failed
      - expired
      - rejected
actions:
  - action: persistent_notification.create
    data:
      title: "SMS.to"
      message: >
        The SMS to {{ state_attr('sensor.sms_to_last_sms', 'recipient') }} was not delivered
        ({{ state_attr('sensor.sms_to_last_sms', 'failed_reason') or states('sensor.sms_to_last_sms') }}).
```

### Dashboard card

```yaml
type: entities
title: SMS.to
entities:
  - entity: sensor.sms_to_balance
  - entity: sensor.sms_to_available_sms
  - entity: sensor.sms_to_last_sms
  - entity: sensor.sms_to_sms_sent_this_month
  - entity: sensor.sms_to_cost_this_month
  - entity: sensor.sms_to_messages_in_the_last_30_days
```

> **Tip:** the entity IDs above are for a Home Assistant in English. They follow the language of your installation (in Romanian: `sensor.sms_to_sold`, `sensor.sms_to_sms_uri_disponibile`, `sensor.sms_to_ultimul_sms` …), get a `_2` suffix for a second account and keep their old names after an upgrade from 2.x. Check yours in **Settings** → **Devices & services** → **SMS.to** → **Entities**.

---

## ⬆️ Upgrading from 2.x

- **No more paid test SMS** at setup — the configuration is checked by reading the balance and the free cost estimate.  
- **The "Total SMS Sent" sensor is removed** (it always showed 0). It is replaced by **SMS sent this month** and **Messages in the last 30 days**.  
- **Balance keeps its entity ID and history.**  
- **Each account has its own device**; the old shared device is removed automatically once its sensors have moved.  
- **`notify.smsto` works as before.** It now picks the account at every call — before, it stayed bound to the first configured account, even after that account was deleted.  
- The sensors refresh every **10 minutes** (cost per SMS and last month: every hour).  

Existing entries keep working after the update; you don't need to reconfigure anything.

---

## 🐞 Diagnostics and debug logging

**Diagnostics:** **Settings** → **Devices & services** → **SMS.to** → **⋮** → **Download diagnostics**. The file contains the balance, the cost estimate and the summaries of the reports — without the API key, with masked phone numbers and without message text.

**Debug logging:** on the integration page, **⋮** → **Enable debug logging**, reproduce the problem, then **Disable debug logging** to download the log. Or permanently, in `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.smsto: debug
```

Every line starts with the sender of the account (`[HomeAssist]` or `[+40712•••678]`) and shows each SMS.to request (address, HTTP status, duration), what each endpoint returned and a summary after every update (the log messages are in Romanian):

```
[HomeAssist] GET https://auth.sms.to/api/balance → HTTP 200 în 142 ms (39 octeți)
[HomeAssist] Actualizare terminată: sold 13.9085 EUR, cost/SMS 0.04 (pentru +40742•••070), luna 2026-10: 3 SMS / 0.12 EUR, …
```

The log never contains the API key, the message text or full phone numbers, so you can attach it to an issue.

---

## ⚠️ Known limitations

- **Messages in the last 30 days** reads at most 1000 messages (the SMS.to API doesn't document pagination); above that, the **List truncated** attribute appears.  
- **Total campaigns** shows `100+` when the account has more than one page of campaigns.  
- **Cost per SMS** is the price of one SMS part to the country and network of the cost number; longer messages or other countries cost differently.  
- **SMS received** works only with a number rented from SMS.to.  
- An SMS.to API key gives access to the whole account: if several entries use the same key, they show the same account data.  

---

## 🔑 Requirements

- Home Assistant **2025.11** or newer.  
- An active [SMS.to](https://sms.to) account with credit.  
- An **API key** from [app.sms.to](https://app.sms.to) → **Settings** → **API keys**.  
- A **sender**: a phone number or an alphanumeric name allowed in your SMS.to account.  

---

## ☕ Support the Developer

If you enjoy this integration, **buy me a coffee**! 🫶  
Your support helps with future development. 🙌  

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support%20the%20developer-orange?style=for-the-badge&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/cnecrea)

Thank you — every gesture of encouragement is truly appreciated! 🤗

---

## 🧑‍💻 Contributions

Contributions are welcome! Create a pull request or report issues [here](https://github.com/cnecrea/smsto/issues).

## 🌟 Support

If you like this integration, give it a ⭐ on [GitHub](https://github.com/cnecrea/smsto/)! 😊
