"""Constants for the myCOOLMAN integration."""

DOMAIN = "mycoolman"

CONF_PIN = "pin"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"

# How often to poke the fridge for a fresh frame (also acts as a keepalive /
# reconnect trigger). Status also arrives asynchronously via notifications.
UPDATE_INTERVAL_SECONDS = 30

# Default setpoint range, confirmed for the single-zone 43. Other models may
# support a different range; the config/options flow lets a user override it
# per entry. These are only the fallback when an entry has no override set.
DEFAULT_MIN_TEMP = -20
DEFAULT_MAX_TEMP = 20
