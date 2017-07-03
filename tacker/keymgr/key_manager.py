# Copyright (c) 2015 The Johns Hopkins University/Applied Physics Laboratory
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
Key manager API
"""

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class KeyManager(object):
    """Base Key Manager Interface

    A Key Manager is responsible for creating, reading, and deleting keys.
    """

    @abc.abstractmethod
    def __init__(self, auth_url):
        """Instantiate a KeyManager object.

        Creates a KeyManager object with implementation specific details
        obtained from the supplied configuration.
        """
        pass

    @abc.abstractmethod
    def store(self, context, managed_object, expiration=None):
        """Stores a managed object with the key manager.

        This method stores the specified managed object and returns its UUID
        that identifies it within the key manager. If the specified context
        does not permit the creation of keys, then a NotAuthorized exception
        should be raised.
        """
        pass

    @abc.abstractmethod
    def get(self, context, managed_object_id, metadata_only=False):
        """Retrieves the specified managed object.

        Implementations should verify that the caller has permissions to
        retrieve the managed object by checking the context object passed in
        as context. If the user lacks permission then a NotAuthorized
        exception is raised.

        If the caller requests only metadata, then the object that is
        returned will contain only the secret metadata and no secret bytes.

        If the specified object does not exist, then a KeyError should be
        raised. Implementations should preclude users from discerning the
        UUIDs of objects that belong to other users by repeatedly calling
        this method. That is, objects that belong to other users should be
        considered "non-existent" and completely invisible.
        """
        pass

    @abc.abstractmethod
    def delete(self, context, managed_object_id):
        """Deletes the specified managed object.

        Implementations should verify that the caller has permission to delete
        the managed object by checking the context object (context). A
        NotAuthorized exception should be raised if the caller lacks
        permission.

        If the specified object does not exist, then a KeyError should be
        raised. Implementations should preclude users from discerning the
        UUIDs of objects that belong to other users by repeatedly calling this
        method. That is, objects that belong to other users should be
        considered "non-existent" and completely invisible.
        """
        pass
