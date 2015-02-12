#!/usr/bin/python
# License: MIT

DOCUMENTATION = '''
---
module: release_folder
author: Marc Bernath
version_added: "0.0.1"
short_description: Manage a Capistrano style release folder
description:
    - Manages a Capistrano-style release folder
options:
    path:
        required: true
        aliases: [ src, dest ]
        description:
            - The base path
    prefix:
        required: false
        default: "release-"
        description:
            - A prefix for all release folders. Set to "" if you don't want any prefix.
    subfolder:
        required: false
        default: 'releases'
        description:
            - The name of the subfolder to store all releases in.
    state:
        required: false
        choices: [ "cleaned", "exists" ]
        description:
            - If no state is set, only information about the release folder will be gathered and returned
            - If set to "cleaned", then all old release folders will be removed. Use the parameters "keep" and "keep_symlinked_dirs" to control this behaviour.
            - If set to "exists", a release directory will be created for the given timestamp, if not exists. That directory will be symlinked, if you specified a symlink.
    keep:
        required: false
        default: 5
        description:
            - An integer (>=0) specifying how many of the latest releases to keep in the folder excluding any symlinked directories that are excluded via "keep_symlinked_dirs".
    keep_symlinked_dirs:
        required: false
        default: true
        description:
            - If true any specified symlinked directories via the parameter "symlink_dirs" will be kept during the clean process - independent of "keep".
            - If false, the target of a symlink might be deleted, so you need to take care about that eventually. 
    symlink:
        require: false
        description:
            - A string specifying the symlink to be created, e.g. "latest" or "current"
            - Use in conjunction with "timestamp" and "state=exists"
    timestamp:
        require: false
        description:
            - The timestamp of the folder to be created and eventually symlinked with "symlink", e.g. "20150212090000"

notes:
    - Use any timestamp format you like, but it must be sortable properly. Okay is for example YYYYMMDDHHMMSS or YYYYMMDD_HH-MM-SS_, but what would not work is SSMMHHDDMMYYYYY.
'''

EXAMPLES = '''

###
# Example 1: Clean the release folder

- release_folder: path=~/app keep=5 symlink_dirs=current,latest state=cleaned

###
# Example 2: Get information about the release folder

- release_folder: path=~/app
  register: result

# result:
# {
#   "symlinked_folders": {
#       "production" : "release-20150101101010",
#       "latest" : "release-2015010210090000"
#   },
#   "absolute_path": "/Users/admin/Src",
#   "releases_path" : "/Users/admin/Src/releases"
#   "removed_releases": [],
#   "releases": [ "release-20150101101010", ... ]
# }

###
# Example: Symlink a release

- release_folder: path=~/app symlink=production target={{ timestamp }} state=exists
'''

import os
from ansible.module_utils.basic import *

def get_releases(path, subfolder, prefix):

    get_releases=[]
    abs_path = os.path.join(path, subfolder)

    for file in os.listdir(abs_path):
        abs_file = os.path.join(abs_path, file)
        if file.startswith(prefix) and os.path.isdir(abs_file) and not os.path.islink(abs_file):
            get_releases.append(file)

    return get_releases

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def main():

    module = AnsibleModule(
        argument_spec = dict(
            path = dict(required=True),
            prefix = dict(default='release-'),
            subfolder = dict(default='releases'),
            keep = dict(default='5', type='int'),
            keep_symlinked_dirs = dict(default='yes', type='bool'),
            symlink_dirs = dict(default=None),
            state = dict(default=None, choices=['exists','cleaned']),
            timestamp = dict(default=None),
            symlink = dict(default=None)
        ),
        supports_check_mode = True
    )

    # Get and check parameters
    state = module.params.get('state')

    path = module.params.get('path')
    path = os.path.realpath(os.path.expanduser(path))

    prefix = module.params.get('prefix')
    if not isinstance(prefix, basestring):
        module.fail_json(msg='Invalid prefix parameter')
        return

    subfolder = module.params.get('subfolder')

    keep = module.params.get('keep')
    if not isinstance(keep, int) or keep<0:
        module.fail_json(msg='Invalid keep parameter')
        return

    keep_symlinked_dirs = module.params.get('keep_symlinked_dirs')

    symlink_dirs = module.params.get('symlink_dirs')
    if isinstance(symlink_dirs, basestring):
        symlink_dirs = symlink_dirs.split(',')
    else:
        symlink_dirs = []

    symlink = module.params.get('symlink')

    timestamp = module.params.get('timestamp')

    # Result variables
    dirs_to_remove = []
    changed = False
    existing_dirs = []
    symlinked_folders = dict()

    # Make sure the base directory and the release directory exist
    directories_exist = True
    if not module.check_mode:
        ensure_dir(path)
        ensure_dir(os.path.join(path, subfolder))
    else:
        directories_exist = os.path.exists(path) and os.path.exists(os.path.join(path, subfolder))

    # Add symlink to symlink_dirs, if it is not included yet
    if symlink:
        if not symlink in symlink_dirs:
            symlink_dirs.append(symlink)

    if (state=='cleaned'):

        # Gather all release directories
        dirs_to_remove = get_releases(path, subfolder, prefix)

        # Remove symlinked directories from list
        if (keep_symlinked_dirs):
            for symlink_dir in symlink_dirs:
                try:
                    protected = os.path.basename(os.readlink(os.path.join(path, symlink_dir)))
                    dirs_to_remove.remove(protected)
                except:
                    pass

        # Keep the most current x releases in the list and leave the rest for deletion
        dirs_to_remove = sorted(dirs_to_remove, reverse=True)[keep:]

        # Delete the directories
        if not module.check_mode:
            if (state=='cleaned'):
                for dir in dirs_to_remove:
                    remove_dir = os.path.join(path, subfolder, dir)
                    try:
                        shutil.rmtree(remove_dir)
                    except OSError as e:
                        print e
                        module.fail_json(msg='Could not remove directory ' + remove_dir)
                        return

        changed = len(dirs_to_remove)>0

    if (state=='exists'):

        # Check if release and symlink parameters are ok and directory exists
        if not timestamp or not isinstance(timestamp, basestring):
            module.fail_json(msg='Invalid timestamp parameter')
            return

        if symlink and not isinstance(symlink, basestring):
            module.fail_json(msg='Invalid symlink parameter')
            return

        release_dir = os.path.join(path, subfolder, prefix + timestamp)

        # Create release directory, if not exists
        if os.path.exists(release_dir) and not os.path.isdir(release_dir):
            module.fail_json(msg='Release directory exists,but is not a directory: ' + release_dir)
            return

        if not os.path.exists(release_dir):
            try:
                os.makedirs(release_dir)
            except OSError as e:
                module.fail_json(msg='Error creating release directory: ' + release_dir)
                return

        # Create/update symlink
        if symlink:
            symlink_dir = os.path.join(path, symlink)

            if os.path.exists(symlink_dir) and not os.path.islink(symlink_dir):
                module.fail_json(msg='Symlink exists but is not a symlink: ' + symlink_dir)
                return

        if not module.check_mode:
            try:
                if os.path.islink(symlink_dir):
                    os.unlink(symlink_dir)
                os.symlink(release_dir, symlink_dir)
            except OSError as e:
                    module.fail_json(msg='Error creating symlink')
                    return
        
        changed = True

    # If the target directories exist, gather information. In check mode these wouldn't be created and the following checks would cause an error, so skip if they don't exist...

    if directories_exist:

        # Gather existing releases
        existing_dirs = get_releases(path, subfolder, prefix)

        # Gather symlinks
        for symlink_dir in symlink_dirs:
            try:
                symlinked_folders[symlink_dir] = os.path.join(path, os.readlink(os.path.join(path, symlink_dir)))
            except:
                symlinked_folders[symlink_dir] = None

    module.exit_json(changed=changed, removed_releases=dirs_to_remove, absolute_path=path, symlinked_folders=symlinked_folders, releases= existing_dirs, releases_path=os.path.join(path, subfolder))

main()