# 1.2.5 - 12/7/2016
  - Add ability to supply key/value metadata (in addition to 'title', 'abstract', 'keywords', and 'metadata')
  to createResource()
  - Add getResourceMap (/hsapi/resource/\<pid\>map/)

# 1.2.4 - 9/2/2016
  - Add support for async resource bag (BagIt archive) creation prior to downloading
  the bag file in getResource()

# 1.2.3 - 7/12/2016
  - Add ability to supply metadata (in addition to 'title', 'abstract', and 'keywords')
  to createResource()

# 1.2.2 - 4/7/2016
  - Fix bug where getResourceList() would fail after the first page of results
    when using HTTPS connections.

# 1.2.1 - 3/1/2016
  - Add getResourceFileList (/hsapi/resource/\<pid\>/file_list/)
  - Add getUserInfo (/hsapi/userInfo/)
  - Add getScienceMetadata (/hsapi/scimeta/\<pid\>/)

# 1.2.0 - 12/2/2015
  - Add support for OAuth 2.0 authentication/authorization

# 1.1.0 - 6/12/2015
  - Add ability to supply user-defined upload progress callback functions to
    createResource() and addResourceFile().

# 1.0.0 - 6/2/2015
  - First release of HydroShare REST API Python client library
