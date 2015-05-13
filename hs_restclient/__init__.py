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
import datetime

import requests

from .util import is_sequence


class HydroShareException(Exception): pass

class HydroShareArgumentException(HydroShareException): pass

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

        self.auth = None
        if auth:
            if isinstance(auth, HydroShareAuthBasic):
                # HTTP basic authentication
                self.auth = (auth.username, auth.password)
            else:
                raise HydroShareAuthException("Unsupported authentication type: {0}".format(str(type(auth))))

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

    def getResourceList(self, creator=None, owner=None, user=None, group=None, from_date=None, to_date=None,
                        types=None):
        """
        Query the GET /hsapi/resourceList/ REST end point of the HydroShare server.

        :param creator: Filter results by the HydroShare user name of resource creators
        :param owner: Filter results by the HydroShare user name of resource owners
        :param user: Filter results by the HydroShare user name of resource users (i.e. owner, editor, viewer, public
        resource)
        :param group: Filter results by the HydroShare group name associated with resources
        :param from_date: Filter results to those created after from_date.  Must be datetime.date.
        :param to_date: Filter results to those created before to_date.  Must be datetime.date.  Because dates have
        no time information, you must specify date+1 day to get results for date (e.g. use 2015-05-06 to get
        resources created up to and including 2015-05-05)
        :param types: Filter results to particular HydroShare resource types.  Must be a sequence type
        (e.g. list, tuple, etc.), but not a string.

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


          Filtering (have):

          /hsapi/resourceList/?from_date=2015-05-03&to_date=2015-05-06
          /hsapi/resourceList/?user=admin
          /hsapi/resourceList/?owner=admin
          /hsapi/resourceList/?creator=admin
          /hsapi/resourceList/?group=groupname
          /hsapi/resourceList/?types=GenericResource&types=RasterResource

          Filtering (need):

          /hsapi/resourceList/?sharedWith=user

        :raise: HydroShareArgumentException if any filter parameters are invalid.
        """
        url = "{url_base}/resourceList/".format(url_base=self.url_base)

        params = {}
        if creator:
            params['creator'] = creator
        if owner:
            params['owner'] = owner
        if user:
            params['user'] = user
        if group:
            params['group'] = group
        if from_date:
            if type(from_date) is datetime.date:
                params['from_date'] = from_date.strftime('%Y-%m-%d')
            else:
                raise HydroShareArgumentException("from_date must of type {0}".format(datetime.date))
        if to_date:
            if type(to_date) is datetime.date:
                params['to_date'] = to_date.strftime('%Y-%m-%d')
            else:
                raise HydroShareArgumentException("to_date must of type {0}".format(datetime.date))
        if types:
            if not is_sequence(types):
                raise HydroShareArgumentException("types must be a sequence type, but not a string")
            params['types'] = types

        num_resources = 0

        # Get first (only?) page of results
        r = requests.get(url, auth=self.auth, params=params)
        if r.status_code != 200:
            raise HydroShareHTTPException("Received status {status_code} when retrieving {url} with params {params}".format(status_code=r.status_code,
                                                                                                                            url=url,
                                                                                                                            params=params))
        res = r.json()
        tot_resources = res['count']
        resources = res['results']
        num_resources += len(res['results'])

        for r in resources:
            yield r

        # Get remaining pages (if any exist)
        while res['next'] and num_resources < tot_resources:
            r = requests.get(res['next'], auth=self.auth, params=params)
            if r.status_code != 200:
                raise HydroShareHTTPException("Received status {status_code} when retrieving {url} with params {params}".format(status_code=r.status_code,
                                                                                                                                url=res['next'],
                                                                                                                                params=params))
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