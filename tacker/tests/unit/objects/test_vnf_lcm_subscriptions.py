# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from unittest import mock

from tacker import context
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel


class TestVnfd(SqlTestCase):

    def setUp(self):
        super(TestVnfd, self).setUp()
        self.context = context.get_admin_context()
        self.vnf_package = self._create_vnf_package()
        self.vnf_package_vnfd = self._create_and_upload_vnf_package_vnfd()
        self.subscription = self._create_subscription()

    def _create_vnf_package(self):
        vnfpkgm = objects.VnfPackage(context=self.context,
                                     **fakes.vnf_package_data)
        vnfpkgm.create()
        return vnfpkgm

    def _create_and_upload_vnf_package_vnfd(self):
        vnf_package = objects.VnfPackage(context=self.context,
                                         **fakes.vnf_package_data)
        vnf_package.create()

        vnf_pack_vnfd = fakes.get_vnf_package_vnfd_data(
            vnf_package.id, uuidsentinel.vnfd_id)

        vnf_pack_vnfd_obj = objects.VnfPackageVnfd(
            context=self.context, **vnf_pack_vnfd)
        vnf_pack_vnfd_obj.create()

        return vnf_pack_vnfd_obj

    @mock.patch.object(objects.vnf_lcm_subscriptions,
                       '_vnf_lcm_subscriptions_create')
    def _create_subscription(self, mock_vnf_lcm_subscriptions_create):
        filter = fakes.filter
        mock_vnf_lcm_subscriptions_create.return_value = \
            '{\
                "filter": "{"operationStates": ["COMPLETED"],\
                "vnfInstanceNames": ["xxxxxxxxxxxxxxxxxx"],\
                "operationTypes": ["INSTANTIATE"],\
                "vnfdIds": ["405d73c7-e964-4c8b-a914-41478ccd7c42"],\
                "vnfProductsFromProviders": [{\
                    "vnfProvider": "x2x", \
                    "vnfProducts": [{\
                        "vnfProductName": "x2xx", \
                        "versions": [{\
                            "vnfSoftwareVersion": "xx2XX", \
                            "vnfdVersions": ["ss2"]\
                        }]\
                    }]\
                }, \
                {\
                    "vnfProvider": "z2z",\
                    "vnfProducts": [{\
                        "vnfProductName": "z2zx", \
                        "versions": [{\
                            "vnfSoftwareVersion": "xx3XX",\
                            "vnfdVersions": \
                            ["s3sx", "s3sa"]\
                        }\
                    ]},\
                    {\
                        "vnfProductName": "zz3ex",\
                        "versions": [{\
                            "vnfSoftwareVersion": "xxe3eXz",\
                            "vnfdVersions": ["ss3xz", "s3esaz"]\
                        },\
                        {\
                            "vnfSoftwareVersion": "xxeeeXw", \
                            "vnfdVersions": ["ss3xw", "ss3w"]\
                        }]\
                    }]\
                }],\
                "notificationTypes": [\
                    "VnfLcmOperationOccurrenceNotification"],\
                "vnfInstanceIds": ["fb0b9a12-4b55-47ac-9ca8-5fdd52c4c07f"]}",\
                "callbackUri": "http://localhost/xxx",\
                "_links": {\
                    "self": {\
                        "href":\
                            "http://localhost:9890//vnflcm/v1/subscriptions\
                            /530a3c43-043a-4b84-9d65-aa0df49f7ced"\
                    }\
                },\
                "id": "530a3c43-043a-4b84-9d65-aa0df49f7ced"\
            }'

        subscription_obj = \
            objects.vnf_lcm_subscriptions.LccnSubscriptionRequest(
                context=self.context, **fakes.subscription_data)
        subscription_obj.create(filter)

        return subscription_obj

    @mock.patch.object(objects.vnf_lcm_subscriptions,
                       '_vnf_lcm_subscriptions_create')
    def test_create(self, mock_vnf_lcm_subscriptions_create):
        filter = fakes.filter
        subscription_obj = \
            objects.vnf_lcm_subscriptions.LccnSubscriptionRequest(
                context=self.context)
        mock_vnf_lcm_subscriptions_create.return_value = \
            '{\
                "filter": "{"operationStates": ["COMPLETED"],\
                "vnfInstanceNames": ["xxxxxxxxxxxxxxxxxx"],\
                "operationTypes": ["INSTANTIATE"],\
                "vnfdIds": ["405d73c7-e964-4c8b-a914-41478ccd7c42"],\
                "vnfProductsFromProviders": [{\
                    "vnfProvider": "x2x", \
                    "vnfProducts": [{\
                        "vnfProductName": "x2xx", \
                        "versions": [{\
                            "vnfSoftwareVersion": "xx2XX", \
                            "vnfdVersions": ["ss2"]\
                        }]\
                    }]\
                }, \
                {\
                    "vnfProvider": "z2z",\
                    "vnfProducts": [{\
                        "vnfProductName": "z2zx", \
                        "versions": [{\
                            "vnfSoftwareVersion": "xx3XX",\
                            "vnfdVersions": \
                            ["s3sx", "s3sa"]\
                        }\
                    ]},\
                    {\
                        "vnfProductName": "zz3ex",\
                        "versions": [{\
                            "vnfSoftwareVersion": "xxe3eXz",\
                            "vnfdVersions": ["ss3xz", "s3esaz"]\
                        },\
                        {\
                            "vnfSoftwareVersion": "xxeeeXw", \
                            "vnfdVersions": ["ss3xw", "ss3w"]\
                        }]\
                    }]\
                }],\
                "notificationTypes": [\
                    "VnfLcmOperationOccurrenceNotification"],\
                "vnfInstanceIds": ["fb0b9a12-4b55-47ac-9ca8-5fdd52c4c07f"]}",\
                "callbackUri": "http://localhost/xxx",\
                "_links": {\
                    "self": {\
                        "href":\
                            "http://localhost:9890//vnflcm/v1/subscriptions\
                            /530a3c43-043a-4b84-9d65-aa0df49f7ced"\
                    }\
                },\
                "id": "530a3c43-043a-4b84-9d65-aa0df49f7ced"\
            }'

        result = subscription_obj.create(filter)
        self.assertTrue(filter, result)

    @mock.patch.object(objects.vnf_lcm_subscriptions,
                       '_vnf_lcm_subscriptions_show')
    def test_show(self, mock_vnf_lcm_subscriptions_show):
        filter = fakes.filter
        subscription_obj = \
            objects.vnf_lcm_subscriptions.LccnSubscriptionRequest(
                context=self.context)
        mock_vnf_lcm_subscriptions_show.return_value = \
            '{\
                "filter": "{"operationStates": ["COMPLETED"],\
                "vnfInstanceNames": ["xxxxxxxxxxxxxxxxxx"],\
                "operationTypes": ["INSTANTIATE"],\
                "vnfdIds": ["405d73c7-e964-4c8b-a914-41478ccd7c42"],\
                "vnfProductsFromProviders": [{\
                    "vnfProvider": "x2x", \
                    "vnfProducts": [{\
                        "vnfProductName": "x2xx", \
                        "versions": [{\
                            "vnfSoftwareVersion": "xx2XX", \
                            "vnfdVersions": ["ss2"]\
                        }]\
                    }]\
                }, \
                {\
                    "vnfProvider": "z2z",\
                    "vnfProducts": [{\
                        "vnfProductName": "z2zx", \
                        "versions": [{\
                            "vnfSoftwareVersion": "xx3XX",\
                            "vnfdVersions": \
                            ["s3sx", "s3sa"]\
                        }\
                    ]},\
                    {\
                        "vnfProductName": "zz3ex",\
                        "versions": [{\
                            "vnfSoftwareVersion": "xxe3eXz",\
                            "vnfdVersions": ["ss3xz", "s3esaz"]\
                        },\
                        {\
                            "vnfSoftwareVersion": "xxeeeXw", \
                            "vnfdVersions": ["ss3xw", "ss3w"]\
                        }]\
                    }]\
                }],\
                "notificationTypes": [\
                    "VnfLcmOperationOccurrenceNotification"],\
                "vnfInstanceIds": ["fb0b9a12-4b55-47ac-9ca8-5fdd52c4c07f"]}",\
                "callbackUri": "http://localhost/xxx",\
                "_links": {\
                    "self": {\
                        "href":\
                            "http://localhost:9890//vnflcm/v1/subscriptions\
                            /530a3c43-043a-4b84-9d65-aa0df49f7ced"\
                    }\
                },\
                "id": "530a3c43-043a-4b84-9d65-aa0df49f7ced"\
            }'

        result = subscription_obj.vnf_lcm_subscriptions_show(
            self.context, self.subscription.id)
        self.assertTrue(filter, result)

    @mock.patch.object(objects.vnf_lcm_subscriptions,
                       '_vnf_lcm_subscriptions_all')
    def test_list(self, mock_vnf_lcm_subscriptions_all):
        filter = fakes.filter
        subscription_obj = \
            objects.vnf_lcm_subscriptions.LccnSubscriptionRequest(
                context=self.context)
        mock_vnf_lcm_subscriptions_all.return_value = \
            '{\
                "filter": "{"operationStates": ["COMPLETED"],\
                "vnfInstanceNames": ["xxxxxxxxxxxxxxxxxx"],\
                "operationTypes": ["INSTANTIATE"],\
                "vnfdIds": ["405d73c7-e964-4c8b-a914-41478ccd7c42"],\
                "vnfProductsFromProviders": [{\
                    "vnfProvider": "x2x", \
                    "vnfProducts": [{\
                        "vnfProductName": "x2xx", \
                        "versions": [{\
                            "vnfSoftwareVersion": "xx2XX", \
                            "vnfdVersions": ["ss2"]\
                        }]\
                    }]\
                }, \
                {\
                    "vnfProvider": "z2z",\
                    "vnfProducts": [{\
                        "vnfProductName": "z2zx", \
                        "versions": [{\
                            "vnfSoftwareVersion": "xx3XX",\
                            "vnfdVersions": \
                            ["s3sx", "s3sa"]\
                        }\
                    ]},\
                    {\
                        "vnfProductName": "zz3ex",\
                        "versions": [{\
                            "vnfSoftwareVersion": "xxe3eXz",\
                            "vnfdVersions": ["ss3xz", "s3esaz"]\
                        },\
                        {\
                            "vnfSoftwareVersion": "xxeeeXw", \
                            "vnfdVersions": ["ss3xw", "ss3w"]\
                        }]\
                    }]\
                }],\
                "notificationTypes": [\
                    "VnfLcmOperationOccurrenceNotification"],\
                "vnfInstanceIds": ["fb0b9a12-4b55-47ac-9ca8-5fdd52c4c07f"]}",\
                "callbackUri": "http://localhost/xxx",\
                "_links": {\
                    "self": {\
                        "href":\
                            "http://localhost:9890//vnflcm/v1/subscriptions\
                            /530a3c43-043a-4b84-9d65-aa0df49f7ced"\
                    }\
                },\
                "id": "530a3c43-043a-4b84-9d65-aa0df49f7ced"\
            }'

        result = subscription_obj.vnf_lcm_subscriptions_list(self.context)
        self.assertTrue(filter, result)

    @mock.patch.object(objects.vnf_lcm_subscriptions,
                       '_destroy_vnf_lcm_subscription')
    @mock.patch.object(objects.vnf_lcm_subscriptions, '_get_by_subscriptionid')
    def test_destroy(self, mock_get_by_subscriptionid,
                     mock_vnf_lcm_subscriptions_destroy):
        mock_get_by_subscriptionid.result_value = "OK"
        self.subscription.destroy(self.context, self.subscription.id)
        mock_vnf_lcm_subscriptions_destroy.assert_called_with(
            self.context, self.subscription.id)
