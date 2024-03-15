# Copyright 2015 Brocade Communications System, Inc.
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

import os
import yaml

from cinderclient import client as cinder_client
from glanceclient.v2 import client as glance_client
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient import adapter
from neutronclient.v2_0 import client as neutron_client
from novaclient import client as nova_client
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from tempest.lib import base

from tacker.common import clients
from tacker.common import utils
from tacker.tests import constants
from tacker.tests.utils import read_file
from tacker import version

from tackerclient.v1_0 import client as tacker_client


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class SessionClient(adapter.Adapter):
    def request(self, *args, **kwargs):
        kwargs.setdefault('authenticated', False)
        kwargs.setdefault('raise_exc', False)

        content_type = kwargs.pop('content_type', None) or 'application/json'

        headers = kwargs.setdefault('headers', {})
        headers.setdefault('Accept', content_type)

        try:
            kwargs.setdefault('data', kwargs.pop('body'))
        except KeyError:
            pass

        if kwargs.get('data'):
            headers.setdefault('Content-Type', content_type)

        return super(SessionClient, self).request(*args, **kwargs)

    def _decode_json(self, response):
        body = response.text
        if body and response.headers['Content-Type'] == 'text/plain':
            return body
        elif body and response.headers['Content-Type'] == 'text/x-sh':
            return body
        elif body:
            return jsonutils.loads(body)
        else:
            return ""

    def do_request(self, url, method, **kwargs):
        kwargs.setdefault('authenticated', True)
        resp = self.request(url, method, **kwargs)
        if ('Content-Type' not in resp.headers or
                resp.headers['Content-Type'] == 'application/zip'):
            return resp, resp.content
        body = self._decode_json(resp)
        return resp, body


class BaseTackerTest(base.BaseTestCase):
    """Base test case class for all Tacker API tests."""

    @classmethod
    def setUpClass(cls):
        super(BaseTackerTest, cls).setUpClass()
        kwargs = {}

        cfg.CONF(args=['--config-file', '/etc/tacker/tacker.conf'],
                 project='tacker',
                 version='%%prog %s' % version.version_info.release_string(),
                 **kwargs)

        cls.client = cls.tackerclient()
        cls.http_client = cls.tacker_http_client()
        cls.h_client = cls.heatclient()
        cls.glance_client = cls.glanceclient()
        cls.cinder_client = cls.cinderclient()
        cls.nova_client = cls.novaclient()

    @classmethod
    def get_credentials(cls, vim_conf_file=None):
        if vim_conf_file is None:
            vim_conf_file = 'local-vim.yaml'
        vim_params = yaml.safe_load(read_file(vim_conf_file))
        vim_params['auth_url'] += '/v3'
        return vim_params

    @classmethod
    def get_auth_session(cls, vim_conf_file=None):
        vim_params = cls.get_credentials(vim_conf_file)
        auth = v3.Password(
            auth_url=vim_params['auth_url'],
            username=vim_params['username'],
            password=vim_params['password'],
            project_name=vim_params['project_name'],
            user_domain_name=vim_params['user_domain_name'],
            project_domain_name=vim_params['project_domain_name'])
        verify = utils.str_to_bool(vim_params.pop('cert_verify', 'False'))
        auth_ses = session.Session(auth=auth, verify=verify)
        return auth_ses

    @classmethod
    def tacker_http_client(cls, vim_conf_file=None):
        auth_session = cls.get_auth_session(vim_conf_file)
        return SessionClient(session=auth_session,
                             service_type='nfv-orchestration',
                             region_name='RegionOne')

    @classmethod
    def tackerclient(cls, vim_conf_file=None):
        auth_session = cls.get_auth_session(vim_conf_file)
        return tacker_client.Client(session=auth_session, retries=5)

    @classmethod
    def novaclient(cls, vim_conf_file=None):
        vim_params = cls.get_credentials(vim_conf_file)
        auth = v3.Password(auth_url=vim_params['auth_url'],
            username=vim_params['username'],
            password=vim_params['password'],
            project_name=vim_params['project_name'],
            user_domain_name=vim_params['user_domain_name'],
            project_domain_name=vim_params['project_domain_name'])
        verify = utils.str_to_bool(vim_params.pop('cert_verify', 'False'))
        auth_ses = session.Session(auth=auth, verify=verify)
        return nova_client.Client(constants.NOVA_CLIENT_VERSION,
                                  session=auth_ses)

    @classmethod
    def neutronclient(cls, vim_conf_file=None):
        vim_params = cls.get_credentials(vim_conf_file)
        auth = v3.Password(auth_url=vim_params['auth_url'],
            username=vim_params['username'],
            password=vim_params['password'],
            project_name=vim_params['project_name'],
            user_domain_name=vim_params['user_domain_name'],
            project_domain_name=vim_params['project_domain_name'])
        verify = utils.str_to_bool(vim_params.pop('cert_verify', 'False'))
        auth_ses = session.Session(auth=auth, verify=verify)
        return neutron_client.Client(session=auth_ses)

    @classmethod
    def heatclient(cls, vim_conf_file=None):
        if vim_conf_file is None:
            vim_conf_file = 'local-vim.yaml'
        data = yaml.safe_load(read_file(vim_conf_file))
        data['auth_url'] = data['auth_url'] + '/v3'
        domain_name = data.pop('domain_name')
        data['user_domain_name'] = domain_name
        data['project_domain_name'] = domain_name
        return clients.OpenstackClients(auth_attr=data).heat

    @classmethod
    def glanceclient(cls, vim_conf_file=None):
        vim_params = cls.get_credentials(vim_conf_file)
        auth = v3.Password(auth_url=vim_params['auth_url'],
            username=vim_params['username'],
            password=vim_params['password'],
            project_name=vim_params['project_name'],
            user_domain_name=vim_params['user_domain_name'],
            project_domain_name=vim_params['project_domain_name'])
        verify = utils.str_to_bool(vim_params.pop('cert_verify', 'False'))
        auth_ses = session.Session(auth=auth, verify=verify)
        return glance_client.Client(session=auth_ses)

    @classmethod
    def cinderclient(cls, vim_conf_file=None):
        vim_params = cls.get_credentials(vim_conf_file)
        auth = v3.Password(auth_url=vim_params['auth_url'],
            username=vim_params['username'],
            password=vim_params['password'],
            project_name=vim_params['project_name'],
            user_domain_name=vim_params['user_domain_name'],
            project_domain_name=vim_params['project_domain_name'])
        verify = utils.str_to_bool(vim_params.pop('cert_verify', 'False'))
        auth_ses = session.Session(auth=auth, verify=verify)
        return cinder_client.Client(constants.CINDER_CLIENT_VERSION,
                                    session=auth_ses)

    def get_vim(self, vim_list, vim_name):
        if len(vim_list.values()) == 0:
            assert False, "vim_list is Empty: Default VIM is missing"

        for vim_list in vim_list.values():
            for vim in vim_list:
                if vim['name'] == vim_name:
                    return vim
        return None

    def assertDictSupersetOf(self, expected_subset, actual_superset):
        """Checks that actual dict contains the expected dict.

        After checking that the arguments are of the right type, this checks
        that each item in expected_subset is in, and matches, what is in
        actual_superset. Separate tests are done, so that detailed info can
        be reported upon failure.
        """
        if not isinstance(expected_subset, dict):
            self.fail("expected_subset (%s) is not an instance of dict" %
                      type(expected_subset))
        if not isinstance(actual_superset, dict):
            self.fail("actual_superset (%s) is not an instance of dict" %
                      type(actual_superset))
        for k, v in expected_subset.items():
            self.assertIn(k, actual_superset)
            self.assertEqual(v, actual_superset[k],
                             "Key %(key)s expected: %(exp)r, actual %(act)r" %
                             {'key': k, 'exp': v, 'act': actual_superset[k]})

    def _list_op_occs(self, filter_string='', http_client=None):
        if http_client is None:
            http_client = self.http_client
        show_url = os.path.join(
            self.base_vnf_lcm_op_occs_url)
        resp, response_body = http_client.do_request(
            show_url + filter_string, "GET")
        return resp, response_body

    def _assert_occ_list(self, resp, op_occs_list):
        self.assertEqual(200, resp.status_code)

        # Only check required parameters.
        for op_occs_info in op_occs_list:
            self.assertIsNotNone(op_occs_info.get('id'))
            self.assertIsNotNone(op_occs_info.get('operationState'))
            self.assertIsNotNone(op_occs_info.get('stateEnteredTime'))
            self.assertIsNotNone(op_occs_info.get('vnfInstanceId'))
            self.assertIsNotNone(op_occs_info.get('operation'))
            self.assertIsNotNone(op_occs_info.get('isAutomaticInvocation'))
            self.assertIsNotNone(op_occs_info.get('isCancelPending'))

            _links = op_occs_info.get('_links')
            self.assertIsNotNone(_links.get('self'))
            self.assertIsNotNone(_links.get('self').get('href'))
            self.assertIsNotNone(_links.get('vnfInstance'))
            self.assertIsNotNone(_links.get('vnfInstance').get('href'))
            self.assertIsNotNone(_links.get('grant'))
            self.assertIsNotNone(_links.get('grant').get('href'))
