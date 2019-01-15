# 1.3.1 - 11/12/2018
  - input compatible with python3

# 1.3.0 - 11/6/2018
  - Add createReferencedFile (/hsapi/scimeta/\<pid\>/)
  - Add updateReferencedFile (/hsapi/resource/\<pid\>/scimeta/elements)
  - Prompt user for input when authencitcation is not provided.
  - Update documentation for overwrite on unzip.

# 1.2.6 - 1/20/2017
  - Add getScienceMetadataRDF (/hsapi/scimeta/\<pid\>/)
  - Add getScienceMetadata (/hsapi/resource/\<pid\>/scimeta/elements)
  - Add updateScienceMetadata (/hsapi/resource/\<pid\>/scimeta/elements)
  - Add getResourceFolderContents (/hsapi/resource/\<pid\>/folders/\<path\>)
  - Add createResourceFolder (/hsapi/resource/\<pid\>/folders/\<path\>)
  - Add deleteResourceFolder (/hsapi/resource/\<pid\>/folders/\<path\>)

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
