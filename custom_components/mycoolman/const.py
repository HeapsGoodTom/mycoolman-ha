"""Constants for the myCOOLMAN integration."""

DOMAIN = "mycoolman"

CONF_PIN = "pin"

# How often to poke the fridge for a fresh frame (also acts as a keepalive /
# reconnect trigger). Status also arrives asynchronously via notifications.
UPDATE_INTERVAL_SECONDS = 30

# Setpoint range exposed to the number entity. Adjust to your model.
MIN_TEMP = -20
MAX_TEMP = 20
