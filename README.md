![icon](https://github.com/user-attachments/assets/a489906a-98ae-466e-962f-744a6cc497ae)

# 📲 SMS Notifications via SMS.to

**SMS Notifications via SMS.to** is a custom integration for [Home Assistant](https://www.home-assistant.io/) that enables sending SMS notifications directly through the **[SMS.to](https://sms.to)** service.

---

## 🔧 Features

✅ Send SMS notifications via SMS.to directly from Home Assistant.  
✅ Configure through Home Assistant's UI with a **test message** to verify your setup.  
✅ **Reconfigure** API Key and Sender ID at any time via the Options flow.  
✅ Two built-in sensors updated automatically every 5 minutes:  
   - **Balance** — current SMS.to account balance (EUR).  
   - **Total SMS Sent** — total number of SMS messages sent.  

✅ Customize notifications with:  
   - **Title** (optional — prepended to the message).  
   - **Recipients** (one or more phone numbers in international format).  
   - **Additional Data** for platform-specific options (e.g., `callback_url`, `priority`).  

---

## 🚀 Installation

### Via HACS (recommended)

1. Go to **HACS** → **Integrations**.  
2. Click the three-dot menu → **Custom Repositories**.  
3. Add `https://github.com/cnecrea/smsto` as a custom repository (category: Integration).  
4. Search for **SMS notifications via SMS.to** and click **Download**.  
5. Restart Home Assistant.  

### Manual Installation

1. Download this repository as a ZIP file.  
2. Extract and copy the `smsto` folder into `config/custom_components/`.  
3. Restart Home Assistant.  

---

## ⚙️ Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**.  
2. Search for **SMS notifications via SMS.to**.  
3. Enter your **API Key** and **Sender ID** (from your [SMS.to dashboard](https://app.sms.to/api-keys)).  
4. Enter a **phone number** to receive a test SMS — this verifies your configuration before saving.  

### Reconfiguration

To update your API Key or Sender ID after setup:  
1. Go to **Settings** → **Devices & Services**.  
2. Find the SMS.to integration and click **Configure**.  
3. Update the values and save.  

---

## 🛠️ Usage

### Automation (YAML)

```yaml
action: notify.smsto
data:
  message: "The garage door is open!"
  target:
    - "+1234567890"
    - "+0987654321"
  data:
    callback_url: "https://example.com/alert"
```

### Developer Tools

Go to **Developer Tools** → **Actions**, select `notify.smsto`, fill in the fields, and click **Perform action**.

---

## 📊 Built-in Sensors

After setup, the integration creates a device **SMS Notifications via SMS.to** with two sensors:

| Sensor | Description | Unit | Icon |
|--------|-------------|------|------|
| **Balance** | Current SMS.to account balance | EUR | `mdi:cash` |
| **Total SMS Sent** | Total number of SMS messages sent | — | `mdi:message-text-outline` |

> **Note:** Sensor data is refreshed automatically every **5 minutes** via a DataUpdateCoordinator.

### Lovelace Card Example

```yaml
type: entities
title: SMS.to Account Status
entities:
  - entity: sensor.sms_notifications_via_sms_to_balance
  - entity: sensor.sms_notifications_via_sms_to_total_sms_sent
```

> **Tip:** Your actual entity IDs may differ. Check **Settings** → **Devices & Services** → **SMS Notifications via SMS.to** → **Entities** to find the correct IDs.

---

## 🔑 Requirements

- An active [SMS.to](https://sms.to) account.  
- A valid **API Key** (generate one at [app.sms.to/](https://app.sms.to)).  
- A configured **Sender ID** (phone number or alphanumeric ID).  

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
