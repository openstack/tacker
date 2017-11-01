#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
URL_ = "/zabbix/api_jsonrpc.php"

HEADERS = {'Content-Type': 'application/json-rpc'}
dAUTH_API = {'jsonrpc': "2.0",
             'method': 'user.login',
             'params': {'user': None,
                        'password': None},
             'id': 1,
             'auth': None}

COMP_VALUE = {'greater': '>',
              'less': '<',
              'and greater': '>=',
              'and less': '<=',
              'down': '=0'}


dTEMPLATE_CREATE_API = {'jsonrpc': "2.0", 'method': "template.create",
                        'params': {'host': "", 'groups': {'groupid': 1},
                                   'hosts': []},
                        'id': 1004, 'auth': None}

dITEM_CREATE_API = {'jsonrpc': "2.0",
                    'method': "item.create",
                    'params': {'hostid': None,
                               'interfaceid': 'NULL',
                               'name': "",
                               'key_': "",
                               'type': 0,
                               'value_type': 3,
                               'delay': 1},
                    'id': 1,
                    'auth': None}


dITEM_KEY_VALUE = {'os_agent_info': 'agent.ping',
                   'os_cpu_usage': 'system.cpu.util[,iowait]',
                   'os_cpu_load': 'system.cpu.load[percpu,avg1]',
                   'os_proc_value': 'proc.num[,,run]',
                   'app_status': 'net.tcp.port[ ,*]',
                   'app_memory': 'proc.mem[*,root]'}

dITEM_KEY_COMP = {'os_agent_info': str(
    dITEM_KEY_VALUE['os_agent_info'] + '.nodata(15s)}=1'),
    'os_cpu_usage': str(
        dITEM_KEY_VALUE['os_cpu_usage'] + '.avg(5s)}'),
    'os_cpu_load': str(
        dITEM_KEY_VALUE['os_cpu_load'] + '.avg(5s)}'),
    'os_proc_value': str(
        dITEM_KEY_VALUE['os_proc_value'] + '.avg(5s)}'),
    'app_status': str(
        dITEM_KEY_VALUE['app_status'] + '.last(,5)}'),
    'app_memory': str(
        dITEM_KEY_VALUE['app_memory'] + '.avg(5s)}')}

dITEM_KEY_INFO = {'os_proc_value': {'name': 'process number',
                                    'key_': str(
                                        dITEM_KEY_VALUE['os_proc_value']),
                                    'value_type': 3},
                  'os_cpu_load': {'name': 'cpu load',
                                  'key_': str(
                                      dITEM_KEY_VALUE['os_cpu_load']),
                                  'value_type': 0},
                  'os_cpu_usage': {'name': 'cpu util usage',
                                   'key_': str(
                                       dITEM_KEY_VALUE['os_cpu_usage']),
                                   'value_type': 0},
                  'os_agent_info': {'name': 'Zabbix agent status check',
                                    'key_': str(
                                        dITEM_KEY_VALUE['os_agent_info']),
                                    'value_type': 0},
                  'app_status': {'name': ' service status check',
                                 'key_': str(
                                     dITEM_KEY_VALUE['app_status']),
                                 'value_type': 3},
                  'app_memory': {'name': ' service memory usage',
                                 'key_': str(
                                     dITEM_KEY_VALUE['app_memory']),
                                 'value_type': 3}}


dTRIGGER_CREATE_API = {'jsonrpc': "2.0",
                       'method': "trigger.create",
                       'templateid': None,
                       'auth': None,
                       'id': 1004}

dTRIGGER_INFO = {'itemname': None,
                 'cmdname': None,
                 'cmd-action': None}

dTRIGGER_LIST = {'os_agent_info': [{'description': 'Zabbix agent on '
                                                   '{HOST.NAME} is '
                                                   'unreachable '
                                                   'for 15 seconds',
                                    'expression': '{', 'priority': 3}],
                 'app_status': [{'description': 'Service is down '
                                                'on {HOST.NAME}',
                                 'expression': '{', 'priority': 3}],
                 'app_memory': [{'description': 'Process Memory '
                                                'is lacking '
                                                'on {HOST.NAME}',
                                 'expression': '{', 'priority': 3}],
                 'os_cpu_usage': [{'description': 'Disk I/O is '
                                                  'overloaded '
                                                  'on {HOST.NAME}',
                                   'expression': '{', 'priority': 3}],
                 'os_cpu_load': [{'description': 'Processor load '
                                                 'is too high '
                                                 'on {HOST.NAME}',
                                  'expression': '{', 'priority': 3}],
                 'os_proc_value': [{'description': 'Too many '
                                                   'processes running '
                                                   'on {HOST.NAME}',
                                    'expression': '{', 'priority': 3}]}

dACTION_CREATE_API = {'jsonrpc': "2.0",
                      'method': "action.create",
                      'params': {'name': '',
                                 'eventsource': 0,
                                 'status': 0,
                                 'esc_period': 120,
                                 'def_shortdata': "{TRIGGER.NAME}:"
                                                  "{TRIGGER.STATUS}",
                                 'def_longdata': "{TRIGGER.NAME}: "
                                                 "{TR`IGGER.STATUS}\r\n"
                                                 "Last value: "
                                                 "{ITEM.LASTVALUE]"
                                                 "\r\n\r\n{TRIGGER.URL}",
                                 "filter": {"evaltype": 0,
                                            "conditions": [{'conditiontype': 2,
                                                            'operator': 0,
                                                            'value': None}]},
                                 'operations': [{'operationtype': 1,
                                                 'esc_period': 0,
                                                 'esc_step_from': 1,
                                                 'esc_step_to': 2,
                                                 'evaltype': 0,
                                                 'opcommand': {
                                                     'command': None,
                                                     'type': 0,
                                                     'execute_on': 0},
                                                 'opcommand_hst': [
                                                     {'hostid': None}]
                                                 }]},
                      'auth': None, 'id': 1}

dHOST_CREATE_API = {'jsonrpc': "2.0",
                    'method': "host.create",
                    'params': {'host': 'ubuntu',
                               'interfaces': [
                                   {'type': 1,
                                    'main': 1,
                                    'useip': 1,
                                    'dns': "",
                                    'ip': None,
                                    'port': "10050"}],
                               'templates': [{'templateid': None}],
                               'groups': [{'groupid': None}]},
                    'id': 4, 'auth': None}

dGROUP_GET_API = {'jsonrpc': "2.0", 'method': "hostgroup.get",
                  'params': {'output': 'extend',
                             'filter': {'name': ["Zabbix servers", ]}},
                  'id': 1, 'auth': None}

dGRAPH_CREATE_API = {'jsonrpc': '2.0', 'method': 'graph.create',
                     'params': {'name': None,
                                'width': 900,
                                'height': 200,
                                'gitems': []},
                     'auth': None, 'id': 1004}

dAPP_INFO = {'app_port': None,
             'app_name': None,
             'ssh_username': None,
             'ssh_password': None}

dZBX_INFO = {'zabbix_user': None,
             'zabbix_pass': None,
             'zabbix_ip': None,
             'zabbix_port': None,
             'zabbix_token': None
             }

dACTION_LIST = {'item': None,
                'action': None,
                'trigger_id': None,
                'cmd-action': None}

dVDU_INFO = {'template_id': None,
             'template_name': None,
             'hostid': None,
             'group_id': None,
             'mgmt_ip': None,
             'vdu_id': None,
             'parameters': None,
             'actioninfo': [],
             'appinfo': None,
             'zbx_info': None
             }
