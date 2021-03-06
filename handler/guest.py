#!/usr/bin/python
# -*- coding:utf-8 -*-
# Powered By KK Studio
# Guests

from BaseHandler import BaseHandler
from tornado.web import authenticated as Auth
from vendor import functions as fun
import libvirt
import json


guest_status = {
    libvirt.VIR_DOMAIN_NOSTATE: u'<span style="color:#ccc;">未知</span>',
    libvirt.VIR_DOMAIN_RUNNING: u'<span style="color:green;">运行中</span>',
    libvirt.VIR_DOMAIN_BLOCKED: u'<span style="color:#ccc;">Blocked</span>',
    libvirt.VIR_DOMAIN_PAUSED: u'<span style="color:#ccc;">已挂起</span>',
    libvirt.VIR_DOMAIN_SHUTDOWN: u'<span style="color:#ccc;">已关机</span>',
    libvirt.VIR_DOMAIN_SHUTOFF: u'<span style="color:#ccc;">已关机</span>',
    libvirt.VIR_DOMAIN_CRASHED: u'<span style="color:red;">Crashed</span>',
    libvirt.VIR_DOMAIN_PMSUSPENDED: u'<span style="color:red;">PMSUSPENDED</span>'
}


class IndexHandler(BaseHandler):

    @Auth
    def get(self):
        guests = self.kvm.getGuests()
        self.render('guest/index.html',guests=guests,state=guest_status)


class AutostartHandler(BaseHandler):

    @Auth
    def post(self):
        name = self.get_argument('name')
        flag = self.get_argument('flag') # 0 or 1
        self.kvm.setAutostart(name,int(flag))
        self.returnJson({'code': 0, 'msg': u'操作成功！'})


class StartHandler(BaseHandler):

    @Auth
    def post(self):
        name = self.get_argument('name')
        result = self.kvm.startGuest(name)
        if result:
            code = 0
            msg = u'已开机！'
        else:
            code = -1
            msg = u'开机失败：%s' % self.kvm.msg
        self.returnJson({'code': code, 'msg': msg})


class ShutdownHandler(BaseHandler):

    @Auth
    def post(self):
        name = self.get_argument('name')
        force = self.get_argument('force','no')
        force = False if force=='no' else True
        result = self.kvm.shutdownGuest(name,force)
        if result:
            code = 0
            msg = u'正在关机……'
        else:
            code = -1
            msg = u'关机失败：%s' % self.kvm.msg
        self.returnJson({'code': code, 'msg': msg})


class RebootHandler(BaseHandler):

    @Auth
    def post(self):
        name = self.get_argument('name')
        result = self.kvm.rebootGuest(name)
        self.returnJson({'code':0,'result':result,'msg':self.kvm.msg})


# 创建虚拟机
class CreateGuestHandler(BaseHandler):

    @Auth
    def get(self):
        servers = self.get_kvm_server()
        iso = self.kvm.getStorageVols('iso')
        self.render('guest/create.html',servers=servers,os=self.kvm_os_type,iso=iso)

    @Auth
    def post(self):
        name = self.get_argument('name')
        cpus = self.get_argument('cpus') # CPU数量
        mem = self.get_argument('mem') # 内存大小，单位：KB
        hdd = self.get_argument('hdd') # 硬盘大小，单位：KB
        network = self.get_argument('network')
        cdrom = self.get_argument('cdrom')
        os = self.get_argument('os')
        desc = self.get_argument('desc')
        if not name:
            self.returnJson({'code':-1,'msg':u'实例名称不能为空'})
        if not cpus:
            self.returnJson({'code':-1,'msg':u'请指定CPU设置'})
        if not mem:
            self.returnJson({'code':-1,'msg':u'请指定内存设置'})
        if not hdd:
            self.returnJson({'code':-1,'msg':u'请指定硬盘设置'})
        if not network:
            self.returnJson({'code':-1,'msg':u'请指定网络设置'})
        if not os:
            self.returnJson({'code':-1,'msg':u'请选择操作系统类型'})
        # cdorm & desc are not require


class DetailHandler(BaseHandler):

    @Auth
    def get(self):
        name = self.get_argument('name')
        guest = self.kvm.getGuestDetail(name)
        self.render('guest/detail.html',name=name,guest=guest,state=guest_status)


# 远程连接
class ConsoleHandler(BaseHandler):

    @Auth
    def get(self):
        uuid = self.get_argument('uuid','')
        token = self.get_argument('token','')
        key = "%s%s" % (self.application.settings['kvman_console_token_key_pre'],uuid)
        stuff = self.redis.get(key)
        guest = ''
        port = 6080 # WebSocket Server Port
        if stuff:
            data = json.loads(stuff)
            guest = data['guest']
        self.render('guest/console.html',guest=guest,port=port,uuid=uuid,token=token)


    # 生成远程访问的Token
    @Auth
    def post(self):
        guest = self.get_argument('guest',None)
        if not guest:
            return self.returnJson({'code': -1, 'msg': u'该主机不存在！'})
        port = self.kvm.getVncPort(guest)
        if port > 0:
            token = fun.random_str(64)
            vnc = {
                'guest': guest,
                'token': token,
                'host': self.kvm_sid, # VNC Server Hostname, use Kvm Server Address
                'port': port # VNC Port
            }
            guest_uuid = self.kvm.getGuestUUID(guest)
            key_pre = self.application.settings['kvman_console_token_key_pre']
            key_expire = self.application.settings['kvman_console_token_expire']
            self.redis.setex(key_pre + guest_uuid, key_expire, json.dumps(vnc))
            data = {
                'guest': guest,
                'uuid': guest_uuid,
                'token': token
            }
            self.returnJson({'code': 0, 'data': data, 'msg': 'success'})
        else:
            self.returnJson({'code': -1, 'msg': u'该主机未开机！'})


# 退出远程连接
class ConsoleExitHandler(BaseHandler):

    @Auth
    def post(self):
        uuid = self.get_argument('uuid')
        key = "%s%s" % (self.application.settings['kvman_console_token_key_pre'], uuid)
        self.redis.delete(key)
        return self.returnJson({'code': 0, 'msg': 'success'})


# 控制台屏幕截图
class screenshotHandler(BaseHandler):

    @Auth
    def get(self):
        name = self.get_argument('name',None)
        force = self.get_argument('force',None)
        #img = '/static/img/console/guest0-win7.jpg' # Just for Testing
        img = self.kvm.getScreenshotImg(name,force)
        if img:
            img += '?delta=' + fun.random_str(32)
        data = {'code': self.kvm.code, 'data': {'img': img},'msg':self.kvm.msg}
        return self.returnJson(data)

