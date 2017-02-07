import requests
import datetime
import psutil
import config
import persistence
import time
import socket

last_notification = 0
storage = persistence.Persistence()

# thanks to https://web.archive.org/web/20111010015624/http://blogmag.net/blog/read/38/Print_human_readable_file_size
def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def processMessage(message):
    if "text" in message:
        processTextMessage(message)

def processTextMessage(message):
    text = message["text"]

    if text.startswith("/"):
        processCommandMessage(message)

def processCommandMessage(message):
    text = message["text"]

    if " " in text:
        command, parameter = text.split(" ", 1)
    else:
        command = text
        parameter = ""

    if "@" in command:
        command, botname = command.split("@", 1)
        if botname.lower() != config.NAME.lower():
            # Ignore messages for other bots
            return

    if command == "/start":
        commandStart(message, parameter)
    elif command == "/stop":
        commandStop(message)
    elif command == "/help":
        commandHelp(message)
    elif command == "/usage":
        commandUsage(message)
    elif command == "/users":
        commandUsers(message)
    elif command == "/disks":
        commandDisks(message)
    elif command == "/ports":
        commandPorts(message)
    else:
        sendTextMessage(message["chat"]["id"], "I do not know what you mean by '{0}'".format(command))

def sendTextMessage(chat_id, text):
    r = requests.post(config.API_URL + "sendMessage", json={
        "chat_id" : chat_id,
        "text" : text
    })

    result = r.json()
    if not result["ok"]:
        print(result)

def sendAuthMessage(chat_id):
    sendTextMessage(chat_id, "Please sign in first.")

def startupMessage():
    for id in storage.allUsers():
        sendTextMessage(id, "Hello there. I just started.")

def shutdownMessage():
    for id in storage.allUsers():
        sendTextMessage(id, "I am shutting down.")

def commandStart(message, parameter):
    chat_id = message["chat"]["id"]
    if storage.isRegisteredUser(chat_id):
        sendTextMessage(chat_id, "You are signed in. Thank you.")
    else:
        if parameter.strip() == config.PASSWORD:
            storage.registerUser(chat_id)
            sendTextMessage(chat_id, "Thanks for signing up. " +
                "Type /help for information.")
        else:
            sendTextMessage(chat_id, "Please provide a valid password. " +
                "Type /start <password> to sign in.")

def commandStop(message):
    chat_id = message["chat"]["id"]
    if storage.isRegisteredUser(chat_id):
        storage.unregisterUser(chat_id)
        sendTextMessage(chat_id, "You signed off. You will no longer receive any messages from me.")
    else:
        sendAuthMessage(chat_id)

def commandHelp(message):
    chat_id = message["chat"]["id"]
    sendTextMessage(chat_id, config.NAME + """
Monitor your server and query usage and network information.

/usage - CPU and Memory information
/users - Active users
/disks - Disk usage
/ports - Open network ports

You do not like me anymore?
/stop - Sign off from the monitoring service
""")

def commandUsage(message):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id)
        return

    text = " ** USAGE **\n"
    try:
        text += "Uptime: {0}\n".format(
str(datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())))
    except BaseException as be:
        text += "Getting uptime failed: {0}\n".format(str(be))

    try:
        text += "CPU: {0} %\n".format(psutil.cpu_percent())
    except BaseException as be:
        text += "Getting CPU failed: {0}\n".format(be)

    try:
        text += "RAM: {0} %\n".format(psutil.virtual_memory().percent)
    except BaseException as be:
        text += "Getting RAM failed: {0}\n".format(be)

    try:
        text += "Swap: {0}".format(psutil.swap_memory().percent)
    except BaseException as be:
        text += "Getting Swap info failed: {0}".format(be)

    sendTextMessage(chat_id, text)

def commandUsers(message):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id)
        return

    text = " ** USERS **\n"
    try:
        for user in psutil.users():
            text += "{0}@{1} {2}\n".format(user.name, user.host, str(datetime.datetime.fromtimestamp(user.started)))
    except BaseException as be:
        text += "Getting user info failed: {0}".format(be)

    sendTextMessage(chat_id, text)

def prettyPrintFamily(f):
    # converting to string as the values are equal for all?!
    families = { str(socket.AF_INET)   :"TCPv4"
               , str(socket.AF_INET6)  :"TCPv6"
               , str(socket.AF_UNIX)   :"Unix"
               , str(socket.SOCK_DGRAM):"UDP"
               }
    for type in families.keys():
        if str(f) == type: return families[type]
    return str(f)

def commandPorts(message):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id)
        return

    text = " ** Listening Ports **\n"
    try:
        for c in psutil.net_connections():
            if c.status == "LISTEN":
                text += "* {0} ({1})\n".format(c.laddr[1], prettyPrintFamily(c.family))

    except BaseException as be:
        text += "Getting port info failed: {0}".format(be)

    sendTextMessage(chat_id, text)

def commandDisks(message):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id)
        return

    text = " ** DISKS **\n"
    num = 0
    try:
        for dev in psutil.disk_partitions(config.ALL_DISKS):
            num += 1
            if len(dev.device) == 0: continue
            usage = psutil.disk_usage(dev.mountpoint)
            text += "{0} ({1}) {2} % (free: {3})\n".format(dev.device
                , dev.mountpoint
                , usage.percent
                , sizeof_fmt(usage.free)
                )
    except BaseException as be:
        text += "Getting disk info failed: {0}".format(be)

    if num == 0:
        text += "No disks found!?"

    sendTextMessage(chat_id, text)

def alarms():
    global last_notification
    now = time.time()

    if config.ENABLE_NOTIFICATIONS and (now - last_notification > config.NOTIFCATION_INTERVAL):
        text = "Alarm!\n"
        should_send = False

        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent

        if cpu > config.NOTIFY_CPU_PERCENT:
            text = text + "CPU: {0} %\n".format(cpu)
            should_send = True
        if ram > config.NOTIFY_RAM_PERCENT:
            text = text + "RAM: {0} %\n".format(ram)
            should_send = True

        if should_send:
            last_notification = now
            for id in storage.allUsers():
                sendTextMessage(id, text)
