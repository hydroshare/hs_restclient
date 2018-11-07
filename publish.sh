#!/bin/bash

# Move .pypirc out of the way so that we don't try to publish
# as someone who is not the hydroshare user at PyPi.
if [ -e ${HOME}/.pypirc ]
  then
    mv ${HOME}/.pypirc ${HOME}/.pypirc-hs_restclient-tmp
fi

echo "python setup.py register sdist upload"
python setup.py register sdist upload

if [ -e ${HOME}/.pypirc-hs_restclient-tmp ]
  then
    mv ${HOME}/.pypirc-hs_restclient-tmp ${HOME}/.pypirc
fi
