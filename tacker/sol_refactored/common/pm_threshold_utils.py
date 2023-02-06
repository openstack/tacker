# Copyright (C) 2023 Fujitsu
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
from oslo_utils import uuidutils

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import coordinate
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored import objects

LOG = logging.getLogger(__name__)
CONF = config.CONF


def get_pm_threshold_all(context, marker=None):
    return objects.ThresholdV2.get_all(context, marker)


def get_pm_threshold(context, pm_threshold_id):
    return objects.ThresholdV2.get_by_id(context, pm_threshold_id)


def get_pm_threshold_state(pm_threshold, sub_object_instance_id):
    if (not pm_threshold.obj_attr_is_set('metadata') or
            not pm_threshold.metadata.get('thresholdState')):
        return None

    pm_threshold_states = pm_threshold.metadata['thresholdState']
    for pm_threshold_state in pm_threshold_states:
        if (pm_threshold_state.get('subObjectInstanceId') ==
                sub_object_instance_id):
            return pm_threshold_state


def pm_threshold_href(threshold_id, endpoint):
    return f"{endpoint}/vnfpm/v2/thresholds/{threshold_id}"


def make_pm_threshold_links(threshold, endpoint):
    links = objects.ThresholdV2_Links()
    links.self = objects.Link(href=pm_threshold_href(threshold.id, endpoint))
    links.object = objects.Link(
        href=inst_utils.inst_href(threshold.objectInstanceId, endpoint))
    return links


@coordinate.lock_resources('{threshold_id}')
def update_threshold_state_data(context, threshold_id,
                                threshold_state_data):
    pm_threshold = get_pm_threshold(context, threshold_id)
    if not pm_threshold:
        raise sol_ex.PMThresholdNotExist(threshold_id=threshold_id)
    if pm_threshold.obj_attr_is_set('metadata'):
        if 'thresholdState' not in pm_threshold.metadata.keys():
            pm_threshold.metadata.update({
                'thresholdState': [threshold_state_data]})
        else:
            is_exist = False
            for threshold_state in pm_threshold.metadata['thresholdState']:
                if (threshold_state.get('subObjectInstanceId') ==
                        threshold_state_data['subObjectInstanceId'] and
                        threshold_state.get('metrics') ==
                        threshold_state_data['metrics']):
                    threshold_state.update(threshold_state_data)
                    is_exist = True
                    break
            if not is_exist:
                pm_threshold.metadata['thresholdState'].append(
                    threshold_state_data)
    else:
        pm_threshold.metadata = {
            'thresholdState': [threshold_state_data]}

    with context.session.begin(subtransactions=True):
        pm_threshold.update(context)


def make_threshold_notif_data(timestamp, threshold_state,
                              endpoint, pm_threshold):

    notif_data = objects.ThresholdCrossedNotificationV2(
        id=uuidutils.generate_uuid(),
        notificationType="ThresholdCrossedNotification",
        timeStamp=timestamp,
        thresholdId=pm_threshold.id,
        crossingDirection=threshold_state['crossingDirection'],
        objectType=pm_threshold.objectType,
        objectInstanceId=pm_threshold.objectInstanceId,
        subObjectInstanceId=threshold_state['subObjectInstanceId'],
        performanceMetric=threshold_state['metrics'],
        performanceValue=threshold_state['performanceValue'],
        _links=objects.ThresholdCrossedNotificationV2_Links(
            objectInstance=objects.NotificationLink(
                href=inst_utils.inst_href(
                    pm_threshold.objectInstanceId, endpoint)
            ),
            threshold=objects.NotificationLink(
                href=pm_threshold_href(
                    pm_threshold.id, endpoint)
            )
        )
    )
    if threshold_state['subObjectInstanceId']:
        notif_data.subObjectInstanceId = threshold_state['subObjectInstanceId']
    return notif_data
