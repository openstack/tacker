# Devstack Installer for Tacker

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

Please also notice the version of vagrant supporting experimental feature
[Vagrant Disks](https://developer.hashicorp.com/vagrant/docs/disks) for
expanding the size of volume if you use Ubuntu box image. 
For other boxes than Ubuntu, plugin `vagrant-disksize` is required instead as
below. It is because the default size is not enough for deploying OpenStack
environment.

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

You should confirm you have a SSH key before you run the command. This tool
expects the type of your key is not `rsa` but `ed25519` because `rsa`
was deprecated as default in Ubuntu 22.04.
Update key path `ssh_pub_key` in `machines.yml` without your key is
`~/.ssh/id_ed25519.pub`.

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
$ ansible-playbook -i hosts site.yaml
```

After finished ansible's tasks, you can login to launched VMs with hostname you
defined in `machines.yml`.
So, let's login to controller node and OpenStack. You will find that two
examples of `local.conf` are prepared in `$HOME/devstack` for your environment.

* local.conf.example
* local.conf.kubernetes

```sh
$ ssh stack@192.168.56.11
$ cd devstack
$ cp local.conf.kubernetes local.conf
$ ./stack.sh
```

See instruction how to configure `local.conf` described in
[DevStack Quick Start](https://docs.openstack.org/devstack/latest/).

### Editor support

Although you can use any editors on the setup VM, it provides `vim` and
`neovim` with minimal configurations for LSP.
You can choose the editor by configuring parameters related vim
in `group_vars/all.yml`, so turn it `false` if you don't use the
support.

