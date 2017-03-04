========================
Tools for tacker
========================

sync_test_requirements.py
========================

Sync the test-requirements.txt with openstack global requirements.
Assume requirements prject is cloned at /opt/stack/requirements, to run::

    $ git clone https://git.openstack.org/openstack/requirements.git /opt/stack/requirements
    $ ./sync_test_requirements.py -g /opt/stack/requirements/global-requirements.txt -t ../test-requirements.txt -o ../test-requirements.txt

If this tool shows us the "../test-requirements.txt" is changed,
please commit it.

This tool is also used in tox.ini to check if the test-requirements.txt is
synchroized with global-requirements.txt. please refer to tox.ini for the
usage.
