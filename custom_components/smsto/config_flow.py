"""Config flow for SMS.to integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_API_KEY, CONF_SENDER_ID, DOMAIN
from .notify import SMSToNotificationService

_LOGGER = logging.getLogger(__name__)


class SmstoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMS.to."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.api_key: str = ""
        self.sender_id: str = ""

    async def async_step_user(self, user_input=None):
        """Handle the initial configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input.get(CONF_API_KEY, "").strip()
            sender_id = user_input.get(CONF_SENDER_ID, "").strip()

            if not api_key or len(api_key) < 10:
                errors["base"] = "invalid_api_key"
                _LOGGER.debug("Validation failed: API key too short or empty.")

            if not sender_id or len(sender_id) < 5:
                errors["base"] = "invalid_sender_id"
                _LOGGER.debug("Validation failed: Sender ID too short or empty.")

            if not errors:
                # Set unique ID and abort if already configured
                await self.async_set_unique_id(sender_id)
                self._abort_if_unique_id_configured(
                    updates={CONF_API_KEY: api_key, CONF_SENDER_ID: sender_id}
                )

                # Store for the test step
                self.api_key = api_key
                self.sender_id = sender_id
                return await self.async_step_test_message()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_SENDER_ID): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_test_message(self, user_input=None):
        """Step to send a test message and verify the configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            test_number = user_input.get("test_number", "").strip()

            if not test_number or len(test_number) < 5:
                errors["base"] = "invalid_test_number"
                _LOGGER.debug("Validation failed: test number too short or empty.")
            else:
                try:
                    session = async_get_clientsession(self.hass)
                    service = SMSToNotificationService(
                        self.api_key, self.sender_id, session
                    )
                    await service.async_send_message(
                        message="Test SMS from Home Assistant integration.",
                        target=[test_number],
                    )
                    _LOGGER.debug("Test message sent successfully to %s.", test_number)

                    return self.async_create_entry(
                        title=f"SMSSID ({self.sender_id})",
                        data={
                            CONF_API_KEY: self.api_key,
                            CONF_SENDER_ID: self.sender_id,
                        },
                    )
                except Exception as err:
                    _LOGGER.error("Test message failed: %s", err)
                    errors["base"] = "test_message_failed"

        data_schema = vol.Schema(
            {
                vol.Required("test_number"): str,
            }
        )
        return self.async_show_form(
            step_id="test_message", data_schema=data_schema, errors=errors
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return SmstoOptionsFlowHandler()


class SmstoOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle the options flow for SMS.to."""

    async def async_step_init(self, user_input=None):
        """Manage SMS.to options."""
        if user_input is not None:
            _LOGGER.debug("Options updated: Sender ID = %s", user_input.get(CONF_SENDER_ID))

            # Update the config entry data and title
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=user_input,
                title=f"SMS.to ({user_input[CONF_SENDER_ID]})",
            )

            return self.async_create_entry(title="", data={})

        current_data = self.config_entry.data

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_API_KEY, default=current_data.get(CONF_API_KEY, "")
                ): str,
                vol.Required(
                    CONF_SENDER_ID, default=current_data.get(CONF_SENDER_ID, "")
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=options_schema)
