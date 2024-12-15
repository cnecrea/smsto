"""Config flow for SMS.to notify service."""
from homeassistant import config_entries
import voluptuous as vol
import logging

from .const import DOMAIN
from .notify import SMSToNotificationService

_LOGGER = logging.getLogger(__name__)


class SmstoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMS.to."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        _LOGGER.debug("Starting SMS.to configuration flow.")
        errors = {}

        if user_input is not None:
            _LOGGER.debug("User input received: %s", user_input)

            api_key = user_input.get("api_key")
            sender_id = user_input.get("sender_id")

            # Validate inputs
            if not api_key or len(api_key.strip()) < 10:
                errors["base"] = "invalid_api_key"
                _LOGGER.error("Invalid API Key provided.")

            if not sender_id or len(sender_id.strip()) < 5:
                errors["base"] = "invalid_sender_id"
                _LOGGER.error("Invalid Sender ID provided.")

            if not errors:
                # Check for an existing entry
                existing_entry = await self.async_set_unique_id(sender_id)
                if existing_entry:
                    self.hass.config_entries.async_update_entry(
                        existing_entry,
                        data={"api_key": api_key, "sender_id": sender_id},
                    )
                    await self.hass.config_entries.async_reload(existing_entry.entry_id)
                    _LOGGER.debug("Updated existing entry with new data.")
                    return self.async_abort(reason="already_configured")

                # Store data and proceed to the test message step
                self.api_key = api_key
                self.sender_id = sender_id
                return await self.async_step_test_message()

        # Define the schema for user input
        data_schema = vol.Schema(
            {
                vol.Required("api_key"): str,
                vol.Required("sender_id"): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_test_message(self, user_input=None):
        """Step to send a test message."""
        _LOGGER.debug("Test Message step initiated.")
        errors = {}

        if user_input is not None:
            test_number = user_input.get("test_number")
            if not test_number or len(test_number.strip()) < 5:
                errors["base"] = "invalid_test_number"
                _LOGGER.error("Invalid test number provided.")
            else:
                # Try sending a test message
                try:
                    service = SMSToNotificationService(self.api_key, self.sender_id)
                    await service.async_send_message(
                        message="Test SMS from Home Assistant integration.",
                        target=[test_number],
                    )
                    _LOGGER.debug("Test message sent successfully.")
                    return self.async_create_entry(
                        title=f"SMSSID ({self.sender_id})",
                        data={"api_key": self.api_key, "sender_id": self.sender_id},
                    )
                except Exception as e:
                    _LOGGER.error("Failed to send test message: %s", e)
                    errors["base"] = "test_message_failed"

        # Schema for test message step
        data_schema = vol.Schema(
            {
                vol.Required("test_number"): str,
            }
        )
        return self.async_show_form(step_id="test_message", data_schema=data_schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return SmstoOptionsFlowHandler(config_entry)


class SmstoOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle the options flow for SMS.to."""

    def __init__(self, config_entry):
        """Initialize the options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options for SMS.to."""
        if user_input is not None:
            _LOGGER.debug("Updating options with: %s", user_input)

            # Update the entry data and title
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=user_input,
                title=f"SMS.to ({user_input['sender_id']})",  # Update the title
            )

            # Log the updated entry details
            _LOGGER.debug("Entry updated: Title - %s, Data - %s", f"SMS.to ({user_input['sender_id']})", user_input)

            return self.async_create_entry(title="", data={})

        # Load current data
        current_data = self.config_entry.data

        options_schema = vol.Schema(
            {
                vol.Required("api_key", default=current_data.get("api_key", "")): str,
                vol.Required("sender_id", default=current_data.get("sender_id", "")): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
