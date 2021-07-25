#!/usr/bin/env python3
import requests
import config
import methods
import atexit
import time
import argparse
import sys, select

last_update_id = 0


parser = argparse.ArgumentParser(description='Telegram Server Monitor')
parser.add_argument('--console', action='store_true',
                    help='Don\'t communicate with telegram but rather just test on the console')

args = parser.parse_args()


if not config.TOKEN:
    print("No TOKEN found in config")
    args.console = True

if args.console:
    print("Running in console mode")

if not args.console:
    methods.startupMessage(args.console)
    atexit.register(methods.shutdownMessage)

server_retry = config.SERVER_RETRY_TIMEOUT
while True:
    methods.alarms(args.console)

    #print("Make request: {0}".format(last_update_id))
    try:
        if args.console:

            i, o, e = select.select( [sys.stdin], [], [], config.TIMEOUT )
            result = {}
            result["ok"] = True
            if i:
                entry = { "message": {
                            "text": sys.stdin.readline().strip(),
                            "chat": { "id": 0 }
                          },
                          "update_id": last_update_id + 1
                        }
                result["result"] = [ entry ]
            else:
                result["result"] = [ ]


        else:
            r = requests.post( config.API_URL + "getUpdates"
                         , json={ "offset" : last_update_id + 1
                                , "timeout" : config.TIMEOUT
                                }
                         , timeout=config.TIMEOUT + 5
                         )
            result = r.json()

        if result["ok"]:
            limit = 10
            for update in result["result"]:
                limit-=1
                if limit <= 0: break
                update_id = update["update_id"]
                if update_id > last_update_id:
                    last_update_id = update_id

                methods.processMessage(update["message"], args.console)
            server_retry = config.SERVER_RETRY_TIMEOUT
        else:
        # TODO error handling
            print(result)
    except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as err:
        print("Connection Error {0}\nRetrying in {1} seconds".format(err, server_retry))
        time.sleep(server_retry)
        server_retry *= 2

    #print(result)
