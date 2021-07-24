import requests
import datetime
import psutil
import config
import persistence
import time
import socket
import netifaces
import subprocess
import re

last_notification = 0
last_ports = []
last_active_services = []
last_pid_usage = 0
last_fd_usage = 0
first_alarm = True #avoid first alarm due to initialization
storage = persistence.Persistence()

# thanks to https://web.archive.org/web/20111010015624/http://blogmag.net/blog/read/38/Print_human_readable_file_size
def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def processMessage(message, console):
    if "text" in message:
        processTextMessage(message, console)

def processTextMessage(message, console):
    text = message["text"]

    if text.startswith("/"):
        processCommandMessage(message, console)

def processCommandMessage(message, console):
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
        commandStart(message, parameter, console)
    elif command == "/stop":
        commandStop(message, console)
    elif command == "/help":
        commandHelp(message, console)
    elif command == "/usage":
        commandUsage(message, console)
    elif command == "/users":
        commandUsers(message, console)
    elif command == "/disks":
        commandDisks(message, console)
    elif command == "/ports":
        commandPorts(message, console)
    elif command == "/procs" or command == "/proc":
        commandProcesses(message, console)
    elif command == "/ip":
        commandIp(message, 6, console)
    elif command == "/ip4":
        commandIp(message, 4, console)
    elif command == "/services":
        commandServices(message, console)
    else:
        sendTextMessage(message["chat"]["id"], "I do not know what you mean by '{0}'".format(command), console)

def _sendMessage(chat_id, text, console,parse_mode=None):
    if console:
        print("---- Message:")
        print(text)
        print("----")
    else:
        j = {
            "chat_id" : chat_id,
            "text" : text
        }

        if parse_mode is not None:
            j["parse_mode"] = parse_mode

        r = requests.post(config.API_URL + "sendMessage", json=j)

        result = r.json()
        if not result["ok"]:
            print(result)

def sendTextMessage(chat_id, text, console):
    _sendMessage(chat_id, text, console)

def sendMarkdownMessage(chat_id, text, console):
    _sendMessage(chat_id, text, console, "Markdown")

def sendHTMLMessage(chat_id, text):
    _sendMessage(chat_id, text, console, "HTML")

def sendAuthMessage(chat_id, console):
    sendTextMessage(chat_id, "Please sign in first.\nType /start <password> to sign in.", console)

def startupMessage(console):
    for id in storage.allUsers():
        sendTextMessage(id, "Hello there. I just started.", console)

def shutdownMessage(console):
    for id in storage.allUsers():
        sendTextMessage(id, "I am shutting down.", console)

def sendToAll(text, console):
    for id in storage.allUsers():
        sendTextMessage(id, text, console)

def commandStart(message, parameter, console):
    chat_id = message["chat"]["id"]
    if storage.isRegisteredUser(chat_id):
        sendTextMessage(chat_id, "You are signed in. Thank you.", console)
    else:
        if parameter.strip() == config.PASSWORD:
            storage.registerUser(chat_id)
            sendTextMessage(chat_id, "Thanks for signing up. " +
                "Type /help for information.", console)
        else:
            sendTextMessage(chat_id, "Please provide a valid password. " +
                "Type /start <password> to sign in.", console)

def commandStop(message, console):
    chat_id = message["chat"]["id"]
    if storage.isRegisteredUser(chat_id):
        storage.unregisterUser(chat_id)
        sendTextMessage(chat_id, "You signed off. You will no longer receive any messages from me.", console)
    else:
        sendAuthMessage(chat_id, console)

def commandHelp(message, console):
    chat_id = message["chat"]["id"]
    sendTextMessage(chat_id, config.NAME + """
Monitor your server and query usage and network information.

/usage    - CPU and Memory information
/users    - Active users
/disks    - Disk usage
/ports    - Open network ports
/procs    - Info about processes
/ip       - list all IPv6 IPs
/ip4      - list all IPv4 IPs
/services - list all system services

You do not like me anymore?
/stop - Sign off from the monitoring service
""", console)

def commandUsage(message, console):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id, console)
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
        text += "RAM: {0} % (free: {1})\n".format(psutil.virtual_memory().percent,sizeof_fmt(psutil.virtual_memory().available))
    except BaseException as be:
        text += "Getting RAM failed: {0}\n".format(be)

    try:
        text += "Swap: {0} % (free: {1})".format(psutil.swap_memory().percent,sizeof_fmt(psutil.swap_memory().free))
    except BaseException as be:
        text += "Getting Swap info failed: {0}".format(be)

    sendTextMessage(chat_id, text, console)

def commandUsers(message, console):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id, console)
        return

    text = " ** USERS **\n"
    try:
        users = psutil.users()
        for user in users:
            text += "{0}@{1} {2}\n".format(user.name, user.host, str(datetime.datetime.fromtimestamp(user.started)))
        if len(users) == 0:
            text += "No users are currently logged in"
    except BaseException as be:
        text += "Getting user info failed: {0}".format(be)

    sendTextMessage(chat_id, text, console)

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

def commandPorts(message, console):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id, console)
        return

    text = " ** Listening Ports **\n"
    try:
        for c in sorted(psutil.net_connections(), key=lambda i:i.laddr[1]):
            if c.status == "LISTEN":
                interface = c.laddr[0]
                if interface == "0.0.0.0" or interface == "::":
                    interface = "all interfaces"
                else:
                    interface = "only on {0}".format(interface)
                text += "* {0} ({1}, {2})\n".format(c.laddr[1], prettyPrintFamily(c.family), interface)

    except BaseException as be:
        text += "Getting port info failed: {0}".format(be)

    sendTextMessage(chat_id, text, console)

def commandProcesses(message, console):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id, console)
        return

    text = " ** Process info **\n"
    try:
        # just query once for consistency
        procs = [ (p.num_threads(),p.pid,p.name(),p.cmdline()) for p in psutil.process_iter()]
        max_pids = int(open("/proc/sys/kernel/pid_max").read())
        pid_sum = sum([ p[0] for p in procs])
        worst = sorted(procs, reverse = True)[0]
        pid_usage = (pid_sum*100/max_pids)
        fds = [int(n) for n in open("/proc/sys/fs/file-nr").read().strip().split('\t')]
        fd_usage = (fds[0]*100/fds[2])
        text += "Processes: {}\n".format(len(procs))
        text += "PIDs used: {}/{} ({:.1f}%)\n".format(pid_sum, max_pids, pid_usage)
        text += "FDs used: {}/{} ({:.1f}%)\n".format(fds[0], fds[2], fd_usage)
        text += "Worst Process: {} ({}) - {} threads\n{}".format(worst[2], worst[1], worst[0], worst[3])

    except BaseException as be:
        text += "Getting process info failed: {0}".format(be)

    sendTextMessage(chat_id, text, console)

def commandDisks(message, console):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id, console)
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

    sendTextMessage(chat_id, text, console)

def commandIp(message, ver, console):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id, console)
        return

    ifaces = netifaces.interfaces()
    try:
        ifaces.remove('lo')
    except:
        pass

    text  = " ** List of IPv{0} addresses **\n".format(ver)
    count = 0

    for ips in [netifaces.ifaddresses(x) for x in ifaces]:
        if ver == 4:
            entry = ips.get(netifaces.AF_INET)
        else:
            entry = ips.get(netifaces.AF_INET6)
        if entry is not None:
            for ip in entry:
                try:
                    text += "{0}\n".format(ip["addr"])
                    count += 1
                except:
                    pass

    if count == 0:
        text += "None found"
    sendTextMessage(chat_id, text, console)

def _getServices():
    #TBD make selection in configfile
    serviceCMD = ["/usr/sbin/service","--status-all"]
    serviceRE = re.compile("^ *\[ (?P<type>.) \] +(?P<service>.+)$")

    with subprocess.Popen(serviceCMD, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
        lines = p.stdout.readlines() + p.stderr.readlines()

    active=[]
    inactive=[]
    dontknow=[]

    for l in lines:
        l = l.decode("utf-8")
        m = serviceRE.match(l)
        if not m: continue
        if m.group("type") == "+":
            active.append(m.group("service"))
        elif m.group("type") == "-":
            inactive.append(m.group("service"))
        else:
            dontknow.append(m.group("service"))
    return (active,inactive,dontknow)
    
def commandServices(message, console):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id, console)
        return
    
    (active,_,dontknow) = _getServices()
    text = " ** Active Services **\n"
    text += "\n".join(active)
    text += "\n ** Unknown Status **\n"
    text += "\n".join(dontknow)

    # inactive ones are usually many and not too interresting

    sendTextMessage(chat_id, text, console)

def alarms(console):
    global last_notification
    now = time.time()
    global last_ports
    global last_active_services
    global last_pid_usage
    global last_fd_usage
    global first_alarm

    if config.ENABLE_NOTIFICATIONS and (now - last_notification > config.NOTIFCATION_INTERVAL):
        text = "Alarm!\n"
        should_send = False

        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent

        if cpu > config.NOTIFY_CPU_PERCENT:
            text += "CPU: {0} %\n".format(cpu)
            should_send = True
        if ram > config.NOTIFY_RAM_PERCENT:
            text += "RAM: {0} %\n".format(ram)
            should_send = True

        ports = ["{0} ({1})".format(c.laddr[1],prettyPrintFamily(c.family))
                 for c in psutil.net_connections() if c.status == "LISTEN"]
        port_diff = list(set(last_ports).symmetric_difference(ports))
        if len(port_diff) > 0:
            should_send = True

            got_more = False
            if len(ports) > len(last_ports):
                got_more = True

            for p in port_diff:
                text += "{0} listening port: {1}\n".format("New" if got_more else "Closed",p)

            last_ports = ports

        (active,_,_) = _getServices()
        service_diff = list(set(last_active_services).symmetric_difference(active))
        if len(service_diff) > 0:
            should_send = True

            got_more = False
            if len(active) > len(last_active_services):
                got_more = True

            for s in service_diff:
                text += "{0} service: {1}\n".format("Started" if got_more else "Stopped",s)
   
            last_active_services = active

        procs = []
        for p in psutil.process_iter():
            try:
                procs.append((p.num_threads(),p.pid,p.name(),p.cmdline()))
            except BaseException as be:
                pass
        max_pids = int(open("/proc/sys/kernel/pid_max").read())
        pid_sum = sum([ p[0] for p in procs])
        pid_usage = (pid_sum*100/max_pids)
        # only alert on 5% changes
        if (pid_usage > config.NOTIFY_PID_PERCENT) and (abs(last_pid_usage - pid_usage) > 5):
            should_send = True
            worst = sorted(procs, reverse = True)[0]
            text += "PIDs used: {}/{} ({:.1f}%)\n".format(pid_sum, max_pids, pid_usage)
            text += "Worst Process: {} ({}) - {} threads\n{}".format(worst[2], worst[1], worst[0], worst[3])
            last_pid_usage = pid_usage
        if (pid_usage <= config.NOTIFY_PID_PERCENT):
            last_pid_usage = 0

        # only alert on 5% changes
        fds = [int(n) for n in open("/proc/sys/fs/file-nr").read().strip().split('\t')]
        fd_usage = (fds[0]*100/fds[2])
        if (fd_usage > config.NOTIFY_FD_PERCENT) and (abs(last_fd_usage - fd_usage) > 5):
            should_send = True
            text += "FDs used: {}/{} ({:.1f}%)\n".format(fds[0], fds[2], fd_usage)
            last_fd_usage = fd_usage
        if (fd_usage <= config.NOTIFY_FD_PERCENT):
            last_fd_usage = 0

        if first_alarm:
            first_alarm = False
            should_send = False
        if should_send:
            last_notification = now
            for id in storage.allUsers():
                sendTextMessage(id, text, console)
