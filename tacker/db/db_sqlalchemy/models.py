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
import sqlalchemy as sa
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


class VnfPackageVnfd(model_base.BASE, models.SoftDeleteMixin,
                  models.TimestampMixin, models_v1.HasId):
    """Contains all info about vnf packages VNFD."""

    __tablename__ = 'vnf_package_vnfd'
    package_uuid = sa.Column(sa.String(36),
                             sa.ForeignKey('vnf_packages.id'),
                             nullable=False)
    vnfd_id = sa.Column(types.Uuid, nullable=False)
    vnf_provider = sa.Column(sa.String(255), nullable=False)
    vnf_product_name = sa.Column(sa.String(255), nullable=False)
    vnf_software_version = sa.Column(sa.String(255), nullable=False)
    vnfd_version = sa.Column(sa.String(255), nullable=False)


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

    @property
    def metadetails(self):
        return {m.key: m.value for m in self._metadata}
