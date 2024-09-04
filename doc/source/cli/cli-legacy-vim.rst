==============
VIM Management
==============

This document describes how to manage VIM with CLI in Tacker.

.. note::

  The content of this document has been confirmed to work
  using Tacker 2024.1 Caracal and Kubernetes 1.26.


Prerequisites
-------------

The following packages should be installed:

* tacker
* python-tackerclient

CLI reference for VIM Management
--------------------------------

1. Register VIM
^^^^^^^^^^^^^^^

a. Use OpenStack as VIM

   * Create VIM configuration file for OpenStack VIM:

     You can use a setup script for generating VIM configuration or
     edit it from scratch as described in :doc:`/reference/vim_config`.
     This script finds parameters for the configuration, such as user
     name or password, from your environment variables.
     Here is an example of generating OpenStack VIM configuration as
     ``vim_config.yaml``. In this document, `TACKER_ROOT` is the root of
     tacker's repository on your server.
     The `PROJECT_NAME` and `OS_USER` should be replaced with the project name
     and username that will be used in VIM registration, respectively.

     .. code-block:: console

       $ bash TACKER_ROOT/tools/gen_vim_config.sh -p PROJECT_NAME --os-user OS_USER
       Config for OpenStack VIM 'vim_config.yaml' generated.


     .. note::

       Use \-\-os\-disable\-cert\-verify option if you have to disable
       the validation of VIM certificate, for example,
       because the VIM uses a self-signed certificate.


     You can also use a sample configuration file `vim_config.yaml`
     instead of using the script.

     .. literalinclude:: /user/v2/getting_started/conf/vim_config.yaml
              :language: yaml


   * Register default OpenStack VIM:

     The `DESCRIPTION` and the `VIM_NAME` should be replaced as desired.

     .. code-block:: console

       $ openstack vim register --config-file vim_config.yaml --is-default \
         --description DESCRIPTION VIM_NAME


     Result:

     .. code-block:: console

       +----------------+-------------------------------------------------+
       | Field          | Value                                           |
       +----------------+-------------------------------------------------+
       | auth_cred      | {                                               |
       |                |     "username": "nfv_user",                     |
       |                |     "user_domain_name": "default",              |
       |                |     "cert_verify": "False",                     |
       |                |     "project_id": null,                         |
       |                |     "project_name": "nfv",                      |
       |                |     "project_domain_name": "default",           |
       |                |     "auth_url": "http://10.0.2.15/identity/v3", |
       |                |     "key_type": "barbican_key",                 |
       |                |     "secret_uuid": "***",                       |
       |                |     "password": "***"                           |
       |                | }                                               |
       | auth_url       | http://10.0.2.15/identity/v3                    |
       | created_at     | 2024-06-10 01:17:50.762223                      |
       | description    | vim for nfv_user in nfv                         |
       | extra          |                                                 |
       | id             | a7298627-93f1-400f-9ef3-5d8749e20245            |
       | is_default     | True                                            |
       | name           | openstack-nfv-vim                               |
       | placement_attr | {                                               |
       |                |     "regions": [                                |
       |                |         "RegionOne"                             |
       |                |     ]                                           |
       |                | }                                               |
       | project_id     | 2e189ea6c1df4e4ba6d89de254b3a534                |
       | status         | ACTIVE                                          |
       | type           | openstack                                       |
       | updated_at     | None                                            |
       | vim_project    | {                                               |
       |                |     "name": "nfv",                              |
       |                |     "project_domain_name": "default"            |
       |                | }                                               |
       +----------------+-------------------------------------------------+


b. Use Kubernetes as VIM

   * Create VIM configuration file for Kubernetes VIM:

     Same as OpenStack VIM, you can use a setup script for generating VIM
     configuration file for Kubernetes VIM by passing ``-t k8s`` option.
     Here is an example of generating OpenStack VIM configuration as
     ``vim_config.yaml``. In this document, `TACKER_ROOT` is the root of
     tacker's repository on your server.
     The `PROJECT_NAME` should be replaced with the project name that will be
     used in VIM registration.

     .. code-block:: console

       $ bash tacker/tools/gen_vim_config.sh -p PROJECT_NAME -t k8s --k8s-use-cert
         Config for Kubernetes VIM 'vim_config.yaml' generated.


     On the other hand, you can also create the VIM configuration
     file for Kubernetes from scratch by following procedure.
     Firstly, gather the information needed in VIM configuration file.

     - Get the IP address of Kubernetes cluster:

       .. code-block:: console

         $ kubectl cluster-info
         Kubernetes control plane is running at https://10.0.2.15:6443

         To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.


     - Create the secret token of Kubernetes API:

       .. code-block:: console

         $ vi default-token-k8s.yaml
         $ cat default-token-k8s.yaml
         apiVersion: v1
         kind: Secret
         metadata:
           name: default-token-k8svim
           annotations:
             kubernetes.io/service-account.name: "default"
         type: kubernetes.io/service-account-token

         $ kubectl create -f default-token-k8s.yaml
         secret/default-token-k8svim created


     - Grant the cluster admin role to the kubernetes service-account:

       .. code-block:: console

         $ kubectl create clusterrolebinding cluster-admin-binding \
           --clusterrole cluster-admin --serviceaccount=default:default


     - Retrieve the secret bearer token:

       .. code-block:: console

         $ kubectl get secret -o jsonpath="{.items[0].metadata.name}"
         default-token-k8svim

         $ kubectl get secret default-token-k8svim -o jsonpath="{.data.token}" | base64 --decode
         eyJhbGciOiJSUzI1NiIsImtpZCI6Ind1dmZuVV9NcGtILWhjaDJwWHNTVlZ2WTItd1NTQlRJbzlEVU1jOTBYX28ifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tazhzdmltIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImRlZmF1bHQiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiIxNmViMTYxZS1mNTNlLTRmNWEtYjI5OS00MjczNDk5NGZlY2QiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6ZGVmYXVsdDpkZWZhdWx0In0.XVQu-vssEgT2PnRTXMr3AoTI6RAjCU1tra3pXxafaNpZHvkRU8_BvWGaqt7qDKZkqyWRWm3K1G2T55U-h0KNNtPG6k1_kl8RG26c275cnFPryZT4t5fZELIqcbRW4tPw21YBIfNtZqC8zOolprmkcGRrIoDeLJYeRtv698CmpryaGBL1mux0FgUNyLoZ4e62XCFTTW86Ull9T5L92ZR08yHtrosnx3SGRnyt32o8NTteApDympYkmuR-QZrsmfknKgI3yFOGCW4TCVdCXwknMWpJvxE93_nCbGoenrPN2R9cMWySqE02YcWYSP6vTBkMKpctgLalWQHKXTo2DspKVg


     - Retrieve the SSL CA certificate:

       .. code-block:: console

         $ kubectl get secret default-token-k8svim -o jsonpath="{.data.ca\.crt}" | base64 --decode
         -----BEGIN CERTIFICATE-----
         MIIDBTCCAe2gAwIBAgIIYAFM312rGhwwDQYJKoZIhvcNAQELBQAwFTETMBEGA1UE
         AxMKa3ViZXJuZXRlczAeFw0yNDA2MDQwMjUxMDZaFw0zNDA2MDIwMjU2MDZaMBUx
         EzARBgNVBAMTCmt1YmVybmV0ZXMwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK
         AoIBAQDf131+RFTzpxdk2jGkJLSJFS+oPxo9nPdRgiKVbSRyhrIQ0uoEDHVNYtSz
         8qR0mIZSvGIEgSFVW36AIysYPilxPHw53K9wzxKN1hEkw0ffnbPpF/4MLr+CMtcR
         UsFxKIqyRQAedOE3JS5v27R7uA+GdIDID6nN8UVNQYv1AicnvTFSOSfCIMBql6MV
         dgUAVlho9hpqBBVz2R0TrfwEQGtJXTwVKiXNXwWctCY7W8MBBw9EV/94v30dmNAE
         Dv+dauVB944XDl+g2Bp9n2l0JnNz9fA4BWJaLzVaBLsor49oyRY5BpDe456Zmvqx
         McO42cbJewsrlOAMP5QZeDZD6hGFAgMBAAGjWTBXMA4GA1UdDwEB/wQEAwICpDAP
         BgNVHRMBAf8EBTADAQH/MB0GA1UdDgQWBBQ9j2P78qCijHYekohBjR/mGxwmBzAV
         BgNVHREEDjAMggprdWJlcm5ldGVzMA0GCSqGSIb3DQEBCwUAA4IBAQB82mwOwNDy
         9UoNbNevalHglI3q/oqahwgQ+aURmNA78XZfxae+AMD6pR0EXGryKp1TXEFD0t6p
         f8BHPgD1V/HjURlGNMpEOyR+VR1g0Im605rkLoEJauFF7fe7C27fRy9NdFjiZ9ck
         bWxRgCfwro9R1CZyWumgi8D6RS+1LIh+WnFGWZZ2/3XZloDnad9v0cfq4ZNt8nYO
         doyiL3UVlnQpDHwuY6cKMwQNQZfRcZKZw80isCFe97ePeJ6m7qNezMVXFYOaSPXX
         ifDW2JlN544ERvnqWHqJ+ycylY49rrjOfXBtZo0B+fekScFweFmzk4VaOY/ePYEN
         tu82PpmIYiL1
         -----END CERTIFICATE-----

     Then, create the VIM configuration file using the information gathered.

     - Create VIM configuration file for Kubernetes VIM:

       .. code-block:: yaml

         $ vi vim_config_k8s.yaml
         $ cat vim_config_k8s.yaml
         auth_url: "https://10.0.2.15:6443"
         bearer_token: "eyJhbGciOiJSUzI1NiIsImtpZCI6Ind1dmZuVV9NcGtILWhjaDJwWHNTVlZ2WTItd1NTQlRJbzlEVU1jOTBYX28ifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tazhzdmltIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImRlZmF1bHQiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiIxNmViMTYxZS1mNTNlLTRmNWEtYjI5OS00MjczNDk5NGZlY2QiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6ZGVmYXVsdDpkZWZhdWx0In0.XVQu-vssEgT2PnRTXMr3AoTI6RAjCU1tra3pXxafaNpZHvkRU8_BvWGaqt7qDKZkqyWRWm3K1G2T55U-h0KNNtPG6k1_kl8RG26c275cnFPryZT4t5fZELIqcbRW4tPw21YBIfNtZqC8zOolprmkcGRrIoDeLJYeRtv698CmpryaGBL1mux0FgUNyLoZ4e62XCFTTW86Ull9T5L92ZR08yHtrosnx3SGRnyt32o8NTteApDympYkmuR-QZrsmfknKgI3yFOGCW4TCVdCXwknMWpJvxE93_nCbGoenrPN2R9cMWySqE02YcWYSP6vTBkMKpctgLalWQHKXTo2DspKVg"
         ssl_ca_cert: "-----BEGIN CERTIFICATE-----
         MIIDBTCCAe2gAwIBAgIIYAFM312rGhwwDQYJKoZIhvcNAQELBQAwFTETMBEGA1UE
         AxMKa3ViZXJuZXRlczAeFw0yNDA2MDQwMjUxMDZaFw0zNDA2MDIwMjU2MDZaMBUx
         EzARBgNVBAMTCmt1YmVybmV0ZXMwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK
         AoIBAQDf131+RFTzpxdk2jGkJLSJFS+oPxo9nPdRgiKVbSRyhrIQ0uoEDHVNYtSz
         8qR0mIZSvGIEgSFVW36AIysYPilxPHw53K9wzxKN1hEkw0ffnbPpF/4MLr+CMtcR
         UsFxKIqyRQAedOE3JS5v27R7uA+GdIDID6nN8UVNQYv1AicnvTFSOSfCIMBql6MV
         dgUAVlho9hpqBBVz2R0TrfwEQGtJXTwVKiXNXwWctCY7W8MBBw9EV/94v30dmNAE
         Dv+dauVB944XDl+g2Bp9n2l0JnNz9fA4BWJaLzVaBLsor49oyRY5BpDe456Zmvqx
         McO42cbJewsrlOAMP5QZeDZD6hGFAgMBAAGjWTBXMA4GA1UdDwEB/wQEAwICpDAP
         BgNVHRMBAf8EBTADAQH/MB0GA1UdDgQWBBQ9j2P78qCijHYekohBjR/mGxwmBzAV
         BgNVHREEDjAMggprdWJlcm5ldGVzMA0GCSqGSIb3DQEBCwUAA4IBAQB82mwOwNDy
         9UoNbNevalHglI3q/oqahwgQ+aURmNA78XZfxae+AMD6pR0EXGryKp1TXEFD0t6p
         f8BHPgD1V/HjURlGNMpEOyR+VR1g0Im605rkLoEJauFF7fe7C27fRy9NdFjiZ9ck
         bWxRgCfwro9R1CZyWumgi8D6RS+1LIh+WnFGWZZ2/3XZloDnad9v0cfq4ZNt8nYO
         doyiL3UVlnQpDHwuY6cKMwQNQZfRcZKZw80isCFe97ePeJ6m7qNezMVXFYOaSPXX
         ifDW2JlN544ERvnqWHqJ+ycylY49rrjOfXBtZo0B+fekScFweFmzk4VaOY/ePYEN
         tu82PpmIYiL1
         -----END CERTIFICATE-----"
         project_name: "nfv"
         type: "kubernetes"


   * Register Kubernetes VIM:

     The `DESCRIPTION` and the `VIM_NAME` should be replaced as desired.

     .. code-block:: console

       $ openstack vim register --config-file vim_config_k8s.yaml \
         --description DESCRIPTION VIM_NAME


     Result:

     .. code-block:: console

       +----------------+-----------------------------------------------------------------------------------------------------+
       | Field          | Value                                                                                               |
       +----------------+-----------------------------------------------------------------------------------------------------+
       | auth_cred      | {                                                                                                   |
       |                |     "bearer_token": "***",                                                                          |
       |                |     "ssl_ca_cert": "b'gAAAAABmZlbz0gFnRL-SpTszQF4KXje3GSL5H6NzZtwcRZNo3BWx0piwLihpLGy8yz6w85bD5a2B6 |
       |                | M4RRF1mnCPsiYYg5ENpZkD5rCVLyLuQOV4R0zvCyrtXmTYwki0nibw0zAaZxmjLmCncxvQXq7y_B5kzYPUtC607QFFhLsMWfAre |
       |                | M8lm-sassp9TqXvLgq_X98nWFXL0P5egyGedp3bPoiQdvVTNSAurtX-                                             |
       |                | yo7CRvmpvAaa2dvg_VyoQj1Oj9-iF_tLshNa0AASFkAdvWUyvnlbJJOG1rxXVbdZ7JWgnq3T9vC4hHE13GIrY-jRMRCjlfZPbC6 |
       |                | TNWs8ifJM0xr7sQjv66li79l8Xx60XZFxyKefYgZV4rEmh5hwglg6XEne2ZMoFV9rEqrRgmDK0cWGLNJNLvqXHtHOpCff8pHhlI |
       |                | Z5RuRvSttp84LyXvZsNryc2dHGYDsMXFgDuTxpkWemxxxgHzHq4UydADaGimfSkvcQRKmEEY8p3kPzAT9esxzL0Alp68BGm80yH |
       |                | 9Heovb11AeWsVealvOiK6WRkuucxSr31jlCKAIYKwLLymnFvfe9yc0IjZpHWa4SqwbyYvMtEUfebddCUMKS8GX_6aBkKKGQBbss |
       |                | 2Zbcg4l8aesblYTMN6LXhY5PciLTUyu_GcO7JVHACa61JeGyne64CTaycIvYfF9j19KJ5Tl9jeOgfjfeV855hJ41q8g4gTqaNAj |
       |                | _NBl61CPvsKp4le-1Vg9RuLgrX5HBRGW30dWYepQC1Mdu4VEQc-6txRxIUW4w-                                      |
       |                | EKxT8HC1DeWgFiPB4DouAbxiB1IxiUzWk8azj4Wg2rhd6iL9_MUPwZO_6-                                          |
       |                | O6L1AROdnoELNwNUWWdTiUrlSIkElOFzg3rs_Oa3Ee5jeaI86LSJFBEqj3PQ8RVCVjIolwA4i4r7CzoHLKf1YLRw3JJsEDUE0s3 |
       |                | xuNAkAkQTWqCK6kRL5CdENkRw1Nb-L62BMOwlPex324-eLzbgz2z54tM8tJ4Mf4kHkIS6Uk851J1jz0dwxSR6-              |
       |                | rPZTOquttUkYlUlR9NrfwfHitRbjT4YBngFP68npLsHEYEg_7-                                                  |
       |                | 1byYsv3kQk5RNPhfrovjDDOUpbDCAQ0nNC1MLoWGzJxP4OexbYu4qku0YYIGcs3YqbF2ArQNyBAdSDX7d7B-4w-             |
       |                | yRbSdtUcIiCU0LxUneXwB37YbyNyHYQihxS3efZmF9lyfheb2Hri3emIAVB-                                        |
       |                | QPJ8f27hFul1cC8rW1xYcTuZOynOJODTgERV4ehGt8I9P8ZmeqjyjEeADuc-Tpp-DrUMLmgR8sIjDdLsVG6loNFVuulp9Apr-Wn |
       |                | I45XkreFOdhKDMXfpt_xQfxlFOBB3VlOcAZfxZTLWymBwJktqscnIgWexjAa5vwe4BRUu8w8t2ZlgmI8phOeN7jVmSMtD8lC-   |
       |                | W8mb-l5-EFE9wo7y_xgIiD1SvnXPPQT_sXxckDhdEwBCqdMRJ-BWNKMoBQPWWFYvT3S_gNQqABovmAwFaxpi9v0hwfccJmWhre8 |
       |                | T_m73B6IN5P75l1yLgKFv1AoiVH0z0VcaJYTbIt9UwPc2VA=='",                                                |
       |                |     "auth_url": "https://10.0.2.15:6443",                                                           |
       |                |     "username": "None",                                                                             |
       |                |     "key_type": "barbican_key",                                                                     |
       |                |     "secret_uuid": "***"                                                                            |
       |                | }                                                                                                   |
       | auth_url       | https://10.0.2.15:6443                                                                              |
       | created_at     | 2024-06-10 01:29:24.234551                                                                          |
       | description    | k8s vim for nfv_user in nfv                                                                         |
       | extra          |                                                                                                     |
       | id             | 81dcd320-c61d-4d04-a794-4ea012801e4c                                                                |
       | is_default     | False                                                                                               |
       | name           | kubernetes-nfv-vim                                                                                  |
       | placement_attr | {                                                                                                   |
       |                |     "regions": [                                                                                    |
       |                |         "default",                                                                                  |
       |                |         "kube-node-lease",                                                                          |
       |                |         "kube-public",                                                                              |
       |                |         "kube-system"                                                                               |
       |                |     ]                                                                                               |
       |                | }                                                                                                   |
       | project_id     | 2e189ea6c1df4e4ba6d89de254b3a534                                                                    |
       | status         | ACTIVE                                                                                              |
       | type           | kubernetes                                                                                          |
       | updated_at     | None                                                                                                |
       | vim_project    | {                                                                                                   |
       |                |     "name": "nfv"                                                                                   |
       |                | }                                                                                                   |
       +----------------+-----------------------------------------------------------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vim register --help
  usage: openstack vim register [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN]
                                [--noindent] [--prefix PREFIX] [--max-width <integer>]
                                [--fit-width] [--print-empty] [--tenant-id TENANT_ID] --config-file
                                CONFIG_FILE [--description DESCRIPTION] [--is-default]
                                NAME

  Register a new VIM

  positional arguments:
    NAME          Set a name for the VIM

  options:
    -h, --help            show this help message and exit
    --tenant-id TENANT_ID
                          The owner tenant ID or project ID
    --config-file CONFIG_FILE
                          YAML file with VIM configuration parameters
    --description DESCRIPTION
                          Set a description for the VIM
    --is-default          Set as default VIM

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX
                          add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the CLIFF_MAX_TERM_WIDTH
                          environment variable, but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than 0. Set the
                          environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.

  This command is provided by the python-tackerclient plugin.


2. List VIMs
^^^^^^^^^^^^

.. code-block:: console

  $ openstack vim list


Result:

.. code-block:: console

  +--------------------------------------+--------------------+----------------------------------+------------+------------+--------+
  | ID                                   | Name               | Tenant_id                        | Type       | Is Default | Status |
  +--------------------------------------+--------------------+----------------------------------+------------+------------+--------+
  | 81dcd320-c61d-4d04-a794-4ea012801e4c | kubernetes-nfv-vim | 2e189ea6c1df4e4ba6d89de254b3a534 | kubernetes | False      | ACTIVE |
  | a7298627-93f1-400f-9ef3-5d8749e20245 | openstack-nfv-vim  | 2e189ea6c1df4e4ba6d89de254b3a534 | openstack  | True       | ACTIVE |
  +--------------------------------------+--------------------+----------------------------------+------------+------------+--------+


Help:

.. code-block:: console

  $ openstack vim list --help
  usage: openstack vim list [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN]
                            [--quote {all,minimal,none,nonnumeric}] [--noindent]
                            [--max-width <integer>] [--fit-width] [--print-empty]
                            [--sort-column SORT_COLUMN] [--sort-ascending | --sort-descending]
                            [--long]

  List VIMs that belong to a given tenant.

  options:
    -h, --help            show this help message and exit
    --long                List additional fields in output

  output formatters:
    output formatter options

    -f {csv,json,table,value,yaml}, --format {csv,json,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple columns
    --sort-column SORT_COLUMN
                          specify the column(s) to sort the data (columns specified first have a priority,
                          non-existing columns are ignored), can be repeated
    --sort-ascending      sort the column(s) in ascending order
    --sort-descending     sort the column(s) in descending order

  CSV Formatter:
    --quote {all,minimal,none,nonnumeric}
                          when to include quotes, defaults to nonnumeric

  json formatter:
    --noindent            whether to disable indenting the JSON

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the CLIFF_MAX_TERM_WIDTH
                          environment variable, but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than 0. Set the
                          environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.

  This command is provided by the python-tackerclient plugin.


3. Show VIM
^^^^^^^^^^^

The `VIM` should be replaced with the name or ID of VIM.

.. code-block:: console

  $ openstack vim show VIM


Result:

.. code-block:: console

  +----------------+-------------------------------------------------+
  | Field          | Value                                           |
  +----------------+-------------------------------------------------+
  | auth_cred      | {                                               |
  |                |     "username": "nfv_user",                     |
  |                |     "user_domain_name": "default",              |
  |                |     "cert_verify": "False",                     |
  |                |     "project_id": null,                         |
  |                |     "project_name": "nfv",                      |
  |                |     "project_domain_name": "default",           |
  |                |     "auth_url": "http://10.0.2.15/identity/v3", |
  |                |     "key_type": "barbican_key",                 |
  |                |     "secret_uuid": "***",                       |
  |                |     "password": "***"                           |
  |                | }                                               |
  | auth_url       | http://10.0.2.15/identity/v3                    |
  | created_at     | 2024-06-10 01:17:51                             |
  | description    | vim for nfv_user in nfv                         |
  | extra          |                                                 |
  | id             | a7298627-93f1-400f-9ef3-5d8749e20245            |
  | is_default     | True                                            |
  | name           | openstack-nfv-vim                               |
  | placement_attr | {                                               |
  |                |     "regions": [                                |
  |                |         "RegionOne"                             |
  |                |     ]                                           |
  |                | }                                               |
  | project_id     | 2e189ea6c1df4e4ba6d89de254b3a534                |
  | status         | ACTIVE                                          |
  | type           | openstack                                       |
  | updated_at     | None                                            |
  | vim_project    | {                                               |
  |                |     "name": "nfv",                              |
  |                |     "project_domain_name": "default"            |
  |                | }                                               |
  +----------------+-------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vim show --help
  usage: openstack vim show [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent]
                            [--prefix PREFIX] [--max-width <integer>] [--fit-width]
                            [--print-empty]
                            <VIM>

  Display VIM details

  positional arguments:
    <VIM>         VIM to display (name or ID)

  options:
    -h, --help            show this help message and exit

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX
                          add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the CLIFF_MAX_TERM_WIDTH
                          environment variable, but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than 0. Set the
                          environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.

  This command is provided by the python-tackerclient plugin.


4. Update VIM
^^^^^^^^^^^^^

The `VIM` and `DESCRIPTION` should be replaced with
the name or ID of VIM and the description that you desired, respectively.

.. code-block:: console

  $ openstack vim set --description DESCRIPTION VIM


Result:

.. code-block:: console

  +----------------+-------------------------------------------------+
  | Field          | Value                                           |
  +----------------+-------------------------------------------------+
  | auth_cred      | {                                               |
  |                |     "username": "nfv_user",                     |
  |                |     "user_domain_name": "default",              |
  |                |     "cert_verify": "False",                     |
  |                |     "project_id": null,                         |
  |                |     "project_name": "nfv",                      |
  |                |     "project_domain_name": "default",           |
  |                |     "auth_url": "http://10.0.2.15/identity/v3", |
  |                |     "key_type": "barbican_key",                 |
  |                |     "secret_uuid": "***",                       |
  |                |     "password": "***"                           |
  |                | }                                               |
  | auth_url       | http://10.0.2.15/identity/v3                    |
  | created_at     | 2024-06-10 01:17:51                             |
  | description    | new description of vim for nfv_user in nfv      |
  | extra          |                                                 |
  | id             | a7298627-93f1-400f-9ef3-5d8749e20245            |
  | is_default     | True                                            |
  | name           | openstack-nfv-vim                               |
  | placement_attr | {                                               |
  |                |     "regions": [                                |
  |                |         "RegionOne"                             |
  |                |     ]                                           |
  |                | }                                               |
  | project_id     | 2e189ea6c1df4e4ba6d89de254b3a534                |
  | status         | ACTIVE                                          |
  | type           | openstack                                       |
  | updated_at     | 2024-06-10 01:41:55.437321                      |
  | vim_project    | {                                               |
  |                |     "name": "nfv",                              |
  |                |     "project_domain_name": "default"            |
  |                | }                                               |
  +----------------+-------------------------------------------------+


Help:

.. code-block:: console

  $ openstack vim set --help
  usage: openstack vim set [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent]
                           [--prefix PREFIX] [--max-width <integer>] [--fit-width]
                           [--print-empty] [--config-file CONFIG_FILE] [--name NAME]
                           [--description DESCRIPTION] [--is-default {True,False}]
                           VIM

  Update VIM.

  positional arguments:
    VIM           ID or name of vim to update

  options:
    -h, --help            show this help message and exit
    --config-file CONFIG_FILE
                          YAML file with VIM configuration parameters
    --name NAME   New name for the VIM
    --description DESCRIPTION
                          New description for the VIM
    --is-default {True,False}
                          Indicate whether the VIM is used as default

  output formatters:
    output formatter options

    -f {json,shell,table,value,yaml}, --format {json,shell,table,value,yaml}
                          the output format, defaults to table
    -c COLUMN, --column COLUMN
                          specify the column(s) to include, can be repeated to show multiple columns

  json formatter:
    --noindent            whether to disable indenting the JSON

  shell formatter:
    a format a UNIX shell can parse (variable="value")

    --prefix PREFIX
                          add a prefix to all variable names

  table formatter:
    --max-width <integer>
                          Maximum display width, <1 to disable. You can also use the CLIFF_MAX_TERM_WIDTH
                          environment variable, but the parameter takes precedence.
    --fit-width           Fit the table to the display width. Implied if --max-width greater than 0. Set the
                          environment variable CLIFF_FIT_WIDTH=1 to always enable
    --print-empty         Print empty table if there is no data to show.

  This command is provided by the python-tackerclient plugin.


5. Delete VIM
^^^^^^^^^^^^^

The `VIM` should be replaced with the name or ID of VIM.

.. code-block:: console

  $ openstack vim delete VIM


Result:

.. code-block:: console

  All specified vim(s) deleted successfully


Help:

.. code-block:: console

  $ openstack vim delete --help
  usage: openstack vim delete [-h] <VIM> [<VIM> ...]

  Delete VIM(s).

  positional arguments:
    <VIM>  VIM(s) to delete (name or ID)

  options:
    -h, --help     show this help message and exit

  This command is provided by the python-tackerclient plugin.
