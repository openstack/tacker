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
from oslo_versionedobjects import base as ovoo_base
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.vnfm import vnfm_db
from tacker.objects import base
from tacker.objects import fields

LOG = logging.getLogger(__name__)


def _vnf_update(context, values):
    update = {'status': values.status,
              'updated_at': values.updated_at}

    api.model_query(context, vnfm_db.VNF). \
        filter_by(id=values.id). \
        update(update, synchronize_session=False)


@db_api.context_manager.reader
def _vnf_get(context, id, columns_to_join=None):
    vnf_data = api.model_query(
        context,
        vnfm_db.VNF).filter_by(
        id=id).filter_by(
            deleted_at='0001-01-01 00:00:00').first()
    if vnf_data:
        vnf_data = vnf_data.__dict__
        vnf_attribute_data = api.model_query(
            context, vnfm_db.VNFAttribute).filter_by(
            vnf_id=vnf_data.get('id')).first()
        vnf_data['vnf_attribute'] = vnf_attribute_data.__dict__
        vnfd_data = api.model_query(
            context, vnfm_db.VNFD).filter_by(
            id=vnf_data.get('vnfd_id')).first()
        vnf_data['vnfd'] = vnfd_data.__dict__
        vnfd_attribute_data = api.model_query(
            context, vnfm_db.VNFDAttribute).filter_by(
            vnfd_id=vnf_data.get('vnfd_id')).first()
        vnf_data['vnfd_attribute'] = vnfd_attribute_data.__dict__
    else:
        vnf_data = ""

    return vnf_data


@base.TackerObjectRegistry.register
class VNF(base.TackerObject, base.TackerObjectDictCompat,
          base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'tenant_id': fields.UUIDField(nullable=False),
        'name': fields.StringField(nullable=False),
        'vnfd_id': fields.UUIDField(nullable=False),
        'instance_id': fields.StringField(nullable=True),
        'mgmt_ip_address': fields.StringField(nullable=True),
        'status': fields.StringField(nullable=True),
        'description': fields.StringField(nullable=True),
        'placement_attr': fields.StringField(nullable=True),
        'vim_id': fields.StringField(nullable=False),
        'error_reason': fields.StringField(nullable=True),
        'vnf_attribute': fields.ObjectField(
            'VNFAttribute', nullable=True),
        'vnfd': fields.ObjectField('VNFD', nullable=True),
    }

    @base.remotable
    def save(self):
        updates = self.obj_clone()
        _vnf_update(self._context, updates)

    @base.remotable_classmethod
    def vnf_index_list(cls, id, context):
        # get vnf_instance data
        expected_attrs = ["vnf_attribute", "vnfd"]
        db_vnf = _vnf_get(context, id, columns_to_join=expected_attrs)
        return db_vnf


@base.TackerObjectRegistry.register
class VnfList(ovoo_base.ObjectListBase, base.TackerObject):

    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('VNF')
    }

    @base.remotable_classmethod
    def vnf_index_list(cls, id, context):
        # get vnf_instance data
        expected_attrs = ["vnf_attribute", "vnfd"]
        db_vnf = _vnf_get(context, id, columns_to_join=expected_attrs)
        return db_vnf
