import requests

def fetch_web_resource(url):
    try:
        response = requests.get(url)
        content = response.content.decode(response.encoding)
        if (content):
            return (response.status_code, content)
        else:
            return (None, None)
    except:
        return (None, None)

def is_site_available(url, pattern = ''):
    status_code, content = fetch_web_resource(url)
    return (status_code == 200 and (not pattern or pattern in content))




