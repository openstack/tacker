#    Copyright 2012 OpenStack Foundation
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
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from six.moves.urllib import parse
from tacker.vnfm.monitor_drivers.token import Token
from tacker import wsgi
# check alarm url with db --> move to plugin


LOG = logging.getLogger(__name__)

OPTS = [
    cfg.StrOpt('username', default='admin',
        help=_('User name for alarm monitoring')),
    cfg.StrOpt('password', default='devstack',
        help=_('password for alarm monitoring')),
    cfg.StrOpt('project_name', default='admin',
        help=_('project name for alarm monitoring')),
]

cfg.CONF.register_opts(OPTS, 'alarm_auth')


def config_opts():
    return [('alarm_auth', OPTS)]


class AlarmReceiver(wsgi.Middleware):
    def process_request(self, req):
        LOG.debug('Process request: %s', req)
        if req.method != 'POST':
            return
        url = req.url
        if not self.handle_url(url):
            return
        prefix, info, params = self.handle_url(req.url)
        auth = cfg.CONF.keystone_authtoken
        token = Token(username=cfg.CONF.alarm_auth.username,
                      password=cfg.CONF.alarm_auth.password,
                      project_name=cfg.CONF.alarm_auth.project_name,
                      auth_url=auth.auth_url + '/v3',
                      user_domain_name='default',
                      project_domain_name='default')

        token_identity = token.create_token()
        req.headers['X_AUTH_TOKEN'] = token_identity
        # Change the body request
        if req.body:
            body_dict = dict()
            body_dict['trigger'] = {}
            body_dict['trigger'].setdefault('params', {})
            # Update params in the body request
            body_info = jsonutils.loads(req.body)
            body_dict['trigger']['params']['data'] = body_info
            body_dict['trigger']['params']['credential'] = info[6]
            # Update policy and action
            body_dict['trigger']['policy_name'] = info[4]
            body_dict['trigger']['action_name'] = info[5]
            req.body = jsonutils.dumps(body_dict)
            LOG.debug('Body alarm: %s', req.body)
        # Need to change url because of mandatory
        req.environ['PATH_INFO'] = prefix + 'triggers'
        req.environ['QUERY_STRING'] = ''
        LOG.debug('alarm url in receiver: %s', req.url)

    def handle_url(self, url):
        # alarm_url = 'http://host:port/v1.0/vnfs/vnf-uuid/mon-policy-name/action-name/8ef785' # noqa
        parts = parse.urlparse(url)
        p = parts.path.split('/')
        if len(p) != 7:
            return None

        if any((p[0] != '', p[2] != 'vnfs')):
            return None
        # decode action name: respawn%25log
        p[5] = parse.unquote(p[5])
        qs = parse.parse_qs(parts.query)
        params = dict((k, v[0]) for k, v in qs.items())
        prefix_url = '/%(collec)s/%(vnf_uuid)s/' % {'collec': p[2],
                                                    'vnf_uuid': p[3]}
        return prefix_url, p, params
