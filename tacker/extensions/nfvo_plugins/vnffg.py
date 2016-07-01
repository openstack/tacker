# Copyright 2016 Red Hat Inc
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

import abc
import six

from tacker.services import service_base


@six.add_metaclass(abc.ABCMeta)
class VNFFGPluginBase(service_base.NFVPluginBase):

    @abc.abstractmethod
    def create_vnffgd(self, context, vnffgd):
        pass

    @abc.abstractmethod
    def delete_vnffgd(self, context, vnffgd_id):
        pass

    @abc.abstractmethod
    def get_vnffgd(self, context, vnffgd_id, fields=None):
        pass

    @abc.abstractmethod
    def get_vnffgds(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def create_vnffg(self, context, vnffg):
        pass

    @abc.abstractmethod
    def get_vnffgs(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_vnffg(self, context, vnffg_id, fields=None):
        pass

    @abc.abstractmethod
    def update_vnffg(self, context, vnffg_id, vnffg):
        pass

    @abc.abstractmethod
    def delete_vnffg(self, context, vnffg_id):
        pass

    @abc.abstractmethod
    def get_nfp(self, context, nfp_id, fields=None):
        pass

    @abc.abstractmethod
    def get_nfps(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_sfcs(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_sfc(self, context, sfc_id, fields=None):
        pass

    @abc.abstractmethod
    def get_classifiers(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_classifier(self, context, classifier_id, fields=None):
        pass
