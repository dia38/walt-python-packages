import time, sys
from plumbum import cli
from walt.common.tools import format_sentence_about_nodes
from walt.client import myhelp
from walt.client.link import ClientToServerLink
from walt.client.tools import confirm
from walt.client.interactive import run_node_cmd, \
                                    run_device_ping, \
                                    NODE_SHELL_MESSAGE
from walt.client.transfer import run_transfer_with_node

POE_REBOOT_DELAY            = 2  # seconds

MSG_SOFT_REBOOT_FAILED = """\
%s did not acknowledge the reboot request. Probably it(they) was(were) not fully booted yet."""
MSG_SOFT_REBOOT_FAILED_TIP = """\
Retry 'walt node reboot %(nodes_ko)s' in a moment (and add option --hard if it still fails)."""

myhelp.register_topic('node-terminology', """
* 'owning' a node
* ---------------
In WalT terminology, if node <N> is deployed with an image created by user <U>,
we consider that "<U> owns <N>".

Thus, if you just started using WalT, "you do not own any node" until you deploy
an image on one of them (use 'walt node deploy <node(s)> <image>' for this).

A good practice is, once you are done with your experiment, to deploy the default
image on them (use 'walt node deploy my-nodes default' for this), in order to
release your 'ownership' on these nodes.
After you run this, these nodes will appear as 'free' to other WalT users.

* specifying a set of nodes 
* -------------------------
Some commands accept a "set of nodes":
- walt node deploy
- walt node reboot
- walt log show         (see option '--nodes')

In this case you can specify either:
* the keyword 'my-nodes' (this will select the nodes that you own)
* the keyword 'all-nodes'
* a coma separated list of nodes (e.g "rpi1,rpi2" or just "rpi1")
""")

class WalTNode(cli.Application):
    """WalT node management sub-commands"""
    @staticmethod
    def confirm_nodes_not_owned(server, node_set):
        not_owned = server.includes_nodes_not_owned(node_set, warn=True)
        if not_owned == None:
            return False
        if not_owned == True:
            if not confirm():
                return False
        return True

    @staticmethod
    def run_cmd(node_set, several_nodes_allowed, cmdargs, startup_msg=None):
        nodes_ip = None
        with ClientToServerLink() as server:
            if not WalTNode.confirm_nodes_not_owned(server, node_set):
                return
            nodes_ip = server.get_nodes_ip(node_set)
            if len(nodes_ip) == 0:
                return  # issue already reported
            elif len(nodes_ip) > 1 and not several_nodes_allowed:
                sys.stderr.write(
                    'Error: this command must target 1 node only.\n')
                return
        if nodes_ip:
            for ip in nodes_ip:
                if startup_msg:
                    print startup_msg
                run_node_cmd(ip, cmdargs)

@WalTNode.subcommand("show")
class WalTNodeShow(cli.Application):
    """show WalT nodes"""
    _all = False # default
    def main(self):
        with ClientToServerLink() as server:
            print server.show_nodes(self._all)
    @cli.autoswitch(help='show nodes used by other users too')
    def all(self):
        self._all = True

@WalTNode.subcommand("blink")
class WalTNodeBlink(cli.Application):
    """make a node blink for a given number of seconds"""
    def main(self, node_name, duration=60):
        try:
            seconds = int(duration)
        except:
            sys.stderr.write(
                '<duration> must be an integer (number of seconds).\n')
        else:
            with ClientToServerLink() as server:
                if server.blink(node_name, True):
                    print 'blinking for %ds... ' % seconds
                    try:
                        time.sleep(seconds)
                        print 'done.'
                    except KeyboardInterrupt:
                        print 'Aborted.'
                    finally:
                        server.blink(node_name, False)

class PoETemporarilyOff:
    def __init__(self, server, node_set):
        self.server = server
        self.node_set = node_set
        self.node_set_off = None
    def __enter__(self):
        self.node_set_off = self.server.poweroff(
                self.node_set, warn_poe_issues=True)
        return self.node_set_off != None
    def __exit__(self, type, value, traceback):
        if self.node_set_off:
            self.server.poweron(
                self.node_set_off, warn_poe_issues=True)

def reboot_nodes(server, node_set, hard=False):
    # try to soft-reboot
    if hard:
        print('Trying soft-reboot...')
    nodes_ok, nodes_ko = server.softreboot(node_set)
        # if it fails, try to power-cycle using PoE
    if len(nodes_ko) > 0:
        if hard:
            print('Trying hard-reboot (PoE)...')
            with PoETemporarilyOff(server, nodes_ko) as really_off:
                if really_off:
                    time.sleep(POE_REBOOT_DELAY)
        else:
            print(format_sentence_about_nodes(
                    MSG_SOFT_REBOOT_FAILED,
                    nodes_ko.split(',')))
            print(MSG_SOFT_REBOOT_FAILED_TIP % dict(nodes_ko = nodes_ko))

@WalTNode.subcommand("reboot")
class WalTNodeReboot(cli.Application):
    """reboot a (set of) node(s)"""
    _hard = False # default
    def main(self, node_set):
        with ClientToServerLink() as server:
            if not WalTNode.confirm_nodes_not_owned(server, node_set):
                return
            reboot_nodes(server, node_set, self._hard)
    @cli.autoswitch(help='try hard-reboot (PoE) if soft-reboot fails')
    def hard(self):
        self._hard = True

@WalTNode.subcommand("deploy")
class WalTNodeDeploy(cli.Application):
    """deploy an operating system image on a (set of) node(s)"""
    def main(self, node_set, image_name_or_default):
        with ClientToServerLink() as server:
            if server.has_image(image_name_or_default):
                # the list of nodes the keyword "my-nodes" refers to
                # may be altered by the server.set_image() call, thus
                # we have to get a real list of nodes before starting
                # anything.
                node_set = server.develop_node_set(node_set)
                if node_set is None:
                    return
                if not WalTNode.confirm_nodes_not_owned(server, node_set):
                    return
                server.set_image(node_set, image_name_or_default)
                reboot_nodes(server, node_set)

@WalTNode.subcommand("ping")
class WalTNodePing(cli.Application):
    """check that a node is reachable on WalT network"""
    def main(self, node_name):
        node_ip = None
        with ClientToServerLink() as server:
            node_ip = server.get_node_ip(node_name)
        if node_ip:
            run_device_ping(node_ip)

@WalTNode.subcommand("shell")
class WalTNodeShell(cli.Application):
    """run an interactive shell connected to the node"""
    def main(self, node_name):
        WalTNode.run_cmd(   node_name, False, [ ],
                            startup_msg=NODE_SHELL_MESSAGE)

@WalTNode.subcommand("run")
class WalTNodeRun(cli.Application):
    """run a command on a (set of) node(s)"""
    def main(self, node_set, *cmdargs):
        WalTNode.run_cmd(node_set, True, cmdargs)

@WalTNode.subcommand("cp")
class WalTNodeCp(cli.Application):
    """transfer files/dirs (client machine <-> node)"""
    def main(self, src, dst):
        with ClientToServerLink() as server:
            info = server.validate_node_cp(src, dst)
            if info == None:
                return
            try:
                run_transfer_with_node(**info)
            except (KeyboardInterrupt, EOFError):
                print
                print 'Aborted.'

@WalTNode.subcommand("wait")
class WalTNodeWait(cli.Application):
    """wait for a node (or a set of nodes) to be ready"""
    def main(self, node_set):
        try:
            with ClientToServerLink() as server_link:
                server_link.set_busy_label('Waiting')
                server_link.wait_for_nodes(node_set)
        except KeyboardInterrupt:
            print 'Aborted.'

