.. -*- rst -*-

======================================================================
Virtualized Network Function Performance Management Interface (VNF PM)
======================================================================

This interface manages the VNF performance management operations of VNF
instances.

This interface allows providing performance management (measurement results
collection and notifications) related to VNFs. The detail of this interface
is described in SOL002 v3.3.1 clause 6. The parameters of some specific
standards need reference SOL013 v3.4.1 clause 5.

Create a PM job (v2)
====================

.. rest_method::  POST /vnfpm/v2/pm_jobs

The POST method creates a new PM job. PM jobs group details of performance
collection and reporting information.

As the result of successfully executing this method, a new PM job shall have
been created, and return detailed PM job data. In case of failure, including
an invalid notification endpoint, appropriate error information is provided in
the response.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 201

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 406
  - 409
  - 422
  - 503

Request Parameters
------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - objectType: vnf_pm_job_create_object_type
  - objectInstanceIds: vnf_pm_job_create_object_instance_ids
  - subObjectInstanceIds: vnf_pm_job_create_sub_object_instance_ids
  - criteria: vnf_pm_job_create_criteria
  - performanceMetric: criteria_performance_metric
  - performanceMetricGroup: criteria_performance_metric_group
  - collectionPeriod: criteria_collection_period
  - reportingPeriod: criteria_reporting_period
  - reportingBoundary: criteria_reporting_boundary
  - callbackUri: vnf_pm_job_create_callback_uri
  - authentication: vnf_pm_job_create_request_authentication
  - authType: authentication_auth_type
  - paramsBasic: authentication_params_basic
  - userName: paramsBasic_userName
  - password: paramsBasic_password
  - paramsOauth2ClientCredentials: authentication_params_oauth2_client_credentials
  - clientId: params_oauth2_client_credentials_client_id
  - clientPassword: params_oauth2_client_credentials_client_password
  - tokenEndpoint: params_oauth2_client_credentials_token_endpoint
  - paramsOauth2ClientCert: authentication_params_oauth2_client_cert
  - clientId: params_oauth2_client_cert_client_id
  - certificateRef: params_oauth2_client_cert_certificate_ref
  - type: params_oauth2_client_cert_type
  - value: params_oauth2_client_cert_value
  - tokenEndpoint: params_oauth2_client_cert_token_endpoint
  - metadata: vnf_pm_job_create_metadata

Request Example
---------------

.. literalinclude:: samples/vnfpm/create-pm-job-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - id: vnf_pm_job_response_id
  - objectType: vnf_pm_job_create_object_type
  - objectInstanceIds: vnf_pm_job_create_object_instance_ids
  - subObjectInstanceIds: vnf_pm_job_create_sub_object_instance_ids
  - criteria: vnf_pm_job_create_criteria
  - performanceMetric: criteria_performance_metric
  - performanceMetricGroup: criteria_performance_metric_group
  - collectionPeriod: criteria_collection_period
  - reportingPeriod: criteria_reporting_period
  - reportingBoundary: criteria_reporting_boundary
  - callbackUri: vnf_pm_job_response_callback_uri
  - reports: vnf_pm_job_reports
  - href: reports_href
  - readyTime: reports_ready_time
  - expiryTime: reports_expiry_time
  - fileSize: reports_file_size
  - _links: pm_job_links
  - self: links_self
  - objects: links_objects

Response Example
----------------

.. literalinclude:: samples/vnfpm/create-pm-job-response.json
   :language: javascript

Get for PM jobs (v2)
====================

.. rest_method::  GET /vnfpm/v2/pm_jobs

The GET method allows users to filter out PM jobs based on query parameter in
the request.

It supports attribute-based filtering and attribute selectors defined in ETSI
NFV SOL013 v3.4.1. The detail of attribute-based filtering is described in
SOL013 v3.4.1 clause 5.2. The detail of attribute selectors is described in
SOL013 v3.4.1 clause 5.3.

An attribute selector allows the API consumer to choose which attributes it
wants to be contained in the response. *all_fields*, *fields*, *exclude_fields*
and *exclude_default* can be set as query parameters.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 406

Response Parameters
-------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - id: vnf_pm_job_response_id
  - objectType: vnf_pm_job_create_object_type
  - objectInstanceIds: vnf_pm_job_create_object_instance_ids
  - subObjectInstanceIds: vnf_pm_job_create_sub_object_instance_ids
  - criteria: vnf_pm_job_create_criteria
  - performanceMetric: criteria_performance_metric
  - performanceMetricGroup: criteria_performance_metric_group
  - collectionPeriod: criteria_collection_period
  - reportingPeriod: criteria_reporting_period
  - reportingBoundary: criteria_reporting_boundary
  - callbackUri: vnf_pm_job_response_callback_uri
  - reports: vnf_pm_job_reports
  - href: reports_href
  - readyTime: reports_ready_time
  - expiryTime: reports_expiry_time
  - fileSize: reports_file_size
  - _links: pm_job_links
  - self: links_self
  - objects: links_objects

Response Example
----------------

.. literalinclude:: samples/vnfpm/list-pm-job-response.json
   :language: javascript

Get a PM job (v2)
=================

.. rest_method::  GET /vnfpm/v2/pm_jobs/{pmJobId}

The GET method gets an individual PM job.

If the API consumer intends to read information about a particular PM job,
it sends a GET request to the "Individual PM job" resource, addressed by the
appropriate PM job identifier in its resource URI. The VNFM returns a "200 OK"
response to the API consumer, and includes one data structure of type "PmJob"
in the payload body. In case of failure, appropriate error information is
provided in the response.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404

Request Parameters
------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - pmJobId: vnf_pm_job_id

Response Parameters
-------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - id: vnf_pm_job_response_id
  - objectType: vnf_pm_job_create_object_type
  - objectInstanceIds: vnf_pm_job_create_object_instance_ids
  - subObjectInstanceIds: vnf_pm_job_create_sub_object_instance_ids
  - criteria: vnf_pm_job_create_criteria
  - performanceMetric: criteria_performance_metric
  - performanceMetricGroup: criteria_performance_metric_group
  - collectionPeriod: criteria_collection_period
  - reportingPeriod: criteria_reporting_period
  - reportingBoundary: criteria_reporting_boundary
  - callbackUri: vnf_pm_job_response_callback_uri
  - reports: vnf_pm_job_reports
  - href: reports_href
  - readyTime: reports_ready_time
  - expiryTime: reports_expiry_time
  - fileSize: reports_file_size
  - _links: pm_job_links
  - self: links_self
  - objects: links_objects

Response Example
----------------

.. literalinclude:: samples/vnfpm/show-pm-job-response.json
   :language: javascript

Modify a PM job(v2)
===================

.. rest_method::  PATCH /vnfpm/v2/pm_jobs/{pmJobId}


The PATCH method Modifies a PM job.

If the API consumer intends to update the callback URI in a PM job, it sends
a PATCH request to the "Individual PM job" resource, including a data
structure of type "PmJobModifications" in the payload body.  The VNFM returns
a "200 OK" response to the API consumer and includes in the payload body a data
structure of type "PmJobModifications" to indicate the performed modifications.
However the authentication parameter shall not be present in response body.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 422

Request Parameters
------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - pmJobId: vnf_pm_job_id
  - callbackUri: vnf_pm_job_create_callback_uri
  - authentication: vnf_pm_job_create_request_authentication
  - authType: authentication_auth_type
  - paramsBasic: authentication_params_basic
  - userName: paramsBasic_userName
  - password: paramsBasic_password
  - paramsOauth2ClientCredentials: authentication_params_oauth2_client_credentials
  - clientId: params_oauth2_client_credentials_client_id
  - clientPassword: params_oauth2_client_credentials_client_password
  - tokenEndpoint: params_oauth2_client_credentials_token_endpoint
  - paramsOauth2ClientCert: authentication_params_oauth2_client_cert
  - clientId: params_oauth2_client_cert_client_id
  - certificateRef: params_oauth2_client_cert_certificate_ref
  - type: params_oauth2_client_cert_type
  - value: params_oauth2_client_cert_value
  - tokenEndpoint: params_oauth2_client_cert_token_endpoint

Request Example
---------------

.. literalinclude:: samples/vnfpm/update-pm-job-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - callbackUri: vnf_pm_job_response_callback_uri

Response Example
----------------

.. literalinclude:: samples/vnfpm/update-pm-job-response.json
   :language: javascript

Delete a PM job (v2)
====================

.. rest_method:: DELETE /vnfpm/v2/pm_jobs/{pmJobId}

The DELETE method deletes a PM job.

If the API consumer intends to delete a PM job, it sends a DELETE request to
the "Individual PM job" resource addressed by the appropriate PM job identifier
in its resource URI. The VNFM returns a response with a "204 No Content"
response code and an empty payload body to the API consumer.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404

Request Parameters
------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - pmJobId: vnf_pm_job_id

Get individual performance report (v2)
======================================

.. rest_method::  GET /vnfpm/v2/pm_jobs/{pmJobId}/reports/{reportId}

The GET method gets individual performance report.

The API consumer sends to the VNFM a GET request to the URI , in order to read
an "Individual performance report" resource. The VNFM returns a "200 OK"
response to the API consumer, and includes a data structure of type
"PerformanceReport" in the payload body.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404

Request Parameters
------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - pmJobId: vnf_pm_job_id
  - reportId: vnf_pm_job_report_id

Response Parameters
-------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - entries: vnf_pm_job_report_entries
  - objectType: vnf_pm_job_create_object_type
  - objectInstanceId: vnf_pm_job_report_entries_object_instance_id
  - subObjectInstanceId: vnf_pm_job_report_entries_sub_object_instance_id
  - performanceMetric: vnf_pm_job_report_entries_performance_metric
  - performanceValues: vnf_pm_job_report_entries_performance_values
  - timeStamp: performance_values_time_stamp
  - value: performance_values_value
  - context: performance_values_context

Response Example
----------------

.. literalinclude:: samples/vnfpm/show-pm-job-report-response.json
   :language: javascript

Create a PM threshold (v2)
==========================

.. rest_method:: POST /vnfpm/v2/thresholds

The POST method creates a new PM threshold.

As the result of successfully executing this method, a new PM threshold shall
have been created, and return detailed PM threshold data. In case of failure,
including an invalid notification endpoint, appropriate error information is
provided in the response.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 201

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404
  - 406
  - 409
  - 422
  - 503

Request Parameters
------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - objectType: vnf_pm_threshold_object_type
  - objectInstanceId: vnf_pm_threshold_object_instance_id
  - subObjectInstanceIds: vnf_pm_threshold_sub_object_instance_ids
  - criteria: vnf_pm_threshold_criteria
  - performanceMetric: vnf_pm_threshold_criteria_performance_metric
  - thresholdType: vnf_pm_threshold_type
  - simpleThresholdDetails: vnf_pm_threshold_simple_threshold_details
  - thresholdValue: vnf_pm_threshold_value
  - hysteresis: vnf_pm_threshold_hysteresis
  - callbackUri: vnf_pm_threshold_create_callback_uri
  - authentication: vnf_pm_threshold_create_request_authentication
  - authType: authentication_auth_type
  - paramsBasic: authentication_params_basic
  - userName: paramsBasic_userName
  - password: paramsBasic_password
  - paramsOauth2ClientCredentials: authentication_params_oauth2_client_credentials
  - clientId: params_oauth2_client_credentials_client_id
  - clientPassword: params_oauth2_client_credentials_client_password
  - tokenEndpoint: params_oauth2_client_credentials_token_endpoint
  - paramsOauth2ClientCert: authentication_params_oauth2_client_cert
  - clientId: params_oauth2_client_cert_client_id
  - certificateRef: params_oauth2_client_cert_certificate_ref
  - type: params_oauth2_client_cert_type
  - value: params_oauth2_client_cert_value
  - tokenEndpoint: params_oauth2_client_cert_token_endpoint
  - metadata: vnf_pm_threshold_create_metadata

Request Example
---------------

.. literalinclude:: samples/vnfpm/create-pm-threshold-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - id: vnf_pm_threshold_id_body
  - objectType: vnf_pm_threshold_object_type
  - objectInstanceId: vnf_pm_threshold_object_instance_id
  - subObjectInstanceIds: vnf_pm_threshold_sub_object_instance_ids
  - criteria: vnf_pm_threshold_criteria
  - performanceMetric: vnf_pm_threshold_criteria_performance_metric
  - thresholdType: vnf_pm_threshold_type
  - simpleThresholdDetails: vnf_pm_threshold_simple_threshold_details
  - thresholdValue: vnf_pm_threshold_value
  - hysteresis: vnf_pm_threshold_hysteresis
  - callbackUri: vnf_pm_threshold_response_callback_uri
  - _links: pm_threshold_links
  - self: links_self
  - object: vnf_pm_threshold_links_object

Response Example
----------------

.. literalinclude:: samples/vnfpm/create-pm-threshold-response.json
   :language: javascript

Get for PM thresholds (v2)
==========================

.. rest_method::  GET /vnfpm/v2/thresholds

The GET method allows users to filter out PM thresholds based on query
parameter in the request.

It supports attribute-based filtering and attribute selectors defined in ETSI
NFV SOL013 v3.4.1. The detail of attribute-based filtering is described in
SOL013 v3.4.1 clause 5.2. The detail of attribute selectors is described in
SOL013 v3.4.1 clause 5.3.

An attribute selector allows the API consumer to choose which attributes it
wants to be contained in the response.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 406

Response Parameters
-------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - id: vnf_pm_threshold_id_body
  - objectType: vnf_pm_threshold_object_type
  - objectInstanceId: vnf_pm_threshold_object_instance_id
  - subObjectInstanceIds: vnf_pm_threshold_sub_object_instance_ids
  - criteria: vnf_pm_threshold_criteria
  - performanceMetric: vnf_pm_threshold_criteria_performance_metric
  - thresholdType: vnf_pm_threshold_type
  - simpleThresholdDetails: vnf_pm_threshold_simple_threshold_details
  - thresholdValue: vnf_pm_threshold_value
  - hysteresis: vnf_pm_threshold_hysteresis
  - callbackUri: vnf_pm_threshold_response_callback_uri
  - _links: pm_threshold_links
  - self: links_self
  - object: vnf_pm_threshold_links_object

Response Example
----------------

.. literalinclude:: samples/vnfpm/list-pm-threshold-response.json
   :language: javascript

Get a PM threshold (v2)
=======================

.. rest_method::  GET /vnfpm/v2/thresholds/{thresholdId}

The GET method gets an individual PM threshold.

If the API consumer intends to read information about a particular PM
threshold, it sends a GET request to the "Individual PM threshold" resource,
addressed by the appropriate PM threshold identifier in its resource URI.
The VNFM returns a "200 OK" response to the API consumer, and includes one
data structure of type "PmThreshold" in the payload body. In case of failure,
appropriate error information is provided in the response.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404

Request Parameters
------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - thresholdId: vnf_pm_threshold_id

Response Parameters
-------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - id: vnf_pm_threshold_id_body
  - objectType: vnf_pm_threshold_object_type
  - objectInstanceId: vnf_pm_threshold_object_instance_id
  - subObjectInstanceIds: vnf_pm_threshold_sub_object_instance_ids
  - criteria: vnf_pm_threshold_criteria
  - performanceMetric: vnf_pm_threshold_criteria_performance_metric
  - thresholdType: vnf_pm_threshold_type
  - simpleThresholdDetails: vnf_pm_threshold_simple_threshold_details
  - thresholdValue: vnf_pm_threshold_value
  - hysteresis: vnf_pm_threshold_hysteresis
  - callbackUri: vnf_pm_threshold_response_callback_uri
  - _links: pm_threshold_links
  - self: links_self
  - object: vnf_pm_threshold_links_object

Response Example
----------------

.. literalinclude:: samples/vnfpm/show-pm-threshold-response.json
   :language: javascript

Modify a PM threshold(v2)
=========================

.. rest_method::  PATCH /vnfpm/v2/thresholds/{thresholdId}


The PATCH method Modifies a PM threshold.

If the API consumer intends to update the callback URI in a PM threshold,
it sends a PATCH request to the "Individual PM threshold" resource, including
a data structure of type "ThresholdModifications" in the payload body.
The VNFM returns a "200 OK" response to the API consumer and includes in
the payload body a data structure of type "ThresholdModifications" to
indicate the performed modifications. However the authentication parameter
shall not be present in response body.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 200

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 422

Request Parameters
------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - thresholdId: vnf_pm_threshold_id
  - callbackUri: vnf_pm_threshold_update_callback_uri
  - authentication: vnf_pm_threshold_update_request_authentication
  - authType: authentication_auth_type
  - paramsBasic: authentication_params_basic
  - userName: paramsBasic_userName
  - password: paramsBasic_password
  - paramsOauth2ClientCredentials: authentication_params_oauth2_client_credentials
  - clientId: params_oauth2_client_credentials_client_id
  - clientPassword: params_oauth2_client_credentials_client_password
  - tokenEndpoint: params_oauth2_client_credentials_token_endpoint
  - paramsOauth2ClientCert: authentication_params_oauth2_client_cert
  - clientId: params_oauth2_client_cert_client_id
  - certificateRef: params_oauth2_client_cert_certificate_ref
  - type: params_oauth2_client_cert_type
  - value: params_oauth2_client_cert_value
  - tokenEndpoint: params_oauth2_client_cert_token_endpoint

Request Example
---------------

.. literalinclude:: samples/vnfpm/update-pm-threshold-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - callbackUri: vnf_pm_threshold_update_resp_callback_uri

Response Example
----------------

.. literalinclude:: samples/vnfpm/update-pm-threshold-response.json
   :language: javascript

Delete a PM threshold (v2)
==========================

.. rest_method:: DELETE /vnfpm/v2/thresholds/{thresholdId}

The DELETE method deletes a PM threshold.

If the API consumer intends to delete a PM threshold, it sends a DELETE
request to the "Individual PM threshold" resource addressed by the
appropriate PM threshold identifier in its resource URI. The VNFM returns
a response with a "204 No Content" response code and an empty payload body
to the API consumer.

Response Codes
--------------

.. rest_status_code:: success status.yaml

  - 204

.. rest_status_code:: error status.yaml

  - 400
  - 401
  - 404

Request Parameters
------------------

.. rest_parameters:: parameters_vnfpm.yaml

  - thresholdId: vnf_pm_threshold_id
