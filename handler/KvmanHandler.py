#!/usr/bin/python
# -*- coding:utf-8 -*-
# Powered By KK Studio
# 2020-04-22

import json
from service.kvm import kvm

class KvmanHandler:

    kvm_sid_update = True # Invoke set_kvm_sid

    # 获取 Kvm Server 配置
    def get_kvm_server(self, hostname=None):
        key = self.application.settings['kvm_servers_key']
        if hostname:
            stuff = self.redis.hget(key, hostname)
            if stuff:
                servers = json.loads(stuff)
            else:
                servers = None
        else:
            stuff = self.redis.hgetall(key)
            if stuff:
                servers = [json.loads(stuff[i]) for i in stuff]
                servers = sorted(servers,key=lambda item : item['hostname']) # Sort by hostname
            else:
                servers = []
        return servers

    @property
    def kvm(self):
        print 'Invoke self.kvm ...'
        if self.kvm_sid:
            server = self.get_kvm_server(self.kvm_sid)
        else:
            server_count = self.redis.hlen(self.application.settings['kvm_servers_key'])
            if server_count == 1:
                servers = self.get_kvm_server()
                server = servers[0]
                self.kvm_sid = server['hostname']
            else:
                server = None
        return kvm(server)
