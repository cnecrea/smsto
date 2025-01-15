![icon](https://github.com/user-attachments/assets/a489906a-98ae-466e-962f-744a6cc497ae)

# 📲 SMS Notifications via SMS.to

**SMS Notifications via SMS.to** is a custom integration for [Home Assistant](https://www.home-assistant.io/) that enables sending SMS notifications directly through the **SMS.to** service.

---

## 🔧 Features

✅ Send SMS notifications via SMS.to directly from Home Assistant.  
✅ Configure SMS notifications through Home Assistant's UI.  
✅ Two built-in sensors:  
   - **`sensor.smsto_balance`**: Displays the current SMS.to account balance in EUR.  
   - **`sensor.smsto_total_sms_sent`**: Shows the total number of SMS messages sent via SMS.to.

✅ Customize notifications with:  
   - **Title** (optional).  
   - **Recipients** (one or more phone numbers).  
   - **Additional Data** for platform-specific functionalities (e.g., `callback_url`).  

---

## 🚀 Installation

### 1. Via HACS (Home Assistant Community Store)

1. Go to **HACS** > **Integrations**.
2. Click the three-dot menu in the top right and select **Custom Repositories**.
3. Add this repository's URL (`https://github.com/cnecrea/smsto`) as a custom repository.
4. Search for `SMS notifications via SMS.to` and click **Download**.
5. Restart Home Assistant after installation.

### 2. Manual Installation

1. Download this repository as a ZIP file.
2. Extract the contents and copy the folder `smsto` into:  
   `config/custom_components/`.
3. Restart Home Assistant after installation.

---

## ⚙️ Configuration

1. Navigate to **Settings** > **Devices & Services** > **Add Integration**.  
2. Search for `SMS notifications via SMS.to`.  
3. Enter your **API Key** and **Sender ID** (obtained from your SMS.to account).  

---

## 🛠️ Usage

### Automation (YAML):

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

## 📊 Built-in Sensors

After setting up the integration, you will have access to the following sensors:

`sensor.balance`

**Description: Displays your SMS.to account balance.**
> Attributes:
- [x] friendly_name: “Balance”
- [x] unit_of_measurement: “EUR”
- [x] icon: mdi:cash

`sensor.total_sms_sent`

**Description: Shows the total number of SMS messages sent.**
> Attributes:
- [x] friendly_name: “Total SMS Sent”
- [x] icon: mdi:message-text-outline

Creating a Lovelace Card for Sensors
```yaml
type: entities
title: SMS.to Account Status
entities:
  - entity: sensor.balance
  - entity: sensor.total_sms_sent
```
This card will display the account balance and the total number of SMS sent directly in your Home Assistant dashboard.

## 🔑 Requirements
- An active SMS.to account. 
- A valid API Key and configured Sender ID from SMS.to. 

---
## ☕ Support the Developer

If you enjoyed this integration and want to support the work behind it, **buy me a coffee**! 🫶  
It costs nothing, and your contribution helps with future development. 🙌  

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support%20the%20developer-orange?style=for-the-badge&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/cnecrea)

Thank you for your support, and I truly appreciate every gesture of encouragement! 🤗

---


## 🧑‍💻 Contributions
- Contributions are welcome! Create a pull request or report issues [here](https://github.com/cnecrea/smsto/issues).

## 🌟 Support
- If you like this integration, give it a ⭐ on [GitHub](https://github.com/cnecrea/smsto/)! 😊
