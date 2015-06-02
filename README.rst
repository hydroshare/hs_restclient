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

To authenticate, and then get a list of resources you have access to::

    from hs_restclient import HydroShare, HydroShareAuthBasic
    auth = HydroShareAuthBasic(username='myusername', password='mypassword')
    hs = HydroShare(auth=auth)
    for resource in hs.getResourceList():
        print(resource)

To connect to a development HydroShare server::

    from hs_restclient import HydroShare
    hs = HydroShare(hostname='mydev.mydomain.net', port=8000)
    for resource in hs.getResourceList():
        print(resource)

For more usage options see the documentation.

Documentation
-------------

Complete installation and usage documentation is available at http://hs-restclient.readthedocs.org/en/latest/




