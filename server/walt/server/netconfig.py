import os, sys
from walt.common.tools import do
from walt.server import conf

IFACE_STATE_FILE='/var/lib/walt/.%(iface)s.state'
DOT1Q_FILTER='''\
ebtables -t filter -A FORWARD -p 802_1Q \
    -i %(src)s -o %(dst)s -j DROP'''

def filter_out_8021q(iface_src, iface_dst):
    do(DOT1Q_FILTER % dict(src=iface_src, dst=iface_dst))

def get_state_file(iface):
    return IFACE_STATE_FILE % dict(iface=iface)

def open_state_file(iface, mode):
    return open(get_state_file(iface), mode)

def remove_state_file(iface):
    os.remove(get_state_file(iface))

def get_vlan(iface_conf):
    if 'vlan' in iface_conf:
        return iface_conf['vlan']
    else:
        return None

def set_iface_up(iface):
    do('ip link set up dev %s' % iface)

def create_dummy_iface(iface, state_file):
    do('ip link add %s type dummy' % iface)
    set_iface_up(iface)
    state_file.write(iface + '\n')

def create_vlan_iface(raw_iface, vlan, vlan_iface, state_file):
    do('ip link add link %s name %s type vlan id %d' % \
        (raw_iface, vlan_iface, vlan))
    set_iface_up(vlan_iface)
    state_file.write(vlan_iface + '\n')

def create_bridge_iface(br_iface, interfaces, state_file):
    do('ip link add %s type bridge' % br_iface)
    for iface in interfaces:
        do('ip link set dev %s master %s' % (iface, br_iface))
    set_iface_up(br_iface)
    state_file.write(br_iface + '\n')

def setup_native_conf(raw_iface, iface, state_file):
    create_bridge_iface(iface, (raw_iface,), state_file)
    # isc-dhcp-server reads packets in raw mode on its interface
    # thus it detects 8021q (VLAN-tagged) packets it should not see.
    # In order to work around this issue we do not let 8021q
    # packets cross the bridge and reach our interface.
    filter_out_8021q(raw_iface, iface)

def setup_ip_conf(iface, ip_conf):
    if ip_conf == 'dhcp':
        do('dhclient %s' % iface)
    else:
        do('ip addr add %s dev %s' % (
                ip_conf, iface))

def up(iface, network_conf):
    with open_state_file(iface, 'w') as state_file:
        if iface in network_conf:
            iface_conf = network_conf[iface]
            raw_iface = iface_conf['raw-device']
            set_iface_up(raw_iface)
            vlan = get_vlan(iface_conf)
            if vlan:
                create_vlan_iface(raw_iface, vlan, iface, state_file)
            else:
                setup_native_conf(raw_iface, iface, state_file)
            if 'ip' in iface_conf:
                setup_ip_conf(iface, iface_conf['ip'])

def down(iface):
    with open_state_file(iface, 'r') as state_file:
        for line in state_file.readlines():
            sub_iface = line.strip()
            do('ip link del dev %s' % sub_iface)
    remove_state_file(iface)

def run():
    action = sys.argv[1]
    iface = os.environ['IFACE']
    if action == 'up':
        network_conf = conf['network']
        up(iface, network_conf)
    elif action == 'down':
        down(iface)
