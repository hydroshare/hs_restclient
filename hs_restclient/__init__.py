"""

Client library for HydroShare REST API

To get a listing of public resources:

    >>> from hs_restclient import HydroShare
    >>> hs = HydroShare()
    >>> for resource in hs.getResourceList():
    >>>     print(resource)

To authenticate, and then get a list of resources you have access to:

    >>> from hs_restclient import HydroShare, HydroShareAuthBasic
    >>> auth = HydroShareAuthBasic(username='myusername', password='mypassword')
    >>> hs = HydroShare(auth=auth)
    >>> for resource in hs.getResourceList():
    >>>     print(resource)

To connect to a development HydroShare server:

    >>> from hs_restclient import HydroShare
    >>> hs = HydroShare(hostname='mydev.mydomain.net', port=8000)
    >>> for resource in hs.getResourceList():
    >>>     print(resource)

"""
import os
import datetime
import zipfile
import tempfile
import shutil
import httplib

import requests

from .util import is_sequence


STREAM_CHUNK_SIZE = 100 * 1024


class HydroShareException(Exception):
    def __init__(self, args):
        super(HydroShareException, self).__init__(args)


class HydroShareArgumentException(HydroShareException):
    def __init__(self, args):
        super(HydroShareArgumentException, self).__init__(args)


class HydroShareAuthException(HydroShareException):
    def __init__(self, args):
        super(HydroShareAuthException, self).__init__(args)


class HydroShareHTTPException(HydroShareException):
    """ Exception used to communicate HTTP errors from HydroShare server

        Arguments in tuple passed to constructor must be: (url, status_code, params).
        url and status_code are of type string, while the optional params argument
        should be a dict.
    """
    def __init__(self, args):
        super(HydroShareHTTPException, self).__init__(args)
        self.url = args[0]
        self.method = args[1]
        self.status_code = args[2]
        if len(args) >= 4:
            self.params = args[3]
        else:
            self.params = None

    def __str__(self):
        msg = "Received status {status_code} {status_msg} when accessing {url} " + \
              "with method {method} and params {params}."
        return msg.format(status_code=self.status_code,
                          status_msg=httplib.responses[self.status_code],
                          url=self.url,
                          method=self.method,
                          params=self.params)

    def __unicode__(self):
        return self.__str__()

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

        self.session = None
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

        self._initializeSession()
        self.resource_types = self.getResourceTypes()

    def _initializeSession(self):
        if self.session:
            self.session.close()
        self.session = requests.Session()
        self.session.auth = self.auth

    def _request(self, method, url, params=None, data=None, files=None, stream=False):
        r = None
        try:
            r = self.session.request(method, url, params=params, data=data, files=files, stream=stream)
        except requests.ConnectionError:
            # We might have gotten a connection error because the server we were talking to went down.
            #  Re-initialize the session and try again
            print('Received connection error retrying...')
            self._initializeSession()
            r = self.session.request(method, url, params=params, data=data, files=files, stream=stream)

        return r

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

        :raise HydroShareHTTPException to signal an HTTP error
        :raise HydroShareArgumentException for any invalid arguments

        :return: A generator that can be used to fetch dict objects, each dict representing
        the JSON object representation of the resource returned by the REST end point.  For example:

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
        r = self._request('GET', url, params=params)
        if r.status_code != 200:
            raise HydroShareHTTPException((url, 'GET', r.status_code, params))
        res = r.json()
        tot_resources = res['count']
        resources = res['results']
        num_resources += len(res['results'])

        for r in resources:
            yield r

        # Get remaining pages (if any exist)
        while res['next'] and num_resources < tot_resources:
            r = self._request('GET', res['next'], params=params)
            if r.status_code != 200:
                raise HydroShareHTTPException((url, 'GET', r.status_code, params))
            res = r.json()
            resources = res['results']
            for r in resources:
                yield r
            num_resources += len(res['results'])

        if num_resources != tot_resources:
            raise HydroShareException("Expected {tot} resources but found {num}".format(tot_resources, num_resources))

    def getResource(self, pid):
        """ Get system metadata for a resource

        :param pid: The HydroShare ID of the resource

        :raise HydroShareHTTPException to signal an HTTP error

        :return: A dict representing the JSON object representation of the resource returned by the REST end point.
        For example:

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
        url = "{url_base}/resource/{pid}/".format(url_base=self.url_base,
                                                  pid=pid)
        r = self._request('GET', url)
        if r.status_code != 200:
            raise HydroShareHTTPException((url, 'GET', r.status_code))

        resource = r.json()
        assert(resource['resource_id'] == pid)

        return resource

    def getResourceBag(self, pid, destination=None, unzip=False):
        """ Get a resource in BagIt format

        :param pid: The HydroShare ID of the resource
        :param destination: String representing the directory to save bag to. Bag will be saved to file named
        $(PID).zip in destination; existing file of the same name will be overwritten. If None, a stream to the zipped
        bag will be returned instead.
        :param unzip: True if the bag should be unzipped when saved to destination. Bag contents to be saved to
        directory named $(PID) residing in destination. Only applies when destination is not None.

        :raise HydroShareHTTPException to signal an HTTP error
        :raise

        :return: None if the bag was saved directly to disk.  Or a generator representing a buffered stream of the
        bytes comprising the bag returned by the REST end point.
        """
        resource = self.getResource(pid)
        bag_url = resource['bag_url']

        if destination:
            self._getBagAndStoreOnFilesystem(bag_url, pid, destination, unzip)
            return None
        else:
            return self._getBagStream(bag_url)

    def _getBagAndStoreOnFilesystem(self, bag_url, pid, destination, unzip=False):
        if not os.path.isdir(destination):
            raise HydroShareArgumentException("{0} is not a directory".format(destination))
        if not os.access(destination, os.W_OK):
            raise HydroShareArgumentException("Do not have write permissions to directory {0}".format(destination))

        r = self._request('GET', bag_url, stream=True)
        if r.status_code != 200:
            raise HydroShareHTTPException((bag_url, 'GET', r.status_code))

        filename = "{pid}.zip".format(pid=pid)
        tempdir = None
        if unzip:
            tempdir = tempfile.mkdtemp()
            filepath = os.path.join(tempdir, filename)
        else:
            filepath = os.path.join(destination, filename)

        # Download bag (maybe temporarily)
        with open(filepath, 'wb') as fd:
            for chunk in r.iter_content(STREAM_CHUNK_SIZE):
                fd.write(chunk)

        if unzip:
            dirname = os.path.join(destination, pid)
            zfile = zipfile.ZipFile(filepath)
            zfile.extractall(dirname)
            shutil.rmtree(tempdir)

    def _getBagStream(self, bag_url):
        r = self._request('GET', bag_url, stream=True)
        if r.status_code != 200:
            raise HydroShareHTTPException((bag_url, 'GET', r.status_code))
        return r.iter_content(STREAM_CHUNK_SIZE)

    def getResourceTypes(self):
        """ Get the list of resource types supported by the HydroShare server

        :return: A set of strings representing the HydroShare resource types

        :raise HydroShareHTTPException to signal an HTTP error
        """
        url = "{url_base}/resourceTypes/".format(url_base=self.url_base)

        r = self._request('GET', url)
        if r.status_code != 200:
            raise HydroShareHTTPException((url, 'GET', r.status_code))

        resource_types = r.json()
        return set([t['resource_type'] for t in resource_types['results']])

    def createResource(self, resource_type, title, resource_file=None, resource_filename=None,
                       abstract=None, keywords=None,
                       edit_users=None, view_users=None, edit_groups=None, view_groups=None):
        """ Create a new resource.

        :param resource_type: string representing the a HydroShare resource type recognized by this
        server.
        :param title: string representing the title of the new resource
        :param resource_file: a read-only binary file-like object (i.e. opened with the flag 'rb') or a string
        representing path to file to be uploaded as part of the new resource
        :param resource_filename: string representing the filename of the resource file.  Must be specified
        if resource_file is a file-like object.  If resource_file is a string representing a valid file path,
        and resource_filename is not specified, resource_filename will be equal to os.path.basename(resource_file).
        is a string
        :param abstract: string representing abstract of resource
        :param keywords: list of strings representing keywords to associate with the resource
        :param edit_users: list of HydroShare usernames who will be given edit permissions
        :param view_users: list of HydroShare usernames who will be given view permissions
        :param edit_groups: list of HydroShare group names that will be given edit permissions
        :param view_groups: list of HydroShare group names that will be given view permissions

        :return: string representing ID of newly created resource.

        :raise HydroShareArgumentException if any parameters are invalid.

        """
        url = "{url_base}/resource/".format(url_base=self.url_base)

        close_fd = False

        if not resource_type in self.resource_types:
            raise HydroShareArgumentException("Resource type {0} is not among known resources: {1}".format(resource_type,
                                                                                                           ", ".join([r for r in self.resource_types])))
        files = None
        if resource_file:
            if type(resource_file) is str:
                if not os.path.isfile(resource_file) or not os.access(resource_file, os.R_OK):
                    raise HydroShareArgumentException("{0} is not a file or is not readable".format(resource_file))
                fd = open(resource_file, 'rb')
                close_fd = True
                if not resource_filename:
                    fname = os.path.basename(resource_file)
            else:
                if not resource_filename:
                    raise HydroShareArgumentException("resource_filename must be specified when resource_file " +
                                                      "is a file-like object")
                # Assume it is a file-like object
                fd = resource_file
                fname = resource_filename
            files = {'file': (fname, fd)}

        # Prepare request
        params = {'resource_type': resource_type, 'title': title}
        if abstract:
            params['abstract'] = abstract
        if keywords:
            # Put keywords in a format that django-rest's serializer will understand
            for (i, kw) in enumerate(keywords):
                key = "keywords[{index}]".format(index=i)
                params[key] = kw
        if edit_users:
            params['edit_users'] = edit_users
        if view_users:
            params['view_users'] = view_users
        if edit_groups:
            params['edit_groups'] = edit_groups
        if view_groups:
            params['view_groups'] = view_groups

        r = self._request('POST', url, data=params, files=files)

        if close_fd:
            fd.close()

        if r.status_code != 201:
            raise HydroShareHTTPException((url, 'POST', r.status_code, params))

        response = r.json()
        new_resource_id = response['resource_id']

        if response['resource_type'] != resource_type:
            msg = "New resource {resource_id} was created, but the new resource type is {new_type}, " + \
                  "while the expected type is {exp_type}."
            msg = msg.format(resource_id=new_resource_id, new_type=response['resource_type'], exp_type=resource_type)
            raise HydroShareException(msg)

        return new_resource_id





class AbstractHydroShareAuth(object): pass

class HydroShareAuthBasic(AbstractHydroShareAuth):
    def __init__(self, username, password):
        self.username = username
        self.password = password