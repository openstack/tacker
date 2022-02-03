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

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import subscription_utils as subsc_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)


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
        LOG.debug("Key %s type %s", self.attr, type(val))
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


class BaseViewBuilder(object):
    value_regexp = r"([^',)]+|('[^']*')+)"
    value_re = re.compile(value_regexp)
    simpleFilterExpr_re = re.compile(r"\(([a-z]+),([^,]+)(," +
                                     value_regexp + r")+\)")
    tildeEscape_re = re.compile(r"~([1ab])")
    opOne = ['eq', 'neq', 'gt', 'gte', 'lt', 'lte']
    opMulti = ['in', 'nin', 'cont', 'ncont']

    def __init__(self):
        pass

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
                LOG.debug("value parse error, %s at loc %d", values, loc)
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

        loc = 0
        res = []
        while True:
            m = self.simpleFilterExpr_re.match(filter[loc:])
            if m is None:
                LOG.debug("filter %s parse error at char %d", filter, loc)
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
                LOG.debug("filter %s parse error at char %d "
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
        if filters is None:
            return True

        for f in filters:
            if not f.match(val):
                return False
        return True

    def detail_list(self, values, filters, selector):
        return [self.detail(v, selector) for v in values
                if self.match_filters(v, filters)]


class InstanceViewBuilder(BaseViewBuilder):
    _EXCLUDE_DEFAULT = ['vnfConfigurableProperties',
                        'vimConnectionInfo',
                        'instantiatedVnfInfo',
                        'metadata',
                        'extensions']

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def parse_filter(self, filter):
        return super().parse_filter(filter)

    def detail(self, inst, selector=None):
        # NOTE: _links is not saved in DB. create when it is necessary.
        if not inst.obj_attr_is_set('_links'):
            inst._links = inst_utils.make_inst_links(inst, self.endpoint)

        resp = inst.to_dict()

        # remove password from vim_connection_info
        # see SOL003 4.4.1.6
        for vim_info in resp.get('vimConnectionInfo', {}).values():
            if ('accessInfo' in vim_info and
                    'password' in vim_info['accessInfo']):
                vim_info['accessInfo'].pop('password')

        if selector is not None:
            resp = selector.filter(inst, resp)
        return resp

    def detail_list(self, insts, filters, selector):
        return super().detail_list(insts, filters, selector)


class LcmOpOccViewBuilder(BaseViewBuilder):
    _EXCLUDE_DEFAULT = ['operationParams',
                        'error',
                        'resourceChanges',
                        'changedInfo',
                        'changedExtConnectivity']

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def parse_filter(self, filter):
        return super().parse_filter(filter)

    def detail(self, lcmocc, selector=None):
        # NOTE: _links is not saved in DB. create when it is necessary.
        if not lcmocc.obj_attr_is_set('_links'):
            lcmocc._links = lcmocc_utils.make_lcmocc_links(lcmocc,
                                                           self.endpoint)
        resp = lcmocc.to_dict()
        if selector is not None:
            resp = selector.filter(lcmocc, resp)
        return resp

    def detail_list(self, lcmoccs, filters, selector):
        return super().detail_list(lcmoccs, filters, selector)


class SubscriptionViewBuilder(BaseViewBuilder):
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def parse_filter(self, filter):
        return super().parse_filter(filter)

    def detail(self, subsc, selector=None):
        # NOTE: _links is not saved in DB. create when it is necessary.
        if not subsc.obj_attr_is_set('_links'):
            self_href = subsc_utils.subsc_href(subsc.id, self.endpoint)
            subsc._links = objects.LccnSubscriptionV2_Links()
            subsc._links.self = objects.Link(href=self_href)

        resp = subsc.to_dict()

        # NOTE: authentication is not included in LccnSubscription
        resp.pop('authentication', None)

        if selector is not None:
            resp = selector.filter(subsc, resp)
        return resp

    def detail_list(self, subscs, filters):
        return super().detail_list(subscs, filters, None)
