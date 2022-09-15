# Copyright 2011 OpenStack Foundation.
# Copyright 2011 Justin Santa Barbara
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

import abc
import os

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils
import routes
import webob.dec
import webob.exc

from tacker._i18n import _
from tacker.common import exceptions
import tacker.extensions
from tacker import policy
from tacker import wsgi


LOG = logging.getLogger(__name__)


class PluginInterface(object, metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, klass):
        """Checking plugin class.

        The __subclasshook__ method is a class method
        that will be called every time a class is tested
        using issubclass(klass, PluginInterface).
        In that case, it will check that every method
        marked with the abstractmethod decorator is
        provided by the plugin class.
        """

        if not cls.__abstractmethods__:
            return NotImplemented

        for method in cls.__abstractmethods__:
            if any(method in base.__dict__ for base in klass.__mro__):
                continue
            return NotImplemented
        return True


class ExtensionDescriptor(object):
    """Base class that defines the contract for extensions.

    Note that you don't have to derive from this class to have a valid
    extension; it is purely a convenience.
    """

    def get_name(self):
        """The name of the extension.

        e.g. 'Fox In Socks'
        """
        raise NotImplementedError()

    def get_alias(self):
        """The alias for the extension.

        e.g. 'FOXNSOX'
        """
        raise NotImplementedError()

    def get_description(self):
        """Friendly description for the extension.

        e.g. 'The Fox In Socks Extension'
        """
        raise NotImplementedError()

    def get_namespace(self):
        """The XML namespace for the extension.

        e.g. 'http://www.fox.in.socks/api/ext/pie/v1.0'
        """
        raise NotImplementedError()

    def get_updated(self):
        """The timestamp when the extension was last updated.

        e.g. '2011-01-22T13:25:27-06:00'
        """
        # NOTE(justinsb): Not sure of the purpose of this is, vs the XML NS
        raise NotImplementedError()

    def get_resources(self):
        """List of extensions.ResourceExtension extension objects.

        Resources define new nouns, and are accessible through URLs.
        """
        resources = []
        return resources

    def get_actions(self):
        """List of extensions.ActionExtension extension objects.

        Actions are verbs callable from the API.
        """
        actions = []
        return actions

    def get_request_extensions(self):
        """List of extensions.RequestException extension objects.

        Request extensions are used to handle custom request data.
        """
        request_exts = []
        return request_exts

    def get_extended_resources(self, version):
        """Retrieve extended resources or attributes for core resources.

        Extended attributes are implemented by a core plugin similarly
        to the attributes defined in the core, and can appear in
        request and response messages. Their names are scoped with the
        extension's prefix. The core API version is passed to this
        function, which must return a
        map[<resource_name>][<attribute_name>][<attribute_property>]
        specifying the extended resource attribute properties required
        by that API version.

        Extension can add resources and their attr definitions too.
        The returned map can be integrated into RESOURCE_ATTRIBUTE_MAP.
        """
        return {}

    def get_plugin_interface(self):
        """Returns an abstract class which defines contract for the plugin.

        The abstract class should inherit from extesnions.PluginInterface,
        Methods in this abstract class  should be decorated as abstractmethod
        """
        return None

    def update_attributes_map(self, extended_attributes,
                              extension_attrs_map=None):
        """Update attributes map for this extension.

        This is default method for extending an extension's attributes map.
        An extension can use this method and supplying its own resource
        attribute map in extension_attrs_map argument to extend all its
        attributes that needs to be extended.

        If an extension does not implement update_attributes_map, the method
        does nothing and just return.
        """
        if not extension_attrs_map:
            return

        for resource, attrs in extension_attrs_map.items():
            extended_attrs = extended_attributes.get(resource)
            if extended_attrs:
                attrs.update(extended_attrs)

    def get_alias_namespace_compatibility_map(self):
        """Returns mappings between extension aliases and XML namespaces.

        The mappings are XML namespaces that should, for backward compatibility
        reasons, be added to the XML serialization of extended attributes.
        This allows an established extended attribute to be provided by
        another extension than the original one while keeping its old alias
        in the name.
        :return: A dictionary of extension_aliases and namespace strings.
        """
        return {}


class ActionExtensionController(wsgi.Controller):

    def __init__(self, application):
        self.application = application
        self.action_handlers = {}

    def add_action(self, action_name, handler):
        self.action_handlers[action_name] = handler

    def action(self, request, id):
        input_dict = self._deserialize(request.body,
                                       request.get_content_type())
        for action_name, handler in (self.action_handlers).items():
            if action_name in input_dict:
                return handler(input_dict, request, id)
        # no action handler found (bump to downstream application)
        response = self.application
        return response


class RequestExtensionController(wsgi.Controller):

    def __init__(self, application):
        self.application = application
        self.handlers = []

    def add_handler(self, handler):
        self.handlers.append(handler)

    def process(self, request, *args, **kwargs):
        res = request.get_response(self.application)
        # currently request handlers are un-ordered
        for handler in self.handlers:
            response = handler(request, res)
        return response


class ExtensionController(wsgi.Controller):

    def __init__(self, extension_manager):
        self.extension_manager = extension_manager

    def _translate(self, ext):
        ext_data = {}
        ext_data['name'] = ext.get_name()
        ext_data['alias'] = ext.get_alias()
        ext_data['description'] = ext.get_description()
        ext_data['namespace'] = ext.get_namespace()
        ext_data['updated'] = ext.get_updated()
        ext_data['links'] = []  # TODO(dprince): implement extension links
        return ext_data

    def index(self, request):
        extensions = []
        for _alias, ext in (self.extension_manager.extensions).items():
            extensions.append(self._translate(ext))
        return dict(extensions=extensions)

    def show(self, request, id):
        # NOTE(dprince): the extensions alias is used as the 'id' for show
        ext = self.extension_manager.extensions.get(id)
        if not ext:
            raise webob.exc.HTTPNotFound(
                _("Extension with alias %s does not exist") % id)
        return dict(extension=self._translate(ext))

    def delete(self, request, id):
        msg = _('Resource not found.')
        raise webob.exc.HTTPNotFound(msg)

    def create(self, request):
        msg = _('Resource not found.')
        raise webob.exc.HTTPNotFound(msg)


class ExtensionMiddleware(wsgi.Middleware):
    """Extensions middleware for WSGI."""

    def __init__(self, application,
                 ext_mgr=None):
        self.ext_mgr = (ext_mgr
                        or ExtensionManager(get_extensions_path()))
        mapper = routes.Mapper()

        # extended resources
        for resource in self.ext_mgr.get_resources():
            path_prefix = resource.path_prefix
            if resource.parent:
                path_prefix = (resource.path_prefix +
                               "/%s/{%s_id}" %
                               (resource.parent["collection_name"],
                                resource.parent["member_name"]))

            LOG.debug('Extended resource: %s', resource.collection)
            for action, method in (resource.collection_actions).items():
                conditions = dict(method=[method])
                path = "/%s/%s" % (resource.collection, action)
                with mapper.submapper(controller=resource.controller,
                                      action=action,
                                      path_prefix=path_prefix,
                                      conditions=conditions) as submap:
                    submap.connect(path)
                    submap.connect("%s.:(format)" % path)

            mapper.resource(resource.collection, resource.collection,
                            controller=resource.controller,
                            member=resource.member_actions,
                            parent_resource=resource.parent,
                            path_prefix=path_prefix)

        # extended actions
        action_controllers = self._action_ext_controllers(application,
                                                          self.ext_mgr, mapper)
        for action in self.ext_mgr.get_actions():
            LOG.debug('Extended action: %s', action.action_name)
            controller = action_controllers[action.collection]
            controller.add_action(action.action_name, action.handler)

        # extended requests
        req_controllers = self._request_ext_controllers(application,
                                                        self.ext_mgr, mapper)
        for request_ext in self.ext_mgr.get_request_extensions():
            LOG.debug('Extended request: %s', request_ext.key)
            controller = req_controllers[request_ext.key]
            controller.add_handler(request_ext.handler)

        self._router = routes.middleware.RoutesMiddleware(self._dispatch,
                                                          mapper)
        super(ExtensionMiddleware, self).__init__(application)

    @classmethod
    def factory(cls, global_config, **local_config):
        """Paste factory."""
        def _factory(app):
            return cls(app, global_config, **local_config)
        return _factory

    def _action_ext_controllers(self, application, ext_mgr, mapper):
        """Return a dict of ActionExtensionController-s by collection."""
        action_controllers = {}
        for action in ext_mgr.get_actions():
            if action.collection not in action_controllers:
                controller = ActionExtensionController(application)
                mapper.connect("/%s/:(id)/action.:(format)" %
                               action.collection,
                               action='action',
                               controller=controller,
                               conditions=dict(method=['POST']))
                mapper.connect("/%s/:(id)/action" % action.collection,
                               action='action',
                               controller=controller,
                               conditions=dict(method=['POST']))
                action_controllers[action.collection] = controller

        return action_controllers

    def _request_ext_controllers(self, application, ext_mgr, mapper):
        """Returns a dict of RequestExtensionController-s by collection."""
        request_ext_controllers = {}
        for req_ext in ext_mgr.get_request_extensions():
            if req_ext.key not in request_ext_controllers:
                controller = RequestExtensionController(application)
                mapper.connect(req_ext.url_route + '.:(format)',
                               action='process',
                               controller=controller,
                               conditions=req_ext.conditions)

                mapper.connect(req_ext.url_route,
                               action='process',
                               controller=controller,
                               conditions=req_ext.conditions)
                request_ext_controllers[req_ext.key] = controller

        return request_ext_controllers

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        """Route the incoming request with router."""
        req.environ['extended.app'] = self.application
        return self._router

    @staticmethod
    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def _dispatch(req):
        """Dispatch the request.

        Returns the routed WSGI app's response or defers to the extended
        application.
        """
        match = req.environ['wsgiorg.routing_args'][1]
        if not match:
            return req.environ['extended.app']
        app = match['controller']
        return app


def extension_middleware_factory(global_config, **local_config):
    """Paste factory."""
    def _factory(app):
        ext_mgr = ExtensionManager.get_instance()
        return ExtensionMiddleware(app, ext_mgr=ext_mgr)
    return _factory


class ExtensionManager(object):
    """Load extensions from the configured extension path.

    See tests/unit/extensions/foxinsocks.py for an
    example extension implementation.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls(get_extensions_path())
        return cls._instance

    def __init__(self, path):
        LOG.info('Initializing extension manager.')
        self.path = path
        self.extensions = {}
        self._load_all_extensions()
        policy.reset()

    def get_resources(self):
        """Returns a list of ResourceExtension objects."""
        resources = []
        resources.append(ResourceExtension('extensions',
                                           ExtensionController(self)))
        for ext in self.extensions.values():
            try:
                resources.extend(ext.get_resources())
            except AttributeError:
                # NOTE(dprince): Extension aren't required to have resource
                # extensions
                pass
        return resources

    def get_actions(self):
        """Returns a list of ActionExtension objects."""
        actions = []
        for ext in self.extensions.values():
            try:
                actions.extend(ext.get_actions())
            except AttributeError:
                # NOTE(dprince): Extension aren't required to have action
                # extensions
                pass
        return actions

    def get_request_extensions(self):
        """Returns a list of RequestExtension objects."""
        request_exts = []
        for ext in self.extensions.values():
            try:
                request_exts.extend(ext.get_request_extensions())
            except AttributeError:
                # NOTE(dprince): Extension aren't required to have request
                # extensions
                pass
        return request_exts

    def extend_resources(self, version, attr_map):
        """Extend resources with additional resources or attributes.

        :param attr_map: the existing mapping from resource name to
                         attrs definition.

        After this function, we will extend the attr_map if an extension
        wants to extend this map.
        """
        update_exts = []
        processed_exts = set()
        exts_to_process = self.extensions.copy()
        # Iterate until there are unprocessed extensions or if no progress
        # is made in a whole iteration
        while exts_to_process:
            processed_ext_count = len(processed_exts)
            for ext_name, ext in list(exts_to_process.items()):
                if not hasattr(ext, 'get_extended_resources'):
                    del exts_to_process[ext_name]
                    continue
                if hasattr(ext, 'update_attributes_map'):
                    update_exts.append(ext)
                if hasattr(ext, 'get_required_extensions'):
                    # Process extension only if all required extensions
                    # have been processed already
                    required_exts_set = set(ext.get_required_extensions())
                    if required_exts_set - processed_exts:
                        continue
                try:
                    extended_attrs = ext.get_extended_resources(version)
                    for resource, resource_attrs in extended_attrs.items():
                        if attr_map.get(resource):
                            attr_map[resource].update(resource_attrs)
                        else:
                            attr_map[resource] = resource_attrs
                except AttributeError:
                    LOG.exception("Error fetching extended attributes for "
                                  "extension '%s'", ext.get_name())
                processed_exts.add(ext_name)
                del exts_to_process[ext_name]
            if len(processed_exts) == processed_ext_count:
                # Exit loop as no progress was made
                break
        if exts_to_process:
            # NOTE(salv-orlando): Consider whether this error should be fatal
            LOG.error("It was impossible to process the following "
                      "extensions: %s because of missing requirements.",
                      ','.join(exts_to_process.keys()))

        # Extending extensions' attributes map.
        for ext in update_exts:
            ext.update_attributes_map(attr_map)

    def _check_extension(self, extension):
        """Checks for required methods in extension objects."""
        try:
            LOG.debug('Ext name: %s', extension.get_name())
            LOG.debug('Ext alias: %s', extension.get_alias())
            LOG.debug('Ext description: %s', extension.get_description())
            LOG.debug('Ext namespace: %s', extension.get_namespace())
            LOG.debug('Ext updated: %s', extension.get_updated())
        except AttributeError as ex:
            LOG.exception("Exception loading extension: %s", ex)
            return False
        return True

    def _load_all_extensions(self):
        """Load extensions from the configured path.

        The extension name is constructed from the module_name. If your
        extension module is named widgets.py, the extension class within that
        module should be 'Widgets'.

        See tests/unit/extensions/foxinsocks.py for an example extension
        implementation.
        """
        for path in self.path.split(':'):
            if os.path.exists(path):
                self._load_all_extensions_from_path(path)
            else:
                LOG.error("Extension path '%s' doesn't exist!", path)

    def _load_all_extensions_from_path(self, path):
        # Sorting the extension list makes the order in which they
        # are loaded predictable across a cluster of load-balanced
        # Tacker Servers
        for f in sorted(os.listdir(path)):
            try:
                LOG.debug('Loading extension file: %s', f)
                mod_name, file_ext = os.path.splitext(os.path.split(f)[-1])
                ext_path = os.path.join(path, f)
                if file_ext.lower() == '.py' and not mod_name.startswith('_'):
                    mod = importutils.import_module(
                        'tacker.extensions.' + mod_name)
                    ext_name = mod_name[0].upper() + mod_name[1:]
                    new_ext_class = getattr(mod, ext_name, None)
                    if not new_ext_class:
                        LOG.warning('Did not find expected name '
                                    '"%(ext_name)s" in %(file)s',
                                    {'ext_name': ext_name,
                                     'file': ext_path})
                        continue
                    new_ext = new_ext_class()
                    self.add_extension(new_ext)
            except Exception as exception:
                LOG.error("Extension file %(f)s wasn't loaded due to "
                          "%(exception)s",
                          {'f': f, 'exception': exception})

    def add_extension(self, ext):
        # Do nothing if the extension doesn't check out
        if not self._check_extension(ext):
            return

        alias = ext.get_alias()

        if alias in self.extensions:
            raise exceptions.DuplicatedExtension(alias=alias)
        self.extensions[alias] = ext


class RequestExtension(object):
    """Extend requests and responses of core Tacker OpenStack API controllers.

    Provide a way to add data to responses and handle custom request data
    that is sent to core Tacker OpenStack API controllers.
    """

    def __init__(self, method, url_route, handler):
        self.url_route = url_route
        self.handler = handler
        self.conditions = dict(method=[method])
        self.key = "%s-%s" % (method, url_route)


class ActionExtension(object):
    """Add custom actions to core Tacker OpenStack API controllers."""

    def __init__(self, collection, action_name, handler):
        self.collection = collection
        self.action_name = action_name
        self.handler = handler


class ResourceExtension(object):
    """Add top level resources to the OpenStack API in Tacker."""

    def __init__(self, collection, controller, parent=None, path_prefix="",
                 collection_actions={}, member_actions={}, attr_map={}):
        self.collection = collection
        self.controller = controller
        self.parent = parent
        self.collection_actions = collection_actions
        self.member_actions = member_actions
        self.path_prefix = path_prefix
        self.attr_map = attr_map


# Returns the extension paths from a config entry and the __path__
# of tacker.extensions
def get_extensions_path():
    paths = ':'.join(tacker.extensions.__path__)
    if cfg.CONF.api_extensions_path:
        paths = ':'.join([cfg.CONF.api_extensions_path, paths])

    return paths


def append_api_extensions_path(paths):
    paths = [cfg.CONF.api_extensions_path] + paths
    cfg.CONF.set_override('api_extensions_path',
                          ':'.join([p for p in paths if p]))
