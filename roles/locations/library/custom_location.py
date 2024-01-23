#!/usr/bin/python

import json
import requests
import yaml
import ipaddress

from urllib3.exceptions import InsecureRequestWarning

def check_ip_or_network(input_string):
    try:
        # Check if it's a valid IP address
        ipaddress.ip_address(input_string)
        return True
    except ValueError:
        pass

    try:
        # Check if it's a valid network address
        ipaddress.ip_network(input_string, strict=False)
        return True
    except ValueError:
        pass

    return False

def grab_credentials(path_to_yaml):
    with open(path_to_yaml, 'r') as f:
        creds = yaml.safe_load(f)
    return (creds[':foreman'][':username'], creds[':foreman'][':password'])

def collect_ids(server_url, auth, name, validate_certs=False):
    try:
      url = f"{server_url}/api/{name}"
      response = requests.get(url, auth=auth, verify=validate_certs)

      if response.status_code == 200:
          
          results = response.json().get('results')
          filtered_data = filter(lambda x: len(x["description"].split(',')) == 4, results)
          return list(map(lambda x: x["id"], filtered_data))
          
      else:
          response.raise_for_status()
    
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error getting {name} from Satellite: {e}")
    
    except ValueError as e:
        raise ValueError(f"Error parsing {name} from Satellite: {e}")
    
    return []

def fix_subnets(server_url, auth, ids, validate_certs=False, output_file='output.txt'):
  for id in ids:
    url = f"{server_url}/api/subnets/{id}"
    response = requests.get(url, auth=auth, verify=validate_certs)
    results = response.json()
    name = results.get('name')

    description_parts = results.get('description', '').split(',')
    if len(description_parts) >= 4:
        cluster = description_parts[2].strip()
        network = description_parts[3].strip()

    name = results.get('name')
    description = results.get('description')
    network = results.get('network')
    mask = results.get('mask')
    ipam = results.get('ipam')
    gateway = results.get('gateway')
    boot_mode = results.get('boot_mode')
    domains = results.get('domains')
    organizations = results.get('organizations')
    locations = results.get('locations')

    domains = [item['name'] for item in domains]
    organizations = [item['name'] for item in organizations]
    locations = [item['name'] for item in locations]

    if not check_ip_or_network(name):
        continue
        
    payload = f"""
    - name: {name}
      description: {description} # "Created to KS VM Templates"
      network: {network} #"192.168.2.0"
      mask: {mask} #"255.255.255.0"
      ipam: {ipam} #"None"
      gateway: {gateway} #"192.168.2.1"
      boot_mode: {boot_mode} # "Static"
      domains: {domains} #"lou.land"
      organizations: {organizations}
      locations: {locations} # hallas
      parameters:
      - name: 'cluster'
        value: {cluster}
      - name: 'network'
        value: {network}
      """
    
    

    with open(output_file, 'a') as file:
      file.write(f"{payload}")

        
def main():
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    auth = grab_credentials('foreman.yml')
    sids = collect_ids('https://satellite.lou.land', auth, 'subnets')
    fix_subnets('https://satellite.lou.land', auth, sids)

if __name__ == '__main__':
    main()