#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2017, Matthias M Dellweg <dellweg@atix.de> (ATIX AG)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = '''
---
module: location
version_added: 1.0.0
short_description: Manage Locations
description:
  - Manage Locations
author:
  - "Louis J Tiches"
options:
  name:
    description:
      - Name of the Location
    required: true
    type: str
  parent:
    description:
      - Title of a parent Location for nesting
    type: str
  organizations:
    description:
      - List of organizations the location should be assigned to
    type: list
    elements: str
'''

EXAMPLES = '''
# Create a simple location
- name: "Create CI Location"
  redhat.satellite.location:
    username: "admin"
    password: "changeme"
    server_url: "https://satellite.example.com"
    name: "My Cool New Location"
    organizations:
      - "Default Organization"
    state: present

# Create a nested location
- name: "Create Nested CI Location"
  redhat.satellite.location:
    username: "admin"
    password: "changeme"
    server_url: "https://satellite.example.com"
    name: "My Nested location"
    parent: "My Cool New Location"
    state: present

# Create a new nested location with parent included in name
- name: "Create New Nested Location"
  redhat.satellite.location:
    username: "admin"
    password: "changeme"
    server_url: "https://satellite.example.com"
    name: "My Cool New Location/New nested location"
    state: present

# Move a nested location to another parent
- name: "Create Nested CI Location"
  redhat.satellite.location:
    username: "admin"
    password: "changeme"
    server_url: "https://satellite.example.com"
    name: "My Cool New Location/New nested location"
    parent: "My Cool New Location/My Nested location"
    state: present
'''

RETURN = '''
entity:
  description: Final state of the affected entities grouped by their type.
  returned: success
  type: dict
  contains:
    locations:
      description: List of locations.
      type: list
      elements: dict
'''

#!/usr/bin/python

import json
import requests
from ansible.module_utils.basic import AnsibleModule

def find_location(server_url, auth, name, validate_certs):
    url = f"{server_url}/api/locations"
    response = requests.get(url, auth=auth, verify=validate_certs, params={'search': f'name="{name}"'})
    if response.status_code == 200:
        locations = response.json()['results']
        if locations:
            return locations[0]  # Assuming unique location names
    return None

def find_location_params(server_url, auth, name, validate_certs, id):
    url = f"{server_url}/api/locations/{id}/parameters"
    response = requests.get(url, auth=auth, verify=validate_certs, params={'search': f'name="{name}"'})
    if response.status_code == 200:
        locations = response.json()['results']
        if locations:
            return locations[0]  # Assuming unique location names
    return None

def get_entity_id_by_name(server_url, auth, validate_certs, entity_type, name):
    url = f"{server_url}/api/{entity_type}"
    response = requests.get(url, auth=auth, verify=validate_certs, params={'search': f'name="{name}"'})

    if response.status_code == 200 and response.json()['results']:
        return response.json()['results'][0]['id']
    return None

def get_entity_ids(server_url, auth, validate_certs, entity_type, names):
    
    if not names:
        return []
    ids = [get_entity_id_by_name(server_url, auth, validate_certs, entity_type, name) for name in names]
    return ids


def manage_location(server_url, auth, data, validate_certs, module):
    location = find_location(server_url, auth, data['name'], validate_certs)
    headers = {'Content-Type': 'application/json'}

    if module.params['organizations']:
        data['location']['organization_ids'] = get_entity_ids(server_url, auth, validate_certs, 'organizations', module.params['organizations'])

    if  module.params['smart_proxies']:
        data['location']['smart_proxy_ids'] = get_entity_ids(server_url, auth, validate_certs, 'smart_proxies', module.params['smart_proxies'])

    if  module.params['subnets']:
        data['location']['subnet_ids'] = get_entity_ids(server_url, auth, validate_certs, 'subnets', module.params['subnets'])

    if  module.params['domains']:
        data['location']['domain_ids'] = get_entity_ids(server_url, auth, validate_certs, 'domains', module.params['domains'])

    if location:
        # Update the existing location
        url = f"{server_url}/api/locations/{location['id']}"
        response = requests.put(url, auth=auth, headers=headers, verify=validate_certs, data=json.dumps(data))
    else:
        # Create a new location
        url = f"{server_url}/api/locations"
        response = requests.post(url, auth=auth, headers=headers, verify=validate_certs, data=json.dumps(data))
    
    if response.status_code in [200, 201, 202]:
        return response.json()
    else:
        raise ValueError(f"Error {response.status_code}: {response.text}")

    if module.params['parameters']:
        location_id =  response.json()['id']
        parameters  = find_location_params(server_url, auth, data['name'], validate_certs, location_id)

        if parameters:
            url = f"{server_url}/api/locations/{location['id']}/parameters/{parameters['id']}"
            response = requests.put(url, auth=auth, headers=headers, verify=validate_certs, data=json.dumps(data))
        else:
            url = f"{server_url}/api/locations/{location['id']}/parameters"
            response = requests.post(url, auth=auth, headers=headers, verify=validate_certs, data=json.dumps(data))
    
    if response.status_code in [200, 201, 202]:
        return response.json()
    else:
        raise ValueError(f"Error {response.status_code}: {response.text}")

def main():
    module_args = dict(
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        server_url=dict(type='str', required=True),
        validate_certs=dict(type='bool', required=True),
        name=dict(type='str', required=True),
        parent=dict(type='str', required=False),
        organizations=dict(type='list', required=False, elements='str'),
        smart_proxies=dict(type='list', required=False, elements='str'),
        subnets=dict(type='list', required=False, elements='str'),
        domains=dict(type='list', required=False, elements='str'),
        parameters=dict(type='list', required=False, elements='dict')
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    auth = (module.params['username'], module.params['password'])
    server_url = module.params['server_url']
    validate_certs = module.params['validate_certs']

    data = {
        'name': module.params['name'],
        'parent_id': module.params.get('parent'),
        'parameters': module.params.get('parameters'),
        'location': {}
          }
    
    try:
        response = manage_location(server_url, auth, data, validate_certs, module)
        module.exit_json(changed=True, location=response)
    except ValueError as e:
        module.fail_json(msg=str(e))

if __name__ == '__main__':
    main()