#!/usr/bin/env python3
import requests
import config
import methods
import atexit
import time

last_update_id = 0

methods.startupMessage()
atexit.register(methods.shutdownMessage)

server_retry = config.SERVER_RETRY_TIMEOUT
while True:
    methods.alarms()

    #print("Make request: {0}".format(last_update_id))
    try:
        r = requests.post( config.API_URL + "getUpdates"
                         , json={ "offset" : last_update_id + 1
                                , "timeout" : config.TIMEOUT
                                }
                         , timeout=config.TIMEOUT + 5
                         )
        result = r.json()

        if result["ok"]:
            for update in result["result"]:
                update_id = update["update_id"]
                if update_id > last_update_id:
                    last_update_id = update_id

                methods.processMessage(update["message"])
            server_retry = config.SERVER_RETRY_TIMEOUT
        else:
        # TODO error handling
            print(result)
    except requests.exceptions.ConnectionError as err:
        methods.sendTextMessage("Connection Error {0}\nRetrying in {1} seconds".format(err, server_retry))
        time.sleep(server_retry)
        server_retry *= 2

    #print(result)
