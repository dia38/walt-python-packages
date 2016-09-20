#!/usr/bin/env python

from walt.common.constants import WALT_SERVER_TCP_PORT
from walt.common.tcp import TCPServer
from walt.server.threads.main.blocking import BlockingTasksManager
from walt.server.threads.main.db import ServerDB
from walt.server.threads.main.images.manager import NodeImageManager
from walt.server.threads.main.interactive import InteractionManager
from walt.server.threads.main.logs import LogsManager
from walt.server.threads.main.mydocker import DockerClient
from walt.server.threads.main.network.dhcpd import DHCPServer
from walt.server.threads.main.network.tools import dhcp_stop
from walt.server.threads.main.nodes.manager import NodesManager
from walt.server.threads.main.devices.manager import DevicesManager
from walt.server.tools import format_sentence_about_nodes
from walt.server.threads.main.transfer import TransferManager
from walt.server.threads.main.apisession import APISession


class Server(object):

    def __init__(self, ev_loop, ui, shared):
        self.ev_loop = ev_loop
        self.ui = ui
        self.db = ServerDB()
        self.docker = DockerClient()
        self.blocking = BlockingTasksManager(shared.tasks)
        self.devices = DevicesManager(self.db)
        self.dhcpd = DHCPServer(self.db)
        self.images = NodeImageManager(self.db, self.blocking, self.dhcpd, self.docker)
        self.tcp_server = TCPServer(WALT_SERVER_TCP_PORT)
        self.logs = LogsManager(self.db, self.tcp_server, self.blocking)
        self.interaction = InteractionManager(\
                        self.tcp_server, self.ev_loop)
        self.transfer = TransferManager(\
                        self.tcp_server, self.ev_loop)
        self.nodes = NodesManager(  db = self.db,
                                    tcp_server = self.tcp_server,
                                    blocking = self.blocking,
                                    images = self.images.store,
                                    dhcpd = self.dhcpd,
                                    docker = self.docker,
                                    devices = self.devices)

    def prepare(self):
        self.tcp_server.join_event_loop(self.ev_loop)
        self.blocking.join_event_loop(self.ev_loop)
        self.db.plan_auto_commit(self.ev_loop)

    def update(self):
        self.ui.task_start('Scanning walt devices and images...')
        self.ui.task_running()
        # ensure the dhcp server is running,
        # otherwise the switches may have ip addresses
        # outside the WalT network, and we will not be able
        # to communicate with them when trying to update
        # the topology.
        self.dhcpd.update(force=True)
        self.ui.task_running()
        # topology exploration
        self.devices.rescan(ui=self.ui)
        self.ui.task_running()
        # re-update dhcp with any new device discovered
        self.dhcpd.update()
        self.ui.task_running()
        # mount images needed
        self.images.update()
        self.ui.task_done()

    def cleanup(self):
        APISession.cleanup_all()
        self.images.cleanup()
        self.blocking.cleanup()
        dhcp_stop()

    def set_image(self, requester, node_set, image_tag, warn_unknown_topology):
        nodes = self.nodes.parse_node_set(requester, node_set)
        if nodes == None:
            return # error already reported
        nodes_ok, nodes_ko = self.nodes.filter_on_connectivity( \
                            requester, nodes, warn_unknown_topology)
        macs = [ n.mac for n in nodes_ok ]
        if self.images.set_image(requester, macs, image_tag):
            if image_tag == 'default':
                sentence = '%s will now boot its(their) default image (other users will see it(they) is(are) \'free\').'
            else:
                sentence = '%s will now boot ' + image_tag + '.'
            requester.stdout.write(format_sentence_about_nodes(
                sentence, [n.name for n in nodes_ok]) + '\n')

    def rename_device(self, requester, old_name, new_name):
        self.devices.rename(requester, old_name, new_name)
        self.dhcpd.update()

    def device_rescan(self, requester):
        self.devices.rescan(requester=requester)
        self.dhcpd.update()

    def forget_device(self, device_name):
        self.db.forget_device(device_name)
        self.dhcpd.update()
