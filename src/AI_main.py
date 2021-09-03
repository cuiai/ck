#!/usr/bin/env python
# -*- encoding: utf-8 F-*-


import os
import psutil
import subprocess, time
from threading import Thread
from bs4 import BeautifulSoup

from application.controller import config
from application.controller.camera import Camera
from application.controller.common import command, cs_command
from application.controller.watch_dog import WatchDog
from application.controller.mic import AudioCollectVlc
from application.controller.status_server import StatServer
from application.controller.config import LOG, CFG, VIEW_CFG
from application.controller.tools.timed_task import startTask
from application.controller.algorithm.openface import Openface
from application.model.data_writing import MongoDBWriterForEda
from application.controller.tools.uploadFile import Upload_File
from application.controller.common import init_resources, get_path
from application.controller.web_server.http_server import HttpServer
from application.model.model_data import init_data_database, update_field
from application.controller.algorithm.voice_intensity import IntensityThread
from application.controller.web_server.websocket_server import WebSocketServer
from application.controller.main_subscriber import SubscriberOpenFaceResult, SubscriberAudioIntensityResult
from application.controller.tools.video_up_rtsp import PutFrameRtsp

def begin():
    if not check_unique():
        LOG.debug("检查服务唯一性失败，警告！")
    if not check_port():
        LOG.debug("检查服务端口失败，警告！")
    if not start_media():
        LOG.debug("检查resp多媒体服务启动失败，警告！")

    if not start_openface_alg():
        LOG.error("启动Openface算法失败，程序退出")
        return
    if not start_camera():
        LOG.error("启动视频解码失败，程序退出")
        return
    if not start_upload_stream():
        LOG.error("启动推流失败，程序退出")
        return

    if not start_audio_collector():
        LOG.error("启动音频解码失败，程序退出")
        return
    if not start_audio_intensity():
        LOG.error("启动声强算法失败，程序退出")
        return
    if not dispose_data():
        LOG.error("启动算法数据线程失败，程序退出")
        return
    if not mongoDbServer():
        LOG.error("启动mongo数据处理服务线程失败，程序退出")
        return
    if not sendFile():
        LOG.error("启动bm服务交互线程失败，程序退出")
        return
    if not start_http_server():
        LOG.error("启动HTTP服务线程失败，程序退出")
        return
    if not start_ws_server():
        LOG.error("启动websocket服务线程失败，程序退出")
        return
    init_data_database()
    init_resources()
    # 看门狗，最后执行
    dog = WatchDog()
    dog.start()
    config.WATCH_DOG = dog
    # 启动磁盘使用率监测/小时 统计
    t = Thread(target=startTask, args=(60,))
    t.start()
    time.sleep(1)
    path = get_path()
    f = open('%s/%s'%(path, config.PDF_TEMPLATE), 'rb')
    LOG.debug("{}: ok".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
    config.BS4_object = BeautifulSoup(f, "lxml")
    start_success_file = CFG.get("main_start_success_file_name", "main_start_success_tmp")
    try:
        with open(start_success_file, 'w'):
            pass
    except Exception as e:
        LOG.error("open {} error: {}".format(start_success_file, e))

def start_media():
    path = get_path()
    if path:
        if "//main//" in path:
            cs_path = path.split("main")[0] + "MediaServer/MediaServer.exe"

            LOG.debug("media_server 路径：{}".format(cs_path))
            try:
                result = cs_command(cs_path, is_shell=True)
                if result:
                    LOG.info("启动多媒体服务成功")
                    return True
                else:
                    LOG.info("启动多媒体服务失败")
                    return False
            except Exception as e:
                LOG.error("error: %s" % str(e))
                return
    else:
        LOG.info("启动多媒体服务失败")
        return False
    LOG.info("启动多媒体服务成功")
    return True

def check_unique():
    ret = False
    name = "AI_main"
    list_ = []
    try:
        # 检测服务当前启动的数量，只保留最旧的服务，节省内存使用率
        for proc in psutil.process_iter():
            if name.lower() in proc.name().lower(): list_.append(proc)
        if len(list_) > 1:
            LOG.debug("{}: ok".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
            try:
                p = psutil.Process(config.MAIN_PID)
                p.terminate()
            except Exception as e:
                LOG.error(e)
                time.sleep(1)
        else:
            ret = True
            return ret
    except Exception as e:
        print(e)
        LOG.error("服务信息检测失败.................")
    return ret

def check_port():
    ret = False
    try:
        # 检测端口是否被占用，保证不影响程序服务正常运行
        ports = [CFG.get("http_port", None), CFG.get("ws_port", None)]
        for port in ports:
            with os.popen('netstat -ano|findstr {}'.format(port)) as res:
                res = res.read().split('\n')
            result = []
            for line in res:
                temp = [i for i in line.split(' ') if i != '']
                if len(temp) > 4:
                    result.append(int(temp[4]))
                    with os.popen('taskkill -f -pid %s' % result[0]) as res:
                        res = res.read()
                        LOG.debug("监察端口：{}".format(res))
    except Exception as e:
        LOG.error(e)
        return ret
    ret = True
    return ret


def start_status_server():
    """ 开启客户端状态检测线程 """
    ret = False
    try:
        server = StatServer()
        config.NAME_THREADS['status'] = server
        server.start()
    except Exception as e:
        LOG.error(e)
        return ret
    ret = True
    return ret

def start_upload_stream():
    """ 开启上传frame线程 """
    ret = False
    try:
        put_frame = PutFrameRtsp()
        config.NAME_THREADS['put_frame'] = put_frame
        put_frame.start()
    except Exception as e:
        LOG.error(e)
        return ret
    ret = True
    return ret

def start_camera():
    """开启视频解码线程"""
    url = CFG.get('dst_stream', 'rtsp://admin:1234qwer@192.168.16.51:554')
    # 判断是否为rtsp，如果不是读取硬件视频数据
    # if not str(url).startswith("rtsp"):
    #     status = usb_video()
    #     return status
    ret = False
    try:
        cam = Camera()
        config.NAME_THREADS['camera'] = cam
        cam.open()
        cam.start()
    except Exception as e:
        LOG.error(e)
        return ret
    ret = True
    return ret


def start_openface_alg():
    ret = False
    try:
        openface = Openface()
        config.NAME_THREADS['openface'] = openface
        openface.start()
    except Exception as e:
        LOG.error(e)
        return ret
    ret = True
    return ret


def start_audio_collector():
    """开启音频解码线程"""
    ret = False
    try:
        audio = AudioCollectVlc()
        config.NAME_THREADS['audio_collect_VLC'] = audio
        audio.start_collect()
    except Exception as e:
        LOG.error(e)
        return ret
    ret = True
    return ret


def start_audio_intensity():
    ret = False
    try:
        intensity = IntensityThread()
        config.NAME_THREADS['intensity'] = intensity
        intensity.start()
    except Exception as e:
        LOG.error(e)
        return ret
    ret = True
    return ret


def dispose_data():
    ret = False
    try:
        opence_data = SubscriberOpenFaceResult()
        config.NAME_THREADS['opence_data'] = opence_data
        voice_data = SubscriberAudioIntensityResult()
        config.NAME_THREADS['voice_data'] = voice_data
        # alg_data_status = SaveDataHandlerThread()
        # config.NAME_THREADS['alg_data_status'] = alg_data_status
        opence_data.start()
        voice_data.start()
        # alg_data_status.start()

    except Exception as e:
        LOG.error(e)
        return ret
    ret = True
    return ret


def start_http_server():
    ret = False
    try:
        httpServer = HttpServer()
        config.NAME_THREADS['httpServer'] = httpServer
        httpServer.start()
    except Exception as e:
        LOG.error(e)
        return ret
    ret = True
    return ret


def start_ws_server():
    ret = False
    try:
        webSocket = WebSocketServer()
        config.NAME_THREADS['webSocket'] = webSocket
    except Exception as e:
        LOG.error(e)
        return ret
    ret = True
    return ret


def mongoDbServer():
    ret = False
    try:
        mongo_ = MongoDBWriterForEda()
        config.NAME_THREADS['mongo_'] = mongo_
        mongo_.start()
    except Exception as e:
        LOG.error(e)
        return ret
    ret = True
    return ret


def sendFile():
    ret = False
    try:
        if VIEW_CFG.get("interaction", 0) == 1:
            upload_ = Upload_File()
            config.NAME_THREADS['upload_'] = upload_
            upload_.start()
    except Exception as e:
        LOG.error(e)
        return ret
    ret = True
    return ret


def usb_video():
    # 进行推流
    status = stream_server()
    if status is False:
        return False
    ret = False
    try:
        video_config = CFG.get('video_config', 'rtsp://admin:1234qwer@192.168.16.51:554')
        audio_config = CFG.get('audio_config', 'rtsp://admin:1234qwer@192.168.16.51:554')
        command = ["ffmpeg",
                   '-f', 'dshow',
                   '-i', 'video="{}"'.format(video_config),
                   '-f', 'dshow',
                   '-i', 'audio="{}"'.format(audio_config),
                   '-vcodec', 'h264',
                   '-preset', 'ultrafast',
                   '-tune', 'zerolatency',
                   '-r', '15',
                   '-s', '1280x720',
                   '-fflags', 'nobuffer',
                   '-rtsp_transport', 'udp',
                   '-f', 'rtsp',
                   'rtsp://127.0.0.1:554/live/999']
        command = ' '.join(command)
        p_record = subprocess.Popen(command,
                                    stdin=subprocess.PIPE,
                                    shell=True)
        config.USB_VIDEO = p_record
        LOG.debug("推流成功............")
        print("推流成功............")
    except Exception as e:
        LOG.error(e)
        return ret
    ret = True
    return ret


def stream_server():
    STREAM_SERVER_NAME = "MediaServer.exe"
    ret = False
    try:
        p = subprocess.Popen(STREAM_SERVER_NAME, stdin=subprocess.PIPE, shell=True)
        config.STREAM_SERVER = p
        LOG.debug("流媒体服务启动成功............")
        print("流媒体服务启动成功............")
    except Exception as e:
        LOG.error("流媒体服务器启动失败.............")
        return ret
    ret = True
    return ret


if __name__ == '__main__':
    config.MAIN_PID = os.getpid()
    begin()
