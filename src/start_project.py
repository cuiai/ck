# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import logging
import subprocess
from threading import Thread
import psutil
import win32api
from PyQt5 import QtGui, QtWidgets

STARTUP_GIF_PATH = 'application/resources/icons/start_up.gif'
MAIN_TEMP_FILE_NAME = "main/main_start_success_tmp"
VIEW_TEMP_FILE_NAME = "view/view_start_success_tmp"
VIEW_START_FAIL_FILENAME = "view/view_start_fail_tmp"


LOG_PATH = 'Debug.log'
FORMAT = '%(asctime)-15s %(module)s.%(funcName)s[%(lineno)d] %(levelname)s %(message)s'
logging.basicConfig(format=FORMAT,
                    filename=LOG_PATH,
                    level=logging.INFO)
LOG = logging.getLogger("startup")


def resource_path(relative_path):
    """Convert relative resource path to the real path"""

    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(relative_path)


def command(cmd, is_shell=False):
    """Command function"""

    ret = None
    try:
        process = subprocess.Popen(cmd,
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   shell=is_shell)
        # out, err = process.communicate()
        out, err = "", ""
        rc = process.returncode
    except Exception as e:
        LOG.error("command %s" % str(e))
        return ret
    return rc, out, err


IS_EXIT = False


class WorkerThread(Thread):
    """Worker thread"""

    def __init__(self, app):
        self.app = app
        super(WorkerThread, self).__init__()
        self.is_exit = False
        self.exec_bin_path_1 = "AI_main.exe"
        self.exec_bin_path_2 = "cs.exe"

    def run(self):
        global IS_EXIT

        # 移除相关文件
        LOG.info(os.getcwd())
        if "start_project_dir" == os.path.basename(os.getcwd()):
            os.chdir("../")
        LOG.info(os.getcwd())


        # 检测服务端和客户端启动文件是否存在
        exe_path_par = os.getcwd()
        main_exe_path = os.path.join(exe_path_par,"main", self.exec_bin_path_1)
        LOG.info(main_exe_path)
        if not os.path.exists(main_exe_path):
            LOG.error("Not found exe file %s, to exit." % main_exe_path)
            win32api.MessageBox(0, "缺少{}文件！".format(main_exe_path), "错误", 0)
            IS_EXIT = True
            return

        view_exe_path = os.path.join(exe_path_par,"cs", self.exec_bin_path_2)
        LOG.info(view_exe_path)
        if not os.path.exists(view_exe_path):
            LOG.error("Not found exe file %s, to exit." % view_exe_path)
            win32api.MessageBox(0, "缺少{}文件！".format(view_exe_path), "错误", 0)
            IS_EXIT = True
            return
        # 启动AI_main.exe
        LOG.info("222 --- main %s" % os.getcwd())
        os.chdir(os.path.join(exe_path_par,"main"))
        LOG.info("222 --- view %s" % os.getcwd())
        # 启动AI_main.exe
        try:
            result = command(self.exec_bin_path_1)
            LOG.info(result)
            if result is None:
                return
            else:
                rc, out, err = result
                if rc is not None:
                    LOG.error(err)
                    return
        except Exception as e:
            LOG.error("error: %s" % str(e))
            IS_EXIT = True
            return
        LOG.info("启动AI_main.exe成功")

        # 等待5秒，启动AI_view.exe
        # time.sleep(5)
        # LOG.info("222 --- view %s" % os.getcwd())
        # os.chdir(os.path.join(exe_path_par, "cs"))
        # LOG.info("222 --- view %s" % os.getcwd())
        # try:
        #     result = command(self.exec_bin_path_2)
        #     LOG.info(result)
        #     if result is None:
        #         LOG.info("----1111111")
        #         os.chdir("../")
        #         kill_main_process()
        #         return
        #     else:
        #         rc, out, err = result
        #         if rc is not None:
        #             LOG.error(err)
        #             LOG.info("----222222")
        #             os.chdir("../")
        #             kill_main_process()
        #             return
        # except Exception as e:
        #     LOG.error("error: %s" % str(e))
        #     LOG.info("----333333")
        #     os.chdir("../")
        #     kill_main_process()
        #     IS_EXIT = True
        #     return
        # LOG.info("启动cs.exe成功")
        IS_EXIT = True





def kill_main_process():
    try:
        os.system("taskkill /F /IM AI_main.exe")
    except Exception as e:
        LOG.error("kill AI_main.exe error: {}".format(e))

    try:
        if os.path.exists(MAIN_TEMP_FILE_NAME):
            os.remove(MAIN_TEMP_FILE_NAME)
    except Exception as e:
        LOG.error("remove {} error: {}".format(MAIN_TEMP_FILE_NAME, e))


class MySplash(QtWidgets.QSplashScreen):
    def __init__(self, *args):
        super(MySplash, self).__init__(*args)

    def mousePressEvent(self, event):
        pass


def run_app():
    app = QtWidgets.QApplication(sys.argv)
    movie = QtGui.QMovie(resource_path(STARTUP_GIF_PATH))
    movie.setCacheMode(QtGui.QMovie.CacheAll)
    movie.setSpeed(40)
    splash = MySplash(QtGui.QPixmap(resource_path(STARTUP_GIF_PATH)))
    label = QtWidgets.QLabel(splash)
    label.setMovie(movie)
    movie.start()
    splash.show()
    wt = WorkerThread(app)
    wt.start()
    while IS_EXIT is False:
        QtWidgets.qApp.processEvents()
        time.sleep(0.1)
    time.sleep(10)
    app.quit()


if __name__ == "__main__":
    LOG.info(os.getcwd())
    run_app()
