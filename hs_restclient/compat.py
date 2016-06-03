import sys

_ver = sys.version_info

#: Python 2.x?
is_py2 = (_ver[0] == 2)

#: Python 3.x?
is_py3 = (_ver[0] == 3)

if is_py2:
    from httplib import responses as http_responses

elif is_py3:
    from http.client import responses as http_responses
    basestring = str
