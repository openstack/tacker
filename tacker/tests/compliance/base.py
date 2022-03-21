# Copyright (C) 2022 NEC, Corp.
# All Rights Reserved.
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

import json
import os
import time
import xml.etree.ElementTree as et

from oslo_serialization import jsonutils
from oslo_utils import uuidutils
import robot
from urllib.parse import urlparse

from tacker.tests.functional import base
from tacker.tests.functional.sol.vnflcm import test_vnf_instance as vnflcmtest

VNFPKG_PATH = '/vnfpkgm/v1/vnf_packages/%s'
VNFINSS_PATH = '/vnflcm/v1/vnf_instances'
VNFINS_PATH = '/vnflcm/v1/vnf_instances/%s'
VNFINS_INST_PATH = '/vnflcm/v1/vnf_instances/%s/instantiate'
VNFINS_TERM_PATH = '/vnflcm/v1/vnf_instances/%s/terminate'
VNFINS_GET_LCM_OP_OCCS_PATH = '/vnflcm/v1/vnf_lcm_op_occs'
VNFINS_GET_IND_LCM_OP_OCCS_PATH = '/vnflcm/v1/vnf_lcm_op_occs/%s'
VNFINS_CREATE_SUBSC_PATH = '/vnflcm/v1/subscriptions'
VNFINS_DEL_SUBSC_PATH = '/vnflcm/v1/subscriptions/%s'
VNFINS_SCALE_PATH = '/vnflcm/v1/vnf_instances/%s/scale'

INSTANTIATION_BODY = {
    'flavourId': 'simple',
    'extVirtualLinks': [
        {
            'id': 'net0',
            'resourceId': None,
            'extCps': [
                {
                    'cpdId': 'CP1',
                    'cpConfig': [
                        {
                            'cpProtocolData': [
                                {
                                    'layerProtocol': 'IP_OVER_ETHERNET'
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ],
    'vimConnectionInfo': [
        {
            'id': None,
            'vimId': None,
            'vimType': 'ETSINFV.OPENSTACK_KEYSTONE.v_2'
        }
    ]
}

TERMINATION_BODY = {
    'terminationType': 'GRACEFUL',
    'gracefulTerminationTimeout': 120
}

PATCH_BODY = {
    'vnfInstanceName': 'vnf new name',
    'vnfInstanceDescription': 'new description'
}

SUBSCRIPTION_BODY = {
    'filter': {
        'vnfInstanceSubscriptionFilter': {
            'vnfdIds': [
                ''
            ]
        }
    },
    'callbackUri': 'http://localhost:9091/endpoint'
}

SCALE_BODY = {
    'type': 'SCALE_OUT',
    'aspectId': 'VDU1',
    'numberOfSteps': 1,
    'additionalParams': {
        'samplekey': 'samplevalue'
    }
}

HEAL_BODY = {
    'vnfcInstanceId': None,
    'cause': 'healing'
}

CHG_EXT_CONN_BODY = {
    "extVirtualLinks": [{
        "id": "8877c521-7c51-4da8-a5b9-308b40437fd2",
        "resourceId": "dfc1872e-69a7-4f14-a2c7-5bac8bd545eb",
        "extCps": [{
            "cpdId": "CP1",
            "cpConfig": [{
            }]
        }]
    }],
    "vimConnectionInfo": [{
        "id": "748f7d54-9fdf-4e7a-a180-ec057a9eefd8",
        "vimId": "310e0d4c-7e85-42e4-b289-d09c0bdc44c8",
        "vimType": "openstack",
        "interfaceInfo": {
            "endpoint": "http://127.0.0.1/identity"
        }
    }]
}


class VnfPkgInfo:
    def __init__(self, vnfpkgid, vnfdid):
        self._vnfpkgid = vnfpkgid
        self._vnfdid = vnfdid

    @property
    def vnfpkgid(self):
        return self._vnfpkgid

    @property
    def vnfdid(self):
        return self._vnfdid


class BaseComplTest(base.BaseTackerTest):
    @classmethod
    def setUpClass(cls):
        super(BaseComplTest, cls).setUpClass()

        for vim_list in cls.client.list_vims().values():
            for vim in vim_list:
                if vim['name'] == 'VIM0':
                    cls.vimid = vim['id']

        for net_list in cls.neutronclient().list_networks().values():
            for net in net_list:
                if net['name'] == 'net0':
                    cls.net0_id = net['id']

        cls.base_dir = os.getcwd()
        cls.test_root_dir = os.path.join(cls.base_dir, 'api-tests')
        cls.sol_dir = os.path.join(cls.test_root_dir, cls.sol)
        cls.api_dir = os.path.join(cls.sol_dir, cls.api)
        cls.test_file = cls.resource + '.robot'
        os.chdir(cls.api_dir)

        parts = urlparse(cls.http_client.get_endpoint())

        cls.common_variables = []
        cls.common_variables.append('VNFM_SCHEMA:%s' % parts.scheme)
        cls.common_variables.append('NFVO_SCHEMA:%s' % parts.scheme)
        cls.common_variables.append('VNFM_HOST:%s' % parts.hostname)
        cls.common_variables.append('NFVO_HOST:%s' % parts.hostname)
        cls.common_variables.append('VNFM_PORT:%s' % parts.port)
        cls.common_variables.append('NFVO_PORT:%s' % parts.port)
        cls.common_variables.append('AUTH_USAGE:1')
        cls.common_variables.append('AUTHORIZATION_HEADER:X-Auth-Token')
        cls.common_variables.append('AUTHORIZATION_TOKEN:%s' %
                                    cls.http_client.get_token())

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.base_dir)

        super(BaseComplTest, cls).tearDownClass()

    @classmethod
    def _get_responses_from_output(cls, output):
        result = []
        for el in et.fromstring(output).findall(
                ".//kw[@name='Output']/[@library='REST']/msg[1]"):
            result.append(json.loads(el.text))
        return result

    @classmethod
    def _get_id_from_output(cls, output):
        res = cls._get_responses_from_output(output)
        if ('status' in res[0] and
                res[0]['status'] in [200, 201, 202, 203, 204]):
            if ('body' in res[0] and 'id' in res[0]['body']):
                return res[0]['body']['id']

        return None

    @classmethod
    def _create_and_upload_vnf_packages(cls, pkgnames):
        vnfpkginfos = []
        for pkgname in pkgnames:
            vnfpkgid, vnfdid = vnflcmtest._create_and_upload_vnf_package(
                cls.http_client, pkgname, {})
            vnfpkginfos.append(VnfPkgInfo(vnfpkgid, vnfdid))

        return vnfpkginfos

    @classmethod
    def _disable_vnf_package(cls, vnfpkgid):
        cls.http_client.do_request(VNFPKG_PATH % vnfpkgid,
            'PATCH', content_type='application/json',
            body=jsonutils.dumps({"operationalState": "DISABLED"}))

    @classmethod
    def _get_vnfpkgids(cls, vnfpkginfos):
        vnfpkgids = []
        for vnfpkginfo in vnfpkginfos:
            vnfpkgids.append(vnfpkginfo.vnfpkgid)

        return vnfpkgids

    @classmethod
    def _delete_vnf_package(cls, vnfpkgid):
        cls.http_client.do_request(VNFPKG_PATH % vnfpkgid, 'DELETE')

    @classmethod
    def _disable_and_delete_vnf_packages(cls, vnfpkginfos):
        for vnfpkginfo in vnfpkginfos:
            cls._disable_vnf_package(vnfpkginfo.vnfpkgid)
            cls._delete_vnf_package(vnfpkginfo.vnfpkgid)

    @classmethod
    def _create_vnf_instance(cls, vnfdid, name=None, description=None):
        body = {'vnfdId': vnfdid}
        if name:
            body['vnfInstanceName'] = name
        if description:
            body['vnfInstanceDescription'] = description

        res, resbody = cls.http_client.do_request(VNFINSS_PATH, 'POST',
                body=jsonutils.dumps(body))

        return res, resbody

    @classmethod
    def _delete_vnf_instance(cls, vnfid):
        resp, body = cls.http_client.do_request(VNFINS_PATH % vnfid, 'DELETE')

    @classmethod
    def _instantiate_vnf_instance(cls, vnfid):
        body = INSTANTIATION_BODY
        body['extVirtualLinks'][0]['resourceId'] = cls.net0_id
        body['vimConnectionInfo'][0]['id'] = uuidutils.generate_uuid()
        body['vimConnectionInfo'][0]['vimId'] = cls.vimid

        cls.http_client.do_request(VNFINS_INST_PATH % vnfid,
            'POST', body=jsonutils.dumps(body))

        cls._wait_vnf_status(vnfid, 'instantiationState', 'INSTANTIATED')

    @classmethod
    def _terminate_vnf_instance(cls, vnfid):
        cls.http_client.do_request(VNFINS_TERM_PATH % vnfid,
            'POST', body=jsonutils.dumps(TERMINATION_BODY))

        cls._wait_vnf_status(vnfid, 'instantiationState', 'NOT_INSTANTIATED')

    @classmethod
    def _get_vnf_ind_instance(cls, vnfid):
        res, resbody = cls.http_client.do_request(VNFINS_PATH % vnfid, 'GET')

        return resbody

    @classmethod
    def _get_vnf_instance_id(cls):
        res, resbody = cls.http_client.do_request(VNFINSS_PATH, 'GET')

        return resbody[0]['id']

    @classmethod
    def _instantiate_vnf_instance_for_scale(cls, vnfid):
        body = INSTANTIATION_BODY
        body['flavourId'] = 'default'
        body['extVirtualLinks'][0]['resourceId'] = cls.net0_id
        body['vimConnectionInfo'][0]['id'] = uuidutils.generate_uuid()
        body['vimConnectionInfo'][0]['vimId'] = cls.vimid
        body['additionalParams'] = {
            "lcm-operation-user-data": "./UserData/lcm_user_data.py",
            "lcm-operation-user-data-class": "SampleUserData"
        }

        cls.http_client.do_request(VNFINS_INST_PATH % vnfid,
            'POST', body=jsonutils.dumps(body))

        cls._wait_vnf_status(vnfid, 'instantiationState', 'INSTANTIATED')

    @classmethod
    def _instantiate_error_vnf_instance(cls, vnfid):
        body = INSTANTIATION_BODY
        body['flavorId'] = 'sample'
        body['extVirtualLinks'][0]['resourceId'] = cls.net0_id
        body['vimConnectionInfo'][0]['id'] = uuidutils.generate_uuid()
        body['vimConnectionInfo'][0]['vimId'] = cls.vimid
        body['additionalParams'] = {
            "lcm-operation-user-data": "./UserData/lcm_user_data2.py",
            "lcm-operation-user-data-class": "SampleUserData"
        }

        cls.http_client.do_request(VNFINS_INST_PATH % vnfid,
            'POST', body=jsonutils.dumps(body))

        cls._wait_vnf_status(vnfid, 'instantiationState', 'INSTANTIATED')

    @classmethod
    def _get_lcm_op_occs_id(cls, vnfid, lcm='INSTANTIATE'):
        res, resbody = cls.http_client.do_request(
            VNFINS_GET_LCM_OP_OCCS_PATH, 'GET')

        lcmid = None
        for entry in resbody:
            lcm_dict = entry
            if ((lcm_dict['vnfInstanceId'] == vnfid) and
                    (lcm_dict['operation'] == lcm)):
                lcmid = lcm_dict['id']
                break

        return lcmid

    @classmethod
    def _create_subscription(cls, vnfdid):
        body = SUBSCRIPTION_BODY
        body['filter']['vnfInstanceSubscriptionFilter']['vnfdIds'] = [vnfdid]
        res, resbody = cls.http_client.do_request(VNFINS_CREATE_SUBSC_PATH,
            'POST', body=jsonutils.dumps(body))

        subscid = cls._get_id_from_output(resbody)
        return subscid

    @classmethod
    def _get_subscription_id(cls):
        res, resbody = cls.http_client.do_request(VNFINS_CREATE_SUBSC_PATH,
            'GET')

        subscid = resbody[0]['id']
        return subscid

    @classmethod
    def _delete_subscription(cls, subscId):
        cls.http_client.do_request(VNFINS_DEL_SUBSC_PATH % subscId,
            'DELETE')

    @classmethod
    def _scaleout_vnf(cls, vnfid):
        body = SCALE_BODY
        body['type'] = 'SCALE_OUT'
        res_scale, resbody = cls.http_client.do_request(
            VNFINS_SCALE_PATH % vnfid,
            'POST', body=jsonutils.dumps(body))

        print("scaleout called")
        print(res_scale)
        print(resbody)
        lcmid = cls._get_lcm_op_occs_id(vnfid, lcm='SCALE')
        res = cls._wait_lcm_status(lcmid)
        return res, lcmid

    @classmethod
    def _wait_lcm_status(cls, lcmid, value='COMPLETED', expire=600):
        start_time = int(time.time())
        res = 1

        final_state = ''
        while True:
            resp, body = cls.http_client.do_request(
                VNFINS_GET_IND_LCM_OP_OCCS_PATH % lcmid, 'GET')

            if body is None:
                break

            if ((body['operationState'] == value) or
                    (((int(time.time()) - start_time) > expire)) or
                    (body['operationState'] == 'FAILED_TEMP')):
                final_state = body['operationState']
                break

            time.sleep(5)
        time.sleep(30)

        if final_state == value:
            res = 0

        return res

    @classmethod
    def _wait_vnf_status(cls, vnfid, attr, value, expire=600):
        start_time = int(time.time())
        while True:
            resp, body = cls.http_client.do_request(VNFINS_PATH % vnfid, 'GET')
            if body[attr] == value:
                break

            if ((int(time.time()) - start_time) > expire):
                break

            time.sleep(5)
        time.sleep(30)

    def _run(self, test_case, variables=[], body=None, filename=None):
        if (body is not None and filename is not None):
            with open(os.path.join('jsons', filename), 'w') as f:
                f.write(body)
        all_vars = []
        all_vars.extend(variables)
        all_vars.extend(self.common_variables)

        odir = os.path.join(self.base_dir, 'log',
                            self.sol, self.api, self.resource,
                            test_case.replace(' ', '_').replace('"', ''))

        if not os.path.exists(odir):
            os.makedirs(odir)

        with open(os.path.join(odir, 'stdout.txt'), 'w') as stdout:
            rc = robot.run(self.test_file, variable=all_vars, test=test_case,
                           outputdir=odir, stdout=stdout)

        with open(os.path.join(odir, 'output.xml'), 'r') as ofile:
            outputxml = ofile.read()

        return rc, outputxml
