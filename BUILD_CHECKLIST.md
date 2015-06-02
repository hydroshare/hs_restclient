
# Version information

The HydroShare REST Python client library uses [semantic versioning 2.0.0](http://semver.org).

1. Update __version__ in hs_restclient.__init__.py

2. Update version in setup.py to match that in hs_restclient.__init__.py

# Documentation

(all commands must be run from the root of the repo, unless otherwise noted.)

1. Update .rst source:

    sphinx-apidoc -o docs hs_restclient -f

2. Generate HTML documentation (only needed if you want a local copy of the HTML version):

    cd docs && make html && cd -

