"""Constants for the SMS.to integration."""

DOMAIN = "smsto"

CONF_API_KEY = "api_key"
CONF_SENDER_ID = "sender_id"

API_URL_SEND = "https://api.sms.to/sms/send"
API_URL_BALANCE = "https://auth.sms.to/api/balance"
API_URL_MESSAGES = "https://api.sms.to/v2/messages"

DEFAULT_TIMEOUT = 10
UPDATE_INTERVAL_MINUTES = 5

ERROR_MESSAGES = {
    400: "Bad request. Please check your payload.",
    401: "Unauthorized. Verify your API key.",
    403: "Forbidden. You may not have permission to send SMS.",
    404: "Resource not found. Check the API endpoint.",
    429: "Rate limit exceeded. Please try again later.",
    500: "Internal server error. Try again later.",
}
DEFAULT_ERROR_MESSAGE = "An unknown error occurred. Please check the logs."
