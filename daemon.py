#!/usr/bin/env python3
import requests
import config
import methods
import atexit

last_update_id = 0

methods.startupMessage()
atexit.register(methods.shutdownMessage)

while True:
    methods.alarms()

    #print("Make request: {0}".format(last_update_id))
    r = requests.post(config.API_URL + "getUpdates", json={
        "offset" : last_update_id + 1,
        "timeout" : config.TIMEOUT
    }, timeout=config.TIMEOUT + 5)
    result = r.json()

    if result["ok"]:
        for update in result["result"]:
            update_id = update["update_id"]
            if update_id > last_update_id:
                last_update_id = update_id

            methods.processMessage(update["message"])
    else:
        # TODO error handling
        print(result)

    #print(result)
