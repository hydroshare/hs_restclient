Python-based client library for HydroShare REST API
===================================================

Questions? brian_miles@unc.edu

To run tests
------------
    
To run unit tests::

    cd tests
    python test_hs_restclient.py
    
To use
------

To get a listing of public resources::

    from hs_restclient import HydroShare
    hs = HydroShare()
    for resource in hs.getResourceList():
        print(resource)

To authenticate using HTTP Basic authentication, and then get a list of resources you have access to::

    from hs_restclient import HydroShare, HydroShareAuthBasic
    auth = HydroShareAuthBasic(username='myusername', password='mypassword')
    hs = HydroShare(auth=auth)
    for resource in hs.getResourceList():
        print(resource)

To authenticate using OAuth2 authentication (using a user and password supplied by the user), and then get a list of
resources you have access to::

    from oauthlib.oauth2 import TokenExpiredError
    from hs_restclient import HydroShare, HydroShareAuthOAuth2

    # Get a client ID and client secret by registering a new application at:
    # https://www.hydroshare.org/o/applications/
    # Choose client type "Confidential" and authorization grant type "Resource owner password-based"
    # Keep these secret!
    client_id = 'MYCLIENTID'
    client_secret = 'MYCLIENTSECRET'

    auth = HydroShareAuthOAuth2(client_id, client_secret,
                                username='myusername', password='mypassword')
    hs = HydroShare(auth=auth)

    try:
        for resource in hs.getResourceList():
            print(resource)
    except TokenExpiredError as e:
        hs = HydroShare(auth=auth)
        for resource in hs.getResourceList():
            print(resource)

Note that currently the client does not handle token renewal, hence the need to catch TokenExpiredError.

To authenticate using OAuth2 authentication (using an existing token), and then get a list of resources you have
access to::

    from oauthlib.oauth2 import TokenExpiredError
    from hs_restclient import HydroShare, HydroShareAuthOAuth2

    # Get a client ID and client secret by registering a new application at:
    # https://www.hydroshare.org/o/applications/
    # Choose client type "Confidential" and authorization grant type "Resource owner password-based"
    # Keep these secret!
    client_id = 'MYCLIENTID'
    client_secret = 'MYCLIENTSECRET'

    # A token dictionary obtained separately from HydroShare of the form:
    #   {
    #       "access_token": "<your_access_token>",
    #       "token_type": "Bearer",
    #       "expires_in": 36000,
    #       "refresh_token": "<your_refresh_token>",
    #       "scope": "read write groups"
    #   }
    # get_token() is a stand in for how you get a new token on your system.
    token = get_token()

    auth = HydroShareAuthOAuth2(client_id, client_secret,
                                token=token)
    try:
        hs = HydroShare(auth=auth)
        for resource in hs.getResourceList():
            print(resource)
    except:
        # get_token() is a stand in for how you get a new token on your system.
        token = get_token()
        hs = HydroShare(auth=auth)
        for resource in hs.getResourceList():
            print(resource)

Note that currently the client does not handle token renewal, hence the need to catch TokenExpiredError.

To connect to a development HydroShare server that uses a self-sign security certificate::

    from hs_restclient import HydroShare
    hs = HydroShare(hostname='mydev.mydomain.net', verify=False)
    for resource in hs.getResourceList():
        print(resource)

To connect to a development HydroShare server that is not running HTTPS::

    from hs_restclient import HydroShare
    hs = HydroShare(hostname='mydev.mydomain.net', port=8000, use_https=False)
    for resource in hs.getResourceList():
        print(resource)

Note that authenticated connections **must** use HTTPS.

For more usage options see the documentation.

Documentation
-------------

Complete installation and usage documentation is available at http://hs-restclient.readthedocs.org/en/latest/




