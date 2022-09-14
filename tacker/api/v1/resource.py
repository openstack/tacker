# Copyright 2012 OpenStack Foundation.
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

"""
Utility methods for working with WSGI servers redux
"""

from oslo_log import log as logging
import webob.dec

from tacker.api import api_common
from tacker import wsgi


LOG = logging.getLogger(__name__)


class Request(wsgi.Request):
    pass


def Resource(controller, faults=None, deserializers=None, serializers=None):
    """API entity resource.

    Represents an API entity resource and the associated serialization and
    deserialization logic
    """
    default_deserializers = {'application/json': wsgi.JSONDeserializer()}
    default_serializers = {'application/json': wsgi.JSONDictSerializer()}
    format_types = {'json': 'application/json'}
    action_status = dict(create=201, delete=204)

    default_deserializers.update(deserializers or {})
    default_serializers.update(serializers or {})

    deserializers = default_deserializers
    serializers = default_serializers
    faults = faults or {}

    @webob.dec.wsgify(RequestClass=Request)
    def resource(request):
        route_args = request.environ.get('wsgiorg.routing_args')
        if route_args:
            args = route_args[1].copy()
        else:
            args = {}

        # NOTE(jkoelker) by now the controller is already found, remove
        #                it from the args if it is in the matchdict
        args.pop('controller', None)
        fmt = args.pop('format', None)
        action = args.pop('action', None)
        content_type = format_types.get(fmt,
                                        request.best_match_content_type())
        language = request.best_match_language()
        deserializer = deserializers.get(content_type)
        serializer = serializers.get(content_type)

        try:
            if request.body:
                args['body'] = deserializer.deserialize(request.body)['body']

            method = getattr(controller, action)

            result = method(request=request, **args)
        except Exception as e:
            mapped_exc = api_common.convert_exception_to_http_exc(e, faults,
                                                                  language)
            if hasattr(mapped_exc, 'code') and 400 <= mapped_exc.code < 500:
                LOG.error('%(action)s failed (client error): %(exc)s',
                          {'action': action, 'exc': mapped_exc})
            else:
                LOG.exception('%(action)s failed: %(details)s',
                              {'action': action,
                               'details': extract_exc_details(e)})
            raise mapped_exc

        status = action_status.get(action, 200)
        body = serializer.serialize(result)
        # NOTE(jkoelker) Comply with RFC2616 section 9.7
        if status == 204:
            content_type = ''
            body = None

        return webob.Response(request=request, status=status,
                              content_type=content_type,
                              body=body)
    return resource


_NO_ARGS_MARKER = object()


def extract_exc_details(e):
    for attr in ('_error_context_msg', '_error_context_args'):
        if not hasattr(e, attr):
            return _('No details.')
    details = e._error_context_msg
    args = e._error_context_args
    if args is _NO_ARGS_MARKER:
        return details
    return details % args
