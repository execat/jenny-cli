# Project: Dropbox File Crawler and Analyzer

This program allows you to use the Dropbox API to look and analyse all the
files/folders in your Dropbox account.

Refer to https://www.dropbox.com/developers/core for documentation on the API.

## Aims

1. Use Python programming language along with free libraries to create a user-
friendly CLI application.
2. The Dropbox API token and other tokens can be easily configured through in the
conf.py file.
3. Instructions to run can be found below under the heading "Instructions".
4. The code has been moderately documented within the source. Use "help" on the custom command prompt to see all the commands and their usage.
5. Future enhancements and suggestions in TODO.md.
6. The code currently does the following:

    * Count the number of files and folders (and the sizes).
    * Print the biggest and smallest file.
    * Count the number of deleted files.
    * Count the number of common files - *.txt, *.pdf, *.doc, *.xlsx etc.

### Bonus points for (TODO?)

1. Running this for a lot of users eg. 5000 users
2. Dealing with a user with a lot of files eg. 30,000 files
3. Instrumenting the code to measuring the performance of the code and the API
access

## Directory structure

    cli_client.py
    do_it.py

## Instructions

1. Configure the tokens in cli_client.py/do_it.py

    12: # Set the application specific details here
    13: APP_KEY = ''
    14: APP_SECRET = ''

2. Execute `python2 cli_client.py`

3. All the tasks can be done for the entire Dropbox folder or a part of it. To apply any operation (say find max and min size of files in "/Public/Animals/Walrus" within the Dropbox folder):

    * cd Public/Animals/Walrus
    * find_maxmin (or whatever command it is that you're trying to execute)
Assuming all tasks are being carried out in /, for simplicity.

4. Each of the tasks is implemented in `cli_client.py` as a separate command, so you can mix and match the possibilities.
    * Count the number of files and folders (and the sizes): `count_files`, `calc_size`
    * Print the biggest and smallest file: `find_maxmin`
    * Count the number of deleted files: `count_deleted`
    * Count the number of common files - *.txt, *.pdf, *.doc, *.xlsx etc: `count_types`

Alternatively, run `it` command in `do_it.py` to run all the utilities over a Dropbox folder.