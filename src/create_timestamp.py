#!/usr/bin/python
# License: MIT

DOCUMENTATION = '''
---
module: create_timestamp
author: Marc Bernath
version_added: "0.0.1"
short_description: Create a timestamp to be used within other tasks
description:
    - Create a timestamp to be used within other tasks. If you deploy to several servers but want to use the same timestamp, this will come in handy.
options:
    format:
        default: "%Y%m%d%H%M%S"
        description:
            - A valid Python strftime format string.
    timezone:
        default: "UTC"
        description:
            - A valid timezone string, e.g. "Europe/Berlin" or "CET". See the pytz library for further info.
notes:
    - Dependencies: If you want to use the "timezone" feature, you need to install pytz (pip install pytz). If you don't specify a timezone, it will also run without pytz.
'''

EXAMPLES = '''
###
# Example 1: Get a timestamp

- create_timestamp
  register: timestamp

# timestamp: { changed: True, timestamp: "20150212121427" }

###
# Example 2: Get a custom timestamp

- create_timestamp: format="%Y_%m_%d_%H_%M_%S" timezone=CET
  register: timestamp

# timestamp: { changed: True, timestamp: "2015_02_12_12_16_55" }
'''

from ansible.module_utils.basic import *
from datetime import datetime

def module_exists(module_name):
    try:
        __import__(module_name)
    except ImportError:
        return False
    else:
        return True

def main():

    module = AnsibleModule(
        argument_spec = dict(
            format = dict(default='%Y%m%d%H%M%S'),
            timezone = dict(default='UTC')
        ),
        supports_check_mode = True
    )

    # Get and check parameters
    format = module.params.get('format')
    timezone = module.params.get('timezone')

    # Get timezone
    tz = None
    if timezone:
        if module_exists('pytz'):
            import pytz
            tz = pytz.timezone(timezone)
        else:
            module.fail_json(msg='You specified a timezone, but pytz is not available')
            return

    # Create timestamp
    result = datetime.now(tz).strftime(format)

    module.exit_json(changed=True, timestamp=result)

main()