# Copyright (C) 2020 NTT DATA
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

import sys

from oslo_log import log as logging

from glanceclient import exc
from tacker.common import clients
from tacker.extensions import vnflcm


LOG = logging.getLogger(__name__)


class GlanceClient(object):

    def __init__(self, vim_connection_info, version=None):
        super(GlanceClient, self).__init__()
        self.connection = clients.OpenstackSdkConnection(
            vim_connection_info, version).connection

    def create(self, name, **fields):
        try:
            return self.connection.image.create_image(
                name, allow_duplicates=True, **fields)
        except exc.HTTPException:
            type_, value, tb = sys.exc_info()
            raise vnflcm.GlanceClientException(msg=value)

    def delete(self, image_id):
        try:
            self.connection.image.delete_image(image_id)
        except exc.HTTPNotFound:
            LOG.warning("Image %(image)s created not found "
                        "at cleanup", {'image': image_id})

    def import_image(self, image, web_path):
        try:
            self.connection.image.import_image(
                image, method='web-download', uri=web_path)
        except exc.HTTPException:
            type_, value, tb = sys.exc_info()
            raise vnflcm.GlanceClientException(msg=value)

    def get(self, image_id):
        try:
            return self.connection.image.get_image(image_id)
        except exc.HTTPNotFound:
            LOG.warning("Image %(image)s created not found ",
                        {'image': image_id})
