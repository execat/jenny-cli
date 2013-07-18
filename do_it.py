#!/usr/bin/env python

import cmd
import locale
import os
import shlex
import sys
import json         # Alt: pprint (http://docs.python.org/2/library/pprint.html)
import itertools    # For compress()

from dropbox import client, rest

# Set the application specific details here
APP_KEY = 'nxc6d8rghbaf0kn'
APP_SECRET = '7v4yz3gxpqawihw'

def command(login_required=True):
    """
    A decorator for handling authentication and exceptions
    """
    def decorate(f):
        def wrapper(self, args):
            if login_required and self.api_client is None:
                self.stdout.write("Please 'login' to execute this command\n")
                return

            try:
                return f(self, *args)
            except TypeError, e:
                self.stdout.write(str(e) + '\n')
            except rest.ErrorResponse, e:
                msg = e.user_error_msg or str(e)
                self.stdout.write('Error: %s\n' % msg)

        wrapper.__doc__ = f.__doc__
        return wrapper
    return decorate

class DropboxTerm(cmd.Cmd):
    """
    A CLI for the Dropbox account
    """
    TOKEN_FILE = "token_store.txt"

    def __init__(self, app_key, app_secret):
        cmd.Cmd.__init__(self)
        self.app_key = app_key
        self.app_secret = app_secret
        self.current_path = '/'
        self.account = {'display_name': 'guest'}    # Default user: guest

        # Add to these. Only change to be made for additional extensions
        # to be included.
        self.extensions = ['tar', '7z', 'rar', 'gz', 'zip', 'doc', 'docx',
                           'odt', 'txt', 'pdf', 'xls', 'xlsx', 'csv', 'xml', 'exe',
                           'msi', 'jar', 'bmp', 'jpg', 'png', 'mp3', 'wav', 'avi']
        self.frequency = [0] * len(self.extensions)

        self.api_client = None
        try:
            token = open(self.TOKEN_FILE).read()
            self.api_client = client.DropboxClient(token)
            self.account = self.api_client.account_info()
            print "[loaded access token]"
        except IOError:
            pass                                # don't worry if it's not there

        self.prompt = "[ " + self.account['display_name'] + "'s Dropbox ][ " \
            + self.current_path + " ] $ "

    #
    # Command functions
    # Do everything as asked. Execute using "everything" in Dropbox command
    # prompt
    #

    def everything(self, rec, path):
        print(path)                                 # Comment this
        size_counter = 0
        num_of_files = 0
        num_of_dir = 0
        num_of_del = 0
        resp = self.api_client.metadata(path, include_deleted=True)

        if not hasattr(self, 'max'):                # Check if self.max is set
            self.max = {'path': '', 'bytes': 0}             # Max = 0
            self.min = {'path': '', 'bytes': float("inf")}  # Min = infinity

        for f in resp['contents']:
            # If the folder is marked deleted
            if 'is_deleted' in f.keys() and f['is_dir']:
                print("* "),

            # If the folder is marked deleted and recursive is True
            if 'is_deleted' in f.keys() and f['is_dir'] and rec:
                ret = self.everything(rec, f['path'])
                num_of_del += ret[2]
            # If the file is marked deleted
            elif 'is_deleted' in f.keys() and not f['is_dir']:
                num_of_del += 1
            # If the folder is not deleted
            elif f['is_dir'] and 'is_deleted' not in f.keys():
                num_of_dir += 1
                # If recursive is True, recurse through the current folder
                if rec:
                    ret = self.everything(rec, f['path'])

                    if ret[0]['bytes'] > self.max['bytes']:
                        self.max = {'path': ret['path'], 'bytes': ret['bytes']}
                    if ret[1]['bytes'] < self.min['bytes']:
                        self.min = {'path': ret['path'], 'bytes': ret['bytes']}
                    num_of_files += ret[2]
                    num_of_dir += ret[3]
                    size_counter += ret[4]
                    num_of_del += ret[5]
            # If the node is a file
            elif not f['is_dir']:
                num_of_files += 1
                size_counter += f['bytes']

                # Check if extension exists in extension list and increment
                if "." in f['path']:
                    extension = f['path'].split(".")[-1]
                    if extension in self.extensions:
                        index = self.extensions.index(extension)
                        self.frequency[index] += 1

                # Max, min bytes
                if f['bytes'] < self.min['bytes']:
                    self.min = {'path': f['path'], 'bytes': f['bytes']}
                if f['bytes'] > self.max['bytes']:
                    self.max = {'path': f['path'], 'bytes': f['bytes']}

        return[self.max, self.min, num_of_files, num_of_dir, size_counter, num_of_del]

    @command()
    def do_reset(self):
        self.frequency = [0] * len(self.extensions)

    @command()
    def do_it(self, rec=False, path=""):
        """
        Get all the requested data from the logged in user

        Usage:
            * it
            * it True
              Do "it" by recursing through folders
            * it
        """
        if path == "":
            path = self.current_path
        ret = self.everything(rec, path)
        print "Largest file :: " + str(ret[0])
        print "Smallest file :: " + str(ret[1])

        print "Num of files :: " + str(ret[2])
        print "Num of dirs :: " + str(ret[3])

        print "Total size :: " + str(ret[4])
        print "Num of deleted :: " + str(ret[5])

        l1 = list(itertools.compress(self.extensions, self.frequency))
        l2 = [x for x in self.frequency if x != 0]
        freq = dict(zip(l1, l2))
        print "Common files count :: \n" + str(freq)

        # Cleanup
        del self.max
        del self.min

    #
    # Non important utilities like account_info, cd, ls, pwd
    #
    @command()
    def do_account_info(self):
        """
        Display account information for the logged in user.

        Usage:
            * account_info
              Displays the account information for the current logged in user
        """
        f = self.api_client.account_info()
        print(json.dumps(f, sort_keys=True, indent=2))

    @command()
    def do_cd(self, path):
        """
        Change current working directory.

        Usage:
            * cd ..
              Go one level higher
            * cd /Dir/Sub_dir
              Absolute path addressing where / is root of the Dropbox folder
            * cd Dir/Sub_dir/ OR cd Dir/Sub_dir (trailing / optional)
              Relative path addressing
        """
        if self.current_path == "":         # Might not belong here
            self.current_path = "/"
        elif path == "..":                  # Moving back into the file heirarchy
            self.current_path = "/".join(self.current_path.split("/")[0:-1])
        elif path[0] == '/':                # Absolute addressing mode
            self.current_path = path
        elif self.current_path[-1] == '/':  # / exists at the end of the currpath
            self.current_path += path
        else:                               # / does not exist at the end
            self.current_path += '/' + path
        self.prompt = "[ " + self.account['display_name'] + "'s Dropbox ][ " \
                + self.current_path + " ] $ "

    @command()
    def do_ls(self, path=""):
        """
        List files in current remote directory.

        Displays all the directories first, followed by files and their sizes.
        Can be used for the current directory, or using absolute path address.

        Usage:
            * ls
              Lists the current directory
            * ls /Dir/Sub_dir
              Absolute addressing for a directory not in the current folder
            * ls Sub_dir
              Relative addressing for a directory within the current folder
        """
        if path == "":
            path = self.current_path
        if path[0] != "/":
            if self.current_path[-1] == "/":
                path = self.current_path + path
            else:
                path = self.current_path + "/" + path

        resp = self.api_client.metadata(path)

        if 'contents' in resp:
            for f in resp['contents']:
                if f['is_dir']:
                    name = os.path.basename(f['path'])
                    encoding = locale.getdefaultlocale()[1]
                    dirname = '%s\n' % name
                    self.stdout.write(dirname.encode(encoding))
            print
            for f in resp['contents']:
                if not f['is_dir']:
                    name = os.path.basename(f['path'])
                    size = f['size']
                    encoding = locale.getdefaultlocale()[1]
                    filename = '%s \t%s\n' % (name, size)
                    self.stdout.write(filename.encode(encoding))

    @command()
    def do_pwd(self):
        """
        Display the current working directory.

        Usage:
            * pwd
        """
        print(self.current_path)


    #
    # Login, logout, exit and help utilities
    #

    @command(login_required=False)
    def do_login(self):
        """
        Log in to a Dropbox account
        """
        flow = client.DropboxOAuth2FlowNoRedirect(self.app_key, self.app_secret)
        authorize_url = flow.start()
        sys.stdout.write("1. Go to: " + authorize_url + "\n")
        sys.stdout.write("2. Click \"Allow\" (you might have to log in first).\n")
        sys.stdout.write("3. Copy the authorization code.\n")
        code = raw_input("Enter the authorization code here: ").strip()

        try:
            access_token, user_id = flow.finish(code)
        except rest.ErrorResponse, e:
            self.stdout.write('Error: %s\n' % str(e))
            return

        with open(self.TOKEN_FILE, 'w') as f:
            f.write(access_token)
        self.api_client = client.DropboxClient(access_token)
        self.account = self.api_client.account_info()
        self.prompt = "[ " + self.account['display_name'] + "'s Dropbox ][ " \
            + self.current_path + " ] $ "


    @command()
    def do_logout(self):
        """
        Log out of the current Dropbox account
        """
        self.api_client = None
        os.unlink(self.TOKEN_FILE)
        self.current_path = ''

    @command(login_required=False)
    def do_exit(self):
        """
        Exit
        """
        return True

    @command(login_required=False)
    def do_help(self):
        """
        Find every "do_" attribute with a non-empty docstring and print
        out the docstring.
        """
        all_names = dir(self)
        cmd_names = []
        for name in all_names:
            if name[:3] == 'do_':
                cmd_names.append(name[3:])
        cmd_names.sort()
        for cmd_name in cmd_names:
            f = getattr(self, 'do_' + cmd_name)
            if f.__doc__:
                self.stdout.write('%s: %s\n' % (cmd_name, f.__doc__))

    #
    # The following are for command line magic and aren't Dropbox-related
    #

    def emptyline(self):
        pass

    def do_EOF(self, line):
        self.stdout.write('\n')
        return True

    def parseline(self, line):
        parts = shlex.split(line)
        if len(parts) == 0:
            return None, None, line
        else:
            return parts[0], parts[1:], line


def main():
    if APP_KEY == '' or APP_SECRET == '':
        exit("You need to set your APP_KEY and APP_SECRET!")
    term = DropboxTerm(APP_KEY, APP_SECRET)
    term.cmdloop()

if __name__ == '__main__':
    main()
