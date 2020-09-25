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
**Definitions/** directory.

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
.. _NFV-SOL004 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/004/02.06.01_60/gs_NFV-SOL004v020601p.pdf
.. _NFV-SOL005 v2.6.1 : https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/005/02.06.01_60/gs_NFV-SOL005v020601p.pdf
