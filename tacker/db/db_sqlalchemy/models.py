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

from oslo_db.sqlalchemy import models
from oslo_utils import timeutils
import sqlalchemy as sa
from sqlalchemy import DateTime
from sqlalchemy import orm

from tacker.db import model_base
from tacker.db import models_v1
from tacker.db import types


class VnfPackageUserData(model_base.BASE, models.SoftDeleteMixin,
                         models.TimestampMixin):
    """Contains all info about vnf packages UserDefinedData."""

    __tablename__ = 'vnf_packages_user_data'
    id = sa.Column(sa.Integer, nullable=False, primary_key=True)
    package_uuid = sa.Column(sa.String(36),
                             sa.ForeignKey('vnf_packages.id'),
                             nullable=False)
    key = sa.Column(sa.String(255), nullable=False)
    value = sa.Column(sa.String(255), nullable=False)


class VnfSoftwareImageMetadata(model_base.BASE, models.SoftDeleteMixin,
                               models.TimestampMixin):
    """Contains all info about vnf packages software image metadata."""

    __tablename__ = 'vnf_software_image_metadata'
    id = sa.Column(sa.Integer, nullable=False, primary_key=True)
    image_uuid = sa.Column(sa.String(36),
                           sa.ForeignKey('vnf_software_images.id'),
                           nullable=False)
    key = sa.Column(sa.String(255), nullable=False)
    value = sa.Column(sa.String(255), nullable=False)


class VnfSoftwareImage(model_base.BASE, models.SoftDeleteMixin,
                       models.TimestampMixin, models_v1.HasId):
    """Contains all info about vnf packages software images."""

    __tablename__ = 'vnf_software_images'
    software_image_id = sa.Column(sa.Integer, nullable=False)
    flavour_uuid = sa.Column(sa.String(36), sa.ForeignKey(
        'vnf_deployment_flavours.id'), nullable=False)
    name = sa.Column(sa.String(255), nullable=True)
    provider = sa.Column(sa.String(255), nullable=True)
    version = sa.Column(sa.String(255), nullable=True)
    algorithm = sa.Column(sa.String(64), nullable=True)
    hash = sa.Column(sa.String(128), nullable=True)
    container_format = sa.Column(sa.String(20), nullable=True)
    disk_format = sa.Column(sa.String(20), nullable=True)
    min_disk = sa.Column(sa.Integer, nullable=False)
    min_ram = sa.Column(sa.Integer, nullable=False)
    size = sa.Column(sa.BigInteger, nullable=False)
    image_path = sa.Column(sa.Text, nullable=False)

    _metadata = orm.relationship(
        VnfSoftwareImageMetadata,
        primaryjoin='and_(VnfSoftwareImage.id == '
                    'VnfSoftwareImageMetadata.image_uuid)')

    @property
    def metadetails(self):
        return {m.key: m.value for m in self._metadata}


class VnfArtifactMetadata(model_base.BASE, models.SoftDeleteMixin,
                          models.TimestampMixin):
    """Contains all info about vnf packages artifacts metadata."""

    __tablename__ = 'vnf_artifact_metadata'
    id = sa.Column(sa.Integer, nullable=False, primary_key=True)
    artifact_uuid = sa.Column(sa.String(36),
                              sa.ForeignKey('vnf_artifacts.id'),
                              nullable=False)
    key = sa.Column(sa.String(255), nullable=False)
    value = sa.Column(sa.String(255), nullable=False)


class VnfDeploymentFlavour(model_base.BASE, models.SoftDeleteMixin,
                models.TimestampMixin, models_v1.HasId):
    """Contains all info about vnf packages Deployment Flavours."""

    __tablename__ = 'vnf_deployment_flavours'
    package_uuid = sa.Column(sa.String(36),
                             sa.ForeignKey('vnf_packages.id'),
                             nullable=False)
    flavour_id = sa.Column(sa.String(255), nullable=False)
    flavour_description = sa.Column(sa.Text(), nullable=False)
    instantiation_levels = sa.Column(sa.Text(), nullable=True)

    software_images = orm.relationship(
        VnfSoftwareImage, primaryjoin='and_(VnfDeploymentFlavour.id == '
                                      'VnfSoftwareImage.flavour_uuid,'
                                      'VnfSoftwareImage.deleted == 0)')


class VnfPackageVnfdSoftDeleteMixin(object):
    deleted_at = sa.Column(DateTime)
    deleted = sa.Column(sa.String(36), default='0')

    def soft_delete(self, session):
        """Mark this object as deleted."""
        self.deleted = self.id
        self.deleted_at = timeutils.utcnow()
        self.save(session=session)


class VnfPackageVnfd(model_base.BASE, VnfPackageVnfdSoftDeleteMixin,
                  models.TimestampMixin, models_v1.HasId):
    """Contains all info about vnf packages VNFD."""

    __tablename__ = 'vnf_package_vnfd'
    __table_args__ = (
        sa.schema.UniqueConstraint(
            "vnfd_id",
            "deleted",
            name="uniq_vnf_package_vnfd0vnfd_id0deleted"),
    )

    package_uuid = sa.Column(sa.String(36),
                             sa.ForeignKey('vnf_packages.id'),
                             nullable=False)
    vnfd_id = sa.Column(types.Uuid, nullable=False)
    vnf_provider = sa.Column(sa.String(255), nullable=False)
    vnf_product_name = sa.Column(sa.String(255), nullable=False)
    vnf_software_version = sa.Column(sa.String(255), nullable=False)
    vnfd_version = sa.Column(sa.String(255), nullable=False)


class VnfPackageArtifactInfo(model_base.BASE, models.SoftDeleteMixin,
                 models.TimestampMixin, models_v1.HasId):
    """Contains all info about vnf artifacts."""

    __tablename__ = 'vnf_artifacts'
    package_uuid = sa.Column(sa.String(36),
                             sa.ForeignKey('vnf_packages.id'),
                             nullable=False)
    artifact_path = sa.Column(sa.Text(), nullable=False)
    algorithm = sa.Column(sa.String(64), nullable=False)
    hash = sa.Column(sa.String(128), nullable=False)
    _metadata = sa.Column(sa.JSON(), nullable=True)


class VnfPackage(model_base.BASE, models.SoftDeleteMixin,
                 models.TimestampMixin, models_v1.HasTenant,
                 models_v1.HasId):
    """Contains all info about vnf packages."""

    __tablename__ = 'vnf_packages'
    onboarding_state = sa.Column(sa.String(255), nullable=False)
    operational_state = sa.Column(sa.String(255), nullable=False)
    usage_state = sa.Column(sa.String(255), nullable=False)
    algorithm = sa.Column(sa.String(64), nullable=True)
    hash = sa.Column(sa.String(128), nullable=True)
    location_glance_store = sa.Column(sa.Text(), nullable=True)
    size = sa.Column(sa.BigInteger, nullable=False, default=0)

    _metadata = orm.relationship(
        VnfPackageUserData,
        primaryjoin='and_(VnfPackage.id == '
                    'VnfPackageUserData.package_uuid)')

    vnf_deployment_flavours = orm.relationship(
        VnfDeploymentFlavour,
        primaryjoin='and_(VnfPackage.id == '
                    'VnfDeploymentFlavour.package_uuid,'
                    'VnfDeploymentFlavour.deleted == 0)')

    vnfd = orm.relationship(
        VnfPackageVnfd, uselist=False,
        primaryjoin='and_(VnfPackage.id == '
                    'VnfPackageVnfd.package_uuid,'
                    'VnfPackageVnfd.deleted == 0)')

    vnf_artifacts = orm.relationship(
        VnfPackageArtifactInfo,
        primaryjoin='and_(VnfPackage.id == '
                    'VnfPackageArtifactInfo.package_uuid,'
                    'VnfPackageArtifactInfo.deleted == 0)')

    @property
    def metadetails(self):
        return {m.key: m.value for m in self._metadata}


class VnfInstance(model_base.BASE, models.SoftDeleteMixin,
                models.TimestampMixin, models_v1.HasId):
    """Represents a Vnf Instance."""

    __tablename__ = 'vnf_instances'
    vnf_instance_name = sa.Column(sa.String(255), nullable=True)
    vnf_instance_description = sa.Column(sa.String(1024), nullable=True)
    vnf_provider = sa.Column(sa.String(255), nullable=False)
    vnf_product_name = sa.Column(sa.String(255), nullable=False)
    vnf_software_version = sa.Column(sa.String(255), nullable=False)
    vnfd_version = sa.Column(sa.String(255), nullable=False)
    vnfd_id = sa.Column(types.Uuid, nullable=False)
    instantiation_state = sa.Column(sa.String(255), nullable=False)
    task_state = sa.Column(sa.String(255), nullable=True)
    vim_connection_info = sa.Column(sa.JSON(), nullable=True)
    tenant_id = sa.Column('tenant_id', sa.String(length=64), nullable=False)
    vnf_pkg_id = sa.Column(types.Uuid, nullable=False)
    vnf_metadata = sa.Column(sa.JSON(), nullable=True)


class VnfInstantiatedInfo(model_base.BASE, models.SoftDeleteMixin,
                    models.TimestampMixin):
    """Contain the details of VNF instance"""

    __tablename__ = 'vnf_instantiated_info'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    vnf_instance_id = sa.Column(sa.String,
                            sa.ForeignKey('vnf_instances.id'),
                            nullable=False)
    flavour_id = sa.Column(sa.String(255), nullable=False)
    scale_status = sa.Column(sa.JSON(), nullable=True)
    ext_cp_info = sa.Column(sa.JSON(), nullable=False)
    ext_virtual_link_info = sa.Column(sa.JSON(), nullable=True)
    ext_managed_virtual_link_info = sa.Column(sa.JSON(), nullable=True)
    vnfc_resource_info = sa.Column(sa.JSON(), nullable=True)
    vnf_virtual_link_resource_info = sa.Column(sa.JSON(), nullable=True)
    virtual_storage_resource_info = sa.Column(sa.JSON(), nullable=True)
    vnfc_info = sa.Column(sa.JSON(), nullable=True)
    vnf_state = sa.Column(sa.String(255), nullable=False)
    instance_id = sa.Column(sa.Text(), nullable=True)
    instantiation_level_id = sa.Column(sa.String(255), nullable=True)
    additional_params = sa.Column(sa.JSON(), nullable=True)

    vnf_instance = orm.relationship(
        VnfInstance,
        backref=orm.backref(
            'instantiated_vnf_info',
            uselist=False),
        foreign_keys=vnf_instance_id,
        primaryjoin='and_(VnfInstantiatedInfo.vnf_instance_id == '
        'VnfInstance.id, VnfInstantiatedInfo.deleted == 0)')


class VnfResource(model_base.BASE, models.SoftDeleteMixin,
                models.TimestampMixin, models_v1.HasId):
    """Resources belongs to the VNF"""

    __tablename__ = 'vnf_resources'
    vnf_instance_id = sa.Column(sa.String(36),
                                sa.ForeignKey('vnf_instances.id'),
                                nullable=False)
    resource_name = sa.Column(sa.Text(), nullable=True)
    resource_type = sa.Column(sa.String(255), nullable=False)
    resource_identifier = sa.Column(sa.String(255), nullable=False)
    resource_status = sa.Column(sa.String(255), nullable=False)


class VnfLcmSubscriptions(model_base.BASE, models.SoftDeleteMixin,
                models.TimestampMixin):
    """Contains all info about vnf LCM Subscriptions."""

    __tablename__ = 'vnf_lcm_subscriptions'
    id = sa.Column(sa.String(36), nullable=False, primary_key=True)
    callback_uri = sa.Column(sa.String(255), nullable=False)
    subscription_authentication = sa.Column(sa.JSON, nullable=True)


class VnfLcmFilters(model_base.BASE):
    """Contains all info about vnf LCM filters."""

    __tablename__ = 'vnf_lcm_filters'
    __maxsize__ = 65536
    id = sa.Column(sa.Integer, nullable=True, primary_key=True)
    subscription_uuid = sa.Column(sa.String(36),
                            sa.ForeignKey('vnf_lcm_subscriptions.id'),
                            nullable=False)
    filter = sa.Column(sa.JSON, nullable=False)
    notification_types = sa.Column(sa.VARBINARY(255), nullable=True)
    notification_types_len = sa.Column(sa.Integer, nullable=True)
    operation_types = sa.Column(
        sa.LargeBinary(
            length=__maxsize__),
        nullable=True)
    operation_types_len = sa.Column(sa.Integer, nullable=True)


class VnfLcmOpOccs(model_base.BASE, models.SoftDeleteMixin,
                models.TimestampMixin):
    """VNF LCM OP OCCS Fields"""

    __tablename__ = 'vnf_lcm_op_occs'
    id = sa.Column(sa.String(16), primary_key=True)
    vnf_instance_id = sa.Column(sa.String(36),
                                sa.ForeignKey('vnf_instances.id'),
                                nullable=False)
    state_entered_time = sa.Column(sa.DateTime(), nullable=False)
    start_time = sa.Column(sa.DateTime(), nullable=False)
    operation_state = sa.Column(sa.String(length=255), nullable=False)
    operation = sa.Column(sa.String(length=255), nullable=False)
    is_automatic_invocation = sa.Column(sa.Boolean, nullable=False)
    operation_params = sa.Column(sa.JSON(), nullable=True)
    is_cancel_pending = sa.Column(sa.Boolean(), nullable=False)
    error = sa.Column(sa.JSON(), nullable=True)
    resource_changes = sa.Column(sa.JSON(), nullable=True)
    changed_info = sa.Column(sa.JSON(), nullable=True)
    error_point = sa.Column(sa.Integer, nullable=False)


class PlacementConstraint(model_base.BASE, models.SoftDeleteMixin,
                models.TimestampMixin, models_v1.HasId):
    """Represents a Vnf Placement Constraint."""

    __tablename__ = 'placement_constraint'
    vnf_instance_id = sa.Column(sa.String(36),
                                sa.ForeignKey('vnf_instances.id'),
                                nullable=False)
    affinity_or_anti_affinity = sa.Column(sa.String(255), nullable=False)
    scope = sa.Column(sa.String(255), nullable=False)
    server_group_name = sa.Column(sa.String(255), nullable=False)
    resource = sa.Column(sa.JSON(), nullable=True)
