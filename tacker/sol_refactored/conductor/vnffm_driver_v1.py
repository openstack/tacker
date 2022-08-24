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

from oslo_log import log as logging

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import fm_alarm_utils as alarm_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.nfvo import nfvo_client


LOG = logging.getLogger(__name__)

CONF = config.CONF


class VnfFmDriverV1():
    def __init__(self):
        self.endpoint = CONF.v2_vnfm.endpoint
        self.nfvo_client = nfvo_client.NfvoClient()

    def store_alarm_info(self, context, alarm):
        # store alarm into DB
        try:
            alarm_utils.get_alarm(context, alarm.id)
            with context.session.begin(subtransactions=True):
                alarm.update(context)
        except sol_ex.AlarmNotFound:
            with context.session.begin(subtransactions=True):
                alarm.create(context)

        # get inst
        inst = inst_utils.get_inst(context, alarm.managedObjectId)

        # send notification
        self.nfvo_client.send_alarm_notification(
            context, alarm, inst, self.endpoint)
