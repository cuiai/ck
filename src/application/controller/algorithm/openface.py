#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""
    获取算法数据
"""

import copy
import time
from threading import Thread
from application.controller.algorithm.RectifyFaceBoundingBox  import RectifyFaceBoundingBox
from application.controller import config
from application.controller.camera import CAMERA_FREQUENCY
from application.controller.config import LOG, CFG
from application.controller.algorithm.OpenFace.main_au_expressions import ProcessSequenceImages
from application.controller.algorithm.OpenFace.core.heart_rate import HeartRateDetection
from application.controller.algorithm.OpenFace.core.pulse import Pulse
# from application.controller.algorithm.OpenFace.core.HeartRateDetection import HeartRateDetection


class Emotions:
    """
        表情结果类
    """
    crt_text = None  # 当前表情文本
    anger = None  # 0: 生气
    contempt = None  # 1: 轻蔑
    disgust = None  # 2: 厌恶
    fear = None  # 3: 害怕
    joy = None  # 4: 开心
    neutral = None  # 5: 平和
    sadness = None  # 6: 伤心
    surprise = None  # 7: 惊讶

    def __init__(self, anger, contempt, disgust, fear, joy, neutral, sadness, surprise, crt_text=None):
        self.anger = anger
        self.contempt = contempt
        self.disgust = disgust
        self.fear = fear
        self.joy = joy
        self.neutral = neutral
        self.sadness = sadness
        self.surprise = surprise
        self.crt_text = crt_text


class AlgResult:
    """
        Openface算法结果类

    """
    is_detectable = True  # 当前头部姿态是否利于检测
    ori_frame = None  # 原始帧
    ts = None  # 时间戳
    pose_estimate = None  # 姿态估计值
    line_left = None
    line_right = None
    gaze_angle = None  # Gaze角度值
    aus_reg = None  # 回归出的AU值
    aus_class = None  # AU分类值
    points = None  # 画landmark点
    eye_landmarks_2d = None
    face_bbox = None  # 检测出的脸部的Bounding Box
    heart_rate = 0  # 心率值
    is_looking_at_me = None  # 是否正视
    emotions: Emotions = None  # 表情结果对象
    pose_lines = None
    #  fx, fy, cx, cy,画头部姿态估计需要的参数
    fx = None
    fy = None
    cx = None
    cy = None
    mind = None  # 心理状态

    def __init__(
            self,
            pose_estimate,
            line_left,
            line_right,
            gaze_angle,
            aus_reg,
            aus_class,
            points,
            eyes_landmarks_2d,
            face_bbox,
            fx, fy, cx, cy,
            pose_lines=None,
            heart_rate=0,
            is_looking_at_me=None,
            emotions=None,
            is_undetectable=True,
            mind=None,
    ):
        self.pose_estimate = pose_estimate
        self.line_left = line_left
        self.line_right = line_right
        self.gaze_angle = gaze_angle
        self.aus_reg = aus_reg
        self.aus_class = aus_class
        self.points = points
        self.eye_landmarks_2d = eyes_landmarks_2d
        self.face_bbox = face_bbox
        self.heart_rate = heart_rate
        self.is_looking_at_me = is_looking_at_me
        self.emotions = emotions
        self.fx, self.fy, self.cx, self.cy = fx, fy, cx, cy
        self.pose_lines = pose_lines
        self.is_detectable = is_undetectable
        self.mind = mind


class Openface(Thread):
    CURRENT_FRAME_RATE = None

    def __init__(self):
        super(Openface, self).__init__()
        self.setName("Openface")
        self.setDaemon(True)
        self.is_exit = False
        self.recv_frame_socket = None
        self.openface_alg = None
        self.heart_rate_alg = None
        self.pulse = None
        self.frame = None  # 当前原始帧
        self.alg_result = None
        self.points_delaunay = None
        self.average_calculator = None

    def run(self):
        """
            request: EDAFrame
        """
        LOG.info("Openface算法处理线程已启动")
        if self.init_alg() is False:
            LOG.error("初始化算法失败，Openface算法线程退出")

        while True:
            if self.is_exit is True:
                break
            # if not config.inquest_status:
            #     time.sleep(CAMERA_FREQUENCY)
            #     # print(time.time())
            #     continue
            try:
                start = time.time()
                request = config.ORIGIN_FRAME[0]
                # 判断是否
                if request is None:
                    time.sleep(CAMERA_FREQUENCY / 2)
                    continue
                self.frame = request.frame
                # 执行Openface算法
                try:
                    openface_result = self.openface_alg.process_sequence_images(request.frame)
                except:
                    time.sleep(CAMERA_FREQUENCY)
                    continue
                if openface_result is None:
                    config.ALG_STATUS = False
                    time.sleep(CAMERA_FREQUENCY)
                    continue
                config.ALG_STATUS = True
                self.alg_result = AlgResult(*openface_result)
                self.alg_result.ori_frame = self.frame
                self.alg_result.is_detectable = self.openface_alg.judge_detectable(self.alg_result)  # 判断当前姿态是利于检测
                self.alg_result.pose_estimate = [float(p) for p in self.alg_result.pose_estimate]
                self.alg_result.gaze_angle = [float(g) for g in self.alg_result.gaze_angle]
                self.alg_result.pose_lines = self.openface_alg.calculate_box(self.alg_result.pose_estimate, (
                    self.alg_result.points[33], self.alg_result.points[33 + 68]))
                # 执行心率算法
                if self.alg_result.is_detectable:
                    heart_rate_img = copy.deepcopy(request.frame)
                    # face_image = self.heart_rate_alg.generate_face_image(heart_rate_img, openface_result[8])
                    face_bbox = self.alg_result.face_bbox
                    # face_img = None
                    if len(face_bbox) != 0:
                        face_bbox = [face_bbox[0], face_bbox[1],
                                     face_bbox[0] + face_bbox[2],
                                     face_bbox[1] + face_bbox[
                                         3]]  # [left, top, right, bottom]
                        RectifyFaceBoundingBox(face_bbox, self.alg_result.ori_frame)
                        face_img = heart_rate_img[face_bbox[1]:face_bbox[3],
                                   face_bbox[0]:face_bbox[2], :]
                        heart_rate_value = self.pulse.heart_rate_detection(face_img)
                        self.alg_result.heart_rate = heart_rate_value
                # 执行au转表情算法
                output_cls, output_reg, cls_text = self.openface_alg.au2emotions(self.alg_result.aus_reg)
                emotions = Emotions(*output_reg.tolist()[0])
                emotions.crt_text = cls_text
                self.alg_result.emotions = emotions
                # 执行判断是否在正视
                self.alg_result.is_looking_at_me = self.openface_alg.is_looking_at_me(self.alg_result)
                # 判断心理状态
                mind = self.openface_alg.state_of_mind(self.alg_result.aus_class, output_reg, cls_text)
                self.alg_result.mind = mind
                # 格式化数据
                self.alg_result.aus_reg = [x[1] for x in list(self.alg_result.aus_reg)]
                self.alg_result.aus_class = [x[1] for x in list(self.alg_result.aus_class)]
                self.alg_result.ts = time.time()
                # 发送算法结果对象
                config.EMOTION_DATA_OBJECT = self.alg_result
                # # 通过ws发送给QT客户端
                # config.FACE_DATA_DEQUE.append(self.alg_result)
                time.sleep(0.01)
                end = time.time()
                fr = 1 / (end - start)
                Openface.CURRENT_FRAME_RATE = fr
            except Exception as e:
                config.LOG.error("Openface算法处理线程异常")
                LOG.error(e)
            # if fr < 10:
            #     print("当前算法运行帧率过低： %.2ffps" % fr)

    def exit(self):
        self.is_exit = True

    def init_alg(self):
        """
            初始化算法
        """
        ret = False
        # 加载Openface算法
        try:
            self.openface_alg = ProcessSequenceImages()
        except Exception as e:
            LOG.error(e)
            return ret
        # 加载心率算法
        try:
            self.pulse = Pulse()
        except Exception as e:
            LOG.error(e)
            return ret
        try:
            self.heart_rate_alg = HeartRateDetection()
        except Exception as e:
            LOG.error(e)
            return ret
        ret = True
        return ret
