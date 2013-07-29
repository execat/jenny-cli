#!/usr/bin/env python

import cmd
import locale
import os
import shlex
import sys
import json     # Alt: pprint (http://docs.python.org/2/library/pprint.html)

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
    """
    TOKEN_FILE = "token_store.txt"

    def __init__(self, app_key, app_secret):
        cmd.Cmd.__init__(self)
        self.app_key = app_key
        self.app_secret = app_secret
        self.current_path = '/'
        self.account = {'display_name': 'guest'}

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
    #

    # Size

    def calc_size(self, path):
        sum = 0
        print(path)
        resp = self.api_client.metadata(path)

        if 'contents' in resp:
            for f in resp['contents']:
                if f['is_dir']:
                    sum += self.calc_size(f['path'])
                if not f['is_dir']:
                    sum += f['bytes']
        return sum

    @command()
    def do_calc_size(self, path=""):
        """
        Calculates size of the directory  in bytes.

        Usage:
            * size
              Total size of the files in the current working directory and its
              subdirectories
            * size /Dir/Sub_dir
              Total size of the files in the specified directory and its
              subdirectories
        """
        if path == "":
            path = self.current_path
        size = self.calc_size(path)
        print str(size) + " B"

    # Element count

    def count_files(self, r, path):
        directories = 0
        files = 0
        #if path == "":
        #    path = self.current_path
        print(path)
        resp = self.api_client.metadata(path)

        if 'contents' in resp:
            for f in resp['contents']:
                if f['is_dir']:
                    directories += 1
					if r:
						d, f = count_files(self, r, f['path'])
						directories += d
						files += f
                if not f['is_dir']:
                    files += 1
        return (directories, files)

    @command()
    def do_count_files(self, rec=True, path=""):
        """

        """
        if path == "":
            path = self.current_path
        ret = self.count_files(r, path)
        print str(ret[0]) + " dir :: " + str(ret[1]) + " files"

    # Find deleted

    def count_deleted(self, path):
        count = 0
        resp = self.api_client.metadata(self.current_path, include_deleted=True)
        for f in resp['contents']:
            if 'is_deleted' in f.keys():
                print(f['name'])
                count = count + 1
            if f['is_dir']:
                count += self.count_deleted(f['path'])
        return count

    @command()
    def do_count_deleted(self, path=""):
        """

        """
        if path == "":
            path = self.current_path


    # Max and min of all files

    def find_maxmin(self, rec, path):
        print(path)                                 # Comment this
        resp = self.api_client.metadata(path)

        if not hasattr(self, 'max'):                # Check if self.max is set
            self.max = {'path': '', 'bytes': 0}             # Max = 0
            self.min = {'path': '', 'bytes': float("inf")}  # Min = infinity

        for f in resp['contents']:
            if f['is_dir'] and rec:
                ret = self.find_maxmin(rec, f['path'])

                if ret[0]['bytes'] > self.max['bytes']:
                    self.max = {'path': ret['path'], 'bytes': ret['bytes']}
                if ret[1]['bytes'] < self.min['bytes']:
                    self.min = {'path': ret['path'], 'bytes': ret['bytes']}

            if not f['is_dir']:
                if f['bytes'] < self.min['bytes']:
                    self.min = {'path': f['path'], 'bytes': f['bytes']}
                if f['bytes'] > self.max['bytes']:
                    self.max = {'path': f['path'], 'bytes': f['bytes']}

                print("Current instance: ")         # Comment next 4 lines
                print(str({'path': f['path'], 'bytes': f['bytes']}))
                print("Global instance:")
                print(self.max, self.min)

        return[self.max, self.min]

    @command()
    def do_find_maxmin(self, rec=True, path=""):
        """
        Finds the largest and the smallest file either recursively or in the
        current working directory.

        The variable self.initial_path is used to remember the start position
        since the output ends at the leaf node of the depth first search.
        Consider it to be a normal temporary variable.

        Usage:
            * find_maxmin
              Finds the largest and the smallest file in the directory tree
              with the top node as . (pwd)
            * find_maxmin False
              Finds the largest and smallest file only in the current working
              directory without recursing into child directories.
        """
        if path == "":
            path = self.current_path
        ret = self.find_maxmin(rec, path)
        print "Largest file :: " + str(ret[0])
        print "Smallest file :: " + str(ret[1])

        # Cleanup
        del self.max
        del self.min

    # View raw meta data

    @command()
    def do_view_raw_metadata(self, path=""):
        """
        Returns the metadata for a directory.

        The metadata format and description can be read from the core API
        REST reference: https://www.dropbox.com/developers/core/docs#metadata
        Metadata queries can be carried out as listed in the Python specific
        documentation:
        https://www.dropbox.com/static/developers/dropbox-python-sdk-1.5-docs/index.html#dropbox.client.DropboxClient.metadata

        Using json.dumps() to beautify the output.

        Usage:
            * view_raw_metadata
              Defaults to the metadata of the current working directory
            * view_raw_metadata /Public
              View metadata of the Public directory
        """

        if path == "":
            path = self.current_path
        resp = self.api_client.metadata(path)
        print(json.dumps(resp, sort_keys=True, indent=2))

    # Search data

    def search_data(self, string, path):
        return self.api_client.search(path, string)

    @command()
    def do_view_raw_searchdata(self, string, path=""):
        """
        Returns the data returned by the search query passed as a parameter

        Usage:
            * view_raw_searchdata pdf
        """
        if path == "":
            path = self.current_path
        print(json.dumps(self.search_data(string, path), sort_keys=True, indent=2))

    # Count types of files

    def count_types(self, filetypes, path=""):
        """
        """
        if path == "":
            path = self.current_path

        for f in filetypes:
            filecount = []
            for g in f['ext']:
                search_result = self.search_data("." + g, path)
                print(g + " " + str(len(search_result)))
                filecount.append(len(search_result))
            f['frequency'] = filecount
        return filetypes

    @command()
    def do_count_types(self, path=""):
        """
        """

        filetypes = [
            {'type': 'Archives', 'ext': ['tar', '7z', 'rar', 'tar.gz', 'zip']},
            {'type': 'Documents', 'ext': ['doc', 'docx', 'odt', 'txt', 'pdf']},
            {'type': 'Data', 'ext': ['xls', 'xlsx', 'csv', 'xml']},
            {'type': 'Executable', 'ext': ['exe', 'msi', 'jar']},
            {'type': 'Images', 'ext': ['bmp', 'jpg', 'png']},
            {'type': 'Media', 'ext': ['mp3', 'wav', 'avi']}
        ]

        print(self.count_types(filetypes))

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
