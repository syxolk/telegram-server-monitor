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

# Initial timeout for retry after ConnectionError from the server
# timeout will be multiplied by 2 every retry to avoid annoing behavior
SERVER_RETRY_TIMEOUT = 10

# The bot will send a push message if any of the conditions succeeds
ENABLE_NOTIFICATIONS = True

# Number of seconds between push messages
NOTIFCATION_INTERVAL = 60

# Maximum cpu percent considered to be normal
NOTIFY_CPU_PERCENT = 50

# Maximum memory percent considered to be normal
NOTIFY_RAM_PERCENT = 50

# Maximum pids used for all processes and threads in precent
NOTIFY_PID_PERCENT = 50

# Maximum FDs used in percent
NOTIFY_FD_PERCENT = 50

# List all disks. When set to False, python
# tries to avoid listing "non physical devices"
ALL_DISKS = False

# DO NOT EDIT BELOW THIS LINE
# ===========================
API_URL = "https://api.telegram.org/bot" + TOKEN + "/"
