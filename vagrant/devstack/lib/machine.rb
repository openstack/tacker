require "yaml"

class Machines < Array

  class Machine
    attr_reader :hostname, :provider, :box, :nof_cpus, :mem_size, :disk_size,
      :private_ips, :public_ips, :ssh_forward_x11, :fwd_port_list

    def initialize(
      hostname="controller", provider="virtualbox", box="ubuntu/focal64",
      nof_cpus=2, mem_size=4, disk_size=10,
      private_ips=["192.168.33.11"], public_ips=nil, ssh_forward_x11=false,
      fwd_port_list=nil)
      @hostname = hostname
      @provider = provider
      @box = box
      @nof_cpus = nof_cpus
      @mem_size = mem_size
      @disk_size = disk_size
      @private_ips = private_ips
      @public_ips = public_ips
      @ssh_forward_x11 = ssh_forward_x11
      @fwd_port_list = fwd_port_list
    end
  end

  def initialize(machines_attr)
    machines_attr.each_with_index do |m, idx|
      self[idx] = Machine.new(
        m["hostname"], m["provider"], m["box"],
        m["nof_cpus"], m["mem_size"], m["disk_size"],
        m["private_ips"], m["public_ips"],
        m["ssh_forward_x11"],
        m["fwd_port_list"])
    end
  end

end
