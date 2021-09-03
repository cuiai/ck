import time
import sched
import psutil
import threading
import subprocess
from os import getcwd
from pathlib import PureWindowsPath
from application.controller import config
# import sys
# sys.setrecursionlimit(1000000)


# schedule = sched.scheduler(time.time, time.sleep)


# 默认参数单位s
def startTask(inc):
    while True:
        try:
            crt_path = getcwd()
            crt_driver = PureWindowsPath(crt_path).drive
            ret = psutil.disk_usage(crt_driver).percent
            free = psutil.disk_usage(crt_driver).free
            res = subprocess.Popen("netstat -ano|findstr 27017 |findstr LISTEN", shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
            res.communicate(input=b"q\r")
            config.MONGOD_ = res.returncode
            config.DISK_RATE = ret
            if free:
                config.DISK_FREE = int(free / 1073741824)
            # data = threading.active_count()
            time.sleep(inc)

            """
                enter四个参数分别为：间隔事件、优先级（用于同时间到达的两个事件同时执行时定序）、被调用触发的函数，
                给该触发函数的参数（tuple形式）
            """
            # schedule.enter(inc, 0, startTask, (inc,))
            # schedule.run()
        except Exception as e:
            config.LOG.error("检测磁盘使用率任务执行失败.....................{}".format(e))
            time.sleep(5)
