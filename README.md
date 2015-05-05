Python-based client library for HydroShare REST API

Questions? brian_miles@unc.edu

# To run tests (Coming soon!!!)
    python setup.py test

# To use

To get a listing of public resources:

    from hs_restclient import HydroShare
    hs = HydroShare()
    resource_list = hs.getResourceList()

To authenticate, and then get a list of resources you have access to:

    from hs_restclient import HydroShare, HydroShareAuthBasic
    auth = HydroShareAuthBasic(username='myusername', password='mypassword')
    hs = HydroShare(auth=auth)
    my_resource_list = hs.getResourceList()

To connect to a development HydroShare server:

    from hs_restclient import HydroShare
    hs = HydroShare(hostname='mydev.mydomain.net', port=8000)
    resource_list = hs.getResourceList()

