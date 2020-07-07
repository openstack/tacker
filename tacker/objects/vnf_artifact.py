#    Copyright 2020 NTT DATA.
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
from oslo_versionedobjects import base as ovoo_base
from tacker._i18n import _
from tacker.common import exceptions
from tacker.common import utils
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker.objects import base
from tacker.objects import fields

LOG = logging.getLogger(__name__)


@db_api.context_manager.writer
def _vnf_artifacts_create(context, values):
    vnf_artifacts = models.VnfPackageArtifactInfo()

    vnf_artifacts.update(values)
    vnf_artifacts.save(context.session)

    return vnf_artifacts


@db_api.context_manager.reader
def _vnf_artifact_get_by_id(context, id):

    query = api.model_query(context, models.VnfPackageArtifactInfo,
                            read_deleted="no").filter_by(id=id)

    result = query.first()

    if not result:
        raise exceptions.VnfArtifactNotFound(id=id)

    return result


@base.TackerObjectRegistry.register
class VnfPackageArtifactInfo(base.TackerObject, base.TackerPersistentObject):
    ALL_ATTRIBUTES = {
        "additionalArtifacts": {
            'artifactPath': ('artifact_path', 'string',
                             'VnfPackageArtifactInfo'),
            'metadata': ('_metadata', 'dict', 'VnfPackageArtifactInfo'),
            "checksum": {
                'hash': ('hash', 'string', 'VnfPackageArtifactInfo'),
                'algorithm': ('algorithm', 'string', 'VnfPackageArtifactInfo')
            }
        }
    }

    FLATTEN_ATTRIBUTES = utils.flatten_dict(ALL_ATTRIBUTES.copy())
    SIMPLE_ATTRIBUTES = ['artifactPath']
    COMPLEX_ATTRIBUTES = [
        'additionalArtifacts',
        'additionalArtifacts/metadata',
        'additionalArtifacts/checksum']

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'package_uuid': fields.UUIDField(nullable=False),
        'artifact_path': fields.StringField(nullable=False),
        'algorithm': fields.StringField(nullable=False),
        'hash': fields.StringField(nullable=False),
        '_metadata': fields.DictOfStringsField(nullable=True, default={})
    }

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        db_artifact = _vnf_artifact_get_by_id(context, id)
        return cls._from_db_object(context, cls(), db_artifact)

    @staticmethod
    def _from_db_object(context, vnf_artifacts, db_vnf_artifacts):

        for key in vnf_artifacts.fields:
            setattr(vnf_artifacts, key, db_vnf_artifacts[key])

        vnf_artifacts._context = context
        vnf_artifacts.obj_reset_changes()

        return vnf_artifacts

    def obj_load_attr(self, attrname):
        if not self._context:
            raise exceptions.OrphanedObjectError(
                method='obj_load_attr', objtype=self.obj_name())
        if 'id' not in self:
            raise exceptions.ObjectActionError(
                action='obj_load_attr',
                reason=_('attribute %s not lazy-loadable') % attrname)

        LOG.debug("Lazy-loading '%(attr)s' on %(name)s id %(id)s",
                  {'attr': attrname,
                   'name': self.obj_name(),
                   'id': self.id,
                   })

        self._obj_load_attr(attrname)

    def _obj_load_attr(self, attrname):

        if attrname in self.fields and attrname != 'id':
            self._load_generic(attrname)
        else:
            # NOTE(nirajsingh): Raise error if non existing field is
            # requested.
            raise exceptions.ObjectActionError(
                action='obj_load_attr',
                reason=_('attribute %s not lazy-loadable') % attrname)

        self.obj_reset_changes([attrname])

    def _load_generic(self, attrname):
        artifact = self.__class__.get_by_id(self._context,
                                            id=self.id)
        if attrname not in artifact:
            raise exceptions.ObjectActionError(
                action='obj_load_attr',
                reason=_('loading %s requires recursion') % attrname)

        for field in self.fields:
            if field in artifact and field not in self:
                setattr(self, field, getattr(artifact, field))

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exceptions.ObjectActionError(action='create',
                                               reason=_('already created'))

        updates = self.obj_get_changes()
        db_vnf_artifacts = _vnf_artifacts_create(
            self._context, updates)
        self._from_db_object(self._context, self, db_vnf_artifacts)

    def to_dict(self, include_fields=None):
        response = dict()
        fields = ['additionalArtifacts/%s' % attribute for attribute in
            self.SIMPLE_ATTRIBUTES]

        to_fields = set(fields).intersection(include_fields)
        for field in to_fields:
            display_field = field.split("/")[-1]
            response[display_field] = getattr(
                self, self.FLATTEN_ATTRIBUTES[field][0])

        to_fields = set([key for key in self.FLATTEN_ATTRIBUTES.keys()
            if key.startswith('additionalArtifacts/checksum')])
        checksum = dict()
        to_fields = to_fields.intersection(include_fields)
        for field in to_fields:
            display_field = field.split("/")[-1]
            checksum[display_field] = getattr(
                self, self.FLATTEN_ATTRIBUTES[field][0])

        if checksum:
            response.update({"checksum": checksum})

        metadata = dict()
        to_fields = set(['additionalArtifacts/metadata']).\
            intersection(include_fields)
        if to_fields:
            metadata_json = \
                getattr(self, self.
                        FLATTEN_ATTRIBUTES['additionalArtifacts/metadata'][0])
            if metadata_json is not None:
                metadata.update(metadata_json)

            response.update({"metadata": metadata})

        return response


@base.TackerObjectRegistry.register
class VnfPackageArtifactInfoList(ovoo_base.ObjectListBase, base.TackerObject):
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('VnfPackageArtifactInfo')
    }

    def to_dict(self, include_fields=None):
        artifactList = list()
        for artifact in self.objects:
            arti_dict = artifact.to_dict(include_fields)

            if arti_dict:
                artifactList.append(arti_dict)

        return artifactList
