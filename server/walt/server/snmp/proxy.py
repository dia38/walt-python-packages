#!/usr/bin/env python
import copy
from snimpy.manager import Manager
from poe import PoEProxy
from lldp import LLDPProxy
from vlan import VlanProxy

SNMP_OPTS = {
    "version": 2,
    "community": "private",
    'retries': 2,
    'timeout': 1
}

class Proxy(object):
        def __init__(self, host, poe=False, lldp=False, vlan=False):
            opts = SNMP_OPTS.copy()
            opts['host'] = host
            self.host = host
            self.snmp = Manager(**opts)
            if poe:
                self.poe = PoEProxy(self.snmp, host)
            if lldp:
                self.lldp = LLDPProxy(self.snmp)
            if vlan:
                self.vlan = VlanProxy(self.snmp)
