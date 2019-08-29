# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import abc
import six

from tacker._i18n import _
from tacker.common import exceptions
from tacker.services import service_base


@six.add_metaclass(abc.ABCMeta)
class NSPluginBase(service_base.NFVPluginBase):

    @abc.abstractmethod
    def create_nsd(self, context, nsd):
        pass

    @abc.abstractmethod
    def delete_nsd(self, context, nsd_id):
        pass

    @abc.abstractmethod
    def get_nsd(self, context, nsd_id, fields=None):
        pass

    @abc.abstractmethod
    def get_nsds(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def create_ns(self, context, ns):
        pass

    @abc.abstractmethod
    def get_nss(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_ns(self, context, ns_id, fields=None):
        pass

    @abc.abstractmethod
    def delete_ns(self, context, ns_id):
        pass


class NSDNotFound(exceptions.NotFound):
    message = _('NSD %(nsd_id)s could not be found')


class NSNotFound(exceptions.NotFound):
    message = _('NS %(ns_id)s could not be found')


class NSInUse(exceptions.InUse):
    message = _('NS %(ns_id)s in use')
