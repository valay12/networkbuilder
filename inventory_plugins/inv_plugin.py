#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
  name: inv_plugin
  plugin_type: inventory
  short_description: Generates inventory of devices to be provisioned
  description: Generates inventory of devices from request.yml
  options:
    plugin:
      description: Name of plugin
      required: True
  '''

from ansible.plugins.inventory import BaseInventoryPlugin
from ansible.errors import AnsibleError, AnsibleParserError
from yaml import safe_load

class InventoryModule(BaseInventoryPlugin):
  NAME = 'inv_plugin'
  LOCATION = {'Singapore': 'SNG',
                'London': 'LON',
                'New York': 'NYC'}
  
  def verify_file(self, path):
    '''Return true/false if file is valid'''
    if path.endswith('hosts.yml'):
      return True
    else:
      return False

  def _get_neighbors(self, host_list):

    for i in range(len(host_list)):
      role = host_list[i]['role']
      downlinks = []
      uplinks = []
      peer = ''
      for neighbor in host_list:
        if host_list[i]['hostname'] == neighbor['hostname']:
          continue
        elif neighbor['role'][:-1] == 'DST':
          if role[:-1] == 'DST':
            peer = neighbor['hostname']
          else:
            uplinks.append(neighbor['hostname'])
        else:
          if role[:-1] == 'DST':
            downlinks.append(neighbor['hostname'])
      host_list[i]['uplinks'] = uplinks
      host_list[i]['downlinks'] = downlinks
      host_list[i]['peer'] = peer
    return host_list 

  def _get_device_specs(self, device):
    try:
      with open('./device_specs/' + device + '.yml', 'r') as f:
        device_specs = safe_load(f)
    except IOError:
      raise AnsibleParserError('Invalid device {}'.format(device))
    return device_specs


  def _get_hostvars(self, host_dict, downlink_switches):
    role = host_dict['role']
    mgmt_ip = host_dict['mgmt_ip']
    device = host_dict['device']
    device_specs = self._get_device_specs(device)
    platform = device_specs['platform']
    peer = device_specs['peer'][:2]
    uplinks = device_specs['uplinks'][:4]
    downlinks = device_specs['downlinks'][:2*downlink_switches]
    topology_connections = {'peer': peer,
                            'uplinks': uplinks,
                            'downlinks': downlinks}

    return {'role': role,
            'ansible_hostname': mgmt_ip,
            'ansible_network_os': platform,
            'topology_connections': topology_connections}

  def _load_inventory(self):
    '''Load inventory'''
    try:
      with open('request.yml','r') as file:
        request = safe_load(file)
    except IOError as e:
      raise AnsibleParserError('request.yml required: {}'.format(e))
    if request['topology'] == 'dst_access_l2':
      self._load_dst_access_l2(request)
    else:
      raise AnsibleParserError('Invalid topology: {}'.format(request['topology']))

  def _load_dst_access_l2(self, request):

    request['topology_nodes']['dst'][0]['role'] = 'DSTA'
    request['topology_nodes']['dst'][1]['role'] = 'DSTB'

    downlink_switches = len(request['topology_nodes']['access'])

    for i in range(downlink_switches):
      request['topology_nodes']['access'][i]['role'] = 'ACC' + str(i+1).zfill(3)
    #topology_connections = _get_device_specs()
    self.inventory.add_group('topology')
    self.inventory.set_variable('topology',
                                'downlink_switches',
                                downlink_switches)
    self.inventory.set_variable('topology', 'offline', request['offline'])

    host_list = request['topology_nodes']['dst'] + request['topology_nodes']['access']
    for i in range(len(host_list)):
      host_vars = self._get_hostvars(host_list[i], downlink_switches)
      hostname = self.LOCATION[request['location']] + request['site'] + '-' + host_vars['role']
      host_list[i]['hostname'] = hostname
      host_vars['hostname'] = hostname

      self.inventory.add_host(host=host_vars['ansible_hostname'], group='topology')
      for k,v in host_vars.items():
        self.inventory.set_variable(host_vars['ansible_hostname'], k, v)

    host_list = self._get_neighbors(host_list)

    for host in host_list:
      self.inventory.set_variable(host['mgmt_ip'], 'peer', host['peer'])
      self.inventory.set_variable(host['mgmt_ip'], 'uplinks', host['uplinks'])
      self.inventory.set_variable(host['mgmt_ip'], 'downlinks', host['downlinks'])

  def parse(self, inventory, loader, path, cache):
    '''Return inventory from source'''
    super(InventoryModule, self).parse(inventory, loader, path, cache)

    self._read_config_data(path)

    try:
      request = self.get_option('plugin')
    except Exception as e:
      raise AnsibleParserError('All options required: {}'.format(e))

    self._load_inventory()
