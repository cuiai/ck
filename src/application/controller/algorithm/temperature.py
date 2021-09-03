# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
#
# import time
# import random
# from threading import Thread
# from datetime import datetime
#
# from application.common_lib import EDAThread
# from application.controller import config
# from application.controller.config import LOG, CFG
# from application.controller.algorithm.Temperature.FTDevManager import FTCamera
#
#
# class EDATemp:
#     temp = None
#     ts = None
#
#     def __init__(self, temp, ts=time.time()):
#         self.temp = temp
#         self.ts = ts
#
#
# class TemperatureThread(Thread):
#     def __init__(self):
#         super(TemperatureThread, self).__init__()
#         self.is_thread_exit = False
#         self.is_thread_pause = False
#         self.ft_obj = FTCamera(log_output=LOG.error)
#         self.last_temperature = 0
#
#     def thread_exit(self):
#         self.is_thread_exit = True
#
#     def thread_pause(self):
#         self.is_thread_pause = True
#
#     def thread_continue(self):
#         self.is_thread_pause = False
#
#     def run(self):
#         while True:
#             rc = self.ft_obj.list_devices()
#             if rc:
#                 try:
#                     rc = self.ft_obj.open()
#                     if not rc:
#                         time.sleep(1)
#                         LOG.debug("open ftcamera usb failed! restart")
#                         continue
#                     rc = self.ft_obj.set_baud_rate()
#                     if not rc:
#                         if self.ft_obj:
#                             self.ft_obj.close()
#                         LOG.debug("ftcamera usb set_baud_rate failed! restart")
#                         time.sleep(1)
#                         continue
#                     rc = self.ft_obj.set_data_characteristics()
#                     if not rc:
#                         if self.ft_obj:
#                             self.ft_obj.close()
#                         LOG.debug("ftcamera usb set_data_characteristics failed! restart")
#                         time.sleep(1)
#                         continue
#                     rc = self.ft_obj.set_timeout()
#                     if not rc:
#                         if self.ft_obj:
#                             self.ft_obj.close()
#                         LOG.debug("ftcamera usb set_timeout failed! restart")
#                         time.sleep(1)
#                         continue
#                     self.ft_obj.send_usart_stop_data()
#                     rc = self.ft_obj.send_usart_data()
#                     time.sleep(3)
#                     if not rc:
#                         if self.ft_obj:
#                             self.ft_obj.close()
#                         LOG.debug("ftcamera usb set_timeout failed! restart")
#                         time.sleep(1)
#                         continue
#                 except Exception as e:
#                     LOG.error("start FTCamera error %s" % str(e))
#                     if self.ft_obj:
#                         self.ft_obj.close()
#                     time.sleep(1)
#                     continue
#             else:
#                 time.sleep(1)
#                 continue
#             while True:
#                 if self.is_thread_exit is True:
#                     break
#                 if self.is_thread_pause is True:
#                     time.sleep(1)
#                     continue
#                 try:
#                     rx_bytes_len = self.ft_obj.get_queue_status()
#                     if rx_bytes_len:
#                         rc = self.ft_obj.read(rx_bytes_len)
#                         if not rc:
#                             break
#                     else:
#                         break
#                 except Exception as e:
#                     LOG.error("get temperature error %s" % str(e))
#                     break
#                 if self.ft_obj.current_temperature != self.last_temperature:
#                     self.last_temperature = self.ft_obj.current_temperature
#                     temperature = [
#                         [self.ft_obj.current_temperature, datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f"), None]]
#                     # must be  verified, it is not corrector.
#                     config.TEMPERATURE_DATA_MUTEX.acquire()
#                     config.TEMPERATURE_DATA = temperature
#                     config.TEMPERATURE_DATA_MUTEX.release()
#                 time.sleep(0.1)
#
#             if self.ft_obj:
#                 self.ft_obj.close()
#
#             # run workflow terminal.
#             if self.is_thread_exit:
#                 break
#
#
# class FakeTemp(EDAThread):
#     """只监视温度传感器是否连接"""
#
#     DEV_STATS = False  # 是否连接
#
#     def __init__(self):
#         super(FakeTemp, self).__init__("TemperatureDevDetector")
#         self.ft_obj = None
#         self.temp_socket = None
#         self.temp_seed = 37.0  # 随机温度基准
#         self.temp_total_cnt = 30  # 随机一个在温度基础上变化值的总次数
#         self.temp_cnt = 0  # 变化计数
#         self.last_temp = 37.0  # 记录上一次的温度值
#         self.is_show_temperature_data = CFG.get("is_show_temperature_data", True)
#         self.is_check_integrated_device = CFG.get("is_check_integrated_device", False)
#
#     def run(self):
#         if self.init_zmq() is False:
#             LOG.error("初始化ZMQ失败，温度传感器线程退出")
#             return
#         try:
#             self.ft_obj = FTCamera(log_output=LOG.error)
#         except Exception as e:
#             LOG.error("初始化温度传感器驱动失败，线程退出: {}".format(e))
#             return
#
#         while True:
#             # 线程控制
#             if self.is_exit is True:
#                 return
#             if self.is_running is False:
#                 time.sleep(0.04)
#                 continue
#
#             # 业务
#             if self.is_show_temperature_data:
#                 if self.is_check_integrated_device:
#                     rc = self.ft_obj.list_devices()
#                 else:
#                     rc = True
#
#                 if rc:
#                     # 设备连接
#                     FakeTemp.DEV_STATS = True
#                     data = EDATemp(self.gen_fake_temperature(), time.time())
#                     self.temp_socket.send_pyobj(data)
#                 else:
#                     # 设备断开
#                     FakeTemp.DEV_STATS = False
#             time.sleep(0.5)
#
#     def exit(self):
#         self.is_exit = True
#
#     def init_zmq(self):
#         ret = False
#         context = zmq.Context()
#         try:
#             self.temp_socket = context.socket(zmq.PUB)
#             self.temp_socket.bind("tcp://*:%s" % CFG.get('temp_port', 60003))
#             LOG.debug("初始化温度数据套接字成功")
#         except Exception as e:
#             LOG.error(e)
#             return ret
#         ret = True
#         return ret
#
#     def gen_fake_temperature(self):
#         """
#         生成体温假数据(平滑)
#         :return: float:体温值
#         """
#         if self.temp_cnt < self.temp_total_cnt:
#             self.temp_cnt += 1
#             fake = self.temp_seed + random.choice(range(-10, 10)) / 100
#             self.last_temp = fake
#             return float('%.2f' % fake)
#         else:
#             self.temp_seed = random.choice(range(368, 375)) / 10
#             self.temp_total_cnt = random.choice(range(700, 1000))
#             self.temp_cnt = 0
#             return float('%.2f' % self.last_temp)
#
#
# def run_thread():
#     tem_thread = TemperatureThread()
#     tem_thread.start()
#     while True:
#         print("temperature:", config.TEMPERATURE_DATA)
#         time.sleep(0.1)
#
#
# if __name__ == "__main__":
#     t = FakeTemp()
#     t.start()
#     # run_thread()
