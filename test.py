#!/usr/bin/env python3
import requests
import config

r = requests.post(config.API_URL + "getMe")
print(r.json())
