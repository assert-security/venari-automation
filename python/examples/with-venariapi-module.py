# import the package
from venariapi.venari import VenariApi

# initializing standalone api
api = VenariApi(api_url=None, token_url='https://host.docker.internal:9002', username='admin', password='password',
              verify_ssl=False)

# get your access token
response = api.get_access_token()
token = response.data['access_token']
print(token)