.. hs_restclient documentation master file, created by
   sphinx-quickstart on Tue May 26 18:13:28 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

HydroShare REST API Python client library
=========================================

Release v\ |version|

.. toctree::
   :maxdepth: 2

Installation
------------

pip install hs_restclient


API documentation
-----------------

:ref:`modindex`


Usage
-----

To get system metadata for public resources:

    >>> from hs_restclient import HydroShare
    >>> hs = HydroShare()
    >>> for resource in hs.getResourceList():
    >>>     print(resource)

To authenticate using HTTP Basic authentication, and then get system metadata for resources you have access to:

    >>> from hs_restclient import HydroShare, HydroShareAuthBasic
    >>> auth = HydroShareAuthBasic(username='myusername', password='mypassword')
    >>> hs = HydroShare(auth=auth)
    >>> for resource in hs.getResourceList():
    >>>     print(resource)

To authenticate using OAuth2 authentication (using a user and password supplied by the user), and then get a list of
resources you have access to:

    >>> from oauthlib.oauth2 import TokenExpiredError
    >>> from hs_restclient import HydroShare, HydroShareAuthOAuth2
    >>>
    >>> # Get a client ID and client secret by registering a new application at:
    >>> # https://www.hydroshare.org/o/applications/
    >>> # Choose client type "Confidential" and authorization grant type "Resource owner password-based"
    >>> # Keep these secret!
    >>> client_id = 'MYCLIENTID'
    >>> client_secret = 'MYCLIENTSECRET'
    >>>
    >>> auth = HydroShareAuthOAuth2(client_id, client_secret,
    >>>                             username='myusername', password='mypassword')
    >>> hs = HydroShare(auth=auth)
    >>>
    >>> try:
    >>>     for resource in hs.getResourceList():
    >>>         print(resource)
    >>> except TokenExpiredError as e:
    >>>     hs = HydroShare(auth=auth)
    >>>    for resource in hs.getResourceList():
    >>>         print(resource)

Note that currently the client does not handle token renewal, hence the need to catch TokenExpiredError.

To authenticate using OAuth2 authentication (using an existing token), and then get a list of resources you have
access to:

    >>> from oauthlib.oauth2 import TokenExpiredError
    >>> from hs_restclient import HydroShare, HydroShareAuthOAuth2
    >>>
    >>> # Get a client ID and client secret by registering a new application at:
    >>> # https://www.hydroshare.org/o/applications/
    >>> # Choose client type "Confidential" and authorization grant type "Resource owner password-based"
    >>> # Keep these secret!
    >>> client_id = 'MYCLIENTID'
    >>> client_secret = 'MYCLIENTSECRET'
    >>>
    >>> # A token dictionary obtained separately from HydroShare of the form:
    >>> #   {
    >>> #       "access_token": "<your_access_token>",
    >>> #       "token_type": "Bearer",
    >>> #       "expires_in": 36000,
    >>> #       "refresh_token": "<your_refresh_token>",
    >>> #       "scope": "read write groups"
    >>> #   }
    >>>
    >>> # get_token() is a stand in for how you get a new token on your system.
    >>> token = get_token()
    >>> auth = HydroShareAuthOAuth2(client_id, client_secret,
    >>>                             token=token)
    >>> try:
    >>>     hs = HydroShare(auth=auth)
    >>>     for resource in hs.getResourceList():
    >>>         print(resource)
    >>> except:
    >>>     # get_token() is a stand in for how you get a new token on your system.
    >>>     token = get_token()
    >>>     auth = HydroShareAuthOAuth2(client_id, client_secret,
    >>>                                 token=token)
    >>>     hs = HydroShare(auth=auth)
    >>>     for resource in hs.getResourceList():
    >>>         print(resource)

Note that currently the client does not handle token renewal, hence the need to catch TokenExpiredError.

To connect to a development HydroShare server that uses a self-sign security certificate:

    >>> from hs_restclient import HydroShare
    >>> hs = HydroShare(hostname='mydev.mydomain.net', verify=False)
    >>> for resource in hs.getResourceList():
    >>>     print(resource)

To connect to a development HydroShare server that is not running HTTPS:

    >>> from hs_restclient import HydroShare
    >>> hs = HydroShare(hostname='mydev.mydomain.net', port=8000, use_https=False)
    >>> for resource in hs.getResourceList():
    >>>     print(resource)

Note that authenticated connections **must** use HTTPS.

To get the system metadata for a particular resource:

    >>> from hs_restclient import HydroShare
    >>> hs = HydroShare()
    >>> resource_md = hs.getSystemMetadata('e62a438bec384087b6c00ddcd1b6475a')
    >>> print(resource_md['resource_title'])

To get the BagIt archive of a particular resource:

    >>> from hs_restclient import HydroShare
    >>> hs = HydroShare()
    >>> hs.getResource('e62a438bec384087b6c00ddcd1b6475a', destination='/tmp')

or to have the BagIt archive unzipped for you:

    >>> from hs_restclient import HydroShare
    >>> hs = HydroShare()
    >>> hs.getResource('e62a438bec384087b6c00ddcd1b6475a', destination='/tmp', unzip=True)

or to get the BagIt archive as a generator (sort of like a buffered stream):

    >>> from hs_restclient import HydroShare
    >>> hs = HydroShare()
    >>> resource = hs.getResource('e62a438bec384087b6c00ddcd1b6475a')
    >>> with open('/tmp/myresource.zip', 'wb') as fd:
    >>>     for chunk in resource:
    >>>         fd.write(chunk)

To create a resource:

    >>> from hs_restclient import HydroShare, HydroShareAuthBasic
    >>> auth = HydroShareAuthBasic(username='myusername', password='mypassword')
    >>> hs = HydroShare(auth=auth)
    >>> abstract = 'My abstract'
    >>> title = 'My resource'
    >>> keywords = ('my keyword 1', 'my keyword 2')
    >>> rtype = 'GenericResource'
    >>> fpath = '/path/to/a/file'
    >>> metadata = '[{"coverage":{"type":"period", "value":{"start":"01/01/2000", "end":"12/12/2010"}}}, {"creator":{"name":"John Smith"}}, {"creator":{"name":"Lisa Miller"}}]'
    >>> resource_id = hs.createResource(rtype, title, resource_file=fpath, keywords=keywords, abstract=abstract, metadata=metadata)

To make a resource public:

    >>> from hs_restclient import HydroShare, HydroShareAuthBasic
    >>> auth = HydroShareAuthBasic(username='myusername', password='mypassword')
    >>> hs = HydroShare(auth=auth)
    >>> hs.setAccessRules('ID OF RESOURCE GOES HERE', public=True)

To delete a resource:

    >>> from hs_restclient import HydroShare, HydroShareAuthBasic
    >>> auth = HydroShareAuthBasic(username='myusername', password='mypassword')
    >>> hs = HydroShare(auth=auth)
    >>> hs.deleteResource('ID OF RESOURCE GOES HERE')

To add a file to a resource:

    >>> from hs_restclient import HydroShare, HydroShareAuthBasic
    >>> auth = HydroShareAuthBasic(username='myusername', password='mypassword')
    >>> hs = HydroShare(auth=auth)
    >>> fpath = '/path/to/somefile.txt'
    >>> resource_id = hs.addResourceFile('ID OF RESOURCE GOES HERE', fpath)

To get a file in a resource:

    >>> from hs_restclient import HydroShare, HydroShareAuthBasic
    >>> auth = HydroShareAuthBasic(username='myusername', password='mypassword')
    >>> hs = HydroShare(auth=auth)
    >>> fname = 'somefile.txt'
    >>> fpath = hs.getResourceFile('ID OF RESOURCE GOES HERE', fname, destination='/directory/to/download/file/to')

To delete a file from a resource:

    >>> from hs_restclient import HydroShare, HydroShareAuthBasic
    >>> auth = HydroShareAuthBasic(username='myusername', password='mypassword')
    >>> hs = HydroShare(auth=auth)
    >>> fname = 'somefile.txt'
    >>> resource_id = hs.deleteResourceFile('ID OF RESOURCE GOES HERE', fname)



Index
-----

* :ref:`genindex`


