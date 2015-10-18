# Rename this file to config.py and insert your token and password

# Name of the Telgram bot (ending with 'bot', without leading '@')
NAME = ""

# Token of your Telegram bot (Given to you by @BotFather)
TOKEN = ""

# Password you need in order to communiate with the bot
# Must be used like "/start <password>"
PASSWORD = ""

# Long polling timeout in seconds
TIMEOUT = 60 * 5

# The bot will send a push message if any of the conditions succeeds
ENABLE_NOTIFICATIONS = True

# Number of seconds between push messages
NOTIFCATION_INTERVAL = 60

# Maximum cpu percent considered to be normal
NOTIFY_CPU_PERCENT = 50

# Maximum memory percent considered to be normal
NOTIFY_RAM_PERCENT = 50

# DO NOT EDIT BELOW THIS LINE
# ===========================
API_URL = "https://api.telegram.org/bot" + TOKEN + "/"
