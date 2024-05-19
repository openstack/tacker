# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

from datetime import datetime
import re

from dateutil import parser

from oslo_log import log as logging

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import subscription_utils as subsc_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import vnf_instance
from tacker.sol_refactored.objects.v2 import vnf_lcm_op_occ


LOG = logging.getLogger(__name__)
CONF = config.CONF


class KeyAttribute(object):
    """A placeholder class for handling @key in filter attribute names"""

    def __str__(self):
        return "@key"


class FilterExpr(object):
    def __init__(self, op, attr, values):
        self.op = op
        self.attr = attr
        self.values = values

    def match_eq(self, val):
        return val == self.values[0]

    def match_neq(self, val):
        return val != self.values[0]

    def match_in(self, val):
        return val in self.values

    def match_nin(self, val):
        return val not in self.values

    def match_gt(self, val):
        return val > self.values[0]

    def match_gte(self, val):
        return val >= self.values[0]

    def match_lt(self, val):
        return val < self.values[0]

    def match_lte(self, val):
        return val <= self.values[0]

    def match_cont(self, val):
        for v in self.values:
            if v in val:
                return True
        return False

    def match_ncont(self, val):
        return not self.match_cont(val)

    def match(self, val):
        try:
            for a in self.attr:
                # NOTE(toshii): The attribute specified by "@key"
                # must be a dict, not a list of dicts. SOL013 isn't
                # very clear on this topic and the current implementation
                # doesn't support the latter.
                if isinstance(a, KeyAttribute):
                    val = list(val.keys())
                else:
                    val = val[a]
        except KeyError:
            LOG.debug("Attr %s not found in %s", self.attr, val)
            return False
        except (AttributeError, TypeError):
            raise sol_ex.InvalidAttributeFilter(
                sol_detail="AttrName %s is invalid" % '/'.join([
                    str(x) for x in self.attr]))
        # If not str, assume type conversion is already done.
        # Note: It is assumed that the type doesn't change between calls,
        # which can be problematic with KeyValuePairs.
        if isinstance(self.values[0], str):
            if isinstance(val, datetime):
                self.values[0] = parser.isoparse(self.values[0])
            elif isinstance(val, bool):
                if self.values[0] == 'true':
                    self.values[0] = True
                elif self.values[0] == 'false':
                    self.values[0] = False
                else:
                    raise sol_ex.InvalidAttributeFilter(
                        sol_detail="invalid value for boolean")
            elif isinstance(val, int):
                self.values = [int(v) for v in self.values]
            elif isinstance(val, float):
                self.values = [float(v) for v in self.values]

        # NOTE: This might not be SOL013 compliant when there are
        # multiple filters with a same attribute prefix.
        match_fn = getattr(self, "match_" + self.op)
        if isinstance(val, list):
            for v in val:
                if match_fn(v):
                    return True
            return False
        else:
            return match_fn(val)


class AttributeSelector(object):
    def __init__(self, default_exclude_list, all_fields=None, fields=None,
                 exclude_fields=None, exclude_default=None):
        self.exclude_fields = []
        self.fields = []
        if all_fields is not None:
            if fields is not None or exclude_fields is not None or \
               exclude_default is not None:
                raise sol_ex.InvalidAttributeSelector()
            # Nothing to do
        elif fields is not None:
            if exclude_fields is not None:
                raise sol_ex.InvalidAttributeSelector()
            self.fields = fields.split(',')
            if exclude_default is not None:
                self.exclude_fields = [v for v in default_exclude_list
                                       if v not in self.fields]
        elif exclude_fields is not None:
            if exclude_default is not None:
                raise sol_ex.InvalidAttributeSelector()
            self.exclude_fields = exclude_fields.split(',')
        else:
            self.exclude_fields = default_exclude_list

    def filter(self, obj, odict):
        deleted = {}
        if self.exclude_fields:
            excl_fields = self.exclude_fields
        else:
            if not self.fields:
                # Implies all_fields
                return odict
            excl_fields = [k for k in odict.keys() if k not in self.fields]

        for attr in excl_fields:
            klist = attr.split('/')

            # Check if the specified attribute has a lower cardinality bound
            # of 0. (SOL013 5.3.2.1)
            obj1 = obj
            for key in klist[:-1]:
                obj1 = getattr(obj1, key)
            if not obj1.fields[klist[-1]].nullable:
                continue

            val = odict
            deleted_ptr = deleted
            try:
                for i, k1 in enumerate(klist, start=1):
                    if i == len(klist):
                        deleted_ptr[k1] = val[k1]
                        del val[k1]
                    else:
                        val = val[k1]
                        if k1 not in deleted_ptr:
                            deleted_ptr[k1] = {}
                        deleted_ptr = deleted_ptr[k1]
            except (KeyError, TypeError):
                pass
        if not self.fields:
            return odict

        # Readd partial dictionary content
        for attr in self.fields:
            klist = attr.split('/')
            val = odict
            deleted_ptr = deleted
            try:
                for i, k1 in enumerate(klist, start=1):
                    if i == len(klist):
                        val[k1] = deleted_ptr[k1]
                    else:
                        if k1 not in val:
                            val[k1] = {}
                        val = val[k1]
                        deleted_ptr = deleted_ptr[k1]
            except KeyError:
                LOG.debug("Key %s not found in %s or %s", k1, val, deleted_ptr)
        return odict


class EnhanceAttributeSelector(object):
    def __init__(self, all_attrs, mandatory_attrs, default_exclude_attrs,
                 all_fields=None, fields=None, exclude_fields=None,
                 exclude_default=None):
        self.all_attrs = all_attrs
        self.return_attrs = set()
        self.exclude_fields = set()
        self.fields = set()
        self.extra_attrs = set()
        if all_fields is not None:
            if fields is not None or exclude_fields is not None or \
               exclude_default is not None:
                raise sol_ex.InvalidAttributeSelector()
            self.return_attrs = all_attrs.copy()
        elif fields is not None:
            if exclude_fields is not None:
                raise sol_ex.InvalidAttributeSelector()
            if exclude_default is not None:
                self.return_attrs = all_attrs - default_exclude_attrs
            else:
                self.return_attrs = mandatory_attrs.copy()
            for field in fields.split(','):
                if '/' in field:
                    self.fields.add(field)
                self.return_attrs.add(field.split('/')[0])
        elif exclude_fields is not None:
            if exclude_default is not None:
                raise sol_ex.InvalidAttributeSelector()
            self.return_attrs = all_attrs.copy()
            for field in exclude_fields.split(','):
                if '/' in field:
                    self.exclude_fields.add(field)
                else:
                    self.return_attrs.remove(field)
        else:
            self.return_attrs = all_attrs - default_exclude_attrs

    def add_extra_attrs(self, attrs):
        self.extra_attrs |= attrs - self.return_attrs

    def filter(self, odict):
        for attr in self.extra_attrs:
            if attr in odict:
                del odict[attr]

        for attr in self.exclude_fields:
            klist = attr.split('/')
            if len(klist) == 1:
                # not occur. just consistency check
                continue
            sub_dict = odict
            for key in klist[:-1]:
                sub_dict = sub_dict.get(key, {})
            if sub_dict.get(klist[-1]) is not None:
                del sub_dict[klist[-1]]

        saved = {}
        for attr in self.fields:
            klist = attr.split('/')
            if len(klist) == 1:
                # not occur. just consistency check
                continue
            if klist[0] not in saved:
                saved[klist[0]] = odict[klist[0]]
                del odict[klist[0]]

            # construct
            sub_dict = odict
            saved_sub_dict = saved
            # first check path is valid
            for key in klist[:-1]:
                saved_sub_dict = saved_sub_dict.get(key, {})
            val = saved_sub_dict.get(klist[-1])
            if val is None:
                continue
            for key in klist[:-1]:
                sub_dict = sub_dict.setdefault(key, {})
            sub_dict[klist[-1]] = val

        return odict


class BaseViewBuilder(object):
    value_regexp = r"([^',)]+|('[^']*')+)"
    value_re = re.compile(value_regexp)
    simpleFilterExpr_re = re.compile(r"\(([a-z]+),([^,]+)(," +
                                     value_regexp + r")+\)")
    tildeEscape_re = re.compile(r"~([1ab])")
    opOne = ['eq', 'neq', 'gt', 'gte', 'lt', 'lte']
    opMulti = ['in', 'nin', 'cont', 'ncont']

    def __init__(self, endpoint, page_size):
        self.endpoint = endpoint
        self.page_size = page_size

    def parse_attr(self, attr):
        def tilde_unescape(string):
            def repl(m):
                if m.group(1) == '1':
                    return '/'
                elif m.group(1) == 'a':
                    return ','
                elif m.group(1) == 'b':
                    return '@'

            if string == '@key':
                return KeyAttribute()
            s1 = self.tildeEscape_re.sub(repl, string)
            return re.sub('~0', '~', s1)

        attrs = attr.split('/')
        return [tilde_unescape(a) for a in attrs]

    def parse_values(self, values):
        loc = 0
        res = []
        while loc < len(values):
            if values[loc] != ",":
                LOG.debug("comma expected, %s at loc %d", values, loc)
                raise sol_ex.InvalidAttributeFilter(
                    sol_detail=("value parse error. comma expected, %s" %
                                values))
            loc += 1
            m = self.value_re.match(values[loc:])
            if m is None:
                LOG.error("value parse error, %s at loc %d", values, loc)
                raise sol_ex.InvalidAttributeFilter(
                    sol_detail="value parse error")
            loc += m.end()
            if m.group(0).startswith("'"):
                res.append(re.sub("''", "'", m.group(0)[1:-1]))
            else:
                res.append(m.group(0))
        return res

    def parse_filter(self, filter):
        """Implement SOL013 5.2 Attribute-based filtering"""

        if filter is None:
            return []

        loc = 0
        res = []
        while True:
            m = self.simpleFilterExpr_re.match(filter[loc:])
            if m is None:
                LOG.error("filter %s parse error at char %d", filter, loc)
                raise sol_ex.InvalidAttributeFilter(
                    sol_detail="filter parse error")
            op = m.group(1)
            if op not in self.opOne and op not in self.opMulti:
                raise sol_ex.InvalidAttributeFilter(
                    sol_detail=("Invalid op %s" % op))
            values = self.parse_values(
                filter[(loc + m.end(2)):(loc + m.end(3))])
            if len(values) > 1 and op not in self.opMulti:
                raise sol_ex.InvalidAttributeFilter(
                    sol_detail=("Only one value is allowed for op %s" % op))
            res.append(FilterExpr(op, self.parse_attr(m.group(2)), values))
            loc += m.end()
            if loc == len(filter):
                return res
            if filter[loc] != ';':
                LOG.error("filter %s parse error at char %d "
                          "(semicolon expected)", filter, loc)
                raise sol_ex.InvalidAttributeFilter(
                    sol_detail="filter parse error. semicolon expected.")
            loc += 1

    def parse_selector(self, req):
        """Implement SOL013 5.3 Attribute selectors"""
        params = {}
        for k in ['all_fields', 'fields', 'exclude_fields', 'exclude_default']:
            v = req.get(k)
            if v is not None:
                params[k] = v
        return AttributeSelector(self._EXCLUDE_DEFAULT, **params)

    def match_filters(self, val, filters):
        for f in filters:
            if not f.match(val):
                return False
        return True

    def parse_pager(self, request):
        """Implement SOL013 5.4 Handling of large query results"""
        marker = request.GET.get('nextpage_opaque_marker')
        req_url = request.url

        return Pager(marker, req_url, self.page_size)

    def parse_query_params(self, request):
        filters = self.parse_filter(request.GET.get('filter'))
        selector = self.parse_selector(request.GET)
        pager = self.parse_pager(request)

        return filters, selector, pager

    def _handle_pager(self, pager, resp_body):
        if pager.page_size == 0:
            pager.next_marker = None
            return resp_body

        if len(resp_body) > pager.page_size:
            resp_body = resp_body[:pager.page_size]
            pager.next_marker = resp_body[-1]["id"]
        else:
            pager.next_marker = None
        return resp_body

    def detail_list(self, values, filters, selector, pager):
        resp_body = [self.detail(v, selector) for v in values
                     if self.match_filters(v, filters)]
        return self._handle_pager(pager, resp_body)


class EnhanceViewBuilder(BaseViewBuilder):
    def parse_selector(self, req):
        """Implement SOL013 5.3 Attribute selectors"""
        params = {}
        for k in ['all_fields', 'fields', 'exclude_fields', 'exclude_default']:
            v = req.get(k)
            if v is not None:
                params[k] = v
        return EnhanceAttributeSelector(self._ALL, self._MANDATORY,
                                        self._EXCLUDE_DEFAULT, **params)

    def get_dict_all(self, context, filters, selector, pager):
        # calc db fields
        extra_attrs = set()
        db_filters = []
        rm_filters = []
        for item in filters:
            if item.attr[0] not in selector.all_attrs:
                # never match
                return []
            extra_attrs.add(item.attr[0])
            # NOTE: cont and ncont are not supported at the moment.
            if len(item.attr) == 1 and item.op not in ['cont', 'ncont']:
                if item.op in self.opOne:
                    db_filters.append(
                        (item.op, item.attr[0], item.values[0]))
                else:  # opMulti
                    db_filters.append(
                        (item.op, item.attr[0], item.values))
                rm_filters.append(item)
        for item in rm_filters:
            filters.remove(item)
        selector.add_extra_attrs(extra_attrs)
        attrs = selector.return_attrs | selector.extra_attrs
        limit = None
        if (pager.page_size > 0 and len(filters) == 0 and
                len(selector.extra_attrs) == 0):
            # short cut. set limit if no filtering need later.
            # NOTE: +1 to find there are more data
            limit = pager.page_size + 1
        if pager.marker:
            db_filters.append(('gt', 'id', pager.marker))

        return self.obj_cls.get_dict_all(context, attrs, db_filters, limit)

    def detail_dict_list(self, values, filters, selector, pager):
        if filters:
            resp_body = [self.detail_dict(v, selector) for v in values
                         if self.match_filters(v, filters)]
        else:
            # short cut a bit
            resp_body = [self.detail_dict(v, selector) for v in values]
        return self._handle_pager(pager, resp_body)


class InstanceViewBuilder(EnhanceViewBuilder):
    _ALL = {'id',
            'vnfInstanceName',
            'vnfInstanceDescription',
            'vnfdId',
            'vnfProvider',
            'vnfProductName',
            'vnfSoftwareVersion',
            'vnfdVersion',
            'instantiationState',
            'vnfConfigurableProperties',
            'vimConnectionInfo',
            'instantiatedVnfInfo',
            'metadata',
            'extensions'}
    _EXCLUDE_DEFAULT = {'vnfConfigurableProperties',
                        'vimConnectionInfo',
                        'instantiatedVnfInfo',
                        'metadata',
                        'extensions'}
    _MANDATORY = _ALL - _EXCLUDE_DEFAULT
    obj_cls = vnf_instance.VnfInstanceV2

    def parse_selector(self, request):
        selector = super().parse_selector(request)
        if config.CONF.oslo_policy.enhanced_tacker_policy:
            selector.add_extra_attrs({'vimConnectionInfo',
                                      'instantiatedVnfInfo'})
        return selector

    def detail(self, inst, selector=None):
        return self.detail_dict(inst.to_dict(), selector)

    def detail_dict(self, inst, selector):
        # NOTE: _links is not saved in DB.
        inst['_links'] = inst_utils.make_inst_links(inst, self.endpoint)

        if selector is not None:
            inst = selector.filter(inst)

        # remove credential data from vim_connection_info
        # see SOL003 4.4.1.6
        cred_data = ['password', 'bearer_token', 'client_secret']
        for vim_info in inst.get('vimConnectionInfo', {}).values():
            if 'accessInfo' in vim_info:
                for cred_key in cred_data:
                    if cred_key in vim_info['accessInfo']:
                        vim_info['accessInfo'].pop(cred_key)

        return inst


class LcmOpOccViewBuilder(EnhanceViewBuilder):
    _ALL = {'id',
            'operationState',
            'stateEnteredTime',
            'startTime',
            'vnfInstanceId',
            'grantId',
            'operation',
            'isAutomaticInvocation',
            'operationParams',
            'isCancelPending',
            'cancelMode',
            'error',
            'resourceChanges',
            'changedInfo',
            'changedExtConnectivity',
            'modificationsTriggeredByVnfPkgChange',
            'vnfSnapshotInfoId'}
    _EXCLUDE_DEFAULT = {'operationParams',
                        'error',
                        'resourceChanges',
                        'changedInfo',
                        'changedExtConnectivity'}
    _MANDATORY = _ALL - _EXCLUDE_DEFAULT
    obj_cls = vnf_lcm_op_occ.VnfLcmOpOccV2

    def _pop_cred(self, resp):
        op_param = resp.get('operationParams', {})
        cred_data = ['password', 'bearer_token', 'client_secret']
        for vim_info in op_param.get('vimConnectionInfo', {}).values():
            if 'accessInfo' in vim_info:
                for cred_key in cred_data:
                    if cred_key in vim_info['accessInfo']:
                        vim_info['accessInfo'].pop(cred_key)

        vdu_params = op_param.get('additionalParams', {}).get('vdu_params', [])
        for vdu_param in vdu_params:
            vnfc_data = ['old_vnfc_param', 'new_vnfc_param']
            for vnfc_key in vnfc_data:
                vnfc_param = vdu_param.get(vnfc_key, {})
                if vnfc_param:
                    if vnfc_param.get('password', None):
                        vnfc_param.pop('password')
                    auth = vnfc_param.get('authentication', {})
                    if auth.get('paramsBasic', {}).get('password', None):
                        vnfc_param['authentication']['paramsBasic'].pop(
                            'password')
                    if (auth.get('paramsOauth2ClientCredentials', {})
                            .get('clientPassword', None)):
                        (vnfc_param['authentication']
                         ['paramsOauth2ClientCredentials']
                         .pop('clientPassword'))

        changed_info = resp.get('changedInfo', {})
        for vim_info in changed_info.get('vimConnectionInfo', {}).values():
            for cred_key in cred_data:
                if cred_key in vim_info['accessInfo']:
                    vim_info['accessInfo'].pop(cred_key)

    def detail(self, lcmocc, selector=None):
        return self.detail_dict(lcmocc.to_dict(), selector)

    def detail_dict(self, lcmocc, selector):
        # NOTE: _links is not saved in DB.
        lcmocc['_links'] = lcmocc_utils.make_lcmocc_links(lcmocc,
                                                          self.endpoint)
        if selector is not None:
            lcmocc = selector.filter(lcmocc)

        # remove credential data
        self._pop_cred(lcmocc)

        return lcmocc


class SubscriptionViewBuilder(BaseViewBuilder):
    def parse_selector(self, req):
        # no selector in the API
        return None

    def detail(self, subsc, selector=None):
        # NOTE: _links is not saved in DB. create when it is necessary.
        if not subsc.obj_attr_is_set('_links'):
            self_href = subsc_utils.subsc_href(subsc.id, self.endpoint)
            subsc._links = objects.LccnSubscriptionV2_Links()
            subsc._links.self = objects.Link(href=self_href)

        resp = subsc.to_dict()

        # NOTE: authentication is not included in LccnSubscription
        resp.pop('authentication', None)

        return resp

    def detail_list(self, subscs, filters, pager):
        return super().detail_list(subscs, filters, None, pager)


class Pager:
    def __init__(self, marker, req_url, page_size):
        self.marker = marker
        self.req_url = req_url
        self.page_size = page_size
        self.next_marker = None

    def _marker_string(self, marker):
        return f'nextpage_opaque_marker={marker}'

    def _link_value(self, url):
        return f'<{url}>;rel="next"'

    def get_link(self):
        if self.next_marker is None:
            return

        if self.marker is not None:
            # req_url includes marker string
            url = self.req_url.replace(self._marker_string(self.marker),
                                       self._marker_string(self.next_marker))
        elif '?' not in self.req_url:
            url = f'{self.req_url}?{self._marker_string(self.next_marker)}'
        else:
            url = f'{self.req_url}&{self._marker_string(self.next_marker)}'

        return self._link_value(url)
