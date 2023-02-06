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

from importlib import import_module
from oslo_log import log as logging

from tacker.sol_refactored.common import exceptions as sol_ex

LOG = logging.getLogger(__name__)


def get_class(package_name, class_name):
    module = import_module(package_name)
    _class = getattr(module, class_name)
    if not issubclass(_class, MonitoringPlugin):
        LOG.error(f"Loading plugin failed: {package_name}.{class_name}.")
        raise sol_ex.MonitoringPluginClassError(class_name=class_name)
    return _class


class MonitoringPlugin():
    @staticmethod
    def get_instance(_class):
        return _class.instance()

    def set_callback(self, notification_callback):
        pass

    def create_job(self, **kwargs):
        pass

    def create_threshold(self, **kwargs):
        pass

    def delete_job(self, **kwargs):
        pass

    def delete_threshold(self, **kwargs):
        pass

    def alert(self, **kwargs):
        pass


class MonitoringPluginStub(MonitoringPlugin):
    _instance = None

    @staticmethod
    def instance():
        if not MonitoringPluginStub._instance:
            MonitoringPluginStub()
        return MonitoringPluginStub._instance

    def __init__(self):
        if MonitoringPluginStub._instance:
            raise SystemError(
                "Not constructor but instance() should be used.")
        MonitoringPluginStub._instance = self
