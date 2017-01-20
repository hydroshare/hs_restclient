"""

Client library for HydroShare REST API

"""

__title__ = 'hs_restclient'
__version__ = '1.2.6'


import os
import time
import zipfile
import tempfile
import shutil
import mimetypes
import json

import requests

from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import LegacyApplicationClient, TokenExpiredError

from .compat import http_responses


STREAM_CHUNK_SIZE = 100 * 1024

DEFAULT_HOSTNAME = 'www.hydroshare.org'

EXPIRES_AT_ROUNDDOWN_SEC = 15


class HydroShareException(Exception):
    def __init__(self, args):
        super(HydroShareException, self).__init__(args)


class HydroShareArgumentException(HydroShareException):
    def __init__(self, args):
        super(HydroShareArgumentException, self).__init__(args)


class HydroShareBagNotReadyException(HydroShareException):
    def __init__(self, args):
        super(HydroShareBagNotReadyException, self).__init__(args)

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


class HydroShareAuthenticationException(HydroShareException):
    def __init__(self, args):
        super(HydroShareArgumentException, self).__init__(args)


def default_progress_callback(monitor):
    pass


class HydroShare(object):
    """
        Construct HydroShare object for querying HydroShare's REST API

        :param hostname: Hostname of the HydroShare server to query
        :param port: Integer representing the TCP port on which to connect to the HydroShare server
        :param use_https: Boolean, if True, HTTPS will be used (HTTP cannot be used when auth is specified)
        :param verify: Boolean, if True, security certificates will be verified
        :param auth: Concrete instance of AbstractHydroShareAuth (e.g. HydroShareAuthBasic)

        :raises: HydroShareAuthenticationException if auth is not a known authentication type.
        :raises: HydroShareAuthenticationException if auth is specified by use_https is False.
        :raises: HydroShareAuthenticationException if other authentication errors occur.
    """

    _URL_PROTO_WITHOUT_PORT = "{scheme}://{hostname}/hsapi"
    _URL_PROTO_WITH_PORT = "{scheme}://{hostname}:{port}/hsapi"

    def __init__(self, hostname=DEFAULT_HOSTNAME, port=None, use_https=True, verify=True,
                 auth=None):
        self.hostname = hostname
        self.verify = verify

        self.session = None
        self.auth = None
        if auth:
            self.auth = auth

        if use_https:
            self.scheme = 'https'
        else:
            self.scheme = 'http'
        self.use_https = use_https

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

        if self.auth is None:
            # No authentication
            self.session = requests.Session()
        elif isinstance(self.auth, HydroShareAuthBasic):
            # HTTP basic authentication
            if not self.use_https:
                raise HydroShareAuthenticationException("HTTPS is required when using authentication.")
            self.session = requests.Session()
            self.session.auth = (self.auth.username, self.auth.password)
        elif isinstance(self.auth, HydroShareAuthOAuth2):
            # OAuth2 authentication
            if not self.use_https:
                raise HydroShareAuthenticationException("HTTPS is required when using authentication.")
            if self.auth.token is None:
                if self.auth.username is None or self.auth.password is None:
                    msg = "Username and password are required when using OAuth2 without an external token"
                    raise HydroShareAuthenticationException(msg)
                self.session = OAuth2Session(client=LegacyApplicationClient(client_id=self.auth.client_id))
                self.session.fetch_token(token_url=self.auth.token_url,
                                         username=self.auth.username,
                                         password=self.auth.password,
                                         client_id=self.auth.client_id,
                                         client_secret=self.auth.client_secret,
                                         verify=self.verify)
            else:
                self.session = OAuth2Session(client_id=self.auth.client_id, token=self.auth.token)
        else:
            raise HydroShareAuthenticationException("Unsupported authentication type '{0}'.".format(str(type(self.auth))))

    def _request(self, method, url, params=None, data=None, files=None, headers=None, stream=False):
        r = None
        try:
            r = self.session.request(method, url, params=params, data=data, files=files, headers=headers, stream=stream,
                                     verify=self.verify)
        except requests.ConnectionError:
            # We might have gotten a connection error because the server we were talking to went down.
            #  Re-initialize the session and try again
            self._initializeSession()
            r = self.session.request(method, url, params=params, data=data, files=files, headers=headers, stream=stream,
                                     verify=self.verify)

        return r

    def _prepareFileForUpload(self, request_params, resource_file, resource_filename=None):
        fname = None
        close_fd = False
        if isinstance(resource_file, str):
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

    def _getResultsListGenerator(self, url, params=None):
        # Get first (only?) page of results
        r = self._request('GET', url, params=params)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('GET', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((url,))
            else:
                raise HydroShareHTTPException((url, 'GET', r.status_code, params))
        res = r.json()
        results = res['results']
        for item in results:
            yield item

        # Get remaining pages (if any exist)
        while res['next']:
            next_url = res['next']
            if self.use_https:
                # Make sure the next URL uses HTTPS
                next_url = next_url.replace('http://', 'https://', 1)
            r = self._request('GET', next_url, params=params)
            if r.status_code != 200:
                if r.status_code == 403:
                    raise HydroShareNotAuthorized(('GET', next_url))
                elif r.status_code == 404:
                    raise HydroShareNotFound((next_url,))
                else:
                    raise HydroShareHTTPException((next_url, 'GET', r.status_code, params))
            res = r.json()
            results = res['results']
            for item in results:
                yield item

    def getResourceList(self, creator=None, owner=None, user=None, group=None, from_date=None, to_date=None,
                        types=None):
        """
        Query the GET /hsapi/resource/ REST end point of the HydroShare server.

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
        url = "{url_base}/resource/".format(url_base=self.url_base)

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

        return self._getResultsListGenerator(url, params)

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
        url = "{url_base}/resource/{pid}/sysmeta/".format(url_base=self.url_base,
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

    def getScienceMetadataRDF(self, pid):
        """ Get science metadata for a resource in XML+RDF format

        :param pid: The HydroShare ID of the resource
        :raises: HydroShareNotAuthorized if the user is not authorized to view the metadata.
        :raises: HydroShareNotFound if the resource was not found.
        :raises: HydroShareHTTPException to signal an HTTP error.
        :return: A string representing the XML+RDF serialization of science metadata.
        Example of data XML+RDF returned:

        <?xml version="1.0"?>
        <!DOCTYPE rdf:RDF PUBLIC "-//DUBLIN CORE//DCMES DTD 2002/07/31//EN"
        "http://dublincore.org/documents/2002/07/31/dcmes-xml/dcmes-xml-dtd.dtd">
        <rdf:RDF xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:hsterms="http://hydroshare.org/terms/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:rdfs1="http://www.w3.org/2001/01/rdf-schema#">
          <rdf:Description rdf:about="http://www.hydroshare.org/resource/87ffb608900e407ab4b67d30c93b329e">
            <dc:title>Great Salt Lake Level and Volume</dc:title>
            <dc:type rdf:resource="http://www.hydroshare.org/terms/GenericResource"/>
            <dc:description>
              <rdf:Description>
                <dcterms:abstract>Time series of level, area and volume in the Great Salt Lake. Volume and area of the Great Salt Lake are derived from recorded levels</dcterms:abstract>
              </rdf:Description>
            </dc:description>
            <hsterms:awardInfo>
              <rdf:Description rdf:about="http://www.nsf.gov">
                <hsterms:fundingAgencyName>National Science Foundation</hsterms:fundingAgencyName>
                <hsterms:awardTitle>Model Execution Cyberinfrastructure </hsterms:awardTitle>
                <hsterms:awardNumber>NSF_9087658_2017</hsterms:awardNumber>
              </rdf:Description>
            </hsterms:awardInfo>
            <dc:creator>
              <rdf:Description>
                <hsterms:name>John Smith</hsterms:name>
                <hsterms:creatorOrder>1</hsterms:creatorOrder>
                <hsterms:organization>Utah State University</hsterms:organization>
                <hsterms:email>john.smith@gmail.com</hsterms:email>
                <hsterms:address>Engineering Building, USU, Logan, Utah</hsterms:address>
                <hsterms:phone rdf:resource="tel:435-797-8967"/>
              </rdf:Description>
            </dc:creator>
            <dc:creator>
              <rdf:Description>
                <hsterms:name>Lisa Miller</hsterms:name>
                <hsterms:creatorOrder>2</hsterms:creatorOrder>
              </rdf:Description>
            </dc:creator>
            <dc:contributor>
              <rdf:Description>
                <hsterms:name>Jenny Parker</hsterms:name>
                <hsterms:organization>Univesity of Utah</hsterms:organization>
                <hsterms:email>jenny_parker@hotmail.com</hsterms:email>
              </rdf:Description>
            </dc:contributor>
            <dc:coverage>
              <dcterms:period>
                <rdf:value>start=2000-01-01T00:00:00; end=2010-12-12T00:00:00; scheme=W3C-DTF</rdf:value>
              </dcterms:period>
            </dc:coverage>
            <dc:date>
              <dcterms:created>
                <rdf:value>2017-01-03T17:06:18.932217+00:00</rdf:value>
              </dcterms:created>
            </dc:date>
            <dc:date>
              <dcterms:modified>
                <rdf:value>2017-01-03T17:35:34.067279+00:00</rdf:value>
              </dcterms:modified>
            </dc:date>
            <dc:format>image/tiff</dc:format>
            <dc:identifier>
              <rdf:Description>
                <hsterms:hydroShareIdentifier>http://www.hydroshare.org/resource/87ffb608900e407ab4b67d30c93b329e</hsterms:hydroShareIdentifier>
              </rdf:Description>
            </dc:identifier>
            <dc:language>eng</dc:language>
            <dc:rights>
              <rdf:Description>
                <hsterms:rightsStatement>This resource is shared under the Creative Commons Attribution CC BY.</hsterms:rightsStatement>
                <hsterms:URL rdf:resource="http://creativecommons.org/licenses/by/4.0/"/>
              </rdf:Description>
            </dc:rights>
            <dc:subject>NSF</dc:subject>
            <dc:subject>Model</dc:subject>
            <dc:subject>Cyberinfrastructure</dc:subject>
            <hsterms:extendedMetadata>
              <rdf:Description>
                <hsterms:key>model</hsterms:key>
                <hsterms:value>ueb</hsterms:value>
              </rdf:Description>
            </hsterms:extendedMetadata>
            <hsterms:extendedMetadata>
              <rdf:Description>
                <hsterms:key>os</hsterms:key>
                <hsterms:value>windows</hsterms:value>
              </rdf:Description>
            </hsterms:extendedMetadata>
          </rdf:Description>
          <rdf:Description rdf:about="http://www.hydroshare.org/terms/GenericResource">
            <rdfs1:label>Generic</rdfs1:label>
            <rdfs1:isDefinedBy>http://www.hydroshare.org/terms</rdfs1:isDefinedBy>
          </rdf:Description>
        </rdf:RDF>
        """

        url = "{url_base}/scimeta/{pid}/".format(url_base=self.url_base, pid=pid)
        r = self._request('GET', url)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('GET', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'GET', r.status_code))

        return str(r.content)

    def getScienceMetadata(self, pid):
        """ Get science metadata for a resource in JSON format
        Note: Only Dublin core metadata is retrieved.

        :param pid: The HydroShare ID of the resource
        :raises: HydroShareNotAuthorized if the user is not authorized to view the metadata.
        :raises: HydroShareNotFound if the resource was not found.
        :raises: HydroShareHTTPException to signal an HTTP error.
        :return: A string representing JSON serialization of science metadata.

        Example of data JSON returned:

        {
            "title":"Great Salt Lake Level and Volume",
            "creators":[
                        {"name":"John Smith","description":"/user/24/","organization":"USU","email":"john.smith@usu.edu","address":"Engineering Building, USU, Logan, Utah","phone":"435-789-9087","homepage":null,"order":1},
                        {"name":"Lisa Miller","description":null,"organization":null,"email":null,"address":null,"phone":null,"homepage":null,"order":2}
                       ],
            "contributors":[
                            {"name":"Jenny Parker","description":"","organization":"Univesity of Utah","email":"jenny_parker@hotmail.com","address":"","phone":"","homepage":""}
                           ],
            "coverages":[
                            {"type":"period","value":{"start":"01/01/2000","end":"12/12/2010"}}
                        ],
            "dates":[
                        {"type":"created","start_date":"2017-01-03T17:06:18.932217Z","end_date":null},
                        {"type":"modified","start_date":"2017-01-03T17:06:19.162694Z","end_date":null}
                    ],
            "description":"Time series of level, area and volume in the Great Salt Lake. Volume and area of the Great Salt Lake are derived from recorded levels",
            "formats":[
                        {"value":"image/tiff"}
                      ],
            "funding_agencies":[
                                {"agency_name":"National Science Foundation","award_title":"Model Execution Cyberinfrastructure ","award_number":"NSF_9087658_2017","agency_url":"http://www.nsf.gov"}
                               ],
            "identifiers":[
                            {"name":"hydroShareIdentifier","url":"http://www.hydroshare.org/resource/87ffb608900e407ab4b67d30c93b329e"}
                        ],
            "language":"eng",
            "rights":"This resource is shared under the Creative Commons Attribution CC BY. http://creativecommons.org/licenses/by/4.0/",
            "type":"http://www.hydroshare.org/terms/GenericResource",
            "publisher":null,"sources":[],
            "subjects":[
                        {"value":"NSF"},
                        {"value":"Modeling"}
                       ],
            "relations":[]
        }
        """

        url = "{url_base}/resource/{pid}/scimeta/elements".format(url_base=self.url_base, pid=pid)

        r = self._request('GET', url)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('GET', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'GET', r.status_code))

        return r.json()

    def updateScienceMetadata(self, pid, metadata):
        """Update Dublin core metadata for a resource

        :param pid: The HydroShare ID of the resource for which science metadata needs to be updated
        :param  metadata: A dict containing data for each of the dublin core metadata elements that needs to be updated
        :raises: HydroShareNotAuthorized if the user is not authorized to view the metadata.
        :raises: HydroShareNotFound if the resource was not found.
        :raises: HydroShareHTTPException to signal an HTTP error.
        :return: A string representing the JSON serialization of resource science metadata.

        Example of data JSON returned:

        {
            "title":"Great Salt Lake Level and Volume",
            "creators":[
                        {"name":"John Smith","description":"/user/24/","organization":"USU","email":"john.smith@usu.edu","address":"Engineering Building, USU, Logan, Utah","phone":"435-789-9087","homepage":null,"order":1},
                        {"name":"Lisa Miller","description":null,"organization":null,"email":null,"address":null,"phone":null,"homepage":null,"order":2}
                       ],
            "contributors":[
                            {"name":"Jenny Parker","description":"","organization":"Univesity of Utah","email":"jenny_parker@hotmail.com","address":"","phone":"","homepage":""}
                           ],
            "coverages":[
                            {"type":"period","value":{"start":"01/01/2000","end":"12/12/2010"}}
                        ],
            "dates":[
                        {"type":"created","start_date":"2017-01-03T17:06:18.932217Z","end_date":null},
                        {"type":"modified","start_date":"2017-01-03T17:06:19.162694Z","end_date":null}
                    ],
            "description":"Time series of level, area and volume in the Great Salt Lake. Volume and area of the Great Salt Lake are derived from recorded levels",
            "formats":[
                        {"value":"image/tiff"}
                      ],
            "funding_agencies":[
                                {"agency_name":"National Science Foundation","award_title":"Model Execution Cyberinfrastructure ","award_number":"NSF_9087658_2017","agency_url":"http://www.nsf.gov"}
                               ],
            "identifiers":[
                            {"name":"hydroShareIdentifier","url":"http://www.hydroshare.org/resource/87ffb608900e407ab4b67d30c93b329e"}
                        ],
            "language":"eng",
            "rights":"This resource is shared under the Creative Commons Attribution CC BY. http://creativecommons.org/licenses/by/4.0/",
            "type":"http://www.hydroshare.org/terms/GenericResource",
            "publisher":null,"sources":[],
            "subjects":[
                        {"value":"NSF"},
                        {"value":"Modeling"}
                       ],
            "relations":[]
        }
        """

        url = "{url_base}/resource/{pid}/scimeta/elements/".format(url_base=self.url_base, pid=pid)

        r = self._request('PUT', url, data=metadata)
        if r.status_code != 202:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('PUT', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'PUT', r.status_code, metadata))

        return r.json()

    def getResourceMap(self, pid):
        """ Get resource map metadata for a resource

        :param pid: The HydroShare ID of the resource
        :raises: HydroShareNotAuthorized if the user is not authorized to view the metadata.
        :raises: HydroShareNotFound if the resource was not found.
        :raises: HydroShareHTTPException to signal an HTTP error.
        :return: A string representing the XML+RDF serialization of resource map metadata.
        Example of data returned:

        <?xml version="1.0" encoding="UTF-8"?>
        <rdf:RDF
           xmlns:citoterms="http://purl.org/spar/cito/"
           xmlns:dc="http://purl.org/dc/elements/1.1/"
           xmlns:dcterms="http://purl.org/dc/terms/"
           xmlns:foaf="http://xmlns.com/foaf/0.1/"
           xmlns:ore="http://www.openarchives.org/ore/terms/"
           xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
           xmlns:rdfs1="http://www.w3.org/2001/01/rdf-schema#"
        >
          <rdf:Description rdf:about="http://foresite-toolkit.googlecode.com/#pythonAgent">
            <foaf:name>Foresite Toolkit (Python)</foaf:name>
            <foaf:mbox>foresite@googlegroups.com</foaf:mbox>
          </rdf:Description>
          <rdf:Description rdf:about="http://www.hydroshare.org/terms/GenericResource">
            <rdfs1:label>Generic</rdfs1:label>
            <rdfs1:isDefinedBy>http://www.hydroshare.org/terms</rdfs1:isDefinedBy>
          </rdf:Description>
          <rdf:Description rdf:about="http://www.hydroshare.org/resource/03c862ccf17b4853ac4288d63ab2d766/data/contents/test.txt">
            <ore:isAggregatedBy>http://www.hydroshare.org/resource/03c862ccf17b4853ac4288d63ab2d766/data/resourcemap.xml#aggregation</ore:isAggregatedBy>
            <dc:format>text/plain</dc:format>
          </rdf:Description>
          <rdf:Description rdf:about="http://www.hydroshare.org/resource/03c862ccf17b4853ac4288d63ab2d766/data/resourcemap.xml">
            <dc:identifier>03c862ccf17b4853ac4288d63ab2d766</dc:identifier>
            <ore:describes rdf:resource="http://www.hydroshare.org/resource/03c862ccf17b4853ac4288d63ab2d766/data/resourcemap.xml#aggregation"/>
            <rdf:type rdf:resource="http://www.openarchives.org/ore/terms/ResourceMap"/>
            <dc:format>application/rdf+xml</dc:format>
            <dc:creator rdf:resource="http://foresite-toolkit.googlecode.com/#pythonAgent"/>
            <dcterms:created>2016-11-29T16:17:52Z</dcterms:created>
            <dcterms:modified>2016-11-29T16:17:52Z</dcterms:modified>
          </rdf:Description>
          <rdf:Description rdf:about="http://www.openarchives.org/ore/terms/ResourceMap">
            <rdfs1:isDefinedBy>http://www.openarchives.org/ore/terms/</rdfs1:isDefinedBy>
            <rdfs1:label>ResourceMap</rdfs1:label>
          </rdf:Description>
          <rdf:Description rdf:about="http://www.hydroshare.org/resource/03c862ccf17b4853ac4288d63ab2d766/data/resourcemap.xml#aggregation">
            <citoterms:isDocumentedBy>http://www.hydroshare.org/resource/03c862ccf17b4853ac4288d63ab2d766/data/resourcemetadata.xml</citoterms:isDocumentedBy>
            <dc:title>Gen Res-1</dc:title>
            <dcterms:type rdf:resource="http://www.hydroshare.org/terms/GenericResource"/>
            <ore:isDescribedBy>http://www.hydroshare.org/resource/03c862ccf17b4853ac4288d63ab2d766/data/resourcemap.xml</ore:isDescribedBy>
            <ore:aggregates rdf:resource="http://www.hydroshare.org/resource/03c862ccf17b4853ac4288d63ab2d766/data/resourcemetadata.xml"/>
            <ore:aggregates rdf:resource="http://www.hydroshare.org/resource/03c862ccf17b4853ac4288d63ab2d766/data/contents/test.txt"/>
            <rdf:type rdf:resource="http://www.openarchives.org/ore/terms/Aggregation"/>
              </rdf:Description>
          <rdf:Description rdf:about="http://www.hydroshare.org/resource/03c862ccf17b4853ac4288d63ab2d766/data/resourcemetadata.xml">
            <ore:isAggregatedBy>http://www.hydroshare.org/resource/03c862ccf17b4853ac4288d63ab2d766/data/resourcemap.xml#aggregation</ore:isAggregatedBy>
            <citoterms:documents>http://www.hydroshare.org/resource/03c862ccf17b4853ac4288d63ab2d766/data/resourcemap.xml#aggregation</citoterms:documents>
            <dc:title>Dublin Core science metadata document describing the HydroShare resource</dc:title>
            <dc:format>application/rdf+xml</dc:format>
          </rdf:Description>
          <rdf:Description rdf:about="http://www.openarchives.org/ore/terms/Aggregation">
            <rdfs1:label>Aggregation</rdfs1:label>
            <rdfs1:isDefinedBy>http://www.openarchives.org/ore/terms/</rdfs1:isDefinedBy>
          </rdf:Description>
        </rdf:RDF>
        """
        url = "{url_base}/resource/{pid}/map/".format(url_base=self.url_base,
                                                 pid=pid)
        r = self._request('GET', url)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('GET', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'GET', r.status_code))

        return str(r.content)

    def getResource(self, pid, destination=None, unzip=False, wait_for_bag_creation=True):
        """ Get a resource in BagIt format

        :param pid: The HydroShare ID of the resource
        :param destination: String representing the directory to save bag to. Bag will be saved to file named
            $(PID).zip in destination; existing file of the same name will be overwritten. If None, a stream to the
            zipped bag will be returned instead.
        :param unzip: True if the bag should be unzipped when saved to destination. Bag contents to be saved to
            directory named $(PID) residing in destination. Only applies when destination is not None.

        :param wait_for_bag_creation: True if to wait to download the bag in case the bag is not ready
            (bag needs to be recreated before it can be downloaded).
        :raises: HydroShareArgumentException if any arguments are invalid.
        :raises: HydroShareNotAuthorized if the user is not authorized to access the
            resource.
        :raises: HydroShareNotFound if the resource was not found.
        :raises: HydroShareHTTPException to signal an HTTP error
        :raise: HydroShareBagNotReady if the bag is not ready to be downloaded and wait_for_bag_creation is False

        :return: None if the bag was saved directly to disk.  Or a generator representing a buffered stream of the
            bytes comprising the bag returned by the REST end point.
        """
        stream = self._getBagStream(pid, wait_for_bag_creation)
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

    def _getBagStream(self, pid, wait_for_bag_creation):
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
        elif r.headers['content-type'] == 'application/json':
            # this  is the case of bag being generated by hydroshare and not ready for download
            content = json.loads(r.content)
            if content['bag_status'] == "Not ready":
                if wait_for_bag_creation:
                    # will wait until the bag is ready for download
                    status = False
                    while not status:
                        # check bag ready status every 3 seconds
                        time.sleep(3)
                        task_id = content['task_id']
                        # check task status
                        status = self._getTaskStatus(task_id)
                        if status:
                            # bag is ready for download
                            return self._getBagStream(pid, wait_for_bag_creation)
                else:
                    raise HydroShareBagNotReadyException("Please try later. The bag is not ready yet for download.")
        elif r.headers['content-type'] == 'text/plain':
            # this is the case of big file issue
            raise HydroShareException(r.content)

        return r.iter_content(STREAM_CHUNK_SIZE)

    def _getTaskStatus(self, task_id):
        task_status_url = "{url_base}/taskstatus/{task_id}/"
        task_status_url = task_status_url.format(url_base=self.url_base, task_id=task_id)
        r = self._request('GET', task_status_url)
        response_data = json.loads(r.content)
        return response_data['status']

    def getResourceTypes(self):
        """ Get the list of resource types supported by the HydroShare server

        :return: A set of strings representing the HydroShare resource types

        :raises: HydroShareHTTPException to signal an HTTP error
        """
        url = "{url_base}/resource/types".format(url_base=self.url_base)

        r = self._request('GET', url)
        if r.status_code != 200:
            raise HydroShareHTTPException((url, 'GET', r.status_code))

        resource_types = r.json()
        return set([t['resource_type'] for t in resource_types])

    def createResource(self, resource_type, title, resource_file=None, resource_filename=None,
                       abstract=None, keywords=None,
                       edit_users=None, view_users=None, edit_groups=None, view_groups=None,
                       metadata=None, extra_metadata=None, progress_callback=None):
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
        :param metadata: json string data for each of the metadata elements
        :param extra_metadata: json string data for key/value pair metadata elements defined by user
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

        if resource_type not in self.resource_types:
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

        if metadata:
            params['metadata'] = metadata

        if extra_metadata:
            params['extra_metadata'] = extra_metadata

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

    def addResourceFile(self, pid, resource_file, resource_filename=None, progress_callback=None):
        """ Add a new file to an existing resource

        :param pid: The HydroShare ID of the resource
        :param resource_file: a read-only binary file-like object (i.e. opened with the flag 'rb') or a string
            representing path to file to be uploaded as part of the new resource
        :param resource_filename: string representing the filename of the resource file.  Must be specified
            if resource_file is a file-like object.  If resource_file is a string representing a valid file path,
            and resource_filename is not specified, resource_filename will be equal to os.path.basename(resource_file).
            is a string
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

    def getResourceFileList(self, pid):
        """ Get a listing of files within a resource.

        :param pid: The HydroShare ID of the resource whose resource files are to be listed.

        :raises: HydroShareArgumentException if any parameters are invalid.
        :raises: HydroShareNotAuthorized if user is not authorized to perform action.
        :raises: HydroShareNotFound if the resource was not found.
        :raises: HydroShareHTTPException if an unexpected HTTP response code is encountered.

        :return: A generator that can be used to fetch dict objects, each dict representing
            the JSON object representation of the resource returned by the REST end point.  For example:

        {
            "count": 95,
            "next": "https://www.hydroshare.org/hsapi/resource/32a08bc23a86e471282a832143491b49/file_list/?page=2",
            "previous": null,
            "results": [
                {
                    "url": "http://www.hydroshare.org/django_irods/download/32a08bc23a86e471282a832143491b49/data/contents/foo/bar.txt",
                    "size": 23550,
                    "content_type": "text/plain"
                },
                {
                    "url": "http://www.hydroshare.org/django_irods/download/32a08bc23a86e471282a832143491b49/data/contents/dem.tif",
                    "size": 107545,
                    "content_type": "image/tiff"
                },
                {
                    "url": "http://www.hydroshare.org/django_irods/download/32a08bc23a86e471282a832143491b49/data/contents/data.csv",
                    "size": 148,
                    "content_type": "text/csv"
                },
                {
                    "url": "http://www.hydroshare.org/django_irods/download/32a08bc23a86e471282a832143491b49/data/contents/data.sqlite",
                    "size": 267118,
                    "content_type": "application/x-sqlite3"
                },
                {
                    "url": "http://www.hydroshare.org/django_irods/download/32a08bc23a86e471282a832143491b49/data/contents/viz.png",
                    "size": 128,
                    "content_type": "image/png"
                }
            ]
        }
        """
        url = "{url_base}/resource/{pid}/files/".format(url_base=self.url_base,
                                                            pid=pid)
        return self._getResultsListGenerator(url)

    def getResourceFolderContents(self, pid, pathname):
        """ Get a listing of files and folders for a resource at the specified path (*pathname*)

        :param pid: The HydroShare ID of the resource whose folder contents to be listed
        :param pathname: Folder path for which contents (files and folders) need to be listed
        :return: A JSON object representing the contents of the specified folder

        :raises: HydroShareNotAuthorized if user is not authorized to perform action.
        :raises: HydroShareNotFound if the resource or resource file was not found.
        :raises: HydroShareHTTPException if an unexpected HTTP response code is encountered.

        Example of JSON data returned:
        {
            "resource_id": "32a08bc23a86e471282a832143491b49",
            "path": "model/initial",
            "files": ["model.exe", "param.txt"],
            "folders": ["run/1", "run/2"]
        }
        """

        url = "{url_base}/resource/{pid}/folders/{path}".format(url_base=self.url_base, pid=pid, path=pathname)

        r = self._request('GET', url)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('GET', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'GET', r.status_code))

        return r.json()

    def createResourceFolder(self, pid, pathname):
        """Create folder as specified by *pathname* for a given resource

        :param pid: The HydroShare ID of the resource for which folder to be created
        :param pathname: Folder path/name for the folder to be created
        :return: A JSON object representing the resource id and path of the folder that was created

        :raises: HydroShareNotAuthorized if user is not authorized to perform action.
        :raises: HydroShareNotFound if the resource or resource file was not found.
        :raises: HydroShareHTTPException if an unexpected HTTP response code is encountered.

        Example of JSON data returned:
        {
            "resource_id": "32a08bc23a86e471282a832143491b49",
            "path": "model/initial"
        }
        """

        url = "{url_base}/resource/{pid}/folders/{path}".format(url_base=self.url_base, pid=pid, path=pathname)

        r = self._request('PUT', url)
        if r.status_code != 201:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('PUT', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'PUT', r.status_code))

        return r.json()

    def deleteResourceFolder(self, pid, pathname):
        """Delete a folder as specified by *pathname* for a given resource

        :param pid: The HydroShare ID of the resource for which folder to be deleted
        :param pathname: Folder path/name for the folder to be deleted
        :return: A JSON object representing the resource id and path of the folder that was deleted

        :raises: HydroShareNotAuthorized if user is not authorized to perform action.
        :raises: HydroShareNotFound if the resource or resource file was not found.
        :raises: HydroShareHTTPException if an unexpected HTTP response code is encountered.

        Example of JSON data returned:
        {
            'resource_id': "32a08bc23a86e471282a832143491b49",
            'path': "model/initial"
        }
        """

        url = "{url_base}/resource/{pid}/folders/{path}".format(url_base=self.url_base, pid=pid, path=pathname)

        r = self._request('DELETE', url)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('DELETE', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'DELETE', r.status_code))

        return r.json()

    def getUserInfo(self):
        """
        Query the GET /hsapi/userInfo/ REST end point of the HydroShare server.

        :raises: HydroShareHTTPException to signal an HTTP error

        :return: A JSON object representing user info, for example:

        {
            "username": "username",
            "first_name": "First",
            "last_name": "Last",
            "email": "user@domain.com"
        }
        """
        url = "{url_base}/userInfo/".format(url_base=self.url_base)

        r = self._request('GET', url)
        if r.status_code != 200:
            raise HydroShareHTTPException((url, 'GET', r.status_code))

        return r.json()


class AbstractHydroShareAuth(object): pass


class HydroShareAuthBasic(AbstractHydroShareAuth):
    def __init__(self, username, password):
        self.username = username
        self.password = password


class HydroShareAuthOAuth2(AbstractHydroShareAuth):

    _TOKEN_URL_PROTO_WITHOUT_PORT = "{scheme}://{hostname}/o/token/"
    _TOKEN_URL_PROTO_WITH_PORT = "{scheme}://{hostname}:{port}/o/token/"

    def __init__(self, client_id, client_secret,
                 hostname=DEFAULT_HOSTNAME, use_https=True, port=None,
                 username=None, password=None,
                 token=None):
        if use_https:
            scheme = 'https'
        else:
            scheme = 'http'

        if port:
            self.token_url = self._TOKEN_URL_PROTO_WITH_PORT.format(scheme=scheme,
                                                                    hostname=hostname,
                                                                    port=port)
        else:
            self.token_url = self._TOKEN_URL_PROTO_WITHOUT_PORT.format(scheme=scheme,
                                                                       hostname=hostname)
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.token = token

        if self.token:
            if 'expires_at' not in self.token:
                self.token['expires_at'] = int(time.time()) + int(self.token['expires_in']) - EXPIRES_AT_ROUNDDOWN_SEC

