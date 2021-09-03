#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import time
import socket
import threading
from application.controller import config
from application.controller.config import CFG, LOG


class StatServer(threading.Thread):
    def __init__(self):
        super(StatServer, self).__init__()
        self.setName("StatusServer")
        self.setDaemon(True)
        self.socket = None
        self.clients = []
        self.has_got_connection = False

    def run(self):
        LOG.debug("客户端状态监测线程已启动")

        if self.init() is False:
            LOG.error('初始化连接失败')
            return

        while True:
            connection, address = self.socket.accept()
            self.has_got_connection = True
            threading.Thread(target=self.monitor, args=(connection, address,)).start()
            time.sleep(2)

    def monitor(self, connection, address):
        while self.has_got_connection is False:
            time.sleep(2)
            continue

        if connection is None or address is None:
            return
        LOG.debug('%s已连接到状态服务器' % address[0])
        while True:
            try:
                data = connection.recv(1024)
            except:
                continue
            uuid = data.decode('utf-8')
            if uuid not in self.clients:
                # print("self.clients.append(uuid={})".format(uuid))
                self.clients.append(uuid)

    def quit(self):
        time.sleep(3)
        while self.has_got_connection is False:
            time.sleep(2)
            continue
        while True:
            if len(self.clients) == 0:
                # print('detect 0')
                time.sleep(5)
                if len(self.clients) == 0:
                    LOG.info("连接到算法服务端的所有客户端都已关闭，程序自动退出")
                    # print('quit')
                    config.IS_EXIT = True
                else:
                    self.clear()
            else:
                self.clear()

            time.sleep(5)

    def clear(self):
        self.clients.clear()
        # print("self.clients.clear()")

    def init(self):
        ret = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = '0.0.0.0'
        port = CFG.get('status_port', 60005)
        try:
            self.socket.bind((host, port))
        except Exception as e:
            LOG.error(e)
            return ret
        self.socket.listen(10)
        threading.Thread(target=self.quit).start()
        ret = True
        return ret


if __name__ == '__main__':
    stat = StatServer()
    stat.start()
    stat.join()
