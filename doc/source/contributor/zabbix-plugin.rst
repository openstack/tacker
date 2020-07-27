..
      Copyright 2014-2017 OpenStack Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

========================
How to use Zabbix Plugin
========================

This document explains how Tacker VNFM's Zabbix-plugin works with Zabbix
monitoring tool to provide application monitoring for VNF.

VNF application monitoring requires three pre-installation or configuration
settings. You do not have to do a lot of work or complex settings.

1. Zabbix-agent Installation and Setting in VNF.

Zabbix-Agent must be installed in the VNF. And you need to set it up. The
necessary settings must be made in /etc/zabbix/zabbix_agentd.conf in the
VNF. Installation and the setting method is as follows.

.. code-block:: console

  sudo apt-get update
  sudo apt-get upgrade
  sudo apt-get install zabbix-agent
  sudo echo 'zabbix ALL=NOPASSWD: ALL' >> /etc/sudoers

Then open the /etc/zabbix/zabbix_agentd.conf file and write for Server,
ServerActive Hostname, EnableRemoteCommands. However, this approach is
more difficult to manage as the number of VNFs increases.

Therefore, to solve this problem, the method presented in this document
are as follows. After creating the VNF based on the TOSCA template,
the USER_DATA parameter is executed on the assumption that the VNF
is initialized. We can install and make the necessary settings
automatically. Here is an example of a User-data script.

.. code-block:: console

  user_data: |
  #!/bin/bash
  sudo apt-get -y update
  sudo apt-get -y upgrade
  sudo apt-get -y install zabbix-agent
  sudo sed -i "2s/.*/`ifconfig [Interface name in VNF] | grep ""\"inet addr:\"""| cut -d: -f2 | awk ""\"{ print $1 }\"""`/g" "/etc/hosts"
  sudo sed -i "s/Bcast/`cat /etc/hostname`/g" "/etc/hosts"
  sudo sed -i "3s/.*/[Zabbix Host IP Address]\tmonitor/g" "/etc/hosts"
  sudo /etc/init.d/networking restart
  sudo echo 'zabbix ALL=NOPASSWD: ALL' >> /etc/sudoers
  sudo sed -i "s/# EnableRemoteCommands=0/EnableRemoteCommands=1/" "/etc/zabbix/zabbix_agentd.conf"
  sudo sed -i "s/Server=127.0.0.1/Server=[Zabbix server's IP Address]/" "/etc/zabbix/zabbix_agentd.conf"
  sudo sed -i "s/ServerActive=127.0.0.1/ServerActive=[Zabbix server's IP Address:Port]/" "/etc/zabbix/zabbix_agentd.conf"
  sudo sed -i "s/Hostname=Zabbix server/Hostname=`cat /etc/hostname`/" "/etc/zabbix/zabbix_agentd.conf"
  sudo service zabbix-agent restart

Use the sed command to modify the information in the conf file.
The basic network interface finds the IP address for ens3, sets it,
and sets the hostname. The zabbix user also needs permissions to run
the monitoring script. EnablRemoteCommands can be set to 1 to enable
execution of action commands created by Zabbix-Server.

2. Installing Zabbix Server

Because Zabbix Server requires a lot of processes for monitoring
projects, it is recommended to build it as a separate physical
node if performance stability is required. Installation instructions
for Zabbix Server are detailed in the manual provided by Zabbix (see [#first]_).
Examples of installation procedures are based on Ubuntu16.04
and zabbix 3.2.

.. code-block:: console

  sudo apt-get update
  sudo apt-get upgrade
  sudo apt-get install php7.0* libapache2-mod-php7.0
  sudo wget http://repo.zabbix.com/zabbix/3.2/ubuntu/pool/main/z/zabbix-release/zabbix-release_3.2-1+xenial_all.deb
  sudo dpkg -i zabbix-release_3.2-1+xenial_all.deb
  sudo apt-get install zabbix-server-mysql zabbix-frontend-php

Install mysql to store Zabbix-server and monitoring data and
necessary information, and install Zabbix-frotend-php to
provide web pages. Database creation is as follows.

.. code-block:: console

  shell> mysql -uroot -p[ROOT_PASSWORD]
  mysql> create database zabbix character set utf8 collate utf8_bin;
  mysql> grant all privileges on zabbix.* to zabbix@localhost identified by '[PASSWORD]';
  FLUSH PRIVILEGES;
  mysql> quit;
  cd /usr/share/doc/zabbix-server-mysql
  zcat create.sql.gz | mysql -u root -p zabbix

We must modify the vi /etc/zabbix/zabbix_server.conf file to
provide the Zabbix-server.

.. code-block:: console

  DBHost=localhost
  DBName=[DBName]
  DBUser=[DBUser]
  DBPassword=[PASSWORD]

At the end of the next operation, we are now ready to use the
Zabbix-server to complete the finish operation.

.. code-block:: console

  service zabbix-server start
  update-rc.d zabbix-server enable
  vi /etc/zabbix/apache.conf
  =>php_value date.timezone [location/city]
  service zabbix-server restart
  service apache2 restart

This installation method is based on manual, but it includes
additional explanation and installation part of dependency
file installation.

3. Template

The following templates are used for application monitoring.
If we create a VNFD by creating the template below and use it
to create a VNF, we can monitor the application without any
additional steps. If we want automatic configuration, it is
recommended to use USER_DATA parameter.

If we enter Zabbix-related information in the template, you will
get a Token according to the internal workflow of Zabbix-plugin.
It it used to configure various monitoring functions.

.. code-block:: console

        app_monitoring_policy:
          name: zabbix
          zabbix_username: [Zabbix user ID]
          zabbix_password: [Zabbix user Password]
          zabbix_server_ip: [Zabbix server IP]
          zabbix_server_port: [Zabbix server Port]
          parameters:
            application:
              app_name: [application-name]
              app_port: [application-port]
              ssh_username: [ssh username in VNF OS]
              ssh_password: [ssh password in VNF OS]
              app_status:
                condition: [comparison,value]
                actionname: [action name]
                cmd-action: [Command to be executed in VNF]
              app_memory:
                condition: [comparison,value]
                actionname: [action name]
                cmd-action: [Command to be executed in VNF]
            OS:
              os_agent_info:
                condition: [comparison,value]
                actionname: [action name]
                cmd-action: [Command to be executed in VNF]
              os_proc_value:
                condition: [comparison,value]
                actionname: [action name]
                cmd-action: [Command to be executed in VNF]
              os_cpu_load:
                condition: [comparison,value]
                actionname: [action name]
                cmd-action: [Command to be executed in VNF]
              os_cpu_usage:
                condition: [comparison,value]
                actionname: [action name]
                cmd-action: [Command to be executed in VNF]

4. Actions
Currently, only cmd is supported as an action function.
Respawn and Scale Action will be updated with additional
proposals and corresponding functionality as more template
definitions and corresponding additional functions are required.

References
==========
.. [#first] https://www.zabbix.com/documentation/3.2/manual

