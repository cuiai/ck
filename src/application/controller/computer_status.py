# #!/usr/bin/env python
# # -*- encoding: utf-8 -*-
#
# import re
# import time
# import psutil
# from os import getcwd
#
# from ping3 import ping
# from threading import Thread
# from pathlib import PureWindowsPath
#
# from application.controller.algorithm.openface import Openface
# from application.controller.config import LOG, CFG
#
#
# class ComputerChecker(Thread):
#     CHECK_INTERVAL = 1  # Sec
#
#     NET_DELAY = ""  # 网络延迟
#     MEM_USAGE = ""  # 内存使用率
#     DISK_USAGE = ""  # 当前磁盘使用率
#     FRAME_RATE = ""  # 当前算法帧率
#
#     def __init__(self):
#         super(ComputerChecker, self).__init__()
#         self.setName("ComputerChecker")
#         self.setDaemon(True)
#         self.is_exit = False
#         self.status_socket = None
#         self.ip_pattern = None
#         self.ip = None
#         self.crt_driver = None
#
#     def run(self):
#         # 从RTSP地址中解析出IP
#         try:
#             self.ip_pattern = re.compile(
#                 r'((?:(?:25[0-5]|2[0-4]\d|(?:1\d{2}|[1-9]?\d))\.){3}(?:25[0-5]|2[0-4]\d|(?:1\d{2}|[1-9]?\d)))'
#             )
#         except Exception as e:
#             LOG.error("编译IP地址正则出错: \n%s" % e)
#             return
#         # 获得当前磁盘盘符
#         crt_path = getcwd()
#         self.crt_driver = PureWindowsPath(crt_path).drive
#         if not self.crt_driver:
#             LOG.error("获取当前磁盘盘符失败")
#             return
#         # 初始化ZMQ
#         if self.init_zmq() is False:
#             return
#         count = 0
#         LOG.debug("计算机状态监测线程已启动")
#
#         while True:
#             if self.is_exit is True:
#                 break
#
#             # 更新数据
#             if count % 2 == 0:
#                 ComputerChecker.FRAME_RATE = self.get_frame_rate()
#             if count % 3 == 0:
#                 ComputerChecker.NET_DELAY = self.check_network_delay()
#             if count % 5 == 0:
#                 ComputerChecker.MEM_USAGE = self.get_memory_usage()
#             if count % 10 == 0:
#                 ComputerChecker.DISK_USAGE = self.get_current_disk_usage()
#
#             result = {
#                 "frame_rate": ComputerChecker.FRAME_RATE,
#                 "net_delay": ComputerChecker.NET_DELAY,
#                 "memory_usage": ComputerChecker.MEM_USAGE,
#                 "disk_usage": ComputerChecker.DISK_USAGE
#             }
#             # 发送数据
#             try:
#                 self.status_socket.send_json(result)
#             except Exception as e:
#                 LOG.error("发送结果失败：%s " % e)
#                 time.sleep(1)
#                 continue
#
#             if count == 10:
#                 count = 0
#             else:
#                 count += 1
#             time.sleep(self.CHECK_INTERVAL)
#
#     def get_frame_rate(self):
#         return Openface.CURRENT_FRAME_RATE
#
#     def check_network_delay(self):
#         ret = None
#         sampling_frequency = 2
#         if self.ip is None:
#             target_protcol_url = CFG.get('dst_stream', 'rtsp://admin:1234qwer@192.168.16.51:554')
#             if not self.ip_pattern:
#                 return ret
#             if target_protcol_url == 0:
#                 return
#             result = self.ip_pattern.findall(target_protcol_url)
#             if not result:
#                 LOG.error("目标IP格式有误")
#                 return ret
#             self.ip = result[0]
#         total = 0
#         for _ in range(sampling_frequency):
#             delay_ms = ping(self.ip, unit='ms')
#             if delay_ms is None:
#                 return ret
#             total += delay_ms
#             time.sleep(1)
#         avg = round(total / sampling_frequency, 4)
#         ret = avg
#         return ret
#
#     def get_memory_usage(self):
#         ret = None
#         memory_info = {}
#         try:
#             mem_info = psutil.virtual_memory()
#             memory_info['total'] = mem_info.total
#             memory_info['available'] = mem_info.available
#             memory_info['percent'] = mem_info.percent
#             memory_info['used'] = mem_info.used
#             memory_info['free'] = mem_info.free
#             ret = mem_info.percent
#         except Exception as e:
#             LOG.error("获取内存状态出错: \n%s" % e)
#             return ret
#         return ret
#
#     def get_current_disk_usage(self):
#         ret = None
#         try:
#             ret = psutil.disk_usage(self.crt_driver).percent
#         except Exception as e:
#             LOG.error(e)
#             return ret
#         return ret
#
#     def init_zmq(self):
#         ret = False
#         context = zmq.Context()
#         try:
#             self.status_socket = context.socket(zmq.PUB)
#             self.status_socket.bind("tcp://*:%s" % CFG.get('computer_status_port', 60004))
#             LOG.debug("初始化计算机状态数据发送套接字成功")
#         except Exception as e:
#             LOG.error(e)
#             return ret
#         ret = True
#         return ret
#
#     def exit(self):
#         self.is_exit = True
#
#
# if __name__ == '__main__':
#     cc = ComputerChecker()
#     cc.start()
