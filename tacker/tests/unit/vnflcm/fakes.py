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


import datetime
import iso8601
import os
import webob

from tacker.api.vnflcm.v1.router import VnflcmAPIRouter
from tacker import context
from tacker.db.db_sqlalchemy import models
from tacker.objects import fields
from tacker.tests import constants
from tacker.tests import uuidsentinel
from tacker import wsgi


def fake_vnf_package_vnfd_model_dict(**updates):
    vnfd = {
        'package_uuid': uuidsentinel.package_uuid,
        'deleted': False,
        'deleted_at': None,
        'updated_at': None,
        'created_at': datetime.datetime(2020, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC),
        'vnf_product_name': 'Sample VNF',
        'vnf_provider': 'test vnf provider',
        'vnf_software_version': '1.0',
        'vnfd_id': uuidsentinel.vnfd_id,
        'vnfd_version': '1.0',
        'id': constants.UUID,
    }

    if updates:
        vnfd.update(updates)

    return vnfd


def return_vnf_package_vnfd():
    model_obj = models.VnfPackageVnfd()
    model_obj.update(fake_vnf_package_vnfd_model_dict())
    return model_obj


def _model_non_instantiated_vnf_instance(**updates):
    vnf_instance = {
        'created_at': datetime.datetime(2020, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC),
        'deleted': False,
        'deleted_at': None,
        'id': uuidsentinel.vnf_instance_id,
        'instantiated_vnf_info': None,
        'instantiation_state': fields.VnfInstanceState.NOT_INSTANTIATED,
        'updated_at': None,
        'vim_connection_info': [],
        'vnf_instance_description': 'Vnf instance description',
        'vnf_instance_name': 'Vnf instance name',
        'vnf_product_name': 'Sample VNF',
        'vnf_provider': 'Vnf provider',
        'vnf_software_version': '1.0',
        'tenant_id': uuidsentinel.tenant_id,
        'vnfd_id': uuidsentinel.vnfd_id,
        'vnfd_version': '1.0'}

    if updates:
        vnf_instance.update(**updates)

    return vnf_instance


def return_vnf_instance_model(
        instantiated_state=fields.VnfInstanceState.NOT_INSTANTIATED,
        **updates):

    model_obj = models.VnfInstance()

    if instantiated_state == fields.VnfInstanceState.NOT_INSTANTIATED:
        model_obj.update(_model_non_instantiated_vnf_instance(**updates))

    return model_obj


def fake_vnf_instance_response(**updates):
    vnf_instance = {
        'vnfInstanceDescription': 'Vnf instance description',
        'vnfInstanceName': 'Vnf instance name',
        'vnfProductName': 'Sample VNF',
        '_links': {
            'self': {'href': os.path.join('/vnflcm/v1/vnf_instances/',
                uuidsentinel.vnf_instance_id)},
            'instantiate': {
                'href': os.path.join('/vnflcm/v1/vnf_instances',
                    uuidsentinel.vnf_instance_id, 'instantiate')
            }
        },
        'instantiationState': 'NOT_INSTANTIATED',
        'vnfProvider': 'Vnf provider',
        'vnfdId': uuidsentinel.vnfd_id,
        'vnfdVersion': '1.0',
        'vnfSoftwareVersion': '1.0',
        'id': uuidsentinel.vnf_instance_id
    }

    if updates:
        vnf_instance.update(**updates)

    return vnf_instance


class InjectContext(wsgi.Middleware):
    """Add a 'tacker.context' to WSGI environ."""

    def __init__(self, context, *args, **kwargs):
        self.context = context
        super(InjectContext, self).__init__(*args, **kwargs)

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        req.environ['tacker.context'] = self.context
        return self.application


def wsgi_app_v1(fake_auth_context=None):
    inner_app_v1 = VnflcmAPIRouter()
    if fake_auth_context is not None:
        ctxt = fake_auth_context
    else:
        ctxt = context.ContextBase(uuidsentinel.user_id,
                                   uuidsentinel.project_id, is_admin=True)
    api_v1 = InjectContext(ctxt, inner_app_v1)
    return api_v1
