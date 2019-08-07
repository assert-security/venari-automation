import json
import requests

class VenariResponse(object):
    """Container for all Venari API responses, even errors."""

    def __init__(self, success, message='OK', response_code=-1, data=None):
        self.message = message
        self.success = success
        self.response_code = response_code
        self.data = data

    def __str__(self):
        if self.data:
            return str(self.data)
        else:
            return self.message

    def data_json(self, pretty=False):
        """Returns the data as a valid JSON string."""
        if pretty:
            return json.dumps(self.data, sort_keys=True, indent=4, separators=(',', ': '))
        else:
            return json.dumps(self.data)

    def hasData(self):
        return self.response_code==200 and self.data != ""

    def debug_text(self):
        text = str.format('message: {}\nsuccess: {}\nstatus code: {}\ndata: {}\n', 
                          self.message, 
                          str(self.success),
                          str(self.response_code),
                          self.data_json(True))
        return text

class VenariException(Exception):
    def __init__(self,result:VenariResponse):
        super().__init__(result.message)
        pass

class RequestHelper(object):
    verify_ssl:bool = False #class property to enable ssl cert enforcement for all venari api calls.
    timeout:int=30

    @staticmethod 
    def __get_json(response)->str:
        if response.text:
            try:
                data = response.json()
            except ValueError:
                data = response.content
        else:
            data = ''
        return data

    @staticmethod
    def request(method, endpoint, params=None, authToken=None, files=None, json=None, data=None, headers=None, stream=False):
        """
        Common handler for all HTTP requests, params are for GET and data for POST
        :param params, files, json, data, headers, stream, method, endpoint
        :return response from HTTP request
        """
        if not params:
            params = {}
        if not headers:
            headers = {'Accept': 'application/json'}

        if authToken:
            headers.update({'Authorization': 'Bearer ' + authToken})

        try:
            response = requests.request(method=method, url=endpoint, params=params, files=files,
                                        headers=headers, json=json, data=data,
                                        verify=RequestHelper.verify_ssl, stream=stream,timeout=RequestHelper.timeout)

            try:
                response.raise_for_status()
                response_code = response.status_code
                success = True if response_code // 100 == 2 else False
                data=RequestHelper.__get_json(response)

                text = str.format('[REQUEST] --> {} {}\n', method, endpoint)
                if (params):
                    text += str.format('params: {}\n', params)
                if (json):
                    text += str.format('json: {}\n', json)
                text += str.format('[RESPONSE] --> {} success: {}\n', response.status_code, success)
                if (data):
                    text += str.format('json: {}\n', data)
                print(text)

                
                return VenariResponse(
                    success=success, response_code=response_code, data=data)

            except ValueError as e:
                return VenariResponse(success=False, message="JSON response could not be decoded {0}.".format(e))
            
            except requests.exceptions.HTTPError as e:
                if response.status_code == 401:
                    raise VenariException(VenariResponse(
                        message='Authentication Error. {} {}'.format(response.content, e),
                        success=False,
                        response_code=401))
                if response.status_code == 404:
                    raise VenariException(VenariResponse(
                        message='Resource Not Found. {} {}'.format(response.content, e),
                        success=False,
                        response_code=401))
                else:
                    data=RequestHelper.__get_json(response)
                    message=repr(e)
                    if(data and type(data) is dict and data["error"]):
                        message=f"Api call failed: {data['error']}"
                    raise VenariException(VenariResponse(
                        message=message,
                        response_code=response.status_code,
                        success=False))
        except requests.exceptions.SSLError as e:
            raise VenariException(VenariResponse(message='An SSL error occurred. {0}'.format(e), success=False))
        
        except requests.exceptions.ConnectionError as e:
            raise VenariException(VenariResponse(message='A connection error occurred. {0}'.format(e), success=False))
        
        except requests.exceptions.Timeout:
            raise VenariException(VenariResponse(message='The request timed out after ' + str(RequestHelper.timeout) + ' seconds.',
                                    success=False))
        
        except requests.exceptions.RequestException as e:
            raise VenariException(VenariResponse(message='There was an error while handling the request. {0}'.format(e),
                                    success=False))

