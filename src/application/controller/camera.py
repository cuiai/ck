#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    解析视频帧，发送给算法
"""

import cv2
import time
from threading import Thread
from imutils.video import VideoStream
from application.controller import config
from application.controller.config import CFG, LOG

FR = CFG.get('frame_rate', 25)
CAMERA_FREQUENCY = 1 / FR / 2


class EDAFrame:
    """
        带时间戳的视频帧类
    """
    frame = None  # 帧
    ts = None  # 时间戳

    def __init__(self, frame, ts):
        self.frame = frame
        self.ts = ts


class Camera(Thread):
    """解码线程"""

    def __init__(self):
        super(Camera, self).__init__()
        self.setDaemon(True)
        self.setName("Camera")
        self.cam_url = config.DST_STREAM
        self.is_close = True  # Whether the camera is closed or not
        self.is_connect = False  # The initialization of the flag or whether the link is successful at present
        self.camera = None
        self.rc = None
        self.socket = None
        self.max_empty_frames = CFG.get('max_empty_frames', 5)
        self.empty_frames_cnt = 0  # 连续读空帧计数

    def run(self):
        LOG.info("视频解码线程已启动")
        while True:

            try:
                if self.is_close:
                    break
                if self.is_connect:
                    ret = self.setup_resource()
                    if ret is False:
                        time.sleep(1)
                        continue
                while True:
                    if self.is_close:
                        break
                    if self.is_connect is False:
                        LOG.info('暂停解码线程')
                        break
                    # if not config.inquest_status:
                    #     time.sleep(CAMERA_FREQUENCY)
                    #     continue
                    raw_image = self.camera.read()
                    # 缩放一半
                    try:
                        raw_image = cv2.resize(raw_image, (0, 0), fx=0.5, fy=0.5,
                                               interpolation=cv2.INTER_NEAREST)
                    except Exception as e:
                        LOG.warning('视频解析图片出错 {}'.format(e))
                    # 空帧计数
                    if raw_image is None:
                        config.inquest_uuid = None
                        config.DASH_BOARD_BEGIN_TIME = None
                        config.DASH_BOARD_WINDOW_1.clear()
                        config.DASH_BOARD_WINDOW_2.clear()
                        config.DASH_BOARD_WINDOW_3.clear()
                        config.DASH_BOARD_WINDOW_4.clear()
                        config.DASH_BOARD_WINDOW_5.clear()
                        config.DASH_BOARD_WINDOW_6.clear()
                        self.empty_frames_cnt += 1
                    else:
                        if not config.STREAM_SHAPE:
                            config.STREAM_SHAPE = raw_image.shape
                        self.empty_frames_cnt = 0
                    # 达到最大空帧后重启解码
                    if self.empty_frames_cnt >= self.max_empty_frames:
                        LOG.warning('达到最大空帧数！解码服务将重启...')
                        config.DST_STREAM = CFG.get('dst_stream', 'rtsp://admin:1234qwer@192.168.16.51:554')
                        config.WATCH_DOG.restart_all()
                        break
                    config.ORIGIN_FRAME = [EDAFrame(raw_image, time.time())]

                    time.sleep(CAMERA_FREQUENCY)
                self.clean_resource()
                LOG.info("1秒后重启解码线程")
                time.sleep(1)
            except Exception as e:
                config.LOG.error("视频解码线程异常")
                LOG.error(e)

    def setup_resource(self):
        ret = False
        try:
            self.camera = VideoStream(src=config.DST_STREAM)
            config.FRAME_WIDTH = int(self.camera.stream.stream.get(cv2.CAP_PROP_FRAME_WIDTH)/2)
            config.FRAME_HEIGHT = int(self.camera.stream.stream.get(cv2.CAP_PROP_FRAME_HEIGHT)/2)
            self.rc = self.camera.stream.stream.isOpened()
            if not self.rc:
                config.videoStream_obj = False
                LOG.error("流地址“%s”连接失败" % config.DST_STREAM)
            else:
                config.videoStream_obj = True
                LOG.info("流地址“%s”连接成功" % config.DST_STREAM)
                ret = True
                self.camera.start()

        except Exception as e:
            LOG.error("Failed to start camera stream %s" % str(e))
            return ret
        return ret

    def open(self):
        """Open the camera
        retval: True, False
        """
        LOG.info('开启视频解码')
        ret = False
        if self.is_connect is False:
            self.is_close = False
            self.is_connect = True
            ret = True
            return ret
        return ret

    def close(self):
        """Close the camera """

        ret = False
        if not self.is_close:
            self.is_close = True
        ret = True
        return ret

    def clean_resource(self):
        if self.camera is not None:
            try:
                self.camera.stop()
            except Exception as e:
                LOG.error(e)

    def thread_exit(self):
        self.close()

    def stop(self):
        self.is_connect = False
        LOG.info('停止视频解码')
