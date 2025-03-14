# Util method in vagrant-devstack

require "fileutils"

module VdUtils

  # Get the contents of SSH public key to upload it to VMs.
  def ssh_pub_key(config)
    default_key_path = "~/.ssh/id_ed25519.pub"

    if config["global"] != nil
      if config["global"]["ssh_pub_key"]
        key_path = File.expand_path(
          config["global"]["ssh_pub_key"].gsub("$HOME", "~"))
      end
    end

    key_path = File.expand_path(default_key_path) if key_path == nil

    begin
      ssh_pub_key = open(key_path).read.chomp
    rescue => e
      puts e
    end

    return ssh_pub_key
  end


  def setup_git_config()
    src = "~/.gitconfig"

    Dir.glob("roles/**/controller").each do |target_dir|
      dst = "#{target_dir}/templates/gitconfig.j2"

      gitconfig = File.expand_path src
      if File.exist? gitconfig
        FileUtils.copy(gitconfig, dst)
      end
    end
  end


  # Generate local ssh config file used by ssh with `-F` option.
  def setup_ssh_config(config)
    dst = File.expand_path "#{__dir__}/../ssh_config"

    if config["machines"] != nil
      entries = []
      config["machines"].each do |m|
        entries << {"Host" => m["hostname"],
                    "HostName" => m["private_ips"][0],
                    "User" => "stack"}
      end

      str = ""
      entries.each do |ent|
        ent.each do |k, v|
          if k == "Host"
            str += "#{k} #{v}\n"
          else
            str += "  #{k} #{v}\n"
          end
        end
      end
      str.chomp

      str += "Host *\n" +
        "  StrictHostKeyChecking no\n" +
        "  UserKnownHostsFile=/dev/null\n"

      open(dst, "w+") {|f|
        f.write(str)
      }
    end
  end

  # Return vagrant experimental features as a list.
  def vagrant_experimentals()
    res = []
    if ENV["VAGRANT_EXPERIMENTAL"]
      res = ENV["VAGRANT_EXPERIMENTAL"].split(",")
    end
    res
  end

  # Experimental feature "disks" can be enabled only for virtualbox provider and
  # included in VAGRANT_EXPERIMENTAL env variable.
  def is_disks_enabled(provider)
    if provider == "virtualbox"
      if vagrant_experimentals().include? "disks"
        return true
      end
    end
    return false
  end

  module_function :ssh_pub_key, :setup_git_config, :setup_ssh_config,
    :vagrant_experimentals, :is_disks_enabled

end
