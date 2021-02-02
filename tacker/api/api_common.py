# Copyright 2011 Citrix System.
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

from functools import cmp_to_key
import netaddr
from oslo_config import cfg
import oslo_i18n
from oslo_log import log as logging
from oslo_policy import policy as oslo_policy
from urllib import parse as urllib_parse
from webob import exc

from tacker._i18n import _
from tacker.common import constants
from tacker.common import exceptions
from tacker import wsgi

LOG = logging.getLogger(__name__)


def get_filters(request, attr_info, skips=None):
    """Extract the filters from the request string.

    Returns a dict of lists for the filters:
    check=a&check=b&name=Bob&
    becomes:
    {'check': ['a', 'b'], 'name': ['Bob']}
    """
    res = {}
    skips = skips or []
    for key, values in request.GET.dict_of_lists().items():
        if key in skips:
            continue
        values = [v for v in values if v]
        key_attr_info = attr_info.get(key, {})
        if 'convert_list_to' in key_attr_info:
            values = key_attr_info['convert_list_to'](values)
        elif 'convert_to' in key_attr_info:
            convert_to = key_attr_info['convert_to']
            values = [convert_to(v) for v in values]
        if values:
            res[key] = values
    return res


def get_previous_link(request, items, id_key):
    params = request.GET.copy()
    params.pop('marker', None)
    if items:
        marker = items[0][id_key]
        params['marker'] = marker
    params['page_reverse'] = True
    return "%s?%s" % (request.path_url, urllib_parse.urlencode(params))


def get_next_link(request, items, id_key):
    params = request.GET.copy()
    params.pop('marker', None)
    if items:
        marker = items[-1][id_key]
        params['marker'] = marker
    params.pop('page_reverse', None)
    return "%s?%s" % (request.path_url, urllib_parse.urlencode(params))


def get_limit_and_marker(request):
    """Return marker, limit tuple from request.

    :param request: `wsgi.Request` possibly containing 'marker' and 'limit'
                    GET variables. 'marker' is the id of the last element
                    the client has seen, and 'limit' is the maximum number
                    of items to return. If limit == 0, it means we needn't
                    pagination, then return None.
    """
    max_limit = _get_pagination_max_limit()
    limit = _get_limit_param(request)
    if max_limit > 0:
        limit = min(max_limit, limit) or max_limit
    if not limit:
        return None, None
    marker = request.GET.get('marker', None)
    return limit, marker


def _get_pagination_max_limit():
    max_limit = -1
    if (cfg.CONF.pagination_max_limit.lower() !=
            constants.PAGINATION_INFINITE):
        try:
            max_limit = int(cfg.CONF.pagination_max_limit)
            if max_limit == 0:
                raise ValueError()
        except ValueError:
            LOG.warning("Invalid value for pagination_max_limit: %s. It "
                        "should be an integer greater to 0",
                        cfg.CONF.pagination_max_limit)
    return max_limit


def _get_limit_param(request):
    """Extract integer limit from request or fail."""
    limit = -1
    try:
        limit = int(request.GET.get('limit', 0))
        if limit >= 0:
            return limit
    except ValueError:
        pass
    msg = _("Limit must be an integer 0 or greater and not '%d'") % limit
    raise exceptions.BadRequest(resource='limit', msg=msg)


def list_args(request, arg):
    """Extract the list of arg from request."""
    return [v for v in request.GET.getall(arg) if v]


def get_sorts(request, attr_info):
    """Extract sort_key and sort_dir from request.

    Return as: [(key1, value1), (key2, value2)]
    """
    sort_keys = list_args(request, "sort_key")
    sort_dirs = list_args(request, "sort_dir")
    if len(sort_keys) != len(sort_dirs):
        msg = _("The number of sort_keys and sort_dirs must be same")
        raise exc.HTTPBadRequest(explanation=msg)
    valid_dirs = [constants.SORT_DIRECTION_ASC, constants.SORT_DIRECTION_DESC]
    absent_keys = [x for x in sort_keys if x not in attr_info]
    if absent_keys:
        msg = _("%s is invalid attribute for sort_keys") % absent_keys
        raise exc.HTTPBadRequest(explanation=msg)
    invalid_dirs = [x for x in sort_dirs if x not in valid_dirs]
    if invalid_dirs:
        msg = (_("%(invalid_dirs)s is invalid value for sort_dirs, "
                 "valid value is '%(asc)s' and '%(desc)s'") %
               {'invalid_dirs': invalid_dirs,
                'asc': constants.SORT_DIRECTION_ASC,
                'desc': constants.SORT_DIRECTION_DESC})
        raise exc.HTTPBadRequest(explanation=msg)
    return list(zip(sort_keys,
                    [x == constants.SORT_DIRECTION_ASC for x in sort_dirs]))


def get_page_reverse(request):
    data = request.GET.get('page_reverse', 'False')
    return data.lower() == "true"


def get_pagination_links(request, items, limit,
                         marker, page_reverse, key="id"):
    key = key if key else 'id'
    links = []
    if not limit:
        return links
    if not (len(items) < limit and not page_reverse):
        links.append({"rel": "next",
                      "href": get_next_link(request, items,
                                            key)})
    if not (len(items) < limit and page_reverse):
        links.append({"rel": "previous",
                      "href": get_previous_link(request, items,
                                                key)})
    return links


class PaginationHelper(object):

    def __init__(self, request, primary_key='id'):
        self.request = request
        self.primary_key = primary_key

    def update_fields(self, original_fields, fields_to_add):
        pass

    def update_args(self, args):
        pass

    def paginate(self, items):
        return items

    def get_links(self, items):
        return {}


class PaginationEmulatedHelper(PaginationHelper):

    def __init__(self, request, primary_key='id'):
        super(PaginationEmulatedHelper, self).__init__(request, primary_key)
        self.limit, self.marker = get_limit_and_marker(request)
        self.page_reverse = get_page_reverse(request)

    def update_fields(self, original_fields, fields_to_add):
        if not original_fields:
            return
        if self.primary_key not in original_fields:
            original_fields.append(self.primary_key)
            fields_to_add.append(self.primary_key)

    def paginate(self, items):
        if not self.limit:
            return items
        i = -1
        if self.marker:
            for item in items:
                i = i + 1
                if item[self.primary_key] == self.marker:
                    break
        if self.page_reverse:
            return items[i - self.limit:i]
        return items[i + 1:i + self.limit + 1]

    def get_links(self, items):
        return get_pagination_links(
            self.request, items, self.limit, self.marker,
            self.page_reverse, self.primary_key)


class PaginationNativeHelper(PaginationEmulatedHelper):

    def update_args(self, args):
        if self.primary_key not in dict(args.get('sorts', [])):
            args.setdefault('sorts', []).append((self.primary_key, True))
        args.update({'limit': self.limit, 'marker': self.marker,
                     'page_reverse': self.page_reverse})

    def paginate(self, items):
        return items


class NoPaginationHelper(PaginationHelper):
    pass


class SortingHelper(object):

    def __init__(self, request, attr_info):
        pass

    def update_args(self, args):
        pass

    def update_fields(self, original_fields, fields_to_add):
        pass

    def sort(self, items):
        return items


class SortingEmulatedHelper(SortingHelper):

    def __init__(self, request, attr_info):
        super(SortingEmulatedHelper, self).__init__(request, attr_info)
        self.sort_dict = get_sorts(request, attr_info)

    def update_fields(self, original_fields, fields_to_add):
        if not original_fields:
            return
        for key in dict(self.sort_dict):
            if key not in original_fields:
                original_fields.append(key)
                fields_to_add.append(key)

    def sort(self, items):
        def cmp_func(obj1, obj2):
            for key, direction in self.sort_dict:
                o1 = obj1[key]
                o2 = obj2[key]

                if o1 is None and o2 is None:
                    ret = 0
                elif o1 is None and o2 is not None:
                    ret = -1
                elif o1 is not None and o2 is None:
                    ret = 1
                else:
                    ret = (o1 > o2) - (o1 < o2)
                if ret:
                    return ret * (1 if direction else -1)
            return 0
        return sorted(items, key=cmp_to_key(cmp_func))


class SortingNativeHelper(SortingHelper):

    def __init__(self, request, attr_info):
        super(SortingNativeHelper, self).__init__(request, attr_info)
        self.sort_dict = get_sorts(request, attr_info)

    def update_args(self, args):
        args['sorts'] = self.sort_dict


class NoSortingHelper(SortingHelper):
    pass


class TackerController(object):
    """Base controller class for Tacker API."""

    # _resource_name will be redefined in sub concrete controller
    _resource_name = None

    def __init__(self, plugin):
        self._plugin = plugin
        super(TackerController, self).__init__()

    def _prepare_request_body(self, body, params):
        """Verify required parameters are in request body.

        Sets default value for missing optional parameters.
        Body argument must be the deserialized body.
        """
        try:
            if body is None:
                # Initialize empty resource for setting default value
                body = {self._resource_name: {}}
            data = body[self._resource_name]
        except KeyError:
            # raise if _resource_name is not in req body.
            raise exc.HTTPBadRequest(_("Unable to find '%s' in request body") %
                                     self._resource_name)
        for param in params:
            param_name = param['param-name']
            param_value = data.get(param_name)
            # If the parameter wasn't found and it was required, return 400
            if param_value is None and param['required']:
                msg = (_("Failed to parse request. "
                         "Parameter '%s' not specified") % param_name)
                LOG.error(msg)
                raise exc.HTTPBadRequest(msg)
            data[param_name] = param_value or param.get('default-value')
        return body


def convert_exception_to_http_exc(e, faults, language):
    serializer = wsgi.JSONDictSerializer()
    e = translate(e, language)
    body = serializer.serialize(
        {'TackerError': get_exception_data(e)})
    kwargs = {'body': body, 'content_type': 'application/json'}
    if isinstance(e, exc.HTTPException):
        # already an HTTP error, just update with content type and body
        e.body = body
        e.content_type = kwargs['content_type']
        return e
    if isinstance(e, (exceptions.TackerException, netaddr.AddrFormatError,
                      oslo_policy.PolicyNotAuthorized)):
        for fault in faults:
            if isinstance(e, fault):
                mapped_exc = faults[fault]
                break
        else:
            mapped_exc = exc.HTTPInternalServerError
        return mapped_exc(**kwargs)
    if isinstance(e, NotImplementedError):
        # NOTE(armando-migliaccio): from a client standpoint
        # it makes sense to receive these errors, because
        # extensions may or may not be implemented by
        # the underlying plugin. So if something goes south,
        # because a plugin does not implement a feature,
        # returning 500 is definitely confusing.
        kwargs['body'] = serializer.serialize(
            {'NotImplementedError': get_exception_data(e)})
        return exc.HTTPNotImplemented(**kwargs)
    # NOTE(jkoelker) Everything else is 500
    # Do not expose details of 500 error to clients.
    msg = _('Request Failed: internal server error while '
            'processing your request.')
    msg = translate(msg, language)
    kwargs['body'] = serializer.serialize(
        {'TackerError': get_exception_data(exc.HTTPInternalServerError(msg))})
    return exc.HTTPInternalServerError(**kwargs)


def get_exception_data(e):
    """Extract the information about an exception.

    Tacker client for the v1 API expects exceptions to have 'type', 'message'
    and 'detail' attributes.This information is extracted and converted into a
    dictionary.

    :param e: the exception to be reraised
    :returns: a structured dict with the exception data
    """
    err_data = {'type': e.__class__.__name__,
                'message': e, 'detail': ''}
    return err_data


def translate(translatable, locale):
    """Translate the object to the given locale.

    If the object is an exception its translatable elements are translated
    in place, if the object is a translatable string it is translated and
    returned. Otherwise, the object is returned as-is.

    :param translatable: the object to be translated
    :param locale: the locale to translate to
    :returns: the translated object, or the object as-is if it
              was not translated
    """
    localize = oslo_i18n.translate
    if isinstance(translatable, exceptions.TackerException):
        translatable.msg = localize(translatable.msg, locale)
    elif isinstance(translatable, exc.HTTPError):
        translatable.detail = localize(translatable.detail, locale)
    elif isinstance(translatable, Exception):
        translatable.message = localize(translatable, locale)
    else:
        return localize(translatable, locale)
    return translatable
