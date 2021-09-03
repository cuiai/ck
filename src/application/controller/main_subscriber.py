#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""
接收后端数据
"""
import cv2
import time
from collections import deque
from application.controller import config
from application.controller.common import EDAThread

FR = config.CFG.get('frame_rate', 25)
CAMERA_FREQUENCY = 1 / FR
DEQUE_TEMP_RESULT = deque(maxlen=5)


# ================================================================================== #
# ------------------------------  协议数据结构  ------------------------------------- #
# ================================================================================== #

class TempResult:
    """温度数据"""
    temp = None
    ts = None


class Emotions:
    """表情结果"""
    crt_text = None  # 当前表情文本
    anger = None  # 0: 生气
    contempt = None  # 1: 轻蔑
    disgust = None  # 2: 厌恶
    fear = None  # 3: 害怕
    joy = None  # 4: 开心
    neutral = None  # 5: 平和
    sadness = None  # 6: 伤心
    surprise = None  # 7: 惊讶


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


class Subscriber(EDAThread):
    OPENFACE_RESULT: AlgResult = None
    VOICE_INTENSITY_RESULT = None
    TEMP_RESULT: TempResult = False

    def __init__(self):
        super(Subscriber, self).__init__("Subscriber")
        self.setDaemon(True)
        self.openface_socket = None
        self.voice_intensity_socket = None
        self.temp_socket = None


class SubscriberOpenFaceResult(EDAThread):

    OPENFACE_RESULT: AlgResult = None

    def __init__(self):
        super(SubscriberOpenFaceResult, self).__init__("SubscriberOpenFaceResult")
        self.setDaemon(True)

    def run(self):
        config.LOG.info("接收算法数据线程已启动")
        while True:
            # 线程控制
            try:
                if self.is_exit is True:
                    return
                if self.is_running is False:
                    time.sleep(CAMERA_FREQUENCY)
                    continue
                if not config.inquest_status:
                    time.sleep(CAMERA_FREQUENCY)
                    # print(time.time())
                    continue
                if config.EMOTION_DATA_OBJECT is None:
                    continue
                # 业务
                # 接收Openface算法结果
                start = time.time()
                try:
                    Subscriber.OPENFACE_RESULT = config.EMOTION_DATA_OBJECT
                    self.openface_handler(Subscriber.OPENFACE_RESULT)
                except Exception as e:
                    config.LOG.error("算法数据解析错误------》{}".format(e))
                end = time.time()
                cost = end - start
                if cost >= 0.03:
                    config.LOG.warning("SubscriberOpenFaceResult 接收并处理数据用时%.3f秒，可能会导致画面延时" % cost)
                    pass
                time.sleep(0.03)
            except Exception as e:
                config.LOG.error("接收算法数据线程线程异常")
                config.LOG.error(e)

    @staticmethod
    def openface_handler(result: AlgResult):
        # emotion_warn_intensity = {"contempt": 1, "disgusted": 1, "surprised": 1, "sad": 1, "fearful": 1, "angry": 1}
        # config.inquest_status = True
        if result:
            if config.inquest_status:
                # TODO 表情获取
                """表情获取"""
                anger = result.emotions.anger * 100 * config.emotion_warn_intensity['angry']  # 0: 生气
                contempt = result.emotions.contempt * 100 * config.emotion_warn_intensity['contempt']  # 1: 轻蔑
                disgust = result.emotions.disgust * 100 * config.emotion_warn_intensity['disgusted']  # 2: 厌恶
                fear = result.emotions.fear * 100 * config.emotion_warn_intensity['fearful']  # 3: 害怕
                joy = result.emotions.joy * 100  # 4: 开心
                neutral = result.emotions.neutral * 100  # 5: 平和
                sadness = result.emotions.sadness * 100 * config.emotion_warn_intensity['sad']  # 6: 伤心
                surprise = result.emotions.surprise * 100 * config.emotion_warn_intensity['surprised']  # 7: 惊讶"""

                # MongoDB数据入库全局变量
                config.MONGODB_EMOTION_DATA = [int(fear), int(anger), int(sadness), int(surprise),
                                               int(disgust), int(contempt), int(joy), int(neutral)]
                if config.MONGODB_EMOTION_DATA == [0, 12, 1, 6, 4, 31, 8, 34]:
                    config.MONGODB_EMOTION_DATA = [0] * 8
                # Rabbitmq 算法数据格式
                config.RabbitMQ_ALG_RESULT = [int(neutral), int(joy), int(sadness), int(anger), int(surprise),
                                              int(fear), int(disgust), int(contempt)]
                if config.RabbitMQ_ALG_RESULT == [34, 8, 1, 12, 6, 0, 4, 31]:
                    config.RabbitMQ_ALG_RESULT = [0] * 8

                """3d面罩"""
                config.WS_3D_MARK_DATA = {
                    "points": result.points,  # 3D Mask
                    "line_left": result.line_left,  # 左眼眼线
                    "line_right": result.line_right,  # 右眼眼线
                    "eye_landmarks_2d": result.eye_landmarks_2d,  # 3d眼部模型
                    "pose_lines": result.pose_lines,  # 头部姿态估计
                }

                # TODO 心率获取
                """
                心率调整规则：
                    1、保持心率横坐标不变，由原逢5取真实值调整为逢10取真实值，降低心率显示密度；
                    2、在正常值“10及10的倍数”前后的“9及9的倍数”和“11及11的倍数”新增虚假打点值“72”，--即逢9及9的倍数或11及11的倍数，打点72；
                    3、当逢10的真实值（65≤X＜70）时，自动将值变更为60，当逢10的真实值（70≤X≤75）时，自动将值变更为80
                """
                # config.CLIENT_CURRENT_HEART_RATE_DATA = int(result.heart_rate)
                config.CLIENT_CURRENT_HEART_RATE_DATA = result.heart_rate

                # TODO   AU 值获取
                """
                    result.aus_class = [1.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0]
                    ('AU1', 'AU2', 'AU4', 'AU5', 'AU6', 'AU7', 'AU9', 'AU10', 'AU12', 'AU14', 'AU15', 'AU17', 'AU20', 'AU23', 'AU25', 'AU26', 'AU45')            
                    result.aus_reg = [0.8935973298522963, 0.8184325321955255, 2.3547847875452583, 0.4452752325630312, 0.42976952390032924, 1.8375906842618774, 1.275739748816783, 1.3906391266518647, 2.6154092251462795, 0.7442616887246916, 0.0, 2.125250760620722, 2.0021380519843857, 2.387952180822345, 1.3598533784432751, 2.4536805699068465, 1.5925587038075342]
                """
                # AU 值获取
                config.API_AU_DATA_OCCURRENCE = result.aus_class
                config.API_AU_DATA_INTENSITIES = result.aus_reg
                # 获取智能帧
                config.QUEUE_FACE_IMAGE.append(result.ori_frame)

                # TODO 获取瞳孔视线角度文本
                if result.is_looking_at_me is True:
                    config.IS_LOOK_AT_ME_TEXT = "正视"
                elif result.is_looking_at_me is False:
                    config.IS_LOOK_AT_ME_TEXT = "转移眼神"
                else:
                    config.IS_LOOK_AT_ME_TEXT = "暂无数据"
                config.inquest_data = True


class SubscriberAudioIntensityResult(EDAThread):
    VOICE_INTENSITY_RESULT = None

    def __init__(self):
        super(SubscriberAudioIntensityResult, self).__init__("SubscriberAudioIntensityResult")
        self.setDaemon(True)
        self.voice_intensity_socket = None

    def run(self):
        config.LOG.info("接收声强数据线程已启动")
        while True:
            # 线程控制
            try:
                if self.is_exit is True:
                    return
                if self.is_running is False:
                    time.sleep(CAMERA_FREQUENCY)
                    continue
                if not config.inquest_status:
                    time.sleep(CAMERA_FREQUENCY)
                    continue
                if config.VOICE_DATA_OBJECT is None:
                    time.sleep(CAMERA_FREQUENCY)
                    continue
                # 业务
                start = time.time()
                # 接收声强结果
                try:
                    Subscriber.VOICE_INTENSITY_RESULT = config.VOICE_DATA_OBJECT
                    # DEQUE_VOICE_INTENSITY_RESULT.append(Subscriber.VOICE_INTENSITY_RESULT)
                    self.voice_intensity_handler(Subscriber.VOICE_INTENSITY_RESULT)
                except Exception as e:
                    config.LOG.error("声强数据解析错误------》{}".format(e))
                end = time.time()
                cost = end - start
                if cost >= 0.03:
                    # VIEW_LOG.warning("SubscriberAudioIntensityResult 接收并处理数据用时%.3f秒，可能会导致音频波动图延时" % cost)
                    pass
                time.sleep(0.03)

            except Exception as e:
                config.LOG.error("接收声强数据线程异常")
                config.LOG.error(e)

    @staticmethod
    def voice_intensity_handler(result):
        # 处理声强数据
        if result:
            if config.inquest_status:
                data = [item[0] for item in Subscriber.VOICE_INTENSITY_RESULT]
                voice_data = [audio_data // 6 if audio_data <= 3000 else int(3000 / 6) for audio_data in data]
                # tmp = json.dumps(voice_data)
                config.MONGODB_VOICE_DATA = voice_data
                # print("config.MONGODB_VOICE_DATA: ", config.MONGODB_VOICE_DATA)



# 处理数据线程
# class SaveDataHandlerThread(EDAThread):
#
#     def __init__(self):
#         super(SaveDataHandlerThread, self).__init__("Subscriber")
#         self.setDaemon(True)
#
#     def run(self):
#         global DEQUE_OPENFACE_RESULT
#         global DEQUE_VOICE_INTENSITY_RESULT
#         config.LOG.info("数据封装线程已启动")
#         while True:
#             print(DEQUE_OPENFACE_RESULT,DEQUE_VOICE_INTENSITY_RESULT)
#             # if len(DEQUE_OPENFACE_RESULT):
#             #     result = DEQUE_OPENFACE_RESULT.popleft()
#             #     self.openface_handler(result)
#             if DEQUE_OPENFACE_RESULT:
#                 self.openface_handler(DEQUE_OPENFACE_RESULT)
#             # if len(DEQUE_VOICE_INTENSITY_RESULT):
#             #     result = DEQUE_VOICE_INTENSITY_RESULT.popleft()
#             if DEQUE_VOICE_INTENSITY_RESULT:
#                 self.voice_intensity_handler(DEQUE_VOICE_INTENSITY_RESULT)
#             #     self.voice_intensity_handler(result)
#             # if len(DEQUE_TEMP_RESULT):
#             #     result = DEQUE_TEMP_RESULT.popleft()
#             #     self.temp_handler(result)
#             # todo
#             """mongo db 入库"""
#             time.sleep(0.03)




if __name__ == '__main__':
    sub = Subscriber()
    sub.start()
    while True:
        if sub.OPENFACE_RESULT:
            key = cv2.waitKey(1) & 0xFF
            cv2.imshow('subscriber', sub.OPENFACE_RESULT.ori_frame)
            if key == ord("q"):
                break
