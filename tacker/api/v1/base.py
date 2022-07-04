# Copyright (c) 2012 OpenStack Foundation.
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

import netaddr
import webob.exc

from oslo_log import log as logging
from oslo_utils import strutils

from tacker._i18n import _
from tacker.api import api_common
from tacker.api.v1 import attributes
from tacker.api.v1 import resource as wsgi_resource
from tacker.common import exceptions
from tacker.common import rpc as n_rpc
from tacker import policy


LOG = logging.getLogger(__name__)

FAULT_MAP = {exceptions.NotFound: webob.exc.HTTPNotFound,
             exceptions.Conflict: webob.exc.HTTPConflict,
             exceptions.InUse: webob.exc.HTTPConflict,
             exceptions.BadRequest: webob.exc.HTTPBadRequest,
             exceptions.ServiceUnavailable: webob.exc.HTTPServiceUnavailable,
             exceptions.NotAuthorized: webob.exc.HTTPForbidden,
             netaddr.AddrFormatError: webob.exc.HTTPBadRequest,
             }


class Controller(object):
    LIST = 'list'
    SHOW = 'show'
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'

    def __init__(self, plugin, collection, resource, attr_info,
                 allow_bulk=False, member_actions=None, parent=None,
                 allow_pagination=False, allow_sorting=False):
        member_actions = member_actions or []
        self._plugin = plugin
        self._collection = collection.replace('-', '_')
        self._resource = resource.replace('-', '_')
        self._attr_info = attr_info
        self._allow_bulk = allow_bulk
        self._allow_pagination = allow_pagination
        self._allow_sorting = allow_sorting
        self._native_bulk = self._is_native_bulk_supported()
        self._native_pagination = self._is_native_pagination_supported()
        self._native_sorting = self._is_native_sorting_supported()
        self._policy_attrs = [name for (name, info) in self._attr_info.items()
                              if info.get('required_by_policy')]
        self._notifier = n_rpc.get_notifier('nfv')
        self._member_actions = member_actions
        self._primary_key = self._get_primary_key()
        if self._allow_pagination and self._native_pagination:
            # Native pagination need native sorting support
            if not self._native_sorting:
                raise exceptions.Invalid(
                    _("Native pagination depend on native sorting")
                )
            if not self._allow_sorting:
                LOG.info("Allow sorting is enabled because native "
                         "pagination requires native sorting")
                self._allow_sorting = True

        if parent:
            self._parent_id_name = '%s_id' % parent['member_name']
            parent_part = '_%s' % parent['member_name']
        else:
            self._parent_id_name = None
            parent_part = ''
        self._plugin_handlers = {
            self.LIST: 'get%s_%s' % (parent_part, self._collection),
            self.SHOW: 'get%s_%s' % (parent_part, self._resource)
        }
        for action in [self.CREATE, self.UPDATE, self.DELETE]:
            self._plugin_handlers[action] = '%s%s_%s' % (action, parent_part,
                                                         self._resource)

    def _get_primary_key(self, default_primary_key='id'):
        for key, value in (self._attr_info).items():
            if value.get('primary_key', False):
                return key
        return default_primary_key

    def _is_native_bulk_supported(self):
        native_bulk_attr_name = ("_%s__native_bulk_support"
                                 % self._plugin.__class__.__name__)
        return getattr(self._plugin, native_bulk_attr_name, False)

    def _is_native_pagination_supported(self):
        native_pagination_attr_name = ("_%s__native_pagination_support"
                                       % self._plugin.__class__.__name__)
        return getattr(self._plugin, native_pagination_attr_name, False)

    def _is_native_sorting_supported(self):
        native_sorting_attr_name = ("_%s__native_sorting_support"
                                    % self._plugin.__class__.__name__)
        return getattr(self._plugin, native_sorting_attr_name, False)

    def _exclude_attributes_by_policy(self, context, data):
        """Identifies attributes to exclude according to authZ policies.

        Return a list of attribute names which should be stripped from the
        response returned to the user because the user is not authorized
        to see them.
        """
        attributes_to_exclude = []
        for attr_name in data:
            attr_data = self._attr_info.get(attr_name)
            if attr_data and attr_data['is_visible']:
                if policy.check(
                    context,
                    '%s:%s' % (self._plugin_handlers[self.SHOW], attr_name),
                    data,
                        might_not_exist=True):
                    # this attribute is visible, check next one
                    continue
            # if the code reaches this point then either the policy check
            # failed or the attribute was not visible in the first place
            attributes_to_exclude.append(attr_name)
        return attributes_to_exclude

    def _view(self, context, data, fields_to_strip=None):
        """Build a view of an API resource.

        :param context: the tacker context
        :param data: the object for which a view is being created
        :param fields_to_strip: attributes to remove from the view

        :returns: a view of the object which includes only attributes
        visible according to API resource declaration and authZ policies.
        """
        fields_to_strip = ((fields_to_strip or []) +
                           self._exclude_attributes_by_policy(context, data))
        return self._filter_attributes(context, data, fields_to_strip)

    def _filter_attributes(self, context, data, fields_to_strip=None):
        if not fields_to_strip:
            return data
        return dict(item for item in (data).items()
                    if (item[0] not in fields_to_strip))

    def _do_field_list(self, original_fields):
        fields_to_add = None
        # don't do anything if fields were not specified in the request
        if original_fields:
            fields_to_add = [attr for attr in self._policy_attrs
                             if attr not in original_fields]
            original_fields.extend(self._policy_attrs)
        return original_fields, fields_to_add

    def __getattr__(self, name):
        if name in self._member_actions:
            def _handle_action(request, id, **kwargs):
                arg_list = [request.context, id]
                # Ensure policy engine is initialized
                policy.init()
                # Fetch the resource and verify if the user can access it
                try:
                    resource = self._item(request, id, True)
                except exceptions.PolicyNotAuthorized:
                    msg = _('The resource could not be found.')
                    raise webob.exc.HTTPNotFound(msg)
                body = kwargs.pop('body', None)
                # Explicit comparison with None to distinguish from {}
                if body is not None:
                    arg_list.append(body)
                # It is ok to raise a 403 because accessibility to the
                # object was checked earlier in this method
                policy.enforce(request.context, name, resource)
                return getattr(self._plugin, name)(*arg_list, **kwargs)
            return _handle_action
        else:
            raise AttributeError

    def _get_pagination_helper(self, request):
        if self._allow_pagination and self._native_pagination:
            return api_common.PaginationNativeHelper(request,
                                                     self._primary_key)
        elif self._allow_pagination:
            return api_common.PaginationEmulatedHelper(request,
                                                       self._primary_key)
        return api_common.NoPaginationHelper(request, self._primary_key)

    def _get_sorting_helper(self, request):
        if self._allow_sorting and self._native_sorting:
            return api_common.SortingNativeHelper(request, self._attr_info)
        elif self._allow_sorting:
            return api_common.SortingEmulatedHelper(request, self._attr_info)
        return api_common.NoSortingHelper(request, self._attr_info)

    def _items(self, request, do_authz=False, parent_id=None):
        """Retrieves and formats a list of elements of the requested entity."""
        # NOTE(salvatore-orlando): The following ensures that fields which
        # are needed for authZ policy validation are not stripped away by the
        # plugin before returning.
        original_fields, fields_to_add = self._do_field_list(
            api_common.list_args(request, 'fields'))
        filters = api_common.get_filters(request, self._attr_info,
                                         ['fields', 'sort_key', 'sort_dir',
                                          'limit', 'marker', 'page_reverse'])
        kwargs = {'filters': filters,
                  'fields': original_fields}
        sorting_helper = self._get_sorting_helper(request)
        pagination_helper = self._get_pagination_helper(request)
        sorting_helper.update_args(kwargs)
        sorting_helper.update_fields(original_fields, fields_to_add)
        pagination_helper.update_args(kwargs)
        pagination_helper.update_fields(original_fields, fields_to_add)
        if parent_id:
            kwargs[self._parent_id_name] = parent_id
        obj_getter = getattr(self._plugin, self._plugin_handlers[self.LIST])
        obj_list = obj_getter(request.context, **kwargs)
        obj_list = sorting_helper.sort(obj_list)
        obj_list = pagination_helper.paginate(obj_list)
        # Check authz
        if do_authz:
            # FIXME(salvatore-orlando): obj_getter might return references to
            # other resources. Must check authZ on them too.
            # Omit items from list that should not be visible
            obj_list = [obj for obj in obj_list
                        if policy.check(request.context,
                                        self._plugin_handlers[self.SHOW],
                                        obj,
                                        plugin=self._plugin)]
        # Use the first element in the list for discriminating which attributes
        # should be filtered out because of authZ policies
        # fields_to_add contains a list of attributes added for request policy
        # checks but that were not required by the user. They should be
        # therefore stripped
        fields_to_strip = fields_to_add or []
        if obj_list:
            fields_to_strip += self._exclude_attributes_by_policy(
                request.context, obj_list[0])
        collection = {self._collection:
                      [self._filter_attributes(
                          request.context, obj,
                          fields_to_strip=fields_to_strip)
                       for obj in obj_list]}
        pagination_links = pagination_helper.get_links(obj_list)
        if pagination_links:
            collection[self._collection + "_links"] = pagination_links
        return collection

    def _item(self, request, id, do_authz=False, field_list=None,
              parent_id=None):
        """Retrieves and formats a single element of the requested entity."""
        kwargs = {'fields': field_list}
        action = self._plugin_handlers[self.SHOW]
        if parent_id:
            kwargs[self._parent_id_name] = parent_id
        obj_getter = getattr(self._plugin, action)
        obj = obj_getter(request.context, id, **kwargs)
        # Check authz
        # FIXME(salvatore-orlando): obj_getter might return references to
        # other resources. Must check authZ on them too.
        if do_authz:
            policy.enforce(request.context, action, obj)
        return obj

    def index(self, request, **kwargs):
        """Returns a list of the requested entity."""
        parent_id = kwargs.get(self._parent_id_name)
        # Ensure policy engine is initialized
        policy.init()
        return self._items(request, True, parent_id)

    def show(self, request, id, **kwargs):
        """Returns detailed information about the requested entity."""
        try:
            # NOTE(salvatore-orlando): The following ensures that fields
            # which are needed for authZ policy validation are not stripped
            # away by the plugin before returning.
            field_list, added_fields = self._do_field_list(
                api_common.list_args(request, "fields"))
            parent_id = kwargs.get(self._parent_id_name)
            # Ensure policy engine is initialized
            policy.init()
            return {self._resource:
                    self._view(request.context,
                               self._item(request,
                                          id,
                                          do_authz=True,
                                          field_list=field_list,
                                          parent_id=parent_id),
                               fields_to_strip=added_fields)}
        except exceptions.PolicyNotAuthorized:
            # To avoid giving away information, pretend that it
            # doesn't exist
            msg = _('The resource could not be found.')
            raise webob.exc.HTTPNotFound(msg)

    def _emulate_bulk_create(self, obj_creator, request, body, parent_id=None):
        objs = []
        try:
            for item in body[self._collection]:
                kwargs = {self._resource: item}
                if parent_id:
                    kwargs[self._parent_id_name] = parent_id
                fields_to_strip = self._exclude_attributes_by_policy(
                    request.context, item)
                objs.append(self._filter_attributes(
                    request.context,
                    obj_creator(request.context, **kwargs),
                    fields_to_strip=fields_to_strip))
            return objs
        # Note(salvatore-orlando): broad catch as in theory a plugin
        # could raise any kind of exception
        except Exception:
            for obj in objs:
                obj_deleter = getattr(self._plugin,
                                      self._plugin_handlers[self.DELETE])
                try:
                    kwargs = ({self._parent_id_name: parent_id} if parent_id
                              else {})
                    obj_deleter(request.context, obj['id'], **kwargs)
                except Exception:
                    # broad catch as our only purpose is to log the exception
                    LOG.exception("Unable to undo add for %(resource)s %(id)s",
                                  {'resource': self._resource,
                                   'id': obj['id']})
            # TODO(salvatore-orlando): The object being processed when the
            # plugin raised might have been created or not in the db.
            # We need a way for ensuring that if it has been created,
            # it is then deleted
            raise

    def create(self, request, body=None, **kwargs):
        """Creates a new instance of the requested entity."""
        parent_id = kwargs.get(self._parent_id_name)
        self._notifier.info(request.context,
                            self._resource + '.create.start',
                            body)
        body = Controller.prepare_request_body(request.context, body, True,
                                               self._resource, self._attr_info,
                                               allow_bulk=self._allow_bulk)
        action = self._plugin_handlers[self.CREATE]
        # Check authz
        if self._collection in body:
            # Have to account for bulk create
            items = body[self._collection]
        else:
            items = [body]
        # Ensure policy engine is initialized
        policy.init()
        for item in items:
            policy.enforce(request.context,
                           action,
                           item[self._resource])

        def notify(create_result):
            notifier_method = self._resource + '.create.end'
            self._notifier.info(request.context,
                                notifier_method,
                                create_result)
            return create_result

        kwargs = {self._parent_id_name: parent_id} if parent_id else {}
        if self._collection in body and self._native_bulk:
            # plugin does atomic bulk create operations
            obj_creator = getattr(self._plugin, "%s_bulk" % action)
            objs = obj_creator(request.context, body, **kwargs)
            # Use first element of list to discriminate attributes which
            # should be removed because of authZ policies
            fields_to_strip = self._exclude_attributes_by_policy(
                request.context, objs[0])
            return notify({self._collection: [self._filter_attributes(
                request.context, obj, fields_to_strip=fields_to_strip)
                for obj in objs]})
        else:
            obj_creator = getattr(self._plugin, action)
            if self._collection in body:
                # Emulate atomic bulk behavior
                objs = self._emulate_bulk_create(obj_creator, request,
                                                 body, parent_id)
                return notify({self._collection: objs})
            else:
                kwargs.update({self._resource: body})
                obj = obj_creator(request.context, **kwargs)
                return notify({self._resource: self._view(request.context,
                                                          obj)})

    def delete(self, request, id, body=None, **kwargs):
        """Deletes the specified entity."""
        self._notifier.info(request.context,
                            self._resource + '.delete.start',
                            {self._resource + '_id': id})
        action = self._plugin_handlers[self.DELETE]

        # Check authz
        policy.init()
        parent_id = kwargs.get(self._parent_id_name)
        obj = self._item(request, id, parent_id=parent_id)
        try:
            policy.enforce(request.context,
                           action,
                           obj)
        except exceptions.PolicyNotAuthorized:
            # To avoid giving away information, pretend that it
            # doesn't exist
            msg = _('The resource could not be found.')
            raise webob.exc.HTTPNotFound(msg)

        obj_deleter = getattr(self._plugin, action)
        if body:
            kwargs.update({self._resource: body})
        obj_deleter(request.context, id, **kwargs)
        notifier_method = self._resource + '.delete.end'
        self._notifier.info(request.context,
                            notifier_method,
                            {self._resource + '_id': id})

    def update(self, request, id, body=None, **kwargs):
        """Updates the specified entity's attributes."""
        parent_id = kwargs.get(self._parent_id_name)
        try:
            payload = body.copy()
        except AttributeError:
            msg = _("Invalid format: %s") % request.body
            raise exceptions.BadRequest(resource='body', msg=msg)
        payload['id'] = id
        self._notifier.info(request.context,
                            self._resource + '.update.start',
                            payload)
        body = Controller.prepare_request_body(request.context, body, False,
                                               self._resource, self._attr_info,
                                               allow_bulk=self._allow_bulk)
        action = self._plugin_handlers[self.UPDATE]
        # Load object to check authz
        # but pass only attributes in the original body and required
        # by the policy engine to the policy 'brain'
        field_list = [name for (name, value) in (self._attr_info).items()
                      if (value.get('required_by_policy') or
                          value.get('primary_key') or
                          'default' not in value)]
        # Ensure policy engine is initialized
        policy.init()
        orig_obj = self._item(request, id, field_list=field_list,
                              parent_id=parent_id)
        orig_obj.update(body[self._resource])
        attribs = attributes.ATTRIBUTES_TO_UPDATE
        orig_obj[attribs] = body[self._resource].keys()
        try:
            policy.enforce(request.context,
                           action,
                           orig_obj)
        except exceptions.PolicyNotAuthorized:
            # To avoid giving away information, pretend that it
            # doesn't exist
            msg = _('The resource could not be found.')
            raise webob.exc.HTTPNotFound(msg)

        obj_updater = getattr(self._plugin, action)
        kwargs = {self._resource: body}
        if parent_id:
            kwargs[self._parent_id_name] = parent_id
        obj = obj_updater(request.context, id, **kwargs)
        result = {self._resource: self._view(request.context, obj)}
        notifier_method = self._resource + '.update.end'
        self._notifier.info(request.context, notifier_method, result)
        return result

    @staticmethod
    def _populate_tenant_id(context, res_dict, is_create):

        if (('tenant_id' in res_dict and
             res_dict['tenant_id'] != context.tenant_id and
             not context.is_admin)):
            msg = _("Specifying 'tenant_id' other than authenticated "
                    "tenant in request requires admin privileges")
            raise webob.exc.HTTPBadRequest(msg)

        if is_create and 'tenant_id' not in res_dict:
            if context.tenant_id:
                res_dict['tenant_id'] = context.tenant_id
                res_dict['project_id'] = context.tenant_id
            else:
                msg = _("Running without keystone AuthN requires "
                        "that tenant_id is specified")
                raise webob.exc.HTTPBadRequest(msg)

    @staticmethod
    def prepare_request_body(context, body, is_create, resource, attr_info,
                             allow_bulk=False):
        """Verifies required attributes are in request body.

        Also checking that an attribute is only specified if it is allowed
        for the given operation (create/update).

        Attribute with default values are considered to be optional.

        body argument must be the deserialized body.
        """
        collection = resource + "s"
        if not body:
            raise webob.exc.HTTPBadRequest(_("Resource body required"))

        LOG.debug("Request body: %(body)s",
                  {'body': strutils.mask_password(body)})
        prep_req_body = lambda x: Controller.prepare_request_body(  # noqa
            context,
            x if resource in x else {resource: x},
            is_create,
            resource,
            attr_info,
            allow_bulk)
        if collection in body:
            if not allow_bulk:
                raise webob.exc.HTTPBadRequest(_("Bulk operation "
                                                 "not supported"))
            bulk_body = [prep_req_body(item) for item in body[collection]]
            if not bulk_body:
                raise webob.exc.HTTPBadRequest(_("Resources required"))
            return {collection: bulk_body}

        res_dict = body.get(resource)
        if res_dict is None:
            msg = _("Unable to find '%s' in request body") % resource
            raise webob.exc.HTTPBadRequest(msg)

        Controller._populate_tenant_id(context, res_dict, is_create)
        Controller._verify_attributes(res_dict, attr_info)

        if is_create:  # POST
            for attr, attr_vals in (attr_info).items():
                if attr_vals['allow_post']:
                    if ('default' not in attr_vals and
                            attr not in res_dict):
                        msg = _("Failed to parse request. Required "
                                "attribute '%s' not specified") % attr
                        raise webob.exc.HTTPBadRequest(msg)
                    res_dict[attr] = res_dict.get(attr,
                                                  attr_vals.get('default'))
                else:
                    if attr in res_dict:
                        msg = _("Attribute '%s' not allowed in POST") % attr
                        raise webob.exc.HTTPBadRequest(msg)
        else:  # PUT
            for attr, attr_vals in (attr_info).items():
                if attr in res_dict and not attr_vals['allow_put']:
                    msg = _("Cannot update read-only attribute %s") % attr
                    raise webob.exc.HTTPBadRequest(msg)

        for attr, attr_vals in (attr_info).items():
            if (attr not in res_dict or
                    res_dict[attr] is attributes.ATTR_NOT_SPECIFIED):
                continue
            # Convert values if necessary
            if 'convert_to' in attr_vals:
                res_dict[attr] = attr_vals['convert_to'](res_dict[attr])
            # Check that configured values are correct
            if 'validate' not in attr_vals:
                continue
            for rule in attr_vals['validate']:
                # skip validating vnfd_id when vnfd_template is specified to
                # create vnf
                if (resource == 'vnf') and ('vnfd_template' in body['vnf'])\
                        and (attr == "vnfd_id") and is_create:
                    continue
                # skip validating vnffgd_id when vnffgd_template is provided
                if ((resource == 'vnffg')
                        and ('vnffgd_template' in body['vnffg'])
                        and (attr == 'vnffgd_id') and is_create):
                    continue
                # skip validating nsd_id when nsd_template is provided
                if (resource == 'ns') and ('nsd_template' in body['ns'])\
                        and (attr == 'nsd_id') and is_create:
                    continue
                res = attributes.validators[rule](res_dict[attr],
                                                  attr_vals['validate'][rule])
                if res:
                    msg_dict = dict(attr=attr, reason=res)
                    msg = _("Invalid input for %(attr)s. "
                            "Reason: %(reason)s.") % msg_dict
                    raise webob.exc.HTTPBadRequest(msg)
        return body

    @staticmethod
    def _verify_attributes(res_dict, attr_info):
        # TODO(h-asahina): The `project_id` is not included in attr_info, but
        # it is used as an alternative of `tenant_id` which is already
        # deprecated in oslo.context. Excluding `project_id` from the
        # verification is a workaround to avoid directly modifying attr_info
        # which has a strong influence on the existing code.
        excluded = {'project_id'}
        extra_keys = set(res_dict.keys()) - set(attr_info.keys()) - excluded
        if extra_keys:
            msg = _("Unrecognized attribute(s) '%s'") % ', '.join(extra_keys)
            raise webob.exc.HTTPBadRequest(msg)


def create_resource(collection, resource, plugin, params, allow_bulk=False,
                    member_actions=None, parent=None, allow_pagination=False,
                    allow_sorting=False):
    controller = Controller(plugin, collection, resource, params, allow_bulk,
                            member_actions=member_actions, parent=parent,
                            allow_pagination=allow_pagination,
                            allow_sorting=allow_sorting)

    return wsgi_resource.Resource(controller, FAULT_MAP)
