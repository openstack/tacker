# Copyright 2013, 2014 Intel Corporation.
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
#

from oslo_log import log as logging

import stevedore.named

from tacker._i18n import _

LOG = logging.getLogger(__name__)


class DriverManager(object):
    def __init__(self, namespace, driver_list, **kwargs):
        super(DriverManager, self).__init__()
        manager = stevedore.named.NamedExtensionManager(
            namespace, driver_list, invoke_on_load=True, **kwargs)

        drivers = {}
        for ext in manager:
            type_ = ext.obj.get_type()
            if type_ in drivers:
                msg = _("driver '%(new_driver)s' ignored because "
                        "driver '%(old_driver)s' is already "
                        "registered for driver '%(type)s'") % {
                            'new_driver': ext.name,
                            'old_driver': drivers[type].name,
                            'type': type_}
                LOG.error(msg)
                raise SystemExit(msg)
            drivers[type_] = ext
        self._drivers = dict((type_, ext.obj)
                             for (type_, ext) in drivers.items())
        LOG.info("Registered drivers from %(namespace)s: %(keys)s",
                 {'namespace': namespace, 'keys': self._drivers.keys()})

    @staticmethod
    def _driver_name(driver):
        return driver.__module__ + '.' + driver.__class__.__name__

    def register(self, type_, driver):
        if type_ in self._drivers:
            new_driver = self._driver_name(driver)
            old_driver = self._driver_name(self._drivers[type_])
            msg = _("can't load driver '%(new_driver)s' because "
                    "driver '%(old_driver)s' is already "
                    "registered for driver '%(type)s'") % {
                        'new_driver': new_driver,
                        'old_driver': old_driver,
                        'type': type_}
            LOG.error(msg)
            raise SystemExit(msg)
        self._drivers[type_] = driver

    def invoke(self, type_, method_name, **kwargs):
        driver = self._drivers[type_]
        return getattr(driver, method_name)(**kwargs)

    def __getitem__(self, type_):
        return self._drivers[type_]

    def __contains__(self, type_):
        return type_ in self._drivers
