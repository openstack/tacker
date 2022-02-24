# vagrant-devstack

## What is this

Deployment tool for devstack for testing multi-VM OpenStack environment,
consists of vagrant and ansible.

It only supports Ubuntu on VirtualBox currently.


## How to use

### Requirements

You need to install required software before running this tool. Please follow
instructions on official sites for installation.

* [VirtualBox](https://www.virtualbox.org/)
* [vagrant](https://www.vagrantup.com/)
* [ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)

Before launching your VMs, you should should install plugin `vagrant-disksize`
for expanding size of volume of VM. It is because the default size of box
provided from Ubuntu, 10GB or so, is not enough for deploying devstack
environment. It's required for expanding the volume size.

```sh
$ vagrant plugin install vagrant-disksize
```

### Configure and Fire Up VMs

Before launching VMs with vagrant, configure `machines.yml`, which defines
parameters of each VM you deploy. It should be placed at project root, or failed
to run `vagrant up`. You can use template files in `samples` directory.

```sh
$ cp samples/machines.yml .
$ YOUR_FAVORITE_EDITOR machines.yml
```

You should take care about `private_ips` which is used in `hosts` for
`ansible-playbook` as explained later.

You should confirm you have a SSH public key before you run vagrant. If your key
is different from `~/.ssh/id_rsa.pub`, update `ssh_pub_key` in `machines.yml`.

Run `vagrant up` after configurations are done. It launches VMs and create a
user `stack` on them.

```sh
$ vagrant up
```

If `vagrant up` is completed successfully, you are ready to login to VMs as
`stack` user with your SSH public key.

### Setup Devstack

This tool provides ansible playbooks for setting up devstack. You should update
entries of IP addresses in `hosts` as you defined `private_ips` in
`machines.yml`.

There are some parameters in `group_vars/all.yml` such as password on devstack
or optional configurations. You don't need to update it usually.

```sh
$ ansible-playbook -i hosts site.yml
```

After finished ansible's tasks, you can login to launched VMs. So, login to
controller node and run `stack.sh` for installing OpenStack. You will find that
`local.conf` is prepared for your environment by using its example.
See instruction how to configure `local.conf` described in
[DevStack Quick Start](https://docs.openstack.org/devstack/latest/)
if you customize it by yourself.

```sh
$ ssh stack@192.168.33.11
$ cd devstack
$ YOUR_FAVORITE_EDITOR local.conf
$ ./stack.sh
```
