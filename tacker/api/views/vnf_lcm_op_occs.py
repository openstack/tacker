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

from tacker.api import views as base
from tacker.common import utils
import tacker.conf
from tacker.objects import vnf_lcm_op_occs as _vnf_lcm_op_occs

CONF = tacker.conf.CONF

LOG = logging.getLogger(__name__)


class ViewBuilder(base.BaseViewBuilder):

    FLATTEN_ATTRIBUTES = _vnf_lcm_op_occs.VnfLcmOpOcc.FLATTEN_ATTRIBUTES
    COMPLEX_ATTRIBUTES = _vnf_lcm_op_occs.VnfLcmOpOcc.COMPLEX_ATTRIBUTES
    FLATTEN_COMPLEX_ATTRIBUTES = [key for key in FLATTEN_ATTRIBUTES.keys()
        if '/' in key]

    def _get_lcm_op_occs_links(self, vnf_lcm_op_occs):
        _links = {
            "self": {
                "href":
                '{endpoint}/vnflcm/v1/vnf_lcm_op_occs/{id}'.format(
                    endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                    id=vnf_lcm_op_occs.id)
            },
            "vnfInstance": {
                "href":
                '{endpoint}/vnflcm/v1/vnf_instances/{id}'.format(
                    endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                    id=vnf_lcm_op_occs.vnf_instance_id)
            },
            "retry": {
                "href":
                '{endpoint}/vnflcm/v1/vnf_lcm_op_occs/{id}/retry'.
                format(
                    endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                    id=vnf_lcm_op_occs.id)
            },
            "rollback": {
                "href":
                '{endpoint}/vnflcm/v1/vnf_lcm_op_occs/{id}/rollback'.
                format(
                    endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                    id=vnf_lcm_op_occs.id)
            },
            "grant": {
                "href":
                '{endpoint}/vnflcm/v1/vnf_lcm_op_occs/{id}/grant'.
                format(
                    endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                    id=vnf_lcm_op_occs.id)
            },
            "fail": {
                "href":
                '{endpoint}/vnflcm/v1/vnf_lcm_op_occs/{id}/fail'.
                format(
                    endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                    id=vnf_lcm_op_occs.id)
            }
        }

        return {"_links": _links}

    def _get_vnf_lcm_op_occs_list(self, vnf_lcm_op_occs, include_fields=None):
        vnf_lcm_op_occs_dict = vnf_lcm_op_occs.to_dict(
            include_fields=include_fields)

        vnf_lcm_op_occs_dict = utils.convert_snakecase_to_camelcase(
            vnf_lcm_op_occs_dict)
        vnf_lcm_op_occs_dict.pop('errorPoint', None)

        links = self._get_lcm_op_occs_links(vnf_lcm_op_occs)

        vnf_lcm_op_occs_dict.update(links)
        return vnf_lcm_op_occs_dict

    def index(self, request, vnf_lcm_op_occs, all_fields=True,
             exclude_fields=None, fields=None, exclude_default=False):

        # Find out which fields are to be returned in the response.
        if all_fields:
            include_fields = set(self.FLATTEN_ATTRIBUTES.keys())
        if fields:
            fields = set(fields.split(','))
            attributes = set(self.COMPLEX_ATTRIBUTES).intersection(fields)
            for attribute in attributes:
                add_fields = set([key for key in self.FLATTEN_ATTRIBUTES.
                    keys() if key.startswith(attribute)])
                fields = fields.union(add_fields)

            include_fields = set(
                _vnf_lcm_op_occs.VnfLcmOpOcc.SIMPLE_ATTRIBUTES).union(fields)
        elif exclude_default:
            include_fields = set(
                _vnf_lcm_op_occs.VnfLcmOpOcc.SIMPLE_ATTRIBUTES)
        elif exclude_fields:
            exclude_fields = set(exclude_fields.split(','))
            exclude_additional_attributes = set(
                self.COMPLEX_ATTRIBUTES).intersection(exclude_fields)
            for attribute in exclude_additional_attributes:
                fields = set([key for key in self.FLATTEN_ATTRIBUTES.keys()
                    if key.startswith(attribute)])
                exclude_fields = exclude_fields.union(fields)

            include_fields = set(self.FLATTEN_ATTRIBUTES.keys()) - \
                exclude_fields

        return [
            self._get_vnf_lcm_op_occs_list(
                vnf_lcm_op_occ, include_fields=include_fields)
            for vnf_lcm_op_occ in vnf_lcm_op_occs]
