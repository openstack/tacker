Tacker WSGI/HTTP API layer
===========================

This section will cover the internals of Tacker's HTTP API, and the classes
in Tacker that can be used to create Extensions to the Tacker API.

Python web applications interface with webservers through the Python Web
Server Gateway Interface (WSGI) - defined in `PEP 333 <https://legacy.python.org/dev/peps/pep-0333/>`_

Startup
-------

Tackers's WSGI server is started from the `server module <https://opendev.org/openstack/tacker/src/branch/master/tacker/service.py>`_
and the entry point `serve_wsgi` is called to build an instance of the
`TackerApiService`_, which is then returned to the server module,
which spawns a `Eventlet`_ `GreenPool`_ that will run the WSGI
application and respond to requests from clients.


.. _TackerApiService: https://opendev.org/openstack/tacker/src/branch/master/tacker/service.py

.. _Eventlet: https://eventlet.net/

.. _GreenPool: https://eventlet.net/doc/modules/greenpool.html

WSGI Application
----------------

During the building of the TackerApiService, the `_run_wsgi` function
creates a WSGI application using the `load_paste_app` function inside
`config.py`_ - which parses `api-paste.ini`_ - in order to create a WSGI app
using `Paste`_'s `deploy`_.

The api-paste.ini file defines the WSGI applications and routes - using the
`Paste INI file format`_.

The INI file directs paste to instantiate the `APIRouter`_ class of
Tacker, which contains several methods that map VNFM resources (such as
vnfd, vnf) to URLs, and the controller for each resource.


.. _config.py: https://opendev.org/openstack/tacker/src/branch/master/tacker/common/config.py

.. _api-paste.ini: https://opendev.org/openstack/tacker/src/branch/master/etc/tacker/api-paste.ini

.. _APIRouter: https://opendev.org/openstack/tacker/src/branch/master/tacker/api/v1/router.py

.. _Paste: https://pythonpaste.readthedocs.io/

.. _Deploy: https://pastedeploy.readthedocs.io/

.. _Paste INI file format: https://pastedeploy.readthedocs.io/#applications

Further reading
---------------

Tacker wsgi is based on neutron's extension. The following doc is still
relevant.

`Yong Sheng Gong: Deep Dive into Neutron <http://www.slideshare.net/gongys2004/inside-neutron-2>`_
