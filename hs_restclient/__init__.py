"""

Client library for HydroShare REST API

"""

__title__ = 'hs_restclient'
__version__ = '1.1.0'

import os
import zipfile
import tempfile
import shutil
import mimetypes

import requests

from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

from .compat import http_responses


STREAM_CHUNK_SIZE = 100 * 1024


class HydroShareException(Exception):
    def __init__(self, args):
        super(HydroShareException, self).__init__(args)


class HydroShareArgumentException(HydroShareException):
    def __init__(self, args):
        super(HydroShareArgumentException, self).__init__(args)


class HydroShareNotAuthorized(HydroShareException):
    def __init__(self, args):
        super(HydroShareNotAuthorized, self).__init__(args)
        self.method = args[0]
        self.url = args[1]

    def __str__(self):
        msg = "Not authorized to perform {method} on {url}."
        return msg.format(method=self.method, url=self.url)

    def __unicode__(self):
        return unicode(str(self))


class HydroShareNotFound(HydroShareException):
    def __init__(self, args):
        super(HydroShareNotFound, self).__init__(args)
        self.pid = args[0]
        if len(args) >= 2:
            self.filename = args[1]
        else:
            self.filename = None

    def __str__(self):
        if self.filename:
            msg = "File '{filename}' was not found in resource '{pid}'."
            msg = msg.format(filename=self.filename, pid=self.pid)
        else:
            msg = "Resource '{pid}' was not found."
            msg = msg.format(pid=self.pid)
        return msg

    def __unicode__(self):
        return unicode(str(self))


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
                          status_msg=http_responses[self.status_code],
                          url=self.url,
                          method=self.method,
                          params=self.params)

    def __unicode__(self):
        return unicode(str(self))


def default_progress_callback(monitor):
    pass


class HydroShare(object):
    """
        Construct HydroShare object for querying HydroShare's REST API

        :param hostname: Hostname of the HydroShare server to query
        :param auth: Concrete instance of AbstractHydroShareAuth (i.e. HydroShareAuthBasic)
        :param use_https: Boolean, if True, HTTPS will be used
        :param port: Integer representing the TCP port on which to connect
            to the HydroShare server

        :raises: HydroShareException if auth is not a known authentication type.
    """

    _URL_PROTO_WITHOUT_PORT = "{scheme}://{hostname}/hsapi"
    _URL_PROTO_WITH_PORT = "{scheme}://{hostname}:{port}/hsapi"

    def __init__(self, hostname='www.hydroshare.org', auth=None,
                 use_https=False, port=None):
        self.hostname = hostname

        self.session = None
        self.auth = None
        if auth:
            if isinstance(auth, HydroShareAuthBasic):
                # HTTP basic authentication
                self.auth = (auth.username, auth.password)
            else:
                raise HydroShareException("Unsupported authentication type '{0}'.".format(str(type(auth))))

        if use_https:
            self.scheme = 'https'
        else:
            self.scheme = 'http'
        if port:
            self.port = int(port)
            if self.port < 0 or self.port > 65535:
                raise HydroShareException("Port number {0} is illegal.".format(self.port))
            self.url_base = self._URL_PROTO_WITH_PORT.format(scheme=self.scheme,
                                                             hostname=self.hostname,
                                                             port=self.port)
        else:
            self.url_base = self._URL_PROTO_WITHOUT_PORT.format(scheme=self.scheme,
                                                                hostname=self.hostname)

        self._initializeSession()
        self._resource_types = None

    @property
    def resource_types(self):
        if self._resource_types is None:
            self._resource_types = self.getResourceTypes()
        return self._resource_types


    def _initializeSession(self):
        if self.session:
            self.session.close()
        self.session = requests.Session()
        self.session.auth = self.auth

    def _request(self, method, url, params=None, data=None, files=None, headers=None, stream=False):
        r = None
        try:
            r = self.session.request(method, url, params=params, data=data, files=files, headers=headers, stream=stream)
        except requests.ConnectionError:
            # We might have gotten a connection error because the server we were talking to went down.
            #  Re-initialize the session and try again
            self._initializeSession()
            r = self.session.request(method, url, params=params, data=data, files=files, headers=headers, stream=stream)

        return r

    def _prepareFileForUpload(self, request_params, resource_file, resource_filename=None):
        fname = None
        if isinstance(resource_file, basestring):
            if not os.path.isfile(resource_file) or not os.access(resource_file, os.R_OK):
                raise HydroShareArgumentException("{0} is not a file or is not readable.".format(resource_file))
            fd = open(resource_file, 'rb')
            close_fd = True
            if not resource_filename:
                fname = os.path.basename(resource_file)
            else:
                fname = resource_filename
        else:
            if not resource_filename:
                raise HydroShareArgumentException("resource_filename must be specified when resource_file " +
                                                  "is a file-like object.")
            # Assume it is a file-like object
            fd = resource_file
            fname = resource_filename

        mime_type = mimetypes.guess_type(fname)
        if mime_type[0] is None:
            mime_type = 'application/octet-stream'
        else:
            mime_type = mime_type[0]
        request_params['file'] = (fname, fd, mime_type)
        return close_fd

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

        :raises: HydroShareHTTPException to signal an HTTP error
        :raises: HydroShareArgumentException for any invalid arguments

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
            params['from_date'] = from_date.strftime('%Y-%m-%d')
        if to_date:
            params['to_date'] = to_date.strftime('%Y-%m-%d')
        if types:
            params['type'] = types

        # Get first (only?) page of results
        r = self._request('GET', url, params=params)
        if r.status_code != 200:
            raise HydroShareHTTPException((url, 'GET', r.status_code, params))
        res = r.json()
        resources = res['results']

        for r in resources:
            yield r

        # Get remaining pages (if any exist)
        while res['next']:
            r = self._request('GET', res['next'], params=params)
            if r.status_code != 200:
                raise HydroShareHTTPException((url, 'GET', r.status_code, params))
            res = r.json()
            resources = res['results']
            for r in resources:
                yield r

    def getSystemMetadata(self, pid):
        """ Get system metadata for a resource

        :param pid: The HydroShare ID of the resource

        :raises: HydroShareHTTPException to signal an HTTP error

        :return: A dict representing the JSON object representation of the resource returned by the REST end point.

        Example of data returned:

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
        url = "{url_base}/sysmeta/{pid}/".format(url_base=self.url_base,
                                                 pid=pid)
        r = self._request('GET', url)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('GET', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'GET', r.status_code))

        return r.json()

    def getResource(self, pid, destination=None, unzip=False):
        """ Get a resource in BagIt format

        :param pid: The HydroShare ID of the resource
        :param destination: String representing the directory to save bag to. Bag will be saved to file named
            $(PID).zip in destination; existing file of the same name will be overwritten. If None, a stream to the
            zipped bag will be returned instead.
        :param unzip: True if the bag should be unzipped when saved to destination. Bag contents to be saved to
            directory named $(PID) residing in destination. Only applies when destination is not None.

        :raises: HydroShareArgumentException if any arguments are invalid.
        :raises: HydroShareNotAuthorized if the user is not authorized to access the
            resource.
        :raises: HydroShareNotFound if the resource was not found.
        :raises: HydroShareHTTPException to signal an HTTP error

        :return: None if the bag was saved directly to disk.  Or a generator representing a buffered stream of the
            bytes comprising the bag returned by the REST end point.
        """
        stream = self._getBagStream(pid)
        if destination:
            self._storeBagOnFilesystem(stream, pid, destination, unzip)
            return None
        else:
            return stream

    def _storeBagOnFilesystem(self, stream, pid, destination, unzip=False):
        if not os.path.isdir(destination):
            raise HydroShareArgumentException("{0} is not a directory.".format(destination))
        if not os.access(destination, os.W_OK):
            raise HydroShareArgumentException("You do not have write permissions to directory '{0}'.".format(destination))

        filename = "{pid}.zip".format(pid=pid)
        tempdir = None
        if unzip:
            tempdir = tempfile.mkdtemp()
            filepath = os.path.join(tempdir, filename)
        else:
            filepath = os.path.join(destination, filename)

        # Download bag (maybe temporarily)
        with open(filepath, 'wb') as fd:
            for chunk in stream:
                fd.write(chunk)

        if unzip:
            try:
                dirname = os.path.join(destination, pid)
                zfile = zipfile.ZipFile(filepath)
                zfile.extractall(dirname)
            except Exception as e:
                print("Received error {e} when unzipping BagIt archive to {dest}.".format(e=repr(e),
                                                                                          dest=destination))
            finally:
                shutil.rmtree(tempdir)

    def _getBagStream(self, pid):
        bag_url = "{url_base}/resource/{pid}/".format(url_base=self.url_base,
                                                      pid=pid)
        r = self._request('GET', bag_url, stream=True)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('GET', bag_url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((bag_url, 'GET', r.status_code))
        return r.iter_content(STREAM_CHUNK_SIZE)

    def getResourceTypes(self):
        """ Get the list of resource types supported by the HydroShare server

        :return: A set of strings representing the HydroShare resource types

        :raises: HydroShareHTTPException to signal an HTTP error
        """
        url = "{url_base}/resourceTypes/".format(url_base=self.url_base)

        r = self._request('GET', url)
        if r.status_code != 200:
            raise HydroShareHTTPException((url, 'GET', r.status_code))

        resource_types = r.json()
        return set([t['resource_type'] for t in resource_types])

    def createResource(self, resource_type, title, resource_file=None, resource_filename=None,
                       abstract=None, keywords=None,
                       edit_users=None, view_users=None, edit_groups=None, view_groups=None,
                       progress_callback=None):
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
        :param progress_callback: user-defined function to provide feedback to the user about the progress
            of the upload of resource_file.  For more information, see:
            http://toolbelt.readthedocs.org/en/latest/uploading-data.html#monitoring-your-streaming-multipart-upload

        :return: string representing ID of newly created resource.

        :raises: HydroShareArgumentException if any parameters are invalid.
        :raises: HydroShareNotAuthorized if user is not authorized to perform action.
        :raises: HydroShareHTTPException if an unexpected HTTP response code is encountered.

        """
        url = "{url_base}/resource/".format(url_base=self.url_base)

        close_fd = False

        if not resource_type in self.resource_types:
            raise HydroShareArgumentException("Resource type {0} is not among known resources: {1}".format(resource_type,
                                                                                                           ", ".join([r for r in self.resource_types])))

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

        if resource_file:
            close_fd = self._prepareFileForUpload(params, resource_file, resource_filename)

        encoder = MultipartEncoder(params)
        if progress_callback is None:
            progress_callback = default_progress_callback
        monitor = MultipartEncoderMonitor(encoder, progress_callback)

        r = self._request('POST', url, data=monitor, headers={'Content-Type': monitor.content_type})

        if close_fd:
            fd = params['file'][1]
            fd.close()

        if r.status_code != 201:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('POST', url))
            else:
                raise HydroShareHTTPException((url, 'POST', r.status_code, params))

        response = r.json()
        new_resource_id = response['resource_id']

        return new_resource_id

    def deleteResource(self, pid):
        """
        Delete a resource.

        :param pid: The HydroShare ID of the resource
        """
        url = "{url_base}/resource/{pid}/".format(url_base=self.url_base,
                                                  pid=pid)

        r = self._request('DELETE', url)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('DELETE', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'DELETE', r.status_code))

        resource = r.json()
        assert(resource['resource_id'] == pid)
        return resource['resource_id']

    def setAccessRules(self, pid, public=False):
        """
        Set access rules for a resource.  Current only allows for setting the public or private setting.

        :param pid: The HydroShare ID of the resource
        :param public: True if the resource should be made public.
        """
        url = "{url_base}/resource/accessRules/{pid}/".format(url_base=self.url_base,
                                                              pid=pid)
        params = {'public': public}

        r = self._request('PUT', url, data=params)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('PUT', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'PUT', r.status_code, params))

        resource = r.json()
        assert(resource['resource_id'] == pid)
        return resource['resource_id']

    def addResourceFile(self, pid, resource_file, progress_callback=None):
        """ Add a new file to an existing resource

        :param pid: The HydroShare ID of the resource
        :param resource_file: a read-only binary file-like object (i.e. opened with the flag 'rb') or a string
            representing path to file to be uploaded as part of the new resource
        :param progress_callback: user-defined function to provide feedback to the user about the progress
            of the upload of resource_file.  For more information, see:
            http://toolbelt.readthedocs.org/en/latest/uploading-data.html#monitoring-your-streaming-multipart-upload

        :return: Dictionary containing 'resource_id' the ID of the resource to which the file was added, and
                'file_name' the filename of the file added.

        :raises: HydroShareNotAuthorized if user is not authorized to perform action.
        :raises: HydroShareNotFound if the resource was not found.
        :raises: HydroShareHTTPException if an unexpected HTTP response code is encountered.
        """
        url = "{url_base}/resource/{pid}/files/".format(url_base=self.url_base,
                                                        pid=pid)

        params = {}
        close_fd = self._prepareFileForUpload(params, resource_file)

        encoder = MultipartEncoder(params)
        if progress_callback is None:
            progress_callback = default_progress_callback
        monitor = MultipartEncoderMonitor(encoder, progress_callback)

        r = self._request('POST', url, data=monitor, headers={'Content-Type': monitor.content_type})

        if close_fd:
            fd = params['file'][1]
            fd.close()

        if r.status_code != 201:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('POST', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'POST', r.status_code))

        response = r.json()
        assert(response['resource_id'] == pid)

        return response['resource_id']

    def getResourceFile(self, pid, filename, destination=None):
        """ Get a file within a resource.

        :param pid: The HydroShare ID of the resource
        :param filename: String representing the name of the resource file to get.
        :param destination: String representing the directory to save the resource file to. If None, a stream
            to the resource file will be returned instead.
        :return: The path of the downloaded file (if destination was specified), or a stream to the resource
            file.

        :raises: HydroShareArgumentException if any parameters are invalid.
        :raises: HydroShareNotAuthorized if user is not authorized to perform action.
        :raises: HydroShareNotFound if the resource was not found.
        :raises: HydroShareHTTPException if an unexpected HTTP response code is encountered.
        """
        url = "{url_base}/resource/{pid}/files/{filename}".format(url_base=self.url_base,
                                                                  pid=pid,
                                                                  filename=filename)

        if destination:
            if not os.path.isdir(destination):
                raise HydroShareArgumentException("{0} is not a directory.".format(destination))
            if not os.access(destination, os.W_OK):
                raise HydroShareArgumentException("You do not have write permissions to directory '{0}'.".format(destination))

        r = self._request('GET', url, stream=True)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('GET', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid, filename))
            else:
                raise HydroShareHTTPException((url, 'GET', r.status_code))

        if destination is None:
            return r.iter_content(STREAM_CHUNK_SIZE)
        else:
            filepath = os.path.join(destination, filename)
            with open(filepath, 'wb') as fd:
                for chunk in r.iter_content(STREAM_CHUNK_SIZE):
                    fd.write(chunk)
            return filepath

    def deleteResourceFile(self, pid, filename):
        """
        Delete a resource file

        :param pid: The HydroShare ID of the resource
        :param filename: String representing the name of the resource file to delete

        :return: Dictionary containing 'resource_id' the ID of the resource from which the file was deleted, and
            'file_name' the filename of the file deleted.

        :raises: HydroShareNotAuthorized if user is not authorized to perform action.
        :raises: HydroShareNotFound if the resource or resource file was not found.
        :raises: HydroShareHTTPException if an unexpected HTTP response code is encountered.
        """
        url = "{url_base}/resource/{pid}/files/{filename}".format(url_base=self.url_base,
                                                                  pid=pid,
                                                                  filename=filename)

        r = self._request('DELETE', url)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('DELETE', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid, filename))
            else:
                raise HydroShareHTTPException((url, 'DELETE', r.status_code))

        response = r.json()
        assert(response['resource_id'] == pid)
        return response['resource_id']


class AbstractHydroShareAuth(object): pass

class HydroShareAuthBasic(AbstractHydroShareAuth):
    def __init__(self, username, password):
        self.username = username
        self.password = password