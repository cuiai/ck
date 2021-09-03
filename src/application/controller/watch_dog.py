#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import os
import threading
import time
import psutil
from application.controller import config
from application.controller.config import LOG
from application.controller.common import EDAThread
from application.controller.algorithm.voice_intensity import IntensityThread

WATCHING_INTERVAL = 2  # 巡查间隔


class WatchDog(EDAThread):
    def __init__(self):
        super(WatchDog, self).__init__("WatchDog")
        self.setDaemon(True)
        self.audio_vlc = None
        self.camera = None
        self.setName("WatchDog")

    def run(self):
        LOG.info("看门狗线程已启动")
        if self.check() is False:
            LOG.error("看门狗线程退出")
            return
        threading.Thread(target=self.check_client).start()
        while True:
            # 10s内找不到AI_VIEW则退出
            try:
                if config.IS_EXIT is True:
                    self.exit()
                    time.sleep(2)
                    LOG.debug("看门狗退出")
                    break
                self.intensity = config.NAME_THREADS.get('intensity')
                self.audio_vlc = config.NAME_THREADS.get('audio_collect_VLC')
                self.camera = config.NAME_THREADS.get('camera')

                if self.intensity.is_alive() is False:
                    self.create_new_audio_thread()
                time.sleep(WATCHING_INTERVAL)
            except Exception as e:
                config.LOG.error("看门狗线程线程异常")
                LOG.error(e)

    def check(self):
        """ 检查能够正确获得线程对象 """
        ret = False
        url = config.CFG.get('dst_stream', 'rtsp://admin:1234qwer@192.168.16.51:554')
        if url == 0:
            check_names = ('intensity', 'audio_collect_VLC',)
        else:
            check_names = ('intensity', 'audio_collect_VLC', 'camera',)
        for n in check_names:
            t = config.NAME_THREADS.get(n)
            if t is None:
                LOG.error('无法获得"%s"线程对象' % n)
                return ret
        ret = True
        return ret

    def check_client(self):
        name = "cs.exe"
        while self.check_if_process_running(name) is False:
            LOG.info("正在等待客户端启动...")
            time.sleep(1)
        LOG.info('检测到客户端进程')
        while True:
            try:
                time.sleep(10)
                if self.check_if_process_running(name) is False:
                    LOG.info('检测到客户端退出')
                    ffmpeg_list = []
                    try:
                        # 检测服务当前启动的数量，只保留最新启动的服务，节省内存使用率
                        for proc in psutil.process_iter():
                            if "ffmpeg.exe".lower() in proc.name().lower(): ffmpeg_list.append(proc)
                        if len(ffmpeg_list) > 0:
                            for i in ffmpeg_list: os.popen('taskkill -f -pid %s' % i.pid);LOG.debug("ffmpeg已关闭.......")
                    except Exception as e:
                        LOG.error('ffmpeg关闭失败-->{}'.format(e))
                    time.sleep(300)
                    if self.check_if_process_running(name) is False:
                        LOG.debug("检测到客户端退出超过五分钟，终止服务端进程")
                        try:
                            try:
                                if config.USB_VIDEO:
                                    t1 = config.USB_VIDEO
                                    t1.kill()
                            except Exception as e:
                                LOG.error('推流服务关闭失败-->{}'.format(e))
                            try:
                                if config.STREAM_SERVER:
                                    t2 = config.STREAM_SERVER
                                    t2.kill()
                            except Exception as e:
                                LOG.error('流媒体服务关闭失败-->{}'.format(e))
                            ffmpeg_list = []
                            try:
                                # 检测服务当前启动的数量，只保留最新启动的服务，节省内存使用率
                                for proc in psutil.process_iter():
                                    if "ffmpeg.exe".lower() in proc.name().lower(): ffmpeg_list.append(proc)
                                if len(ffmpeg_list) > 0:
                                    for i in ffmpeg_list: os.popen('taskkill -f -pid %s' % i.pid);LOG.debug("ffmpeg已关闭.......")
                            except Exception as e:
                                LOG.error('ffmpeg关闭失败-->{}'.format(e))
                            media_list = []
                            try:
                                # 检测服务当前启动的数量，只保留最新启动的服务，节省内存使用率
                                for proc in psutil.process_iter():
                                    if "MediaServer.exe".lower() in proc.name().lower(): media_list.append(proc)
                                if len(media_list) > 0:
                                    for i in media_list: os.popen('taskkill -f -pid %s' % i.pid);LOG.debug("MediaServer已关闭.......")
                            except Exception as e:
                                LOG.error('MediaServer关闭失败-->{}'.format(e))
                            ffmpeg_put_list = []
                            try:
                                # 检测服务当前启动的数量，只保留最新启动的服务，节省内存使用率
                                for proc in psutil.process_iter():
                                    if "ffmpeg_put.exe".lower() in proc.name().lower(): ffmpeg_put_list.append(proc)
                                if len(ffmpeg_put_list) > 0:
                                    for i in ffmpeg_put_list: os.popen('taskkill -f -pid %s' % i.pid);LOG.debug(
                                        "ffmpeg_put已关闭.......")
                            except Exception as e:
                                LOG.error('ffmpeg_put关闭失败-->{}'.format(e))
                            p = psutil.Process(config.MAIN_PID)
                            p.terminate()
                        except Exception as e:
                            LOG.error(e)
                            time.sleep(1)
            except Exception as e:
                config.LOG.error("检测客户端线程异常")
                LOG.error(e)


    def create_new_audio_thread(self):
        LOG.warning("正在执行音频流重连业务...")
        self.audio_vlc.restart()
        time.sleep(2)
        new_intensity_thread = IntensityThread()
        new_intensity_thread.start()
        config.NAME_THREADS['intensity'] = new_intensity_thread
        time.sleep(2)

    def check_if_process_running(self, process_name):
        for proc in psutil.process_iter():

            try:
                if process_name.lower() in proc.name().lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def exit(self):
        # 暂停音频解码
        audio = config.NAME_THREADS['audio_collect_VLC']
        audio.stop()
        # 关闭camera线程
        if config.NAME_THREADS.get("camera"):
            cam = config.NAME_THREADS['camera']
            cam.thread_exit()
        # 关闭openface线程
        openface = config.NAME_THREADS['openface']
        openface.exit()
        # 关闭声强线程
        intensity = config.NAME_THREADS['intensity']
        intensity.exit()
        # 关闭接收算法数据线程
        opence_data = config.NAME_THREADS['opence_data']
        opence_data.is_exit()
        # 关闭接收声强数据线程
        voice_data = config.NAME_THREADS['voice_data']
        voice_data.is_exit()
        # 关闭处理数据线程
        # alg_data_status = config.NAME_THREADS['alg_data_status']
        # alg_data_status.is_exit()
        # 关闭mongodb处理数据线程
        mongo_ = config.NAME_THREADS['mongo_']
        mongo_.exit()
        # 关闭bm交互线程
        if config.NAME_THREADS.get("upload_"):
            upload_ = config.NAME_THREADS['upload_']
            upload_.exit()


    def restart_audio(self):
        self.audio_vlc.restart()

    def restart_video(self):
        self.camera.stop()
        time.sleep(0.5)
        self.camera.open()

    def restart_all(self):
        self.restart_video()
        self.restart_audio()