"""

Client library for HydroShare REST API

To get a listing of public resources:

    >>> from hs_restclient import HydroShare
    >>> hs = HydroShare()
    >>> resource_list = hs.getResourceList()

To authenticate, and then get a list of resources you have access to:

    >>> from hs_restclient import HydroShare, HydroShareAuthBasic
    >>> auth = HydroShareAuthBasic(username='myusername', password='mypassword')
    >>> hs = HydroShare(auth=auth)
    >>> my_resource_list = hs.getResourceList()

To connect to a development HydroShare server:

    >>> from hs_restclient import HydroShare
    >>> hs = HydroShare(hostname='mydev.mydomain.net', port=8000)
    >>> resource_list = hs.getResourceList()

"""

import requests


class HydroShareException(Exception): pass

class HydroShareAuthException(HydroShareException): pass

class HydroShareHTTPException(HydroShareException): pass

class HydroShare(object):

    _URL_PROTO_WITHOUT_PORT = "{scheme}://{hostname}/hsapi"
    _URL_PROTO_WITH_PORT = "{scheme}://{hostname}:{port}/hsapi"

    def __init__(self, hostname='www.hydroshare.org', auth=None,
                 use_https=False, port=None):
        """
        Construct HydroShare object for querying HydroShare's REST API

        :param hostname: Hostname of the HydroShare server to query
        :param auth: Concrete instance of AbstractHydroShareAuth (i.e. HydroShareAuthBasic)
        :param use_https: Boolean, if True, HTTPS will be used
        :param port: Integer representing the TCP port on which to connect
        to the HydroShare server

        """
        self.hostname = hostname
        self.auth = auth

        if use_https:
            self.scheme = 'https'
        else:
            self.scheme = 'http'
        if port:
            self.port = int(port)
            if self.port < 0 or self.port > 65535:
                raise HydroShareException("Port number {0} is illegal".format(self.port))
            self.url_base = self._URL_PROTO_WITH_PORT.format(scheme=self.scheme,
                                                             hostname=self.hostname,
                                                             port=self.port)
        else:
            self.url_base = self._URL_PROTO_WITHOUT_PORT.format(scheme=self.scheme,
                                                                hostname=self.hostname)

    def getResourceList(self):
        """
        Query the GET /hsapi/resourceList/ REST end point of the HydroShare server.

        :return: A generator that can be used to iterate over dict objects, each dict representing
        the JSON representation of the resource returned by the REST end point.  For example:

        >>> for resource in hs.getResourceList():
        >>>>    print resource
         {u'bag_url': u'http://www.hydroshare.org/static/media/bags/e62a438bec384087b6c00ddcd1b6475a.zip',
          u'creator': u'B Miles',
          u'date_created': u'05-05-2015',
          u'date_last_updated': u'05-05-2015',
          u'resource_id': u'e62a438bec384087b6c00ddcd1b6475a',
          u'resource_title': u'My sample DEM',
          u'resource_type': u'RasterResource',
          u'science_metadata_url': u'http://www.hydroshare.org/hsapi/scimeta/e62a438bec384087b6c00ddcd1b6475a/',
          u'public': True}
         {u'bag_url': u'http://www.hydroshare.org/static/media/bags/hr3hy35y5ht4y54hhthrtg43w.zip',
          u'creator': u'B Miles',
          u'date_created': u'01-02-2015',
          u'date_last_updated': u'05-13-2015',
          u'resource_id': u'hr3hy35y5ht4y54hhthrtg43w',
          u'resource_title': u'Other raster',
          u'resource_type': u'RasterResource',
          u'science_metadata_url': u'http://www.hydroshare.org/hsapi/scimeta/hr3hy35y5ht4y54hhthrtg43w/',
          u'public': True}
        """
        url = "{url_base}/resourceList/".format(url_base=self.url_base)

        resources = None
        num_resources = 0

        auth = None
        if self.auth:
            if isinstance(self.auth, HydroShareAuthBasic):
                # HTTP basic authentication
                auth = (self.auth.username, self.auth.password)
            else:
                raise HydroShareAuthException("Unsupported authentication type: {0}".format(str(type(self.auth))))

        # Get first (only?) page of results
        r = requests.get(url, auth=auth)
        if r.status_code != 200:
            raise HydroShareHTTPException("Received status {status_code} when retrieving {url}".format(status_code=r.status_code,
                                                                                                       url=url))
        res = r.json()
        tot_resources = res['count']
        resources = res['results']
        num_resources += len(res['results'])

        for r in resources:
            yield r

        # Get remaining pages (if any exist)
        while res['next'] and num_resources < tot_resources:
            r = requests.get(res['next'], auth=auth)
            if r.status_code != 200:
                raise HydroShareHTTPException("Received status {status_code} when retrieving {url}".format(status_code=r.status_code,
                                                                                                           url=res['next']))
            res = r.json()
            resources = res['results']
            for r in resources:
                yield r
            num_resources += len(res['results'])

        if num_resources != tot_resources:
            raise HydroShareException("Expected {tot} resources but found {num}".format(tot_resources, num_resources))


    # def getResource(self, pid):
    #     url = "{url_base}/resource/{pid}/".format(url_base=self.url_base,
    #                                                 pid=pid)
    #     headers = {'Accept': 'application/zip'}
    #     if self.auth:
    #         if isinstance(self.auth, HydroShareAuthBasic):
    #             # HTTP basic authentication
    #             r = requests.get(url, headers=headers,
    #                              auth=(self.auth.username, self.auth.password))
    #         else:
    #             raise HydroShareAuthException("Unsupported authentication type: {0}".format(str(type(self.auth))))
    #     else:
    #         r = requests.get(url, headers=headers)



class AbstractHydroShareAuth(object): pass

class HydroShareAuthBasic(AbstractHydroShareAuth):
    def __init__(self, username, password):
        self.username = username
        self.password = password