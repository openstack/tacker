# Copyright (C) 2019 NTT DATA
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


import datetime
import iso8601
import webob

from tacker.api.vnfpkgm.v1.router import VnfpkgmAPIRouter
from tacker import context
from tacker.db.db_sqlalchemy import models
from tacker.objects import vnf_package as vnf_package_obj
from tacker.tests import constants
from tacker.tests import uuidsentinel
from tacker import wsgi


VNFPACKAGE_RESPONSE = {'_links': {
    'packageContent': {
        'href':
            '/vnfpkgm/v1/vnf_packages/'
            'f26f181d-7891-4720-b022-b074ec1733ef/package_content'},
    'self': {
        'href':
            '/vnfpkgm/v1/vnf_packages/'
            'f26f181d-7891-4720-b022-b074ec1733ef'},
},
    'id': 'f26f181d-7891-4720-b022-b074ec1733ef',
    'onboardingState': 'CREATED',
    'operationalState': 'DISABLED',
    'usageState': 'NOT_IN_USE',
    'userDefinedData': {'abc': 'xyz'}
}

VNFPACKAGE_INDEX_RESPONSE = {'vnf_packages': [{'_links': {
    'packageContent': {
        'href':
            '/vnfpkgm/v1/vnf_packages/'
            'f26f181d-7891-4720-b022-b074ec1733ef/package_content'},
    'self': {
        'href': '/vnfpkgm/v1/vnf_packages/'
                'f26f181d-7891-4720-b022-b074ec1733ef'}},
    'id': 'f26f181d-7891-4720-b022-b074ec1733ef',
    'onboardingState': 'CREATED',
    'operationalState': 'DISABLED',
    'usageState': 'NOT_IN_USE',
    'userDefinedData': {}}]
}


def fake_vnf_package(**updates):
    vnf_package = {
        'algorithm': None,
        'deleted': False,
        'deleted_at': None,
        'updated_at': None,
        'created_at': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC),
        'hash': None,
        'location_glance_store': None,
        'onboarding_state': 'CREATED',
        'operational_state': 'DISABLED',
        'tenant_id': uuidsentinel.tenant_id,
        'usage_state': 'NOT_IN_USE',
        'user_data': {'abc': 'xyz'},
        'id': constants.UUID,
    }

    if updates:
        vnf_package.update(updates)

    return vnf_package


class InjectContext(wsgi.Middleware):
    """Add a 'tacker.context' to WSGI environ."""

    def __init__(self, context, *args, **kwargs):
        self.context = context
        super(InjectContext, self).__init__(*args, **kwargs)

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        req.environ['tacker.context'] = self.context
        return self.application


def return_vnf_package():
    model_obj = models.VnfPackage()
    model_obj.update(fake_vnf_package())
    return model_obj


def return_vnfpkg_obj():
    vnf_package = vnf_package_obj.VnfPackage._from_db_object(
        context, vnf_package_obj.VnfPackage(),
        return_vnf_package(), expected_attrs=None)
    return vnf_package


def return_vnf_package_list():
    vnf_package = return_vnfpkg_obj()
    return [vnf_package]


def wsgi_app_v1(fake_auth_context=None):
    inner_app_v1 = VnfpkgmAPIRouter()
    if fake_auth_context is not None:
        ctxt = fake_auth_context
    else:
        ctxt = context.ContextBase(uuidsentinel.user_id,
                                   uuidsentinel.project_id, is_admin=True)
    api_v1 = InjectContext(ctxt, inner_app_v1)
    return api_v1
