==========================================
Scripts for Setting of v1 Functional Tests
==========================================

We provide sample setup scripts for running Tacker v1 Functional Tests (FT).
It's intended to help to run the tests on your local environment.

.. note::

  The content of this document has been confirmed to work
  using Ubuntu 22.04, Kubernetes 1.30.5 and Helm 3.15.4.


Target Tests
~~~~~~~~~~~~

Not all the v1 functional tests are supported.

* tacker-ft-legacy-vim
* tacker-ft-v1-vnfpkgm
* tacker-ft-v1-k8s
* tacker-ft-v1-tosca-vnflcm
* tacker-ft-v1-userdata-vnflcm


Files
~~~~~

.. code-block::

  tools/doc_samples/setting_ft/
  |
  +--- openstack/
  |       openstack-controller.sh
  |       openstack-controller-tacker.sh
  |
  \--- kubernetes/
          kube-controller.sh
          kube-controller-k8s.sh
          kube-controller-tacker.sh

* openstack/{openstack-controller.sh,openstack-controller-tacker.sh}:
  These shell script files are what you would run without k8s.
  Store the shell script files on each of the virtual machine (VM) hosts
  controller and controller-tacker that you have created.
  Execute them on each host in order.

* kubernetes/
  {kube-controller.sh,kube-controller-k8s.sh,kube-controller-tacker.sh}:
  These shell script files are what you run when using k8s.
  The rest is the same as above.
  Store the shell script files on each of your VM hosts controller,
  controller-k8s, and controller-tacker.
  Execute them on each host in order.


Usage
~~~~~

Here is how to use the shell script files provided.
Run these provided shell script files after the shell script file
./stack.sh that you ran to build the DevStack has finished successfully.
Perform the following steps:

#. Edit files (if necessary)

   Edit these shell script files as needed for your environment.

   .. code-block:: console

     $ vi openstack-controller.sh
     $ vi openstack-controller-tacker.sh
     $ vi kube-controller.sh
     $ vi kube-controller-k8s.sh
     $ vi kube-controller-tacker.sh


#. Grant execution rights to each shell script file

   Grant execution rights to the shell script files provided here as follows:

   .. code-block:: console

     $ chmod +x openstack-controller.sh
     $ chmod +x openstack-controller-tacker.sh
     $ chmod +x kube-controller.sh
     $ chmod +x kube-controller-k8s.sh
     $ chmod +x kube-controller-tacker.sh


#. Run the shell script files

   Run the shell script files provided here as follows.
   The command prompt (e.g. stack@controller:~$ ) represents the user
   name and host name to run.
   Follow Step (a) if you're not using Kubernetes (k8s), or Step (b)
   if you're using k8s.
   In each case, execute the shell script files in the following order:

   Step (a) not using k8s

   .. code-block:: console

     stack@controller:~$ ./openstack-controller.sh
     stack@controller-tacker:~$ ./openstack-controller-tacker.sh

   Output example:

   .. code-block:: console

     stack@controller:~$ ./openstack-controller.sh
     d02ebf6e-9b4b-474f-9eb4-6492454653d4
         Manager "ptcp:6640:127.0.0.1"
             is_connected: true
         Bridge br-ex
             Port eth1
                 Interface eth1
             Port br-ex
                 Interface br-ex
                     type: internal
         Bridge br-int
             fail_mode: secure
             datapath_type: system
             Port ovn-0d4c53-0
                 Interface ovn-0d4c53-0
                     type: geneve
                     options: {csum="true", key=flow, remote_ip="192.168.56.12"}
             Port ovn-19aa8a-0
                 Interface ovn-19aa8a-0
                     type: geneve
                     options: {csum="true", key=flow, remote_ip="192.168.56.14"}
             Port br-int
                 Interface br-int
                     type: internal
             Port ovn-b5aa08-0
                 Interface ovn-b5aa08-0
                     type: geneve
                     options: {csum="true", key=flow, remote_ip="192.168.56.13"}
         ovs_version: "2.17.9"
     mysql: [Warning] Using a password on the command line interface can be insecure.
     host    hypervisor_hostname     mapped  uuid
     compute1        compute1        0       36fa9820-f25d-4ee9-8ec6-348c61230367
     compute2        compute2        0       52cb3474-aaba-4168-bcbe-d5eb2ec9c2d2
     INFO dbcounter [None req-fa994509-fb86-4112-a675-88f62d29f404 None None] Registered counter for database nova_api
     DEBUG dbcounter [-] [102425] Writer thread running {{(pid=102425) stat_writer /opt/stack/data/venv/lib/python3.10/site-packages/dbcounter.py:102}}
     INFO dbcounter [None req-fa994509-fb86-4112-a675-88f62d29f404 None None] Registered counter for database nova_cell1
     DEBUG dbcounter [-] [102425] Writer thread running {{(pid=102425) stat_writer /opt/stack/data/venv/lib/python3.10/site-packages/dbcounter.py:102}}
     mysql: [Warning] Using a password on the command line interface can be insecure.
     host    hypervisor_hostname     mapped  uuid
     compute1        compute1        1       36fa9820-f25d-4ee9-8ec6-348c61230367
     compute2        compute2        1       52cb3474-aaba-4168-bcbe-d5eb2ec9c2d2


   .. code-block:: console

     stack@controller-tacker:~$ ./openstack-controller-tacker.sh
     +----------------+-----------------------------------------------------+
     | Field          | Value                                               |
     +----------------+-----------------------------------------------------+
     | auth_cred      | {                                                   |
     |                |     "username": "nfv_user",                         |
     |                |     "user_domain_name": "Default",                  |
     |                |     "cert_verify": "False",                         |
     |                |     "project_id": null,                             |
     |                |     "project_name": "nfv",                          |
     |                |     "project_domain_name": "Default",               |
     |                |     "auth_url": "http://192.168.56.11/identity/v3", |
     |                |     "key_type": "barbican_key",                     |
     |                |     "secret_uuid": "***",                           |
     |                |     "password": "***"                               |
     |                | }                                                   |
     | auth_url       | http://192.168.56.11/identity/v3                    |
     | created_at     | 2024-12-20 02:50:33.307091                          |
     | description    | Default VIM                                         |
     | extra          |                                                     |
     | id             | aef62040-8bbf-42a6-ae67-41ecb176b676                |
     | is_default     | True                                                |
     | name           | VIM0                                                |
     | placement_attr | {                                                   |
     |                |     "regions": [                                    |
     |                |         "RegionOne"                                 |
     |                |     ]                                               |
     |                | }                                                   |
     | project_id     | d43072cade474f6183fafe62a723964a                    |
     | status         | ACTIVE                                              |
     | type           | openstack                                           |
     | updated_at     | None                                                |
     | vim_project    | {                                                   |
     |                |     "name": "nfv",                                  |
     |                |     "project_domain_name": "Default"                |
     |                | }                                                   |
     +----------------+-----------------------------------------------------+


   Step (b) using k8s

   .. code-block:: console

     stack@controller:~$ ./kube-controller.sh
     stack@controller-k8s:~$ ./kube-controller-k8s.sh
     stack@controller-tacker:~$ ./kube-controller-tacker.sh

   Output example:

   .. code-block:: console

     stack@controller:~$ ./kube-controller.sh
     d2ecc874-7e67-4de0-acc6-a91c85a3db3d
         Manager "ptcp:6640:127.0.0.1"
             is_connected: true
         Bridge br-int
             fail_mode: secure
             datapath_type: system
             Port ovn-965252-0
                 Interface ovn-965252-0
                     type: geneve
                     options: {csum="true", key=flow, remote_ip="192.168.56.23"}
             Port br-int
                 Interface br-int
                     type: internal
             Port ovn-947be9-0
                 Interface ovn-947be9-0
                     type: geneve
                     options: {csum="true", key=flow, remote_ip="192.168.56.22"}
         Bridge br-ex
             Port br-ex
                 Interface br-ex
                     type: internal
             Port eth1
                 Interface eth1
         ovs_version: "2.17.9"


   .. code-block:: console

     stack@controller-k8s:~$ ./kube-controller-k8s.sh
     1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000
         link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
     2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP mode DEFAULT group default qlen 1000
         link/ether 08:00:27:c8:98:64 brd ff:ff:ff:ff:ff:ff
         altname enp0s3
     3: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP mode DEFAULT group default qlen 1000
         link/ether 08:00:27:fe:b8:4b brd ff:ff:ff:ff:ff:ff
         altname enp0s8
     4: ovs-system: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
         link/ether ce:a5:37:75:58:27 brd ff:ff:ff:ff:ff:ff
     5: br-int: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
         link/ether 1a:b4:9a:5c:f7:f3 brd ff:ff:ff:ff:ff:ff
     7: veth8a11ff95@if2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default
         link/ether 4e:9f:3b:b9:1a:54 brd ff:ff:ff:ff:ff:ff link-netns 6516b4bd-db04-404d-ae04-c82203f4cd86
     8: veth76da22e3@if2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default
         link/ether 02:e6:c1:b1:42:57 brd ff:ff:ff:ff:ff:ff link-netns 9d7ff2fb-21c1-457e-9fa1-a7b3e8e87176
     9: genev_sys_6081: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 65000 qdisc noqueue master ovs-system state UNKNOWN mode DEFAULT group default qlen 1000
         link/ether 5e:44:4d:87:83:7f brd ff:ff:ff:ff:ff:ff
     10: br-ex: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
         link/ether 86:af:dc:f3:fe:4d brd ff:ff:ff:ff:ff:ff
     NAMESPACE      NAME                                         READY   STATUS    RESTARTS      AGE
     kube-flannel   pod/kube-flannel-ds-cv57g                    1/1     Running   0             38d
     kube-system    pod/coredns-55cb58b774-9qmrm                 1/1     Running   0             38d
     kube-system    pod/coredns-55cb58b774-tn9pq                 1/1     Running   0             38d
     kube-system    pod/kube-apiserver-controller-k8s            1/1     Running   5 (17m ago)   38d
     kube-system    pod/kube-controller-manager-controller-k8s   1/1     Running   2 (21m ago)   38d
     kube-system    pod/kube-proxy-9t2rz                         1/1     Running   0             38d
     kube-system    pod/kube-scheduler-controller-k8s            1/1     Running   2 (21m ago)   38d

     NAMESPACE     NAME                 TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)                  AGE
     default       service/kubernetes   ClusterIP   10.96.0.1    <none>        443/TCP                  38d
     kube-system   service/kube-dns     ClusterIP   10.96.0.10   <none>        53/UDP,53/TCP,9153/TCP   38d

     NAMESPACE      NAME                             DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR            AGE
     kube-flannel   daemonset.apps/kube-flannel-ds   1         1         1       1            1           <none>                   38d
     kube-system    daemonset.apps/kube-proxy        1         1         1       1            1           kubernetes.io/os=linux   38d

     NAMESPACE     NAME                      READY   UP-TO-DATE   AVAILABLE   AGE
     kube-system   deployment.apps/coredns   2/2     2            2           38d

     NAMESPACE     NAME                                 DESIRED   CURRENT   READY   AGE
     kube-system   replicaset.apps/coredns-55cb58b774   2         2         2       38d
     pod "coredns-55cb58b774-9qmrm" deleted
     pod "coredns-55cb58b774-tn9pq" deleted
     NAMESPACE      NAME                                         READY   STATUS    RESTARTS      AGE
     kube-flannel   pod/kube-flannel-ds-cv57g                    1/1     Running   0             38d
     kube-system    pod/coredns-55cb58b774-6dllm                 1/1     Running   0             7s
     kube-system    pod/coredns-55cb58b774-xmkqq                 0/1     Running   0             7s
     kube-system    pod/kube-apiserver-controller-k8s            1/1     Running   5 (17m ago)   38d
     kube-system    pod/kube-controller-manager-controller-k8s   1/1     Running   2 (21m ago)   38d
     kube-system    pod/kube-proxy-9t2rz                         1/1     Running   0             38d
     kube-system    pod/kube-scheduler-controller-k8s            1/1     Running   2 (21m ago)   38d

     NAMESPACE     NAME                 TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)                  AGE
     default       service/kubernetes   ClusterIP   10.96.0.1    <none>        443/TCP                  38d
     kube-system   service/kube-dns     ClusterIP   10.96.0.10   <none>        53/UDP,53/TCP,9153/TCP   38d

     NAMESPACE      NAME                             DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR            AGE
     kube-flannel   daemonset.apps/kube-flannel-ds   1         1         1       1            1           <none>                   38d
     kube-system    daemonset.apps/kube-proxy        1         1         1       1            1           kubernetes.io/os=linux   38d

     NAMESPACE     NAME                      READY   UP-TO-DATE   AVAILABLE   AGE
     kube-system   deployment.apps/coredns   1/2     2            1           38d

     NAMESPACE     NAME                                 DESIRED   CURRENT   READY   AGE
     kube-system   replicaset.apps/coredns-55cb58b774   2         2         1       38d
     Reading package lists... Done
     Building dependency tree... Done
     Reading state information... Done
     The following NEW packages will be installed:
       sshpass
     0 upgraded, 1 newly installed, 0 to remove and 55 not upgraded.
     Need to get 11.7 kB of archives.
     After this operation, 35.8 kB of additional disk space will be used.
     Get:1 http://us.archive.ubuntu.com/ubuntu jammy/universe amd64 sshpass amd64 1.09-1 [11.7 kB]
     Fetched 11.7 kB in 2s (5,856 B/s)
     Selecting previously unselected package sshpass.
     (Reading database ... 79969 files and directories currently installed.)
     Preparing to unpack .../sshpass_1.09-1_amd64.deb ...
     Unpacking sshpass (1.09-1) ...
     Setting up sshpass (1.09-1) ...
     Processing triggers for man-db (2.10.2-1) ...
     Scanning processes...
     Scanning candidates...
     Scanning linux images...

     Running kernel seems to be up-to-date.

     Restarting services...
      /etc/needrestart/restart.d/systemd-manager
      systemctl restart packagekit.service polkit.service ssh.service systemd-networkd.service systemd-resolved.service systemd-timesyncd.service systemd-udevd.service udisks2.service
     Service restarts being deferred:
      /etc/needrestart/restart.d/dbus.service
      systemctl restart networkd-dispatcher.service
      systemctl restart systemd-logind.service
      systemctl restart user@1000.service

     No containers need to be restarted.

     No user sessions are running outdated binaries.

     No VM guests are running outdated hypervisor (qemu) binaries on this host.
     Warning: Permanently added 'controller-tacker' (ED25519) to the list of known hosts.
     Adding user `helm' ...
     Adding new group `helm' (1002) ...
     Adding new user `helm' (1002) with group `helm' ...
     Creating home directory `/home/helm' ...
     Copying files from `/etc/skel' ...
     total 16
     drwxr-xr-x 2 root  root  4096 Nov 11 10:32 .
     drwxr-x--- 3 helm  helm  4096 Dec 20 04:43 ..
     -rw------- 1 stack stack 5653 Nov 11 10:32 config
     total 16
     drwxr-xr-x 2 helm helm 4096 Nov 11 10:32 .
     drwxr-x--- 3 helm helm 4096 Dec 20 04:43 ..
     -rw------- 1 helm helm 5653 Nov 11 10:32 config
     total 4
     drwxr-xr-x 2 helm helm 4096 Dec 20 04:43 helm
     --- /etc/ssh/sshd_config_bk     2024-07-23 18:04:13.103999238 +0000
     +++ /etc/ssh/sshd_config        2024-12-20 04:43:09.287879199 +0000
     @@ -54,7 +54,7 @@
      #IgnoreRhosts yes

      # To disable tunneled clear text passwords, change to no here!
     -#PasswordAuthentication yes
     +PasswordAuthentication yes
      #PermitEmptyPasswords no

      # Change to yes to enable challenge-response passwords (beware issues with
       % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                      Dload  Upload   Total   Spent    Left  Speed
     100 15.8M  100 15.8M    0     0  9656k      0  0:00:01  0:00:01 --:--:-- 9658k
     linux-amd64/
     linux-amd64/helm
     linux-amd64/LICENSE
     linux-amd64/README.md
     version.BuildInfo{Version:"v3.15.4", GitCommit:"fa9efb07d9d8debbb4306d72af76a383895aa8c4", GitTreeState:"clean", GoVersion:"go1.22.6"}


   .. code-block:: console

     stack@controller-tacker:~$ ./kube-controller-tacker.sh
     +----------------+-----------------------------------------------------+
     | Field          | Value                                               |
     +----------------+-----------------------------------------------------+
     | auth_cred      | {                                                   |
     |                |     "username": "nfv_user",                         |
     |                |     "user_domain_name": "Default",                  |
     |                |     "cert_verify": "False",                         |
     |                |     "project_id": null,                             |
     |                |     "project_name": "nfv",                          |
     |                |     "project_domain_name": "Default",               |
     |                |     "auth_url": "http://192.168.56.21/identity/v3", |
     |                |     "key_type": "barbican_key",                     |
     |                |     "secret_uuid": "***",                           |
     |                |     "password": "***"                               |
     |                | }                                                   |
     | auth_url       | http://192.168.56.21/identity/v3                    |
     | created_at     | 2024-12-20 09:36:53.346748                          |
     | description    | Default VIM                                         |
     | extra          |                                                     |
     | id             | 76bf55a1-7df9-4d0b-999a-9febd074dc6f                |
     | is_default     | True                                                |
     | name           | VIM0                                                |
     | placement_attr | {                                                   |
     |                |     "regions": [                                    |
     |                |         "RegionOne"                                 |
     |                |     ]                                               |
     |                | }                                                   |
     | project_id     | 89047a7c599f44978802b1330fecc646                    |
     | status         | ACTIVE                                              |
     | type           | openstack                                           |
     | updated_at     | None                                                |
     | vim_project    | {                                                   |
     |                |     "name": "nfv",                                  |
     |                |     "project_domain_name": "Default"                |
     |                | }                                                   |
     +----------------+-----------------------------------------------------+
       % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                      Dload  Upload   Total   Spent    Left  Speed
     100   138  100   138    0     0    500      0 --:--:-- --:--:-- --:--:--   500
     100 49.0M  100 49.0M    0     0  31.9M      0  0:00:01  0:00:01 --:--:-- 46.5M
       % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                      Dload  Upload   Total   Spent    Left  Speed
     100   138  100   138    0     0    512      0 --:--:-- --:--:-- --:--:--   513
     100    64  100    64    0     0    164      0 --:--:-- --:--:-- --:--:--   164
     kubectl: OK
     Client Version: v1.30.5
     Kustomize Version: v5.0.4-0.20230601165947-6ce0bf390ce3
     total 8
     -rw------- 1 stack stack 5653 Nov 11 10:32 config
     Kubernetes control plane is running at https://192.168.56.23:6443
     CoreDNS is running at https://192.168.56.23:6443/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

     To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.
     Config for Kubernetes VIM 'tacker/samples/tests/etc/samples/local-k8s-vim.yaml' generated.
     NAME                   TYPE                                  DATA   AGE
     default-token-k8svim   kubernetes.io/service-account-token   3      1s
     --- tacker/samples/tests/etc/samples/local-k8s-vim.yaml_bk      2024-11-11 02:46:00.096741454 +0000
     +++ tacker/samples/tests/etc/samples/local-k8s-vim.yaml 2024-12-20 09:36:57.433035278 +0000
     @@ -1,5 +1,24 @@
     -auth_url: "https://127.0.0.1:6443"
     -bearer_token: "secret_token"
     +auth_url: "https://192.168.56.23:6443"
     +bearer_token: "eyJhbGciOiJSUzI1NiIsImtpZCI6IkItQ1FuM2FCcmNDaF9uRzNTd05ETWFtbFFhVWgtbmZwaExLY0dUeFRPRE0ifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tazhzdmltIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImRlZmF1bHQiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiI5YWFmNWJlYi02MTIzLTQyYWItYTE3Ni04ODUxZWJkNGFkOTAiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6ZGVmYXVsdDpkZWZhdWx0In0.qSxCrtCjtVG1AbyeDuXpkxrenskrSPLx9pnLhNyL5Bgckis97ILaqSjf4IbUL0myqQUKET9smlNxXm1Hjk7bmjL5TBUMNJiewywuOXZkQhF3xqJWmdcl_9bPWcYp0D4olHbtPNpgImbRLn_ZfzymdqtYx6I-SRUCKQunkAGq4dxOM9wLQ3VPLja1li9lDeU6NXgkX7XGO8rA2m1Q0tPzINVNanN-z0Rut0XdWzEhepDwo_MyLnLdhg4oC5gbfNqbUwwqkDDV3Pt6c6_d1vXohDeS5VJETrTZG16qbDY5Ah8YPeiayfLseuznk3rui3lYUWvHZvO4J_ZCUV1LZ7zcOQ"
     +ssl_ca_cert: "-----BEGIN CERTIFICATE-----
     +MIIDBTCCAe2gAwIBAgIIWX6AGYfkbaYwDQYJKoZIhvcNAQELBQAwFTETMBEGA1UE
     +AxMKa3ViZXJuZXRlczAeFw0yNDExMTExMDI1MzhaFw0zNDExMDkxMDMwMzhaMBUx
     +EzARBgNVBAMTCmt1YmVybmV0ZXMwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK
     +AoIBAQC+jwt4uPT7uyx6DlWrJ7OnnfQFKKfPJ/rHEOiVpV57qG6JW9rCnYzXZ0i/
     +eEVDXtQnQ/NZ2VXPY0UZI30Ew+w99z+Eh/m/MCsyTOq5YUuN3/5NQ4NsXc8VBHSm
     +yoelJLw2hPwmzNsgDouZqtvIURFuwxL4tc1/UeH51sj4cw4l6yJcRC0I2llYxF8Q
     +znTaOWeQ5LuaxoHOFb01wENFacoRNgcNoFB7oVeb5h+c0hM+cHqeRdQVc96VQDxa
     +ynqIzdJ+whDmzEif5RK2R7LWNLXLQlEIUkGnOg+iaLdXPbGKzS38o5mZqRheXVHD
     +nFb5ZeOQ1oqPStQJCz7cNMMkS983AgMBAAGjWTBXMA4GA1UdDwEB/wQEAwICpDAP
     +BgNVHRMBAf8EBTADAQH/MB0GA1UdDgQWBBTqeh0oly+huPQfzIMaslJesN+CsjAV
     +BgNVHREEDjAMggprdWJlcm5ldGVzMA0GCSqGSIb3DQEBCwUAA4IBAQBrpAL5oE6b
     +Dw/di4gowUfv5boTpHmbpRxXhA/MBL5THTV0rR7hkdt3O+j2wsoGWrbuSkyfBhUi
     +AVp3V98+qNmKiLKKYlugCTCUK3J0uHewWdlCY+voKiBR0oMdzMGqbApqZ7GFPIVJ
     +ORycUf3R8Gg07BeMzrXNM4AylRu8jsfwa/xCLCLg4ueNwHxQYHlA77vmj+2tTb8K
     +mmkaAGRaIZrzH+Y/Dg7whAKtym7S5TxutXqWa3mRL/2M2kwP+Y3RdhXqvAFlmytK
     +eHFOJSeuYYa1kLTiCMknLAcwd6XLA7CyWiS1FJmSHGp5eIlCUku4oV7IhaMb6Fgp
     +mRmUryUhgyKs
     +-----END CERTIFICATE-----"
      project_name: "default"
     -ssl_ca_cert: None
      type: "kubernetes"
     +
     Config for Kubernetes VIM 'tacker/samples/tests/etc/samples/local-k8s-vim-helm.yaml' generated.
     --- tacker/samples/tests/etc/samples/local-k8s-vim-helm.yaml_bk 2024-11-11 02:46:00.096741454 +0000
     +++ tacker/samples/tests/etc/samples/local-k8s-vim-helm.yaml    2024-12-20 09:36:58.733045070 +0000
     @@ -1,7 +1,25 @@
     -auth_url: "https://127.0.0.1:6443"
     -bearer_token: "secret_token"
     +auth_url: "https://192.168.56.23:6443"
     +bearer_token: "eyJhbGciOiJSUzI1NiIsImtpZCI6IkItQ1FuM2FCcmNDaF9uRzNTd05ETWFtbFFhVWgtbmZwaExLY0dUeFRPRE0ifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tazhzdmltIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImRlZmF1bHQiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiI5YWFmNWJlYi02MTIzLTQyYWItYTE3Ni04ODUxZWJkNGFkOTAiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6ZGVmYXVsdDpkZWZhdWx0In0.qSxCrtCjtVG1AbyeDuXpkxrenskrSPLx9pnLhNyL5Bgckis97ILaqSjf4IbUL0myqQUKET9smlNxXm1Hjk7bmjL5TBUMNJiewywuOXZkQhF3xqJWmdcl_9bPWcYp0D4olHbtPNpgImbRLn_ZfzymdqtYx6I-SRUCKQunkAGq4dxOM9wLQ3VPLja1li9lDeU6NXgkX7XGO8rA2m1Q0tPzINVNanN-z0Rut0XdWzEhepDwo_MyLnLdhg4oC5gbfNqbUwwqkDDV3Pt6c6_d1vXohDeS5VJETrTZG16qbDY5Ah8YPeiayfLseuznk3rui3lYUWvHZvO4J_ZCUV1LZ7zcOQ"
     +ssl_ca_cert: "-----BEGIN CERTIFICATE-----
     +MIIDBTCCAe2gAwIBAgIIWX6AGYfkbaYwDQYJKoZIhvcNAQELBQAwFTETMBEGA1UE
     +AxMKa3ViZXJuZXRlczAeFw0yNDExMTExMDI1MzhaFw0zNDExMDkxMDMwMzhaMBUx
     +EzARBgNVBAMTCmt1YmVybmV0ZXMwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK
     +AoIBAQC+jwt4uPT7uyx6DlWrJ7OnnfQFKKfPJ/rHEOiVpV57qG6JW9rCnYzXZ0i/
     +eEVDXtQnQ/NZ2VXPY0UZI30Ew+w99z+Eh/m/MCsyTOq5YUuN3/5NQ4NsXc8VBHSm
     +yoelJLw2hPwmzNsgDouZqtvIURFuwxL4tc1/UeH51sj4cw4l6yJcRC0I2llYxF8Q
     +znTaOWeQ5LuaxoHOFb01wENFacoRNgcNoFB7oVeb5h+c0hM+cHqeRdQVc96VQDxa
     +ynqIzdJ+whDmzEif5RK2R7LWNLXLQlEIUkGnOg+iaLdXPbGKzS38o5mZqRheXVHD
     +nFb5ZeOQ1oqPStQJCz7cNMMkS983AgMBAAGjWTBXMA4GA1UdDwEB/wQEAwICpDAP
     +BgNVHRMBAf8EBTADAQH/MB0GA1UdDgQWBBTqeh0oly+huPQfzIMaslJesN+CsjAV
     +BgNVHREEDjAMggprdWJlcm5ldGVzMA0GCSqGSIb3DQEBCwUAA4IBAQBrpAL5oE6b
     +Dw/di4gowUfv5boTpHmbpRxXhA/MBL5THTV0rR7hkdt3O+j2wsoGWrbuSkyfBhUi
     +AVp3V98+qNmKiLKKYlugCTCUK3J0uHewWdlCY+voKiBR0oMdzMGqbApqZ7GFPIVJ
     +ORycUf3R8Gg07BeMzrXNM4AylRu8jsfwa/xCLCLg4ueNwHxQYHlA77vmj+2tTb8K
     +mmkaAGRaIZrzH+Y/Dg7whAKtym7S5TxutXqWa3mRL/2M2kwP+Y3RdhXqvAFlmytK
     +eHFOJSeuYYa1kLTiCMknLAcwd6XLA7CyWiS1FJmSHGp5eIlCUku4oV7IhaMb6Fgp
     +mRmUryUhgyKs
     +-----END CERTIFICATE-----"
      project_name: "default"
     -ssl_ca_cert: None
      type: "kubernetes"
      extra:
     -  use_helm: true
     \ No newline at end of file
     +    use_helm: true
     +--------------------------------------+------+----------------------------------+-----------+------------+--------+
     | ID                                   | Name | Tenant_id                        | Type      | Is Default | Status |
     +--------------------------------------+------+----------------------------------+-----------+------------+--------+
     | 76bf55a1-7df9-4d0b-999a-9febd074dc6f | VIM0 | 89047a7c599f44978802b1330fecc646 | openstack | True       | ACTIVE |
     +--------------------------------------+------+----------------------------------+-----------+------------+--------+
     +----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
     | Field          | Value                                                                                                                                                                |
     +----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
     | auth_cred      | {                                                                                                                                                                    |
     |                |     "bearer_token": "***",                                                                                                                                           |
     |                |     "ssl_ca_cert": "b'gAAAAABnZTrA9T2bRK905WuX6oZxoIcorZEsX_St5bu-iKqepORVUseveibpN5NLeMDj5K8n3bTV6VFegWuoBK467CZ8re-mGEFfGXMFjhGF5kjDAf_Ec-                         |
     |                | EqrC5c4s1qNW7oaklGL1lNg6yDvbDPhGp_N79pyfn9bMbocEh_tBK_CCOythaJ1QudoObqbXglmgTY45xH_-h4WzZWd0TTC-p-ESd5BOlCLM-                                                        |
     |                | uCHunD1SN9Ext6dy3vsfU6mVMDNaSiEgHMUe0zpiuOBJd0ld-U1NtXRmbmTw_Stg66Gx8AVLEIDxmqFmsAjzK-                                                                               |
     |                | XW62L3N2NqXJ0WBc_E0VmSpnvXOvLR1cpNkCL08ZPqJ5jZonriTFoEId9V2e1UFQrQBnigiwvGEH8_GQ4mZI1LxIqzQLpUwkd_jPtzsCTpdRnFeec6YmJms2JCoIWrNOQOeGwpXXqSRIVk9LqqzMQ5pBhx7LH-ODwJy8 |
     |                | GLHc2cEoy2OiyZ4jfhkhBnBzK99QqFWGTkWAoOfbCAxSswnQQNXJPZDB8rZ_tBowvUGAHh1WaIz3c5nArKEM2ynpB_naii6KmsGTP7cA3Vh0uF5DAn3vDk1W_sjt93edzUT9k2sHpwSvqcLkJep3HibGeFKxO72AljgE |
     |                | UOUAX0ap63x3Hf5-                                                                                                                                                     |
     |                | 1HuZrRyWWBE7Je4QoDVE_vcGVQlVeTC5BihADUPHzhRc1S8FbtGGg5WALV65c7HdsvSRzXtzN4_qEBz_0aD7BcFBXSoXimk3er8DT96zH6MADc62Z_4vnHglwV_jpRkfk1HuMpwCtobRuh5T6RX9tQ9Bbldx3G8gOoMz |
     |                | mhcdwDOX8G5ILd_UdArwS9_5Bxm7T9nNfTTiadmHj7saYPe3uQim0BTuqcPxQOieXvukmz7ge29HLJBOZ8DrwRQX8xnXIzf5AezaGzpWV61ADa8VlGei62cbJa3fM1rxboB_YVETfjjReNqT84n8s7sSy2KrjcqOXJA7 |
     |                | cwi_Bg1z1zXzd2Dp3bmqJzFYuIcHc0errA4GajrtyppmMxIteZeNB8ai6Kwc9Zi2zra4nh7r3Ybbn_zR9Hg4Zb0RYD9BdRQAb4qJTK1zFA5bgCGMrWCaZb-                                              |
     |                | e9UBrCXo5_BkGPg9Ow0emifG2fCkB0qLN7yAuoMl34xuBs7v6ZkA0TSRTh2Mdg5fnNUPsAXH32xJ0fDkiKA9pcR9dkBbG04flDqZpy2niV19PF2JYHo-                                                 |
     |                | 1Zej591qKwEan_tpGDOzArFDNAFYrAkScFhCIzlE53MCsq99n-ETLMYMTZRZtbAWcP8BQRerbEaZsRBUw6YsqI9MLKeTaiAZz8ZVt_JKwSIVqs-Mlx9jlcE-                                             |
     |                | NsPNMFQSPl8WqEJlCvAI_HWOhang59N0UasjcQTw44H6lVXzQB8CfNBea1uQS4dDm43zITaScto2wwccLyTSg9RAAwneWOuDDaLPNu0vQKf5IJ5eD_w-fbH-U-                                           |
     |                | Vzuw2RyNCfbOaTnqzb66nR8JEqQ8P64TkXAgkl2K6y_yXYIxEd2SkGjMSq3mTnx6SNbLpcwY7DsT9v0iNJEyemB8078EWZOaZr1_WqlH8uEA=='",                                                    |
     |                |     "auth_url": "https://192.168.56.23:6443",                                                                                                                        |
     |                |     "username": "None",                                                                                                                                              |
     |                |     "key_type": "barbican_key",                                                                                                                                      |
     |                |     "secret_uuid": "***"                                                                                                                                             |
     |                | }                                                                                                                                                                    |
     | auth_url       | https://192.168.56.23:6443                                                                                                                                           |
     | created_at     | 2024-12-20 09:37:05.618109                                                                                                                                           |
     | description    | Kubernetes VIM                                                                                                                                                       |
     | extra          | helm_info={'masternode_ip':['192.168.56.23'],'masternode_username':'helm','masternode_password':'helm_password'}                                                     |
     | id             | adf0cca6-8d5d-4e92-9e21-a5638ddf5113                                                                                                                                 |
     | is_default     | False                                                                                                                                                                |
     | name           | vim-kubernetes                                                                                                                                                       |
     | placement_attr | {                                                                                                                                                                    |
     |                |     "regions": [                                                                                                                                                     |
     |                |         "default",                                                                                                                                                   |
     |                |         "kube-flannel",                                                                                                                                              |
     |                |         "kube-node-lease",                                                                                                                                           |
     |                |         "kube-public",                                                                                                                                               |
     |                |         "kube-system"                                                                                                                                                |
     |                |     ]                                                                                                                                                                |
     |                | }                                                                                                                                                                    |
     | project_id     | 89047a7c599f44978802b1330fecc646                                                                                                                                     |
     | status         | ACTIVE                                                                                                                                                               |
     | type           | kubernetes                                                                                                                                                           |
     | updated_at     | None                                                                                                                                                                 |
     | vim_project    | {                                                                                                                                                                    |
     |                |     "name": "default"                                                                                                                                                |
     |                | }                                                                                                                                                                    |
     +----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
     +----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
     | Field          | Value                                                                                                                                                                |
     +----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
     | auth_cred      | {                                                                                                                                                                    |
     |                |     "bearer_token": "***",                                                                                                                                           |
     |                |     "ssl_ca_cert": "b'gAAAAABnZTrD-FN762CKIgk_kmZym19PDCeTd9Bh8rXTwdHS_p5lKGg0aGGNdJmdSZwmpWI4HwrJxZeq_LCaritEqF4_HukQs1Z7jq5G_Zj9b-                                 |
     |                | JztptO530v6_LjrKVJmnYQb8Jupsx01Z52gfkSbfaBmThAE4SbmpOBBpHfdcBwUFpHe3OAIzl9GFG2wWNteVrZ-                                                                              |
     |                | TLhFro9YwlM8oh9kQKVOHEapiA8SFrIGPpOn1XcWN6t__KbqDrU2nrK0rDry0jCsPuRZ2MPIrKjCczphoA2MmgDSiEO-CEfdLHfegULpKYfAEgxRr-CpNYJCcRNHIJvrEzxZHiBHLD38q0w7XsyAdaTNLn6Z6p-S-nm_ |
     |                | rucwA3lwz7EaVxGBImsoO2XRgydLRsZy5M60-                                                                                                                                |
     |                | zjWhiiIVtsVQBF9U6WXHl432okRZxLG0TIQIiwiZMh1S9cGaCsiPkGbYZcl176Li3pfA1ERbzAdlK7Fro8tKwEzc3qy0Rs9aMMP5VbHCGNISLtQHVOiQfedbykuQqKje9ILs7QyIHbtPj_zxe1o0XYfE8Y0ALc1jUBfR |
     |                | 3F9M7VSun-Q9XYdUuuejGNtkGAZTaLTZVuwZiLRVg4hyNN1Qz09Qgm-                                                                                                              |
     |                | 9Qnhq6ygpThX2ytcQeds0zwdC3VQ9tsN1dMzjz_xR49QwwlIYYL0d_gMMuQnwnSbW5YEB3qznCNxDdZ2tG_EGBQE7T5UybCQU7UzcwCxpXnh6-m1aA5aoY5EryAhaVWukQ9Iv-                               |
     |                | jjyzGVh50gMnO8UJBjF4N0JH-7fzRsqxGxOpm7NTpBURMzrdFtq4wqDbZ_KGXWL_rAhRN7rlkizvm2-4JDRhEjndHHnN41AJbj8zEM5_u_ufbPklv6Sy6hQ70j8ojVz8Bqxqv5RF39NPiT-kgVJsMqkrX0C7_yvkva9O |
     |                | V9SxorgdhyksyhPFUgCVraLdXVJY95UKsQeA_GpTTQJ0CryD6OWU0BhUAN5SvqARr4zElA_TAvjaKxr4v7fVFddT0v2DcncG2OhOe6k82svwPVvvhA8avHLgTHOdl_qSPDrv9AWguBom0wqQex_EgcsLdwrBFMI2uJqe |
     |                | inn1ISd-Lg6JKcYfrC9klVWSw9XNRn9jM_fhd3SfttzSId6NPm5y_rSJlE_aE6UmlbMBRJzM0_zaFuI0IYzu-_If63ADCB9gN9b1XTlCgb64VWKucse_aahftvTi73arcBegUKu-                             |
     |                | KScpZ9BIFyQHcrPiR3uAeLHxn_wXv2-5Nhxw35IMZzGBgael1N8bBaSEsgAGLfl2kNjt9j1O1XryDdmiqYmPaMyqq1M02CpAHoI7AIUKvv3-4ULHj7yT3MYoe0SFVZ7J_iKHl0wZKm-                          |
     |                | qmP8CRL34hQbzs89pkCIrYKmo2KxcmcAdmYdBuQiVhwWqW4VDuA64wB0IP-QIQTVrtmikcFYH8huT85m-rU5230f2MiamQMZ01ADV1PMu8uJf-                                                       |
     |                | ASgqfaesWeC61Of4nhbIZ5Wm1Rp0Ln2Y45CmiM5V5DbtXsHeYhkwT8KjEO9LvJ7WNLlYyuRMFO6Xwh8bEjE78H91RAKjgQQurL65svtLxA=='",                                                      |
     |                |     "auth_url": "https://192.168.56.23:6443",                                                                                                                        |
     |                |     "username": "None",                                                                                                                                              |
     |                |     "key_type": "barbican_key",                                                                                                                                      |
     |                |     "secret_uuid": "***"                                                                                                                                             |
     |                | }                                                                                                                                                                    |
     | auth_url       | https://192.168.56.23:6443                                                                                                                                           |
     | created_at     | 2024-12-20 09:37:08.136510                                                                                                                                           |
     | description    | Kubernetes VIM                                                                                                                                                       |
     | extra          | use_helm=True                                                                                                                                                        |
     | id             | 4d843bcc-af0b-42ab-86dd-dd710905a3c2                                                                                                                                 |
     | is_default     | False                                                                                                                                                                |
     | name           | vim-kubernetes-helm                                                                                                                                                  |
     | placement_attr | {                                                                                                                                                                    |
     |                |     "regions": [                                                                                                                                                     |
     |                |         "default",                                                                                                                                                   |
     |                |         "kube-flannel",                                                                                                                                              |
     |                |         "kube-node-lease",                                                                                                                                           |
     |                |         "kube-public",                                                                                                                                               |
     |                |         "kube-system"                                                                                                                                                |
     |                |     ]                                                                                                                                                                |
     |                | }                                                                                                                                                                    |
     | project_id     | 89047a7c599f44978802b1330fecc646                                                                                                                                     |
     | status         | ACTIVE                                                                                                                                                               |
     | type           | kubernetes                                                                                                                                                           |
     | updated_at     | None                                                                                                                                                                 |
     | vim_project    | {                                                                                                                                                                    |
     |                |     "name": "default"                                                                                                                                                |
     |                | }                                                                                                                                                                    |
     +----------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------+
     +--------------------------------------+---------------------+----------------------------------+------------+------------+--------+
     | ID                                   | Name                | Tenant_id                        | Type       | Is Default | Status |
     +--------------------------------------+---------------------+----------------------------------+------------+------------+--------+
     | 4d843bcc-af0b-42ab-86dd-dd710905a3c2 | vim-kubernetes-helm | 89047a7c599f44978802b1330fecc646 | kubernetes | False      | ACTIVE |
     | 76bf55a1-7df9-4d0b-999a-9febd074dc6f | VIM0                | 89047a7c599f44978802b1330fecc646 | openstack  | True       | ACTIVE |
     | adf0cca6-8d5d-4e92-9e21-a5638ddf5113 | vim-kubernetes      | 89047a7c599f44978802b1330fecc646 | kubernetes | False      | ACTIVE |
     +--------------------------------------+---------------------+----------------------------------+------------+------------+--------+
     constants.py  container_update_mgmt.py  __init__.py  __pycache__  vnflcm_abstract_driver.py  vnflcm_noop.py
     --- /opt/stack/tacker/setup.cfg_bk      2024-11-11 02:46:00.132741905 +0000
     +++ /opt/stack/tacker/setup.cfg 2024-12-20 09:37:11.401141579 +0000
     @@ -63,6 +63,7 @@
      tacker.tacker.mgmt.drivers =
          noop = tacker.vnfm.mgmt_drivers.noop:VnfMgmtNoop
          vnflcm_noop = tacker.vnfm.mgmt_drivers.vnflcm_noop:VnflcmMgmtNoop
     +    mgmt-container-update = tacker.vnfm.mgmt_drivers.container_update_mgmt:ContainerUpdateMgmtDriver
      oslo.config.opts =
          tacker.auth = tacker.auth:config_opts
          tacker.common.config = tacker.common.config:config_opts
     --- /etc/tacker/tacker.conf_bk  2024-11-11 03:11:18.252006525 +0000
     +++ /etc/tacker/tacker.conf     2024-12-20 09:37:11.781144499 +0000
     @@ -3059,6 +3059,7 @@
      # MGMT driver to communicate with Hosting VNF/logical service instance tacker
      # plugin will use (list value)
      #vnflcm_mgmt_driver = vnflcm_noop
     +vnflcm_mgmt_driver = vnflcm_noop,mgmt-container-update

      #
      # From tacker.vnfm.plugin
     ...
     copying tacker/tests/var/ca.crt -> build/lib/tacker/tests/var
     copying tacker/tests/var/certandkey.pem -> build/lib/tacker/tests/var
     copying tacker/tests/var/certificate.crt -> build/lib/tacker/tests/var
     copying tacker/tests/var/privatekey.key -> build/lib/tacker/tests/var
