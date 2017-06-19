# Copyright 2016 Brocade Communications System, Inc.
# All Rights Reserved.
#
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

from tacker.common import log
from tacker.db.common_services import common_services_db_plugin


class CommonServicesPlugin(common_services_db_plugin.CommonServicesPluginDb):
    """Reference plugin for COMMONSERVICES extension

    Implements the COMMONSERVICES extension and defines public facing APIs for
    common utility operations.
    """

    supported_extension_aliases = ['CommonServices']

    def __init__(self):
        super(CommonServicesPlugin, self).__init__()

    @log.log
    def get_event(self, context, event_id, fields=None):
        return super(CommonServicesPlugin, self).get_event(context, event_id,
                                                      fields)

    @log.log
    def get_events(self, context, filters=None, fields=None, sorts=None,
                   limit=None, marker_obj=None, page_reverse=False):
        return super(CommonServicesPlugin, self).get_events(context, filters,
                                                       fields, sorts, limit,
                                                       marker_obj,
                                                       page_reverse)
