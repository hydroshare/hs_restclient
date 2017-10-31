""" 
Originally written by Jefferson Heard. 
Forked from github.com/hydroshare/django_irods/storage.py
Adapted for use by clients by Alva Couch. 
"""
import os
from tempfile import NamedTemporaryFile
from uuid import uuid4

# from django.utils.deconstruct import deconstructible
# from django.conf import settings
# from django.core.files.storage import Storage
# from django.core.urlresolvers import reverse
# from django.core.exceptions import ValidationError

from isession import ISession, GLOBAL_SESSION, GLOBAL_ENVIRONMENT, ISessionException, IRodsEnv


@deconstructible
class ICommands(Object):
    def __init__(self, **args):
        session = ISession(**args)

    def download(self, name):
        return self._open(name, mode='rb')

    def getFile(self, src_name, dest_name):
        self.session.run("iget", None, '-f', src_name, dest_name)

    def runBagitRule(self, rule_name, input_path, input_resource):
        """
        run iRODS bagit rule which generated bag-releated files without bundling
        :param rule_name: the iRODS rule name to run
        :param input_path: input parameter to the rule that indicates the collection path to
        create bag for
        :param input_resource: input parameter to the rule that indicates the default resource
        to store generated bag files
        :return: None
        """
        # SessionException will be raised from run() in icommands.py
        self.session.run("irule", None, '-F', rule_name, input_path, input_resource)

    def zipup(self, in_name, out_name):
        """
        run iRODS ibun command to generate zip file for the bag
        :param in_name: input parameter to indicate the collection path to generate zip
        :param out_name: the output zipped file name
        :return: None
        """
        self.session.run("imkdir", None, '-p', out_name.rsplit('/', 1)[0])
        # SessionException will be raised from run() in icommands.py
        self.session.run("ibun", None, '-cDzip', '-f', out_name, in_name)

    def setAVU(self, name, attName, attVal, attUnit=None):
        """
        set AVU on resource collection - this is used for on-demand bagging by indicating
        whether the resource has been modified via AVU pairs

        Parameters:
        :param
        name: the resource collection name to set AVU.
        attName: the attribute name to set
        attVal: the attribute value to set
        attUnit: the attribute Unit to set, default is None, but can be set to
        indicate additional info
        """

        # SessionException will be raised from run() in icommands.py
        if attUnit:
            self.session.run("imeta", None, 'set', '-C', name, attName, attVal, attUnit)
        else:
            self.session.run("imeta", None, 'set', '-C', name, attName, attVal)

    def getAVU(self, name, attName):
        """
        set AVU on resource collection - this is used for on-demand bagging by indicating
        whether the resource has been modified via AVU pairs

        Parameters:
        :param
        name: the resource collection name to set AVU.
        attName: the attribute name to set
        attVal: the attribute value to set
        attUnit: the attribute Unit to set, default is None, but can be set to
        indicate additional info
        """

        # SessionException will be raised from run() in icommands.py
        stdout = self.session.run("imeta", None, 'ls', '-C', name, attName)[0].split("\n")
        ret_att = stdout[1].strip()
        if ret_att == 'None':  # queried attribute does not exist
            return None
        else:
            vals = stdout[2].split(":")
            return vals[1].strip()

    def copyFiles(self, src_name, dest_name):
        """
        Parameters:
        :param
        src_name: the iRODS data-object or collection name to be copied from.
        dest_name: the iRODS data-object or collection name to be copied to
        copyFiles() copied an irods data-object (file) or collection (directory)
        to another data-object or collection
        """

        if src_name and dest_name:
            if '/' in dest_name:
                splitstrs = dest_name.rsplit('/', 1)
                if not self.exists(splitstrs[0]):
                    self.session.run("imkdir", None, '-p', splitstrs[0])
            self.session.run("icp", None, '-rf', src_name, dest_name)
        return

    def moveFile(self, src_name, dest_name):
        """
        Parameters:
        :param
        src_name: the iRODS data-object or collection name to be moved from.
        dest_name: the iRODS data-object or collection name to be moved to
        moveFile() moves/renames an irods data-object (file) or collection
        (directory) to another data-object or collection
        """
        if src_name and dest_name:
            if '/' in dest_name:
                splitstrs = dest_name.rsplit('/', 1)
                if not self.exists(splitstrs[0]):
                    self.session.run("imkdir", None, '-p', splitstrs[0])
            self.session.run("imv", None, src_name, dest_name)
        return

    def saveFile(self, from_name, to_name, create_directory=False, data_type_str=''):
        """
        Parameters:
        :param from_name: the temporary file name in local disk to be uploaded from.
        :param to_name: the data object path in iRODS to be uploaded to
        :param create_directory: create directory as needed when set to True. Default is False

        Note if only directory needs to be created without saving a file, from_name should be empty
        and to_name should have "/" as the last character
        """
        if create_directory:
            splitstrs = to_name.rsplit('/', 1)
            self.session.run("imkdir", None, '-p', splitstrs[0])
            if len(splitstrs) <= 1:
                return

        if from_name:
            try:
                if data_type_str:
                    self.session.run("iput", None, '-D', data_type_str, '-f', from_name, to_name)
                else:
                    self.session.run("iput", None, '-f', from_name, to_name)
            except:
                if data_type_str:
                    self.session.run("iput", None, '-D', data_type_str, '-f', from_name, to_name)
                else:
                    # IRODS 4.0.2, sometimes iput fails on the first try.
                    # A second try seems to fix it.
                    self.session.run("iput", None, '-f', from_name, to_name)
        return

    ###################################################
    # The following methods are required by the Django Storage API 
    # in order to make this kind of object manipulable via Django forms. 
    ###################################################

    def _open(self, name, mode='rb'):
        """ 
        Open a file for reading and return a pointer to the file 

        required by Django Storage API 

        TODO: This copies the whole file to /tmp without cache management. 
        Thus this can crash the master Django server. 
        """
        tmp = NamedTemporaryFile()
        self.session.run("iget", None, '-f', name, tmp.name)
        return tmp

    def _save(self, name, content):
        """ 
        Save content in a file.

        required by Django Storage API 

        TODO: If file is present, should not require cacheing in /tmp. 
        Simultaneous use by many clients can crash the master Django server. 
        """
        self.session.run("imkdir", None, '-p', name.rsplit('/', 1)[0])
        with NamedTemporaryFile(delete=False) as f:
            for chunk in content.chunks():
                f.write(chunk)
            f.flush()
            f.close()
            try:
                self.session.run("iput", None, '-f', f.name, name)
            except:
                # IRODS 4.0.2, sometimes iput fails on the first try. A second try seems to fix it.
                self.session.run("iput", None, '-f', f.name, name)
            os.unlink(f.name)
        return name

    def delete(self, name):
        """ 
        Delete a file or directory.

        Required by Django Storage API.
        """
        self.session.run("irm", None, "-rf", name)

    def exists(self, name):
        """ 
        Check whether a specific file or directory exists. 

        Required by Django Storage API.
        """
        try:
            stdout = self.session.run("ils", None, name)[0]
            return stdout != ""
        except SessionException:
            return False

    def listdir(self, path):
        """ 
        List contents of a directory.

        Required by Django Storage API.
        """
        stdout = self.session.run("ils", None, path)[0].split("\n")
        listing = ([], [])
        directory = stdout[0][0:-1]
        directory_prefix = "  C- " + directory + "/"
        for i in range(1, len(stdout)):
            if stdout[i][:len(directory_prefix)] == directory_prefix:
                dirname = stdout[i][len(directory_prefix):].strip()
                if dirname:
                    listing[0].append(dirname)
            else:
                filename = stdout[i].strip()
                if filename:
                    listing[1].append(filename)
        return listing

    def size(self, name):
        """ 
        Determine size of a file.

        Required by Django Storage API.
        """
        stdout = self.session.run("ils", None, "-l", name)[0].split()
        return int(stdout[3])

    def url(self, name):
        """
        Give the URL for a file or directory in iRODS
        
        Required by Django Storage API.

        TODO: This is designed to work inside the Django core 
        and needs to be modified to work outside the Django core. 
        """
        return reverse('django_irods.views.download', kwargs={'path': name})

    def get_available_name(self, name):
        """
        Reject duplicate file names rather than renaming them.

        This is an optional part of the Django Storage API. 
        Note that get_valid_name may also be implemented to 
        change a name according to local conventions. 
        """
        if self.exists(name):
            raise ValidationError(str.format("File {} already exists.", name))
        return name
