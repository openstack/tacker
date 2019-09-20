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

import os

import glance_store
from glance_store import exceptions as store_exceptions
from oslo_log import log as logging
from oslo_utils import encodeutils
from oslo_utils import units
from six.moves import urllib

from tacker.common import exceptions
from tacker.common import utils
import tacker.conf


CONF = tacker.conf.CONF
LOG = logging.getLogger(__name__)


def initialize_glance_store():
    """Initialize glance store."""
    glance_store.create_stores(CONF)
    glance_store.verify_default_store()


def get_csar_data_iter(body):
    try:
        if isinstance(body, dict):
            url = body['address_information']
            data_iter = urllib.request.urlopen(url)
        else:
            data_iter = body

        return data_iter
    except Exception:
        LOG.warn("Failed to open csar URL: %s", url)
        raise exceptions.VNFPackageURLInvalid(url=url)


def store_csar(context, package_uuid, body):

    data_iter = get_csar_data_iter(body)

    try:
        # store CSAR file in glance_store
        (location, size, checksum, multihash,
         loc_meta) = glance_store.add_to_backend_with_multihash(
            CONF, package_uuid,
            utils.LimitingReader(
                utils.CooperativeReader(data_iter),
                CONF.vnf_package.csar_file_size_cap * units.Gi),
            0,
            CONF.vnf_package.hashing_algorithm,
            context=context)
    except Exception as e:
        error = encodeutils.exception_to_unicode(e)
        LOG.warn("Failed to store csar data in glance store for "
                 "package %(uuid)s due to error: %(error)s",
                 {"uuid": package_uuid,
                 "error": error})
        raise exceptions.UploadFailedToGlanceStore(uuid=package_uuid,
                                                   error=error)
    finally:
        if hasattr(data_iter, 'close'):
            data_iter.close()

    return location, size, checksum, multihash, loc_meta


def delete_csar(context, package_uuid, location):

    try:
        glance_store.delete_from_backend(location, context)
    except store_exceptions.NotFound:
        LOG.info("Failed to find csar data in glance store for "
                 "package %(uuid)s",
                 {"uuid": package_uuid})


def load_csar(package_uuid, location):
    zip_path = os.path.join(CONF.vnf_package.vnf_package_csar_path,
                            package_uuid + ".zip")

    try:
        resp, size = glance_store.backend.get_from_backend(location)
    except Exception as exp:
        LOG.info("Failed to get csar data from glance store %(location)s for "
                 "package %(uuid)s",
                 {"location": location, "uuid": package_uuid})

    try:
        temp_data = open(zip_path, 'wb')
        for chunk in resp:
            temp_data.write(chunk)
        temp_data.close()
    except Exception as exp:
        LOG.exception("Exception encountered while tee'ing "
                      "csar '%(package_uuid)s' into csar path %(zip_path)s:"
                      "%(error)s. ", {'package_uuid': package_uuid,
                       'zip_path': zip_path,
                       'error': encodeutils.exception_to_unicode(exp)})

    return zip_path
