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
from tacker._i18n import _
from tacker.vnfm.monitor_drivers.token import Token
from tacker import wsgi
# check alarm url with db --> move to plugin


LOG = logging.getLogger(__name__)

OPTS = [
    cfg.StrOpt('username', default='admin',
        help=_('User name for alarm monitoring')),
    cfg.StrOpt('password', default='devstack',
        help=_('Password for alarm monitoring')),
    cfg.StrOpt('project_name', default='admin',
        help=_('Project name for alarm monitoring')),
    cfg.StrOpt('user_domain_name', default='default',
        help=_('User domain name for alarm monitoring')),
    cfg.StrOpt('project_domain_name', default='default',
        help=_('Project domain name for alarm monitoring')),
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
        resource = 'trigger' if info[4] != 'maintenance' else 'maintenance'
        redirect = resource + 's'
        auth = cfg.CONF.keystone_authtoken
        alarm_auth = cfg.CONF.alarm_auth
        token = Token(username=alarm_auth.username,
                      password=alarm_auth.password,
                      project_name=alarm_auth.project_name,
                      auth_url=auth.auth_url + '/v3',
                      user_domain_name=alarm_auth.user_domain_name,
                      project_domain_name=alarm_auth.project_domain_name)

        token_identity = token.create_token()
        req.headers['X_AUTH_TOKEN'] = token_identity
        # Change the body request
        if req.body:
            body_dict = dict()
            body_dict[resource] = {}
            body_dict[resource].setdefault('params', {})
            # Update params in the body request
            body_info = jsonutils.loads(req.body)
            body_dict[resource]['params']['credential'] = info[6]
            if resource == 'maintenance':
                body_info.update({
                    'body': self._handle_maintenance_body(body_info)})
                del body_info['reason_data']
            else:
                # Update policy and action
                body_dict[resource]['policy_name'] = info[4]
                body_dict[resource]['action_name'] = info[5]
            body_dict[resource]['params']['data'] = body_info
            req.body = jsonutils.dump_as_bytes(body_dict)
            LOG.debug('Body alarm: %s', req.body)
        # Need to change url because of mandatory
        req.environ['PATH_INFO'] = prefix + redirect
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

    def _handle_maintenance_body(self, body_info):
        body = {}
        traits_list = body_info['reason_data']['event']['traits']
        if type(traits_list) is not list:
            return
        for key, t_type, val in traits_list:
            if t_type == 1 and val and (val[0] == '[' or val[0] == '{'):
                body[key] = eval(val)
            else:
                body[key] = val
        return body
