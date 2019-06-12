from  request_helper import *
class VenariAuth(object):
    def __init__(self,token_url):
        self.token_url=token_url
    #Login using password flow. This will be deprecated in 1.2
    def login_password(self,username,password):
        self.grant_type = 'password'
        self.client_id = 'venari'
        """
        Used for obtaining an oauth access token from the OpenId node to impersonate a user
        :param: grant_type, client_id, username, password
        :return: access_token
        """
        data = dict(
            username=username,
            password=password,
            client_id=self.client_id,
            grant_type=self.grant_type
            )
        response=RequestHelper.request('POST', self.token_url, data=data)
        self.access_token = response.data['access_token']