
SETUP_INTF                  = "eth0"
WALT_INTF                   = "walt-net"
EXTERN_INTF                 = "walt-out"
DEFAULT_IMAGE               = 'default'
SNMP_TIMEOUT                = 3
DOCKER_HUB_GET_TAGS_URL     = 'https://registry.hub.docker.com/v1/repositories/%(image_name)s/tags'
WALT_DBNAME                 = "walt"
WALT_DBUSER                 = "root"
SSH_COMMAND                 = "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5"
UI_FIFO_PATH                = '/var/lib/walt/ui.fifo'
UI_RESPONSE_FIFO_PATH       = '/var/lib/walt/ui-response.fifo'
WALT_NODE_NET_SERVICE_PORT  = 12346
SERVER_SNMP_CONF            = dict(version = 2, community = 'private')
