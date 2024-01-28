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

from collections import abc
import copy
import re
import sys

from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_log import log as logging
from oslo_policy import opts
from oslo_policy import policy
from oslo_utils import excutils
from oslo_utils import importutils

from tacker._i18n import _
from tacker.api.v1 import attributes
from tacker.common import exceptions
from tacker.common.utils import is_valid_area
from tacker import policies


LOG = logging.getLogger(__name__)

_ENFORCER = None
ADMIN_CTX_POLICY = 'context_is_admin'

# TODO(gmann): Remove setting the default value of config policy_file
# once oslo_policy change the default value to 'policy.yaml'.
# https://github.com/openstack/oslo.policy/blob/a626ad12fe5a3abd49d70e3e5b95589d279ab578/oslo_policy/opts.py#L49
DEFAULT_POLICY_FILE = 'policy.yaml'
opts.set_defaults(cfg.CONF, DEFAULT_POLICY_FILE)


def reset():
    global _ENFORCER
    if _ENFORCER:
        _ENFORCER.clear()
        _ENFORCER = None


def init(conf=cfg.CONF, policy_file=None):
    """Init an instance of the Enforcer class."""

    global _ENFORCER
    if not _ENFORCER:
        _ENFORCER = policy.Enforcer(conf, policy_file=policy_file)
        register_rules(_ENFORCER)
        _ENFORCER.load_rules()


def _pre_enhanced_policy_check(target, credentials):
    """Preprocesses target and credentials for enhanced tacker policy.

    This method does the following things:
    1) Convert special roles to enhanced policy attributes in credentials.
    Note: Special roles are roles that have prefixes 'AREA_', 'VENDOR_',
        or 'TENANT_'.
    Example::

    Before conversion:
        credentials = {
            'roles': [
                'AREA_area_A@region_A',
                'VENDOR_company_A',
                'TENANT_default'
            ]
        }
    After conversion:
        credentials = {
            'roles': [
                'AREA_area_A@region_A',
                'VENDOR_company_A',
                'TENANT_default'
            ],
            'area': ['*', 'area_A@region_A'],
            'vendor': ['*', 'company_A'],
            'tenant: ['*', 'default']
        }
    2) Convert special value `all` to the corresponding attribute value in
    target.

    :param target: a dictionary of the attributes of the object
        being accessed.
    :param credentials: The information about the user performing the action.
    :return tgt: The preprocessed target is returned.
    :return user_attrs: The preprocessed credentials is returned.
    """
    if not cfg.CONF.oslo_policy.enhanced_tacker_policy:
        return target, credentials

    if target is None:
        tgt = {}
    else:
        tgt = copy.copy(target)

    LOG.debug(f'target: {target}')

    convert_map = {
        'area_': 'area',
        'vendor_': 'vendor',
        'tenant_': 'tenant'
    }
    user_attrs = {
        'area': ['*'],
        'vendor': ['*'],
        'tenant': ['*']
    }
    # Convert special roles to enhanced policy attributes in credentials.
    for role in credentials.get('roles'):
        role = role.lower()
        for prefix, key in convert_map.items():
            if role.startswith(prefix):
                attr = role[len(prefix):]
                if attr:
                    user_attrs[key].append(attr)

    common_keys = user_attrs.keys() & tgt.keys()

    # Convert special value `all` to the corresponding attribute value in
    # target.
    for key in common_keys:
        tgt[key] = tgt[key].lower()
        attrs = user_attrs.get(key)
        if tgt.get(key) == '*':
            continue
        to_remove = []
        if 'area' == key:
            if not is_valid_area(tgt.get(key)):
                continue
            for attr in attrs:
                if not is_valid_area(attr):
                    continue
                if 'all@all' == attr:
                    # example:
                    #   target = {'area': 'area_A@region_A'}
                    #   then:
                    #       'all@all' -> 'area_A@region_A'
                    to_remove.append('all@all')
                    attrs.append(tgt.get(key))
                elif attr.startswith('all@'):
                    to_remove.append(attr)
                    area, region = attr.split('@', 1)
                    t_area, t_region = tgt.get(key).split('@', 1)
                    if region == t_region:
                        # example:
                        #   target = {'area': 'area_A@region_A'}
                        #   then:
                        #       'all@region_A' -> 'area_A@region_A'
                        attrs.append(f'{t_area}@{region}')
                    # else:
                    # example:
                    #   target = {'area': 'area_A@region_B'}
                    #   then:
                    #       'all@region_A' -> to be removed.

        else:
            for attr in attrs:
                if 'all' == attr:
                    # example:
                    #   target = {'vendor': 'company_A'}
                    #   then:
                    #       'all' -> 'company_A'
                    to_remove.append('all')
                    attrs.append(tgt.get(key))
        for item in to_remove:
            attrs.remove(item)

    user_attrs.update(credentials)

    return tgt, user_attrs


def authorize(context, action, target, do_raise=True, exc=None):

    init()
    credentials = context.to_policy_values()
    # NOTE(gmann): For system, scope token, oslo.policy check
    # for a key 'system' in creds. The oslo.context library uses
    # `system_scope` instead. Because we are converting the context
    # attribute to creds via context.to_policy_values which does not
    # convert 'system_scope' key. There are two ways to solve this:
    # 1. Pass full context to oslo.policy and their it convert this key
    # but Tacker has special case of enhanced policy conversion
    # (via _pre_enhanced_policy_check(), method which sets its own
    # key in creds. So passing full context to oslo.policy make enhance
    # policy conversion more complex.
    # 2. Set 'system' key in creds explicitly. This is easy and more
    # readable way.
    if context.system_scope:
        credentials['system'] = context.system_scope
    target, credentials = _pre_enhanced_policy_check(target, credentials)
    if not exc:
        exc = exceptions.PolicyNotAuthorized
    try:
        result = _ENFORCER.authorize(action, target, credentials,
                                     do_raise=do_raise, exc=exc, action=action)
    except policy.PolicyNotRegistered:
        with excutils.save_and_reraise_exception():
            LOG.error('Policy not registered')
    except policy.InvalidScope:
        LOG.debug('Policy check for %(action)s failed with scope check '
                  '%(credentials)s',
                  {'action': action,
                   'credentials': credentials})
        raise exc(action=action)
    except Exception:
        with excutils.save_and_reraise_exception():
            LOG.error('Policy check for %(action)s failed with credentials '
                      '%(credentials)s',
                      {'action': action, 'credentials': credentials})

    return result


def refresh(policy_file=None):
    """Reset policy and init a new instance of Enforcer."""
    reset()
    init(policy_file=policy_file)


def get_resource_and_action(action, pluralized=None):
    """Return resource and enforce_attr_based_check(boolean).

    It is per resource and action extracted from api operation.
    """

    data = action.split(':', 1)[0].split('_', 1)
    resource = pluralized or ("%ss" % data[-1])
    enforce_attr_based_check = data[0] not in ('get', 'delete')
    return (resource, enforce_attr_based_check)


def set_rules(policies, overwrite=True):
    """Set rules based on the provided dict of rules.

    :param policies: New policies to use. It should be an instance of dict.
    :param overwrite: Whether to overwrite current rules or update them
                          with the new rules.
    """

    LOG.debug("Loading policies from file: %s", _ENFORCER.policy_path)
    init()
    _ENFORCER.set_rules(policies, overwrite)


def _is_attribute_explicitly_set(attribute_name, resource, target, action):
    """Verify that an attribute is present and is explicitly set."""
    if 'update' in action:
        # In the case of update, the function should not pay attention to a
        # default value of an attribute, but check whether it was explicitly
        # marked as being updated instead.
        return (attribute_name in target[attributes.ATTRIBUTES_TO_UPDATE] and
                target[attribute_name] is not attributes.ATTR_NOT_SPECIFIED)
    return ('default' in resource[attribute_name] and
            attribute_name in target and
            target[attribute_name] is not attributes.ATTR_NOT_SPECIFIED and
            target[attribute_name] != resource[attribute_name]['default'])


def _should_validate_sub_attributes(attribute, sub_attr):
    """Verify that sub-attributes are iterable and should be validated."""
    validate = attribute.get('validate')
    return (validate and isinstance(sub_attr, abc.Iterable) and
            any([k.startswith('type:dict') and
                 v for (k, v) in validate.items()]))


def _build_subattr_match_rule(attr_name, attr, action, target):
    """Create the rule to match for sub-attribute policy checks."""
    # TODO(salv-orlando): Instead of relying on validator info, introduce
    # typing for API attributes
    # Expect a dict as type descriptor
    validate = attr['validate']
    key = list(filter(lambda k: k.startswith('type:dict'), validate.keys()))
    if not key:
        LOG.warning("Unable to find data type descriptor for attribute %s",
                    attr_name)
        return
    data = validate[key[0]]
    if not isinstance(data, dict):
        LOG.debug("Attribute type descriptor is not a dict. Unable to "
                  "generate any sub-attr policy rule for %s.",
                  attr_name)
        return
    sub_attr_rules = [policy.RuleCheck('rule', '%s:%s:%s' %
                                       (action, attr_name,
                                        sub_attr_name)) for
                      sub_attr_name in data if sub_attr_name in
                      target[attr_name]]
    return policy.AndCheck(sub_attr_rules)


def _process_rules_list(rules, match_rule):
    """Recursively walk a policy rule to extract a list of match entries."""
    if isinstance(match_rule, policy.RuleCheck):
        rules.append(match_rule.match)
    elif isinstance(match_rule, policy.AndCheck):
        for rule in match_rule.rules:
            _process_rules_list(rules, rule)
    return rules


def _build_match_rule(action, target, pluralized):
    """Create the rule to match for a given action.

    The policy rule to be matched is built in the following way:
    1) add entries for matching permission on objects
    2) add an entry for the specific action (e.g.: create_network)
    3) add an entry for attributes of a resource for which the action
       is being executed (e.g.: create_network:shared)
    4) add an entry for sub-attributes of a resource for which the
       action is being executed
       (e.g.: create_router:external_gateway_info:network_id)
    """
    match_rule = policy.RuleCheck('rule', action)
    resource, enforce_attr_based_check = get_resource_and_action(
        action, pluralized)
    if enforce_attr_based_check:
        # assigning to variable with short name for improving readability
        res_map = attributes.RESOURCE_ATTRIBUTE_MAP
        if resource in res_map:
            for attribute_name in res_map[resource]:
                if _is_attribute_explicitly_set(attribute_name,
                                                res_map[resource],
                                                target, action):
                    attribute = res_map[resource][attribute_name]
                    if 'enforce_policy' in attribute:
                        attr_rule = policy.RuleCheck('rule', '%s:%s' %
                                                     (action, attribute_name))
                        # Build match entries for sub-attributes
                        if _should_validate_sub_attributes(
                                attribute, target[attribute_name]):
                            attr_rule = policy.AndCheck(
                                [attr_rule, _build_subattr_match_rule(
                                    attribute_name, attribute,
                                    action, target)])
                        match_rule = policy.AndCheck([match_rule, attr_rule])
    return match_rule


# This check is registered as 'tenant_id' so that it can override
# GenericCheck which was used for validating parent resource ownership.
# This will prevent us from having to handling backward compatibility
# for policy.yaml
# TODO(salv-orlando): Reinstate GenericCheck for simple tenant_id checks
@policy.register('tenant_id')
class OwnerCheck(policy.Check):
    """Resource ownership check.

    This check verifies the owner of the current resource, or of another
    resource referenced by the one under analysis.
    In the former case it falls back to a regular GenericCheck, whereas
    in the latter case it leverages the plugin to load the referenced
    resource and perform the check.
    """
    def __init__(self, kind, match):
        # Process the match
        try:
            self.target_field = re.findall(r'^\%\((.*)\)s$',
                                           match)[0]
        except IndexError:
            err_reason = (_("Unable to identify a target field from: %s. "
                            "Match should be in the form %%(<field_name>)s") %
                          match)
            LOG.exception(err_reason)
            raise exceptions.PolicyInitError(
                policy="%s:%s" % (kind, match),
                reason=err_reason)
        super(OwnerCheck, self).__init__(kind, match)

    def __call__(self, target, creds, enforcer):
        if self.target_field not in target:
            # policy needs a plugin check
            # target field is in the form resource:field
            # however if they're not separated by a colon, use an underscore
            # as a separator for backward compatibility

            def do_split(separator):
                parent_res, parent_field = self.target_field.split(
                    separator, 1)
                return parent_res, parent_field

            for separator in (':', '_'):
                try:
                    parent_res, parent_field = do_split(separator)
                    break
                except ValueError:
                    LOG.debug("Unable to find ':' as separator in %s.",
                              self.target_field)
            else:
                # If we are here split failed with both separators
                err_reason = ("Unable to find resource name in %s" %
                              self.target_field)
                LOG.error(err_reason)
                raise exceptions.PolicyCheckError(
                    policy="%s:%s" % (self.kind, self.match),
                    reason=err_reason)
            parent_foreign_key = attributes.RESOURCE_FOREIGN_KEYS.get(
                "%ss" % parent_res, None)
            if not parent_foreign_key:
                err_reason = ("Unable to verify match:%(match)s as the "
                              "parent resource: %(res)s was not found" %
                              {'match': self.match, 'res': parent_res})
                LOG.error(err_reason)
                raise exceptions.PolicyCheckError(
                    policy="%s:%s" % (self.kind, self.match),
                    reason=err_reason)
            # NOTE(salv-orlando): This check currently assumes the parent
            # resource is handled by the core plugin. It might be worth
            # having a way to map resources to plugins so to make this
            # check more general
            # NOTE(ihrachys): if import is put in global, circular
            # import failure occurs
            manager = importutils.import_module('tacker.manager')
            f = getattr(manager.TackerManager.get_instance().plugin,
                        'get_%s' % parent_res)
            # f *must* exist, if not found it is better to let tacker
            # explode. Check will be performed with admin context
            context = importutils.import_module('tacker.context')
            try:
                data = f(context.get_admin_context(),
                         target[parent_foreign_key],
                         fields=[parent_field])
                target[self.target_field] = data[parent_field]
            except exceptions.NotFound as e:
                # NOTE(kevinbenton): a NotFound exception can occur if a
                # list operation is happening at the same time as one of
                # the parents and its children being deleted. So we issue
                # a RetryRequest so the API will redo the lookup and the
                # problem items will be gone.
                raise db_exc.RetryRequest(e)
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.exception('Policy check error while calling %s!', f)
        match = self.match % target
        if self.kind in creds:
            return match == str(creds[self.kind])
        return False


@policy.register('field')
class FieldCheck(policy.Check):
    def __init__(self, kind, match):
        # Process the match
        resource, field_value = match.split(':', 1)
        field, value = field_value.split('=', 1)

        super(FieldCheck, self).__init__(kind, '%s:%s:%s' %
                                         (resource, field, value))

        # Value might need conversion - we need help from the attribute map
        try:
            attr = attributes.RESOURCE_ATTRIBUTE_MAP[resource][field]
            conv_func = attr['convert_to']
        except KeyError:
            conv_func = lambda x: x  # noqa: E731

        self.field = field
        self.value = conv_func(value)
        self.regex = re.compile(value[1:]) if value.startswith('~') else None

    def __call__(self, target_dict, cred_dict, enforcer):
        target_value = target_dict.get(self.field)
        # target_value might be a boolean, explicitly compare with None
        if target_value is None:
            LOG.debug("Unable to find requested field: %(field)s in target: "
                      "%(target_dict)s",
                      {'field': self.field, 'target_dict': target_dict})
            return False
        if self.regex:
            return bool(self.regex.match(target_value))
        return target_value == self.value


def _prepare_check(context, action, target, pluralized):
    """Prepare rule, target, and credentials for the policy engine."""
    # Compare with None to distinguish case in which target is {}
    if target is None:
        target = {}
    match_rule = _build_match_rule(action, target, pluralized)
    credentials = context.to_dict()
    return match_rule, target, credentials


def log_rule_list(match_rule):
    if LOG.isEnabledFor(logging.DEBUG):
        rules = _process_rules_list([], match_rule)
        LOG.debug("Enforcing rules: %s", rules)


def check(context, action, target, plugin=None, might_not_exist=False,
          pluralized=None):
    """Verifies that the action is valid on the target in this context.

    :param context: tacker context
    :param action: string representing the action to be checked
        this should be colon separated for clarity.
    :param target: dictionary representing the object of the action
        for object creation this should be a dictionary representing the
        location of the object e.g. ``{'project_id': context.project_id}``
    :param plugin: currently unused and deprecated.
        Kept for backward compatibility.
    :param might_not_exist: If True the policy check is skipped (and the
        function returns True) if the specified policy does not exist.
        Defaults to false.
    :param pluralized: pluralized case of resource
        e.g. firewall_policy -> pluralized = "firewall_policies"

    :return: Returns True if access is permitted else False.
    """
    # If we already know the context has admin rights do not perform an
    # additional check and authorize the operation
    if context.is_admin:
        return True
    if might_not_exist and not (_ENFORCER.rules and action in _ENFORCER.rules):
        return True
    match_rule, target, credentials = _prepare_check(context,
                                                     action,
                                                     target,
                                                     pluralized)
    target = copy.copy(target)
    if 'area' not in target:
        area = target.get('extra', {}).get('area')
        if area:
            target.update({'area': area})
    if 'tenant_id' in target:
        target['project_id'] = target['tenant_id']
    target, credentials = _pre_enhanced_policy_check(target, credentials)

    result = _ENFORCER.enforce(match_rule,
                               target,
                               credentials,
                               pluralized=pluralized)
    # logging applied rules in case of failure
    if not result:
        log_rule_list(match_rule)
    return result


def enforce(context, action, target, plugin=None, pluralized=None,
            exc=exceptions.PolicyNotAuthorized):
    """Verifies that the action is valid on the target in this context.

    :param context: tacker context
    :param action: string representing the action to be checked
        this should be colon separated for clarity.
    :param target: dictionary representing the object of the action
        for object creation this should be a dictionary representing the
        location of the object e.g. ``{'project_id': context.project_id}``
    :param plugin: currently unused and deprecated.
        Kept for backward compatibility.
    :param pluralized: pluralized case of resource
        e.g. firewall_policy -> pluralized = "firewall_policies"
    :param exc: Class of the exception to raise if the check fails.
            If not specified, :class:`PolicyNotAuthorized` will be used.

    :raises tacker.common.exceptions.PolicyNotAuthorized or exc specified by
            caller:
                if verification fails.
    """
    # If we already know the context has admin rights do not perform an
    # additional check and authorize the operation
    if context.is_admin:
        return True
    rule, target, credentials = _prepare_check(context,
                                               action,
                                               target,
                                               pluralized)
    target = copy.copy(target)
    if 'area' not in target:
        area = target.get('extra', {}).get('area')
        if area:
            target.update({'area': area})
    if 'tenant_id' in target:
        target['project_id'] = target['tenant_id']
    target, credentials = _pre_enhanced_policy_check(target, credentials)

    try:
        result = _ENFORCER.enforce(rule, target, credentials, action=action,
                                   do_raise=True, exc=exc)
    except Exception:
        with excutils.save_and_reraise_exception():
            log_rule_list(rule)
            LOG.error("Failed policy check for '%s'", action)
    return result


def check_is_admin(context):
    """Verify context has admin rights according to policy settings."""
    init()
    # the target is user-self
    credentials = context.to_policy_values()
    try:
        return _ENFORCER.authorize(ADMIN_CTX_POLICY, credentials, credentials)
    except policy.PolicyNotRegistered:
        return False


def register_rules(enforcer):
    enforcer.register_defaults(policies.list_rules())


def get_enforcer():
    # NOTE(amotoki): This was borrowed from nova/policy.py.
    # This method is for use by oslo.policy CLI scripts. Those scripts need the
    # 'output-file' and 'namespace' options, but having those in sys.argv means
    # loading the tacker config options will fail as those are not expected to
    # be present. So we pass in an arg list with those stripped out.
    conf_args = []
    # Start at 1 because cfg.CONF expects the equivalent of sys.argv[1:]
    i = 1
    while i < len(sys.argv):
        if sys.argv[i].strip('-') in ['namespace', 'output-file']:
            i += 2
            continue
        conf_args.append(sys.argv[i])
        i += 1

    # 'project' must be 'tacker' so that get_enforcer looks at
    # /etc/tacker/policy.yaml by default.
    cfg.CONF(conf_args, project='tacker')
    init()
    return _ENFORCER
