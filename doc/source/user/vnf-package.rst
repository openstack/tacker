===========
VNF Package
===========

VNF Package is a ZIP file including VNFD, software images for VM, and other
artifact resources such as scripts and config files. The directory structure
and file contents are defined in `NFV-SOL004 v2.6.1`_.

According to `NFV-SOL004 v2.6.1`_, VNF Package should be the ZIP file format
with the `TOSCA-Simple-Profile-YAML-v1.1`_ Specifications. The ZIP file is
called TOSCA YAML Cloud Service Archive (CSAR), and two different structures
are available:

* CSAR with TOSCA-Metadata directory
* CSAR zip without TOSCA-Metadata directory

.. note:: VNF LCM API version 1 supports both structures.
          VNF LCM API version 2 supports only
          *CSAR with TOSCA-Metadata directory*.

.. note:: For more detailed definitions of CSAR, see section 16 in
          `TOSCA-Simple-Profile-YAML-v1.1`_.

Some examples for VNF Package are available in Tacker repository.

* https://opendev.org/openstack/tacker/

CSAR with TOSCA-Metadata directory
----------------------------------

The directory structure:

* **TOSCA-Metadata/TOSCA.meta**
* **Definitions/**
* **Files/images/**
* (optional) **Scripts/**
* (optional) **<manifest file name>.mf**
* (optional) **BaseHOT/**
* (optional) **UserData/**

.. note:: BaseHOT and UserData are optional, but they are required when
          running LCM operation user data.
          This methodology is under discussion within `NFV-SOL014 v2.8.1`_
          and there is no clear directory structure yet.
          Please check with :doc:`./etsi_vnf_deployment_as_vm_with_user_data`.

The specification can be modified according to standardization
`NFV-SOL014 v2.8.1`_.

.. code-block::

  !----TOSCA-Metadata
          !---- TOSCA.meta
  !----Definitions
          !---- etsi_nfv_sol001_common_types.yaml
          !---- etsi_nfv_sol001_vnfd_types.yaml
          !---- vnfd_top.yaml
          !---- vnfd_df_1.yaml
          !---- ..
          !---- vnfd_df_x.yaml
          !---- vnfd_types.yaml
  !----Files
          !---- images
                  !---- image_1.img
                  !---- ..
                  !---- image_x.img
  !----Scripts (optional)
          !---- install.sh
  !---- manifest.mf
  !----BaseHOT (optional)
          !---- df_1
                  !---- base_hot_df_1.yaml
          !---- ..
          !---- df_x
                  !---- base_hot_df_x.yaml
  !----UserData (optional)
          !---- __init__.py
          !---- lcm_user_data.py


TOSCA-Metadata/TOSCA.meta
^^^^^^^^^^^^^^^^^^^^^^^^^

According to `TOSCA-Simple-Profile-YAML-v1.1`_ specifications, the
``TOSCA.meta`` metadata file is described in `TOSCA-1.0-specification`_,
and it should have the following contents:

* *TOSCA-Meta-File-Version*: This is the version number of the TOSCA meta
  file format and must be "1.0".
* *CSAR-Version*: This is the version number of the CSAR specification and
  must be "1.1"
* *Created-By*: The person or vendor, respectively, who created the CSAR.
* *Entry-Definitions*: This is the reference to the top-level VNFD file in
  **Definitions/** directory.
* (optional) *ETSI-Entry-Manifest*: This is the reference to the manifest
  file. When this key/value is not provided, Tacker tries to find the manifest
  file with the name of top-level VNF file as ``<VNFD file name>.mf``.

In ``TOSCA.meta`` file, artifact resources related information, which is also
possible to locate in manifest file, can be described in the following manner
according to `TOSCA-1.0-specification`_ section 16.2:

.. note:: It is highly recommended to put artifacts information in the
          manifest file other than in TOSCA.meta file because it's more
          simple and easy to understand.

* (optional) *artifact info* - describes location and digest of all files
  other than VNFD YAML files.

  * *Name*: The path and identifier of the file.
  * *Content-Type*: The type of the file described. This type is a MIME type
    complying with the type/subtype structure.

  * *Algorithm*: The name of hash algorithm. "SHA-224", "SHA-256", "SHA-384",
    and "SHA-512" are supported.

  * *Hash*: Text string corresponding to the hexadecimal representation.

.. note:: For software images, note that the algorithm of hash calculation is
          the same as the `Glance configuration`_, the default is "SHA-512".
          The software images are not additionalArtifacts but softwareImages
          according to `NFV-SOL005 v2.6.1`_.

.. note:: The "Name" and "Content-Type" attributes are defined in
          `TOSCA-1.0-specification`_ section 16.2. The "Algorithm" and "Hash" are
          requirement from `NFV-SOL004 v2.6.1`_ section 5.3 and
          `NFV-SOL005 v2.6.1`_ section 9.5.3.3, the checksum field is required
          and the manner should be the same with the manifest file.

Example:

.. code-block:: yaml

  TOSCA-Meta-File-Version: 1.0
  CSAR-Version: 1.1
  Created-By: Tacker
  Entry-Definitions: vnfd_top.yaml
  ETSI-Entry-Manifest: manifest.mf

  Name: manifest.mf
  Content-Type: text/plain
  Algorithm: SHA-256
  Hash: 09e5a788acb180162c51679ae4c998039fa6644505db2415e35107d1ee213943

  Name: scripts/install.sh
  Content-Type: application/x-sh
  Algorithm: SHA-256
  Hash: d0e7828293355a07c2dccaaa765c80b507e60e6167067c950dc2e6b0da0dbd8b

  Name: https://www.example.com/example.sh
  Content-Type: application/x-sh
  Algorithm: SHA-256
  Hash: 36f945953929812aca2701b114b068c71bd8c95ceb3609711428c26325649165


Definitions/
^^^^^^^^^^^^

All VNFD YAML files are located here. How to create VNFD composed of plural
deployment flavours is described in :doc:`./vnfd-sol001`.

VNFD type files provided from `ETSI NFV-SOL001 repository`_ are also included:

* etsi_nfv_sol001_common_types.yaml
* etsi_nfv_sol001_vnfd_types.yaml

Files/images/
^^^^^^^^^^^^^

VNF Software Images are located here. These files are also described in
``TOSCA.meta`` or manifest file as artifacts.

Scripts/
^^^^^^^^

Any script files are located here. These scripts are executed in Action
Driver or Management Driver. All these files also appear in ``TOSCA.meta``
or manifest file as artifacts.

.. TODO(yoshito-ito): add links to ActionDriver and MgmtDriver.
   How to implement and utilize Action Driver is described in
   :doc:`../admin/action-driver` and Management Driver is described in
   :doc:`../admin/management-driver`.

<manifest file name>.mf
^^^^^^^^^^^^^^^^^^^^^^^

The manifest file contains two types of information, *metadata* and *artifact*
*info*. *metadata* is optional and *artifact info* is required when one or
more artifacts are included in the VNF Package file such as software images,
scripts or config files. This *artifact info* is also possible to be in
``TOSCA.meta`` file.

* (optional) *metadata* - is optional metadata for the VNF Package file.

  * *vnf_product_name*: The product name of VNF.
  * *vnf_provider_id*: The ID of VNF provider.
  * *vnf_package_version*: The version of the VNF Package file.
  * *vnf_release_date_time*: The format according to `IETF RFC 3339`_.

.. note:: The *metadata* in manifest file is not stored in Tacker DB.

* *artifact info* - describes location and digest of all files other than
  VNFD YAML files.

  * *Source*: The path and identifier of the file.
  * *Algorithm*: The name of hash algorithm. "SHA-224", "SHA-256", "SHA-384",
    and "SHA-512" are supported.
  * *Hash*: Text string corresponding to the hexadecimal representation.

Example:

.. code-block:: yaml

  metadata:
    vnf_product_name: VNF
    vnf_provider_id: Tacker
    vnf_package_version: 1.0
    vnf_release_date_time: 2020-01-01T10:00:00+09:00

  Source: VNFD.yaml
  Algorithm: SHA-256
  Hash: 09e5a788acb180162c51679ae4c998039fa6644505db2415e35107d1ee213943

  Source: scripts/install.sh
  Algorithm: SHA-256
  Hash: d0e7828293355a07c2dccaaa765c80b507e60e6167067c950dc2e6b0da0dbd8b

  Source: https://www.example.com/example.sh
  Algorithm: SHA-256
  Hash: 36f945953929812aca2701b114b068c71bd8c95ceb3609711428c26325649165


BaseHOT/
^^^^^^^^

Base HOT file is a Native cloud orchestration template, HOT in this context,
which is commonly used for LCM operations in different VNFs.
This Base HOT can work on OpenStack API and be filled by Heat input parameters
generated by LCM operation user data.
It is the responsibility of the user to prepare this file, and it is necessary
to make it consistent with VNFD placed under the **Definitions/** directory.

.. note:: Place the directory corresponding to deployment-flavour stored in
          the **Definitions/** under the **BaseHOT/** directory, and store the
          Base HOT files in it.
          In this DQ example, it is assumed that there is a deployment-flavour
          from `df_1` to` df_x`.
          For more information on deployment-flavour, see
          `NFV-SOL001 v2.6.1`_ Annex A.

Example:

.. code-block:: yaml

  heat_template_version: 2013-05-23
  description: 'Template for test _generate_hot_from_tosca().'

  parameters:
    nfv:
      type: json

  resources:
    VDU1:
      type: OS::Nova::Server
      properties:
        flavor:
          get_resource: VDU1_flavor
        name: VDU1
        image: { get_param: [ nfv, VDU, VDU1, image ] }
        networks:
        - port:
            get_resource: CP1

    CP1:
      type: OS::Neutron::Port
      properties:
        network: { get_param: [ nfv, CP, CP1, network ] }

    VDU1_flavor:
      type: OS::Nova::Flavor
      properties:
        ram: { get_param: [ nfv, VDU, VDU1, flavor, ram ] }
        vcpus: { get_param: [ nfv, VDU, VDU1, flavor, vcpus ] }
        disk: { get_param: [ nfv, VDU, VDU1, flavor, disk ] }

  outputs: {}


.. note:: For property (e.g. image in VDU1) whose value is "get_param",
          the Heat input parameters generated by script placed under
          **UserData/** directory.


UserData/
^^^^^^^^^

LCM operation user data is a script that returns key/value data as
Heat input parameters used for Base HOT.
As Heat input parameter, OpenStack parameters that are not statically defined
in the VNFD(e.g. flavors, images, hardware acceleration, driver-setup, etc.)
can be assigned.


.. note:: It is necessary to generate Heat input parameters for HOT file
          This script has the following advantages/disadvantages for VNF
          package creators/users.
          The advantage is that this script has no operational restrictions,
          so it can be freely described by creators and operated by users.
          The disadvantage is that creators can write a script that
          involves DB operations, which can lead to unexpected behavior for users.
          The trade-off between being able to write scripts freely and
          limiting operations is an issue for the future.

.. note:: User data script is incompatible between VNF LCM API version 1 and 2
          due to different requirements for them.

The requirements of User data script for VNF LCM API version 2 is described
in :doc:`./userdata_script`.

Following shows an example of user data script for VNF LCM API version 1.

.. code-block:: python

  import tacker.vnfm.lcm_user_data.utils as UserDataUtil

  from tacker.vnfm.lcm_user_data.abstract_user_data import AbstractUserData

  class SampleUserData(AbstractUserData):

      @staticmethod
      def instantiate(base_hot_dict=None,
                      vnfd_dict=None,
                      inst_req_info=None,
                      grant_info=None):

          # Create HOT input parameter using util functions.
          initial_param_dict = UserDataUtil.create_initial_param_dict(
              base_hot_dict)

          vdu_flavor_dict = UserDataUtil.create_vdu_flavor_dict(vnfd_dict)
          vdu_image_dict = UserDataUtil.create_vdu_image_dict(grant_info)
          cpd_vl_dict = UserDataUtil.create_cpd_vl_dict(
              base_hot_dict, inst_req_info)

          final_param_dict = UserDataUtil.create_final_param_dict(
              initial_param_dict, vdu_flavor_dict, vdu_image_dict, cpd_vl_dict)

          return final_param_dict


.. note:: It is necessary to generate Heat input parameters for HOT file
          placed under **BaseHOT/** directory by this scprit.


CSAR zip without TOSCA-Metadata directory
-----------------------------------------

The file structure:

* **<VNFD file name>.yaml**
* **Definitions/**
* **<manifest file name>.yaml**

.. code-block::

  !---- vnfd_top.yaml
  !----Definitions/
          !---- etsi_nfv_sol001_common_types.yaml
          !---- etsi_nfv_sol001_vnfd_types.yaml
          !---- vnfd_top.yaml
          !---- vnfd_df_1.yaml
          !---- ..
          !---- vnfd_df_x.yaml
          !---- vnfd_types.yaml
  !---- vnfd_top.mf


<VNFD file name>.yaml
^^^^^^^^^^^^^^^^^^^^^

This is the top-level VNFD file. It can import additional VNFD files from
the **Definitions/** directory.

Definitions/
^^^^^^^^^^^^

All VNFD YAML files other than top-level VNFD are located here. How to create
VNFD composed of plural deployment flavours is described in
:doc:`./vnfd-sol001`.

VNFD type files provided from `ETSI NFV-SOL001 repository`_ may be included:

* etsi_nfv_sol001_common_types.yaml
* etsi_nfv_sol001_vnfd_types.yaml

<manifest file name>.yaml
^^^^^^^^^^^^^^^^^^^^^^^^^

The manifest file has an extension .mf, the same name as the top-level VNFD
YAML file. The contents is exactly same as described in the previous section.

.. _TOSCA-Simple-Profile-YAML-v1.1 : http://docs.oasis-open.org/tosca/TOSCA-Simple-Profile-YAML/v1.1/TOSCA-Simple-Profile-YAML-v1.1.html
.. _TOSCA-1.0-specification : http://docs.oasis-open.org/tosca/TOSCA/v1.0/os/TOSCA-v1.0-os.pdf
.. _Glance configuration : https://docs.openstack.org/glance/latest/user/signature.html#using-the-signature-verification
.. _ETSI NFV-SOL001 repository : https://forge.etsi.org/rep/nfv/SOL001
.. _IETF RFC 3339 : https://tools.ietf.org/html/rfc3339
.. _NFV-SOL001 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/001/02.06.01_60/gs_NFV-SOL001v020601p.pdf
.. _NFV-SOL004 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/004/02.06.01_60/gs_NFV-SOL004v020601p.pdf
.. _NFV-SOL005 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/005/02.06.01_60/gs_NFV-SOL005v020601p.pdf
.. _NFV-SOL014 v2.8.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/014/02.08.01_60/gs_NFV-SOL014v020801p.pdf
.. _UserData script (VNF LCM v2):
