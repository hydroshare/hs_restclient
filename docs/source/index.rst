.. hs_restclient documentation master file, created by
   sphinx-quickstart on Tue May 26 18:13:28 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

HydroShare REST API Python client library
=========================================

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


Contents:

.. toctree::
   :maxdepth: 2



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

