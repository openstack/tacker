# Copyright (C) 2022 Fujitsu
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


from openstack import connection
from openstack import exceptions as os_ex
from oslo_log import log as logging


LOG = logging.getLogger(__name__)


class CinderClient(object):

    def __init__(self, vim_info):
        auth = dict(
            auth_url=vim_info.interfaceInfo['endpoint'],
            username=vim_info.accessInfo['username'],
            password=vim_info.accessInfo['password'],
            project_name=vim_info.accessInfo['project'],
            user_domain_name=vim_info.accessInfo['userDomain'],
            project_domain_name=vim_info.accessInfo['projectDomain']
        )
        self.conn = connection.Connection(
            region_name=vim_info.accessInfo.get('region'),
            auth=auth,
            identity_interface='internal')

    def get_volume(self, volume_id):
        try:
            return self.conn.volume.get_volume(volume_id)
        except os_ex.ResourceNotFound:
            LOG.debug("volume %s not found.", volume_id)
