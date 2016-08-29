import datetime, cPickle as pickle

from walt.common.crypto.dh import DHPeer
from walt.common.versions import API_VERSIONING
from walt.common.api import api, api_expose_method
from walt.common.versions import UPLOAD

WALT_SERVER_DAEMON_VERSION = 'server v' + str(UPLOAD)

@api
class CSAPI(object):

    def __init__(self, server, images, devices, nodes, logs):
        self.server = server
        self.images = images
        self.devices = devices
        self.nodes = nodes
        self.logs = logs
        self.requester = None

    @api_expose_method
    def get_version(self):
        return WALT_SERVER_DAEMON_VERSION

    @api_expose_method
    def get_CS_API_version(self):
        return API_VERSIONING['CS'][0]

    @api_expose_method
    def device_rescan(self):
        self.server.device_rescan(self.requester)

    @api_expose_method
    def device_tree(self):
        return self.devices.topology.tree()

    @api_expose_method
    def device_show(self):
        return self.devices.topology.show()

    @api_expose_method
    def show_nodes(self, show_all):
        return self.nodes.show(self.requester, show_all)

    @api_expose_method
    def get_reachable_nodes_ip(self, node_set):
        return self.nodes.get_reachable_nodes_ip(
                        self.requester, node_set)

    @api_expose_method
    def get_device_ip(self, device_name):
        return self.devices.get_device_ip(
                        self.requester, device_name)

    @api_expose_method
    def get_node_ip(self, node_name):
        return self.nodes.get_node_ip(
                        self.requester, node_name)

    @api_expose_method
    def blink(self, node_name, blink_status):
        return self.nodes.blink(self.requester, node_name, blink_status)

    @api_expose_method
    def parse_set_of_nodes(self, node_set):
        nodes = self.nodes.parse_node_set(self.requester, node_set)
        if nodes:
            return [n.name for n in nodes]

    @api_expose_method
    def includes_nodes_not_owned(self, node_set, warn):
        return self.nodes.includes_nodes_not_owned(self.requester, node_set, warn)

    @api_expose_method
    def develop_node_set(self, node_set):
        return self.nodes.develop_node_set(self.requester, node_set)

    @api_expose_method
    def poweroff(self, node_set, warn_unknown_topology):
        return self.nodes.setpower(self.requester, node_set, False, warn_unknown_topology)

    @api_expose_method
    def poweron(self, node_set, warn_unknown_topology):
        return self.nodes.setpower(self.requester, node_set, True, warn_unknown_topology)

    @api_expose_method
    def validate_node_cp(self, src, dst):
        return self.nodes.validate_cp(self.requester, src, dst)

    @api_expose_method
    def wait_for_nodes(self, q, node_set):
        self.nodes.wait(self.requester, q, node_set)

    @api_expose_method
    def rename(self, old_name, new_name):
        self.server.rename_device(self.requester, old_name, new_name)

    @api_expose_method
    def has_image(self, image_tag):
        return self.images.has_image(self.requester, image_tag)

    @api_expose_method
    def set_image(self, node_set, image_tag, warn_unknown_topology):
        self.server.set_image(self.requester, node_set, image_tag, warn_unknown_topology)

    @api_expose_method
    def is_device_reachable(self, device_name):
        return self.devices.is_reachable(self.requester, device_name)

    @api_expose_method
    def count_logs(self, history, **kwargs):
        unpickled_history = (pickle.loads(e) if e else None for e in history)
        return self.server.db.count_logs(history = unpickled_history, **kwargs)

    @api_expose_method
    def forget(self, device_name):
        self.server.forget_device(device_name)

    @api_expose_method
    def fix_image_owner(self, other_user):
        return self.images.fix_owner(self.requester, other_user)

    @api_expose_method
    def search_images(self, q, keyword):
        self.images.search(self.requester, q, keyword)

    @api_expose_method
    def clone_image(self, q, clonable_link, force=False, auto_update=False):
        self.images.clone(requester = self.requester,
                          q = q,
                          clonable_link = clonable_link,
                          force = force,
                          auto_update = auto_update)

    @api_expose_method
    def get_dh_peer(self):
        return DHPeer()

    @api_expose_method
    def publish_image(self, q, auth_conf, image_tag):
        self.images.publish(requester = self.requester,
                          q = q,
                          auth_conf = auth_conf,
                          image_tag = image_tag)

    @api_expose_method
    def docker_login(self, auth_conf):
        return self.server.docker.login(auth_conf, self.requester.stdout)

    @api_expose_method
    def show_images(self):
        return self.images.show(self.requester.username)

    @api_expose_method
    def create_image_shell_session(self, image_tag):
        return self.images.create_shell_session(self.requester, image_tag)

    @api_expose_method
    def remove_image(self, image_tag):
        self.images.remove(self.requester, image_tag)

    @api_expose_method
    def rename_image(self, image_tag, new_tag):
        self.images.rename(self.requester, image_tag, new_tag)

    @api_expose_method
    def duplicate_image(self, image_tag, new_tag):
        self.images.duplicate(self.requester, image_tag, new_tag)

    @api_expose_method
    def update_image(self, image_tag, force):
        self.images.update_walt_software(self.requester, image_tag, force)

    @api_expose_method
    def validate_image_cp(self, src, dst):
        return self.images.validate_cp(self.requester, src, dst)

    @api_expose_method
    def add_checkpoint(self, cp_name, pickled_date):
        date = None
        if pickled_date:
            date = pickle.loads(pickled_date)
        self.logs.add_checkpoint(self.requester, cp_name, date)

    @api_expose_method
    def remove_checkpoint(self, cp_name):
        self.logs.remove_checkpoint(self.requester, cp_name)

    @api_expose_method
    def list_checkpoints(self):
        self.logs.list_checkpoints(self.requester)

    @api_expose_method
    def get_pickled_time(self):
        return pickle.dumps(datetime.datetime.now())

    @api_expose_method
    def get_pickled_checkpoint_time(self, cp_name):
        return self.logs.get_pickled_checkpoint_time(self.requester, cp_name)

