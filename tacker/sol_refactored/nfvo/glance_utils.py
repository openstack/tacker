# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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


class GlanceClient(object):

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

    def create_image(self, name, **fields):
        return self.conn.image.create_image(
            name, allow_duplicates=True, **fields)

    def list_images(self, **params):
        return self.conn.image.images(**params)

    def get_image(self, image_id):
        try:
            return self.conn.image.get_image(image_id)
        except os_ex.ResourceNotFound:
            LOG.debug("image %s not found.", image_id)

    def delete_image(self, image_id):
        try:
            return self.conn.image.delete_image(image_id)
        except os_ex.ResourceNotFound:
            LOG.debug("image %s not found.", image_id)
