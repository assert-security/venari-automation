#### Usage

_Acquiring an access_token_
```python
# import the package
from venariapi.venari import VenariApi

# Initialize your Venari IDP
token_url = 'https://host.docker.internal:9002'

# initializing standalone api
api = VenariApi(api_url=None, token_url=token_url, username='admin', password='password', verify_ssl=False)

# get your access token
response = api.get_access_token()
token = response.data['access_token']
print(token)
```

_Authenticating and listing jobs_
```python
from venariapi.venari import VenariApi

# Initialize your Venari IDP
token_url = 'https://host.docker.internal:9002'

# Initialize your Venari api
api_url = 'https://host.docker.internal:9000'


def get_venari_token():
    api = VenariApi(api_url=api_url, token_url=token_url, username='admin', password='password', verify_ssl=False)
    response = api.get_access_token()
    token = response.data['access_token']
    return token

print(get_venari_token())

def get_venari_jobs():
    api = VenariApi(api_url=api_url, token_url=token_url, username='admin', password='password', verify_ssl=False, token=get_venari_token())
    response = api.get_job_listing()
    return response

print(get_venari_jobs())


```