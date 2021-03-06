.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0
.. (c) 2017 OPNFV.

====================================
Enabling OPNFV Doctor using DevStack
====================================

This directory contains the files necessary to run OpenStack with enabled
OPNFV Doctor in DevStack.

To configure DevStack to enable OPNFV Doctor edit
``${DEVSTACK_DIR}/local.conf`` file and add::

    enable_plugin aodh http://git.openstack.org/openstack/aodh
    enable_plugin panko https://git.openstack.org/openstack/panko
    enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer
    enable_plugin osprofiler https://git.openstack.org/openstack/osprofiler
    enable_plugin doctor https://git.opnfv.org/doctor

to the ``[[local|localrc]]`` section.

.. note:: The order of enabling plugins matters.

Run DevStack as normal::

    $ ./stack.sh
