# Copyright (c) The Johns Hopkins University/Applied Physics Laboratory
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
Key manager implementation for Barbican
"""
from barbicanclient import client as barbican_client
from barbicanclient import exceptions as barbican_exception
from keystoneauth1 import identity
from keystoneauth1 import session
from oslo_log import log as logging

from tacker._i18n import _
from tacker.keymgr import exception
from tacker.keymgr import key_manager


LOG = logging.getLogger(__name__)


class BarbicanKeyManager(key_manager.KeyManager):
    """Key Manager Interface that wraps the Barbican client API."""

    def __init__(self, auth_url):
        self._barbican_client = None
        self._base_url = None
        self._auth_url = auth_url

    def _get_barbican_client(self, context):
        """Creates a client to connect to the Barbican service.

        :param context: the user context for authentication
        :return: a Barbican Client object
        :raises Forbidden: if the context is empty
        :raises KeyManagerError: if context is missing tenant or tenant is
                                 None or error occurs while creating client
        """

        # Confirm context is provided, if not raise forbidden
        if not context:
            msg = _("User is not authorized to use key manager.")
            LOG.error(msg)
            raise exception.Forbidden(msg)

        if self._barbican_client and self._current_context == context:
            return self._barbican_client

        try:
            auth = self._get_keystone_auth(context)
            sess = session.Session(auth=auth)

            self._barbican_endpoint = self._get_barbican_endpoint(auth, sess)
            if self._barbican_endpoint[-1] != '/':
                self._barbican_endpoint += '/'
            self._barbican_client = barbican_client.Client(
                session=sess,
                endpoint=self._barbican_endpoint)
            self._current_context = context

        except Exception as e:
            LOG.error("Error creating Barbican client: %s", e)
            raise exception.KeyManagerError(reason=e)

        self._base_url = self._create_base_url(auth,
                                               sess,
                                               self._barbican_endpoint)

        return self._barbican_client

    def _get_keystone_auth(self, context):

        if context.__class__.__name__ is 'KeystonePassword':
            return identity.Password(
                auth_url=self._auth_url,
                username=context.username,
                password=context.password,
                user_id=context.user_id,
                user_domain_id=context.user_domain_id,
                user_domain_name=context.user_domain_name,
                trust_id=context.trust_id,
                domain_id=context.domain_id,
                domain_name=context.domain_name,
                project_id=context.project_id,
                project_name=context.project_name,
                project_domain_id=context.project_domain_id,
                project_domain_name=context.project_domain_name,
                reauthenticate=context.reauthenticate)
        elif context.__class__.__name__ is 'KeystoneToken':
            return identity.Token(
                auth_url=self._auth_url,
                token=context.token,
                trust_id=context.trust_id,
                domain_id=context.domain_id,
                domain_name=context.domain_name,
                project_id=context.project_id,
                project_name=context.project_name,
                project_domain_id=context.project_domain_id,
                project_domain_name=context.project_domain_name,
                reauthenticate=context.reauthenticate)
        # this will be kept for oslo.context compatibility until
        # projects begin to use utils.credential_factory
        elif (context.__class__.__name__ is 'RequestContext' or
              context.__class__.__name__ is 'Context'):
            return identity.Token(
                auth_url=self._auth_url,
                token=context.auth_token,
                project_id=context.tenant)
        else:
            msg = _("context must be of type KeystonePassword, "
                    "KeystoneToken, RequestContext, or Context.")
            LOG.error(msg)
            raise exception.Forbidden(reason=msg)

    def _get_barbican_endpoint(self, auth, sess):
        service_parameters = {'service_type': 'key-manager',
                              'service_name': 'barbican',
                              'interface': 'internal'}
        return auth.get_endpoint(sess, **service_parameters)

    def _create_base_url(self, auth, sess, endpoint):
        discovery = auth.get_discovery(sess, url=endpoint)
        raw_data = discovery.raw_version_data()
        if len(raw_data) == 0:
            msg = _(
                "Could not find discovery information for %s") % endpoint
            LOG.error(msg)
            raise exception.KeyManagerError(reason=msg)
        latest_version = raw_data[-1]
        api_version = latest_version.get('id')
        base_url = "%s%s/" % (endpoint, api_version)
        return base_url

    def store(self, context, secret, expiration=None):
        """Stores a secret with the key manager.

        :param context: contains information of the user and the environment
            for the request
        :param secret: a secret object with unencrypted payload.
            Known as "secret" to the barbicanclient api
        :param expiration: the expiration time of the secret in ISO 8601
            format
        :returns: the UUID of the stored object
        :raises KeyManagerError: if object store fails
        """
        barbican_client = self._get_barbican_client(context)

        try:
            secret = barbican_client.secrets.create(
                payload=secret,
                secret_type='opaque')
            secret.expiration = expiration
            secret_ref = secret.store()
            return self._retrieve_secret_uuid(secret_ref)
        except (barbican_exception.HTTPAuthError,
                barbican_exception.HTTPClientError,
                barbican_exception.HTTPServerError) as e:
            LOG.error("Error storing object: %s", e)
            raise exception.KeyManagerError(reason=e)

    def _create_secret_ref(self, object_id):
        """Creates the URL required for accessing a secret.

        :param object_id: the UUID of the key to copy
        :return: the URL of the requested secret
        """
        if not object_id:
            msg = _("Key ID is None")
            raise exception.KeyManagerError(reason=msg)
        return "%ssecrets/%s" % (self._base_url, object_id)

    def _retrieve_secret_uuid(self, secret_ref):
        """Retrieves the UUID of the secret from the secret_ref.

        :param secret_ref: the href of the secret
        :return: the UUID of the secret
        """

        # The secret_ref is assumed to be of a form similar to
        # http://host:9311/v1/secrets/d152fa13-2b41-42ca-a934-6c21566c0f40
        # with the UUID at the end. This command retrieves everything
        # after the last '/', which is the UUID.
        return secret_ref.rpartition('/')[2]

    def _is_secret_not_found_error(self, error):
        if (isinstance(error, barbican_exception.HTTPClientError) and
                error.status_code == 404):
            return True
        else:
            return False

    def get(self, context, managed_object_id, metadata_only=False):
        """Retrieves the specified managed object.

        :param context: contains information of the user and the environment
                        for the request
        :param managed_object_id: the UUID of the object to retrieve
        :param metadata_only: whether secret data should be included
        :return: ManagedObject representation of the managed object
        :raises KeyManagerError: if object retrieval fails
        :raises ManagedObjectNotFoundError: if object not found
        """
        barbican_client = self._get_barbican_client(context)

        try:
            secret_ref = self._create_secret_ref(managed_object_id)
            return barbican_client.secrets.get(secret_ref)
        except (barbican_exception.HTTPAuthError,
                barbican_exception.HTTPClientError,
                barbican_exception.HTTPServerError) as e:
            LOG.error("Error retrieving object: %s", e)
            if self._is_secret_not_found_error(e):
                raise exception.ManagedObjectNotFoundError(
                    uuid=managed_object_id)
            else:
                raise exception.KeyManagerError(reason=e)

    def delete(self, context, managed_object_id):
        """Deletes the specified managed object.

        :param context: contains information of the user and the environment
                     for the request
        :param managed_object_id: the UUID of the object to delete
        :raises KeyManagerError: if object deletion fails
        :raises ManagedObjectNotFoundError: if the object could not be found
        """
        barbican_client = self._get_barbican_client(context)

        try:
            secret_ref = self._create_secret_ref(managed_object_id)
            barbican_client.secrets.delete(secret_ref)
        except (barbican_exception.HTTPAuthError,
                barbican_exception.HTTPClientError,
                barbican_exception.HTTPServerError) as e:
            LOG.error("Error deleting object: %s", e)
            if self._is_secret_not_found_error(e):
                raise exception.ManagedObjectNotFoundError(
                    uuid=managed_object_id)
            else:
                raise exception.KeyManagerError(reason=e)
