#!/bin/bash -xe

# This script will be run by OpenStack CI before unit tests are run,
# it sets up the test system as needed.
# Developers should setup their test systems in a similar way.

# This setup needs to be run as a user that can run sudo.

function is_fedora {
  if [[ -x $(command -v dnf 2>/dev/null) ]]; then
      sudo dnf install -qy redhat-lsb-core
  else
      return
  fi



  if [[ -x $(command -v lsb_release 2>/dev/null) ]]; then
    os_VENDOR=$(lsb_release -i -s)

    if [ "$os_VENDOR" = "Fedora" ] || [ "$os_VENDOR" = "Red Hat" ] || \
        [ "$os_VENDOR" = "RedHatEnterpriseServer" ] || \
        [ "$os_VENDOR" = "RedHatEnterprise" ] || \
        [ "$os_VENDOR" = "CentOS" ] || [ "$os_VENDOR" = "OracleServer" ] || \
        [ "$os_VENDOR" = "Virtuozzo" ] ; then
        return 0
    else
        return
    fi
  fi
}

# The root password for the MySQL database; pass it in via
# MYSQL_ROOT_PW.
DB_ROOT_PW=${MYSQL_ROOT_PW:-insecure_slave}

# This user and its password are used by the tests, if you change it,
# your tests might fail.
DB_USER=openstack_citest
DB_PW=openstack_citest

if is_fedora ; then
    # services are not started by default

    # Enable and start MariaDB
    sudo systemctl enable --now mariadb
    
    # Intialiaze, Enable and start PostgreSQL
    pg_hba=/var/lib/pgsql/data/pg_hba.conf
    pg_conf=/var/lib/pgsql/data/postgresql.conf
    if ! sudo [ -e $pg_hba ]; then
        sudo postgresql-setup initdb
    fi
    sudo systemctl enable --now postgresql

    if sudo [ -e $pg_conf ]; then
        # Listen on all addresses
        sudo sed -i "/listen_addresses/s/.*/listen_addresses = '*'/" $pg_conf
    fi

    if sudo [ -e $pg_hba ];then
        # Do password auth from all IPv4 clients
        sudo sed -i "/^host/s/all\s\+127.0.0.1\/32\s\+ident/$DB_USER\t0.0.0.0\/0\tpassword/" $pg_hba
        # Do password auth for all IPv6 clients
        sudo sed -i "/^host/s/all\s\+::1\/128\s\+ident/$DB_USER\t::0\/0\tpassword/" $pg_hba
    fi

    sudo systemctl stop postgresql
    sudo systemctl start postgresql
fi

sudo -H mysqladmin -u root password $DB_ROOT_PW

# It's best practice to remove anonymous users from the database.  If
# a anonymous user exists, then it matches first for connections and
# other connections from that host will not work.
sudo -H mysql -u root -p$DB_ROOT_PW -h localhost -e "
    DELETE FROM mysql.user WHERE User='';
    FLUSH PRIVILEGES;
    CREATE USER '$DB_USER'@'%' IDENTIFIED BY '$DB_PW';
    GRANT ALL PRIVILEGES ON *.* TO '$DB_USER'@'%' WITH GRANT OPTION;"

# Now create our database.
mysql -u $DB_USER -p$DB_PW -h 127.0.0.1 -e "
    SET default_storage_engine=MYISAM;
    DROP DATABASE IF EXISTS openstack_citest;
    CREATE DATABASE openstack_citest CHARACTER SET utf8;"

# Same for PostgreSQL
# The root password for the PostgreSQL database; pass it in via
# POSTGRES_ROOT_PW.
DB_ROOT_PW=${POSTGRES_ROOT_PW:-insecure_slave}

# Setup user
root_roles=$(sudo -u root sudo -u postgres -i psql -t -c "
   SELECT 'HERE' from pg_roles where rolname='$DB_USER'")
if [[ ${root_roles} == *HERE ]];then
    sudo -u root sudo -u postgres -i psql -c "ALTER ROLE $DB_USER WITH SUPERUSER LOGIN PASSWORD '$DB_PW'"
else
    sudo -u root sudo -u postgres psql -c "CREATE ROLE $DB_USER WITH SUPERUSER LOGIN PASSWORD '$DB_PW'"
fi

# Store password for tests
cat << EOF > $HOME/.pgpass
*:*:*:$DB_USER:$DB_PW
EOF
chmod 0600 $HOME/.pgpass

# Now create our database
psql -h 127.0.0.1 -U $DB_USER -d template1 -c "DROP DATABASE IF EXISTS openstack_citest"
createdb -h 127.0.0.1 -U $DB_USER -l C -T template0 -E utf8 openstack_citest
