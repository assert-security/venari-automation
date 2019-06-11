#!/usr/bin/env python

import requests
import json

grant_type = "password"
username = "admin"
password = "password"
token_url = "https://host.docker.internal:10002/connect/token"

# not used.
callback_uri = "venari://idpCallback"
test_api_url = "https://host.docker.internal:10000"
client_id = 'venari'
client_secret = '3cd83edf-38d7-45d0-8783-788cad36ae5f'

# impersonate a user
r = requests.post(url=token_url, data={
    'grant_type': grant_type, 'client_id': client_id, 'username': username, 'password': password}, verify=False)
access_token = r.json()["access_token"]
print(access_token)

print(r)
content = json.loads(r.content.decode('utf-8'))
print("{}".format(content))



