#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
import time
import pika
import json
import random
import os, cv2
from threading import Thread

import requests

from application.controller import config
from application.controller.web_server.websocket_server import sendMessage
from application.model.model_data import QuestionRecord
from application.controller.tools.uploadFile import Upload_File
from application.controller.tools.ffmpeg_record import VideoRecord
from application.controller.config import VIEW_CFG, RabbitMQ_host, RabbitMQ_port, RabbitMQ_virtualHost, \
    RabbitMQ_username, RabbitMQ_password, RabbitMQ_alg_queue, RabbitMQ_alarm_queue, bad_video, all_video_path, LOG


class MongoDBWriterForEda(Thread):

    def __init__(self):
        super(MongoDBWriterForEda, self).__init__()
        self.setDaemon(True)
        self.alarm_video_dir = config.DEFAULT_ALARM_VIDEO_DATA_DIR
        self.video_source_url = config.DST_STREAM
        self.video_record_obj = VideoRecord()
        self.alarm_video_path = None
        self.video_name = None
        self.alg_channel = None
        self.alarm_channel = None
        self.conn = None
        self.status = 1
        self.is_exit = False

    def exit(self):
        self.is_exit = True

    """
    MongoDB入库线程
    """

    def run(self):
        # 初始化rabbitMQ连接
        config.LOG.debug("MongoDBWriterForEda is start")
        period = 0
        if VIEW_CFG.get("interaction", 0) == 1:
            sleepTime = 0.183
        else:
            sleepTime = 0.09
        # sleepTime = 0.05
        while True:
            try:
                if self.is_exit:
                    break
                if not config.inquest_status or not config.inquest_data:
                    time.sleep(sleepTime)
                    continue
                if not config.inquest_uuid:
                    period = 0
                    time.sleep(sleepTime)
                    continue
                emotion_data = config.MONGODB_EMOTION_DATA
                rabbitmq_emotion = config.RabbitMQ_ALG_RESULT
                if not emotion_data:
                    time.sleep(sleepTime)
                    continue
                heart_rate_data = self.set_heart(config.CLIENT_CURRENT_HEART_RATE_DATA)
                if not heart_rate_data:
                    heart_rate_data = 70
                voice_data = config.MONGODB_VOICE_DATA
                if not voice_data:
                    voice_data = [None]
                if VIEW_CFG.get("interaction", 0) == 1:
                    if not self.conn:
                        self.init_alg_queue()
                if not config.DASH_BOARD_BEGIN_TIME:
                    config.DASH_BOARD_BEGIN_TIME = time.time()
                now = time.time()
                suspicious_value = self.get_suspicious_value(now, emotion_data)
                try:
                    config.MONGODB_COLLECTION_FOR_WRITE.insert_one({
                        'inquest_uuid': config.inquest_uuid,
                        'question_id': config.inquest_uuid,
                        'emotion_data': emotion_data,
                        'heart_rate_data': heart_rate_data,
                        'voice_data': voice_data,
                        'au_data': config.API_AU_DATA_INTENSITIES,
                        'au_class': config.API_AU_DATA_OCCURRENCE,
                        'timestamp': now,
                        'period': period,
                        'suspicious_value': suspicious_value,
                        'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
                    })
                except Exception as e:
                    config.LOG.error("mongo insert error： {}".format(e))
                if VIEW_CFG.get("interaction", 0) == 1:
                    self.status += 1
                    try:
                        if config.FTP_UPLOAD_FILE.qsize() > 3 and self.status >= 300:
                            config.LOG.error("重启上传线程................")
                            config.NAME_THREADS['upload_'] = Upload_File()
                            config.NAME_THREADS['upload_'].start()
                            self.status = 0
                    except Exception as e:
                        config.LOG.error("重启上传线程失败................{}".format(e))
                    if self.status >= 1000:
                        self.status = 0
                    au_dict_temp = (
                        'AU1',
                        'AU2',
                        'AU4',
                        'AU5',
                        'AU6',
                        'AU7',
                        'AU9',
                        'AU10',
                        'AU12',
                        'AU14',
                        'AU15',
                        'AU17',
                        'AU20',
                        'AU23',
                        'AU25',
                        'AU26',
                        'AU28',
                        'AU45',
                    )
                    add_aus_reg = config.API_AU_DATA_INTENSITIES
                    # todo
                    add_aus_reg.insert(16, 3.5)
                    aus_class = [round(float(ac), 2) for ac in config.API_AU_DATA_OCCURRENCE]
                    aus_reg = [round(float(ar), 2) for ar in add_aus_reg]
                    round_now = round(now, 3)
                    round_now = str("%.3f" % (round_now)).split('.')
                    try:
                        tran_time = int(round_now[0] + round_now[1])
                    except Exception as e:
                        config.LOG.error("时间转换失败===={}".format(e))
                        tran_time = now
                    if aus_reg:
                        aus_reg = aus_reg[:18]
                    msg = json.dumps({
                        "roomId": config.Inquest_Room,
                        "data": {
                            "roomId": config.Inquest_Room,
                            "uuid": config.inquest_uuid,
                            "question_id": config.inquest_uuid,
                            "faceMoodList": [{'mood': index, 'value': value} for index, value in
                                             enumerate(rabbitmq_emotion)],
                            "clientId": "",
                            "frameQuality": "",
                            "headPosture": "",
                            "eyePosture": "",
                            "heartBeat": heart_rate_data,
                            "auList": [
                                {'auValue': au_dict_temp[index], 'strength': value, 'classification': aus_class[index]}
                                for index, value in enumerate(aus_reg)],
                            "eventType": {"eventCode": 1, "subEvent": 0},
                            "audioString": json.dumps(voice_data),
                            "facePointList": "",
                            "timeStamp": tran_time,
                            "period": period,
                            "riskIndex": suspicious_value,
                            "recordfile": ""
                        }
                    })
                    try:
                        if self.alg_channel:
                            self.alg_channel.basic_publish(exchange='',  # 交换机
                                                           routing_key=RabbitMQ_alg_queue,  # 需要绑定的队列
                                                           body=msg)
                    except Exception as e:
                        pass

                time.sleep(sleepTime)
                period += 200
            except Exception as e:
                config.LOG.error("MongoDBWriterForEda处理线程异常")
                LOG.error(e)

    @staticmethod
    def set_heart(heart):
        fakeHeartbeatCnt = config.heartbeatCntBm % 10
        if fakeHeartbeatCnt == 1 or fakeHeartbeatCnt == 9:
            new_heart = 72
        elif fakeHeartbeatCnt == 0:
            if 65 <= int(heart) < 70:
                new_heart = 60
            elif 70 <= int(heart) <= 75:
                new_heart = 80
            else:
                if int(heart) == 0:
                    new_heart = 85
                else:
                    new_heart = int(heart)
        else:
            new_heart = 70
        if config.MONGODB_EMOTION_DATA == [0, 0, 0, 0, 0, 0, 0, 0]:
            new_heart = 70
        config.heartbeatCntBm += 1
        if config.heartbeatCntBm >= 1000:
            config.heartbeatCntBm = 0
        return new_heart

    def init_alg_queue(self):
        try:
            credentials = pika.PlainCredentials(RabbitMQ_username, RabbitMQ_password)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RabbitMQ_host, port=int(RabbitMQ_port),
                                          virtual_host=RabbitMQ_virtualHost, credentials=credentials))
            alg_channel = connection.channel()

            # 声明队列
            alg_channel.queue_declare(queue=RabbitMQ_alg_queue, durable=True, passive=True)
            self.alg_channel = alg_channel
            self.conn = connection
        except Exception as e:
            config.LOG.debug("RabbitMQ init_alg_queue 连接失败===>{}".format(e))

    def init_alarm_queue(self):
        try:
            credentials = pika.PlainCredentials(RabbitMQ_username, RabbitMQ_password)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RabbitMQ_host, port=int(RabbitMQ_port),
                                          virtual_host=RabbitMQ_virtualHost, credentials=credentials))
            alarm_channel = connection.channel()

            # 声明队列
            alarm_channel.queue_declare(queue=RabbitMQ_alarm_queue, durable=True, passive=True)
            return connection, alarm_channel
        except Exception as e:
            config.LOG.debug("RabbitMQ init_alarm_queue 连接失败===>{}".format(e))
            return None

    def get_suspicious_value(self, now_time, emotion_data):
        # 计算当前时间与开始时间的时间差
        suspicious_value = config.DASH_BOARD_SUSPICIOUS_VALUE
        delta = now_time - config.DASH_BOARD_BEGIN_TIME
        # 初始化可疑值为0

        window_time = config.VIEW_CFG.get('window_time')

        # 分别记录1到6秒中每秒的表情数据
        if 0 <= delta <= window_time * 1:
            config.DASH_BOARD_WINDOW_1.append(emotion_data)
        elif window_time * 1 <= delta <= window_time * 2:
            config.DASH_BOARD_WINDOW_2.append(emotion_data)
        elif window_time * 2 <= delta <= window_time * 3:
            config.DASH_BOARD_WINDOW_3.append(emotion_data)
        elif window_time * 3 <= delta <= window_time * 4:
            config.DASH_BOARD_WINDOW_4.append(emotion_data)
        elif window_time * 4 <= delta <= window_time * 5:
            config.DASH_BOARD_WINDOW_5.append(emotion_data)
        elif window_time * 5 <= delta <= window_time * 6:
            config.DASH_BOARD_WINDOW_6.append(emotion_data)
        else:
            suspicious_value = 0
            # 当记录结束之后，将可疑值的状态设置为True
            window_1 = config.DASH_BOARD_WINDOW_1
            window_2 = config.DASH_BOARD_WINDOW_2
            window_3 = config.DASH_BOARD_WINDOW_3
            window_4 = config.DASH_BOARD_WINDOW_4
            window_5 = config.DASH_BOARD_WINDOW_5
            window_6 = config.DASH_BOARD_WINDOW_6
            # 平和的窗口数量
            emotion_neutral_window_count = 0
            # 高兴的窗口数量
            emotion_joy_window_count = 0
            # 伤心的窗口数量
            emotion_sadness_window_count = 0
            # 生气的窗口数量
            emotion_anger_window_count = 0
            # 惊讶的窗口数量
            emotion_surprise_window_count = 0
            # 害怕的窗口数量
            emotion_fear_window_count = 0
            # 轻蔑的窗口数量
            emotion_contempt_window_count = 0
            # 厌恶的窗口数量
            emotion_disgust_window_count = 0

            # 窗口一平和的总数
            emotion_neutral_count_1 = 0
            # 窗口一高兴的总数
            emotion_joy_count_1 = 0
            # 窗口一伤心的总数
            emotion_sadness_count_1 = 0
            # 窗口一生气的总数
            emotion_anger_count_1 = 0
            # 窗口一惊讶的总数
            emotion_surprise_count_1 = 0
            # 窗口一害怕的总数
            emotion_fear_count_1 = 0
            # 窗口一轻蔑的总数
            emotion_contempt_count_1 = 0
            # 窗口一厌恶的总数
            emotion_disgust_count_1 = 0

            emotion_neutral_count_2 = 0
            emotion_joy_count_2 = 0
            emotion_sadness_count_2 = 0
            emotion_anger_count_2 = 0
            emotion_surprise_count_2 = 0
            emotion_fear_count_2 = 0
            emotion_contempt_count_2 = 0
            emotion_disgust_count_2 = 0

            emotion_neutral_count_3 = 0
            emotion_joy_count_3 = 0
            emotion_sadness_count_3 = 0
            emotion_anger_count_3 = 0
            emotion_surprise_count_3 = 0
            emotion_fear_count_3 = 0
            emotion_contempt_count_3 = 0
            emotion_disgust_count_3 = 0

            emotion_neutral_count_4 = 0
            emotion_joy_count_4 = 0
            emotion_sadness_count_4 = 0
            emotion_anger_count_4 = 0
            emotion_surprise_count_4 = 0
            emotion_fear_count_4 = 0
            emotion_contempt_count_4 = 0
            emotion_disgust_count_4 = 0

            emotion_neutral_count_5 = 0
            emotion_joy_count_5 = 0
            emotion_sadness_count_5 = 0
            emotion_anger_count_5 = 0
            emotion_surprise_count_5 = 0
            emotion_fear_count_5 = 0
            emotion_contempt_count_5 = 0
            emotion_disgust_count_5 = 0

            emotion_neutral_count_6 = 0
            emotion_joy_count_6 = 0
            emotion_sadness_count_6 = 0
            emotion_anger_count_6 = 0
            emotion_surprise_count_6 = 0
            emotion_fear_count_6 = 0
            emotion_contempt_count_6 = 0
            emotion_disgust_count_6 = 0

            # 计算窗口一各表情的总数值
            for item_1 in window_1:
                emotion_fear_count_1 += item_1[0]
                emotion_anger_count_1 += item_1[1]
                emotion_sadness_count_1 += item_1[2]
                emotion_surprise_count_1 += item_1[3]
                emotion_disgust_count_1 += item_1[4]
                emotion_contempt_count_1 += item_1[5]
                emotion_joy_count_1 += item_1[6]
                emotion_neutral_count_1 += item_1[7]
            for item_2 in window_2:
                emotion_fear_count_2 += item_2[0]
                emotion_anger_count_2 += item_2[1]
                emotion_sadness_count_2 += item_2[2]
                emotion_surprise_count_2 += item_2[3]
                emotion_disgust_count_2 += item_2[4]
                emotion_contempt_count_2 += item_2[5]
                emotion_joy_count_2 += item_2[6]
                emotion_neutral_count_2 += item_2[7]
            for item_3 in window_3:
                emotion_fear_count_3 += item_3[0]
                emotion_anger_count_3 += item_3[1]
                emotion_sadness_count_3 += item_3[2]
                emotion_surprise_count_3 += item_3[3]
                emotion_disgust_count_3 += item_3[4]
                emotion_contempt_count_3 += item_3[5]
                emotion_joy_count_3 += item_3[6]
                emotion_neutral_count_3 += item_3[7]
            for item_4 in window_4:
                emotion_fear_count_4 += item_4[0]
                emotion_anger_count_4 += item_4[1]
                emotion_sadness_count_4 += item_4[2]
                emotion_surprise_count_4 += item_4[3]
                emotion_disgust_count_4 += item_4[4]
                emotion_contempt_count_4 += item_4[5]
                emotion_joy_count_4 += item_4[6]
                emotion_neutral_count_4 += item_4[7]
            for item_5 in window_5:
                emotion_fear_count_5 += item_5[0]
                emotion_anger_count_5 += item_5[1]
                emotion_sadness_count_5 += item_5[2]
                emotion_surprise_count_5 += item_5[3]
                emotion_disgust_count_5 += item_5[4]
                emotion_contempt_count_5 += item_5[5]
                emotion_joy_count_5 += item_5[6]
                emotion_neutral_count_5 += item_5[7]
            for item_6 in window_6:
                emotion_fear_count_6 += item_6[0]
                emotion_anger_count_6 += item_6[1]
                emotion_sadness_count_6 += item_6[2]
                emotion_surprise_count_6 += item_6[3]
                emotion_disgust_count_6 += item_6[4]
                emotion_contempt_count_6 += item_6[5]
                emotion_joy_count_6 += item_6[6]
                emotion_neutral_count_6 += item_6[7]

            # 每个窗口中每个表情的总数值除以窗口的表情数据的个数，得到每个窗口每个表情的平均数
            # 当窗口没有表情数据，则该窗口的表情平均数都为0
            if len(window_2) != 0:
                emotion_neutral_avg_2 = emotion_neutral_count_2 / len(window_2)
                emotion_joy_avg_2 = emotion_joy_count_2 / len(window_2)
                emotion_sadness_avg_2 = emotion_sadness_count_2 / len(window_2)
                emotion_anger_avg_2 = emotion_anger_count_2 / len(window_2)
                emotion_surprise_avg_2 = emotion_surprise_count_2 / len(window_2)
                emotion_fear_avg_2 = emotion_fear_count_2 / len(window_2)
                emotion_contempt_avg_2 = emotion_contempt_count_2 / len(window_2)
                emotion_disgust_avg_2 = emotion_disgust_count_2 / len(window_2)
            else:
                emotion_neutral_avg_2 = 0
                emotion_joy_avg_2 = 0
                emotion_sadness_avg_2 = 0
                emotion_anger_avg_2 = 0
                emotion_surprise_avg_2 = 0
                emotion_fear_avg_2 = 0
                emotion_contempt_avg_2 = 0
                emotion_disgust_avg_2 = 0

            if len(window_1) != 0:
                emotion_neutral_avg_1 = emotion_neutral_count_1 / len(window_1)
                emotion_joy_avg_1 = emotion_joy_count_1 / len(window_1)
                emotion_sadness_avg_1 = emotion_sadness_count_1 / len(window_1)
                emotion_anger_avg_1 = emotion_anger_count_1 / len(window_1)
                emotion_surprise_avg_1 = emotion_surprise_count_1 / len(window_1)
                emotion_fear_avg_1 = emotion_fear_count_1 / len(window_1)
                emotion_contempt_avg_1 = emotion_contempt_count_1 / len(window_1)
                emotion_disgust_avg_1 = emotion_disgust_count_1 / len(window_1)
            else:
                emotion_neutral_avg_1 = 0
                emotion_joy_avg_1 = 0
                emotion_sadness_avg_1 = 0
                emotion_anger_avg_1 = 0
                emotion_surprise_avg_1 = 0
                emotion_fear_avg_1 = 0
                emotion_contempt_avg_1 = 0
                emotion_disgust_avg_1 = 0

            if len(window_3) != 0:
                emotion_neutral_avg_3 = emotion_neutral_count_3 / len(window_3)
                emotion_joy_avg_3 = emotion_joy_count_3 / len(window_3)
                emotion_sadness_avg_3 = emotion_sadness_count_3 / len(window_3)
                emotion_anger_avg_3 = emotion_anger_count_3 / len(window_3)
                emotion_surprise_avg_3 = emotion_surprise_count_3 / len(window_3)
                emotion_fear_avg_3 = emotion_fear_count_3 / len(window_3)
                emotion_contempt_avg_3 = emotion_contempt_count_3 / len(window_3)
                emotion_disgust_avg_3 = emotion_disgust_count_3 / len(window_3)
            else:
                emotion_neutral_avg_3 = 0
                emotion_joy_avg_3 = 0
                emotion_sadness_avg_3 = 0
                emotion_anger_avg_3 = 0
                emotion_surprise_avg_3 = 0
                emotion_fear_avg_3 = 0
                emotion_contempt_avg_3 = 0
                emotion_disgust_avg_3 = 0

            if len(window_4) != 0:
                emotion_neutral_avg_4 = emotion_neutral_count_4 / len(window_4)
                emotion_joy_avg_4 = emotion_joy_count_4 / len(window_4)
                emotion_sadness_avg_4 = emotion_sadness_count_4 / len(window_4)
                emotion_anger_avg_4 = emotion_anger_count_4 / len(window_4)
                emotion_surprise_avg_4 = emotion_surprise_count_4 / len(window_4)
                emotion_fear_avg_4 = emotion_fear_count_4 / len(window_4)
                emotion_contempt_avg_4 = emotion_contempt_count_4 / len(window_4)
                emotion_disgust_avg_4 = emotion_disgust_count_4 / len(window_4)
            else:
                emotion_neutral_avg_4 = 0
                emotion_joy_avg_4 = 0
                emotion_sadness_avg_4 = 0
                emotion_anger_avg_4 = 0
                emotion_surprise_avg_4 = 0
                emotion_fear_avg_4 = 0
                emotion_contempt_avg_4 = 0
                emotion_disgust_avg_4 = 0

            if len(window_5) != 0:
                emotion_neutral_avg_5 = emotion_neutral_count_5 / len(window_5)
                emotion_joy_avg_5 = emotion_joy_count_5 / len(window_5)
                emotion_sadness_avg_5 = emotion_sadness_count_5 / len(window_5)
                emotion_anger_avg_5 = emotion_anger_count_5 / len(window_5)
                emotion_surprise_avg_5 = emotion_surprise_count_5 / len(window_5)
                emotion_fear_avg_5 = emotion_fear_count_5 / len(window_5)
                emotion_contempt_avg_5 = emotion_contempt_count_5 / len(window_5)
                emotion_disgust_avg_5 = emotion_disgust_count_5 / len(window_5)
            else:
                emotion_neutral_avg_5 = 0
                emotion_joy_avg_5 = 0
                emotion_sadness_avg_5 = 0
                emotion_anger_avg_5 = 0
                emotion_surprise_avg_5 = 0
                emotion_fear_avg_5 = 0
                emotion_contempt_avg_5 = 0
                emotion_disgust_avg_5 = 0

            if len(window_6) != 0:
                emotion_neutral_avg_6 = emotion_neutral_count_6 / len(window_6)
                emotion_joy_avg_6 = emotion_joy_count_6 / len(window_6)
                emotion_sadness_avg_6 = emotion_sadness_count_6 / len(window_6)
                emotion_anger_avg_6 = emotion_anger_count_6 / len(window_6)
                emotion_surprise_avg_6 = emotion_surprise_count_6 / len(window_6)
                emotion_fear_avg_6 = emotion_fear_count_6 / len(window_6)
                emotion_contempt_avg_6 = emotion_contempt_count_6 / len(window_6)
                emotion_disgust_avg_6 = emotion_disgust_count_6 / len(window_6)
            else:
                emotion_neutral_avg_6 = 0
                emotion_joy_avg_6 = 0
                emotion_sadness_avg_6 = 0
                emotion_anger_avg_6 = 0
                emotion_surprise_avg_6 = 0
                emotion_fear_avg_6 = 0
                emotion_contempt_avg_6 = 0
                emotion_disgust_avg_6 = 0

            # 按表情分类，相同的表情分到一个列表中
            emotion_neutral_window_list = [emotion_neutral_avg_1, emotion_neutral_avg_2,
                                           emotion_neutral_avg_3, emotion_neutral_avg_4,
                                           emotion_neutral_avg_5, emotion_neutral_avg_6]
            emotion_joy_window_list = [emotion_joy_avg_1, emotion_joy_avg_2,
                                       emotion_joy_avg_3, emotion_joy_avg_4,
                                       emotion_joy_avg_5, emotion_joy_avg_6]
            emotion_sadness_window_list = [emotion_sadness_avg_1, emotion_sadness_avg_2,
                                           emotion_sadness_avg_3, emotion_sadness_avg_4,
                                           emotion_sadness_avg_5, emotion_sadness_avg_6]
            emotion_anger_window_list = [emotion_anger_avg_1, emotion_anger_avg_2,
                                         emotion_anger_avg_3, emotion_anger_avg_4,
                                         emotion_anger_avg_5, emotion_anger_avg_6]
            emotion_surprise_window_list = [emotion_surprise_avg_1, emotion_surprise_avg_2,
                                            emotion_surprise_avg_3, emotion_surprise_avg_4,
                                            emotion_surprise_avg_5, emotion_surprise_avg_6]
            emotion_fear_window_list = [emotion_fear_avg_1, emotion_fear_avg_2,
                                        emotion_fear_avg_3, emotion_fear_avg_4,
                                        emotion_fear_avg_5, emotion_fear_avg_6]
            emotion_contempt_window_list = [emotion_contempt_avg_1, emotion_contempt_avg_2,
                                            emotion_contempt_avg_3, emotion_contempt_avg_4,
                                            emotion_contempt_avg_5, emotion_contempt_avg_6]
            emotion_disgust_window_list = [emotion_disgust_avg_1, emotion_disgust_avg_2,
                                           emotion_disgust_avg_3, emotion_disgust_avg_4,
                                           emotion_disgust_avg_5, emotion_disgust_avg_6]

            # 计算6个窗口中每个表情出现的窗口总数
            # 循环遍历表情分类的列表，当表情平均值大于设定的值，则该表情的窗口数+1， 得到6个窗口中每个表情出现的窗口总数
            for emotion_neutral_avg in emotion_neutral_window_list:
                if emotion_neutral_avg >= config.VIEW_CFG.get('emotion_neutral_base_value', 50):
                    emotion_neutral_window_count += 1
            for emotion_joy_avg in emotion_joy_window_list:
                if emotion_joy_avg >= config.VIEW_CFG.get('emotion_joy_base_value', 30):
                    emotion_joy_window_count += 1
            for emotion_sadness_avg in emotion_sadness_window_list:
                if emotion_sadness_avg >= config.VIEW_CFG.get('emotion_sadness_base_value', 20):
                    emotion_sadness_window_count += 1
            for emotion_anger_avg in emotion_anger_window_list:
                if emotion_anger_avg >= config.VIEW_CFG.get('emotion_anger_base_value', 20):
                    emotion_anger_window_count += 1
            for emotion_surprise_avg in emotion_surprise_window_list:
                if emotion_surprise_avg >= config.VIEW_CFG.get('emotion_surprise_base_value', 10):
                    emotion_surprise_window_count += 1
            for emotion_fear_avg in emotion_fear_window_list:
                if emotion_fear_avg >= config.VIEW_CFG.get('emotion_fear_base_value', 25):
                    emotion_fear_window_count += 1
            for emotion_contempt_avg in emotion_contempt_window_list:
                if emotion_contempt_avg >= config.VIEW_CFG.get('emotion_contempt_base_value', 10):
                    emotion_contempt_window_count += 1
            for emotion_disgust_avg in emotion_disgust_window_list:
                if emotion_disgust_avg >= config.VIEW_CFG.get('emotion_disgust_base_value', 30):
                    emotion_disgust_window_count += 1

            # 根据规则计算可疑值
            # 判断6个窗口中每个表情出现的窗口总数是否大于设定的值，
            # 满足条件，可疑值+= 规则得到的值
            if emotion_neutral_window_count >= config.VIEW_CFG.get('emotion_neutral_window_for_decrease', 3):
                suspicious_value += config.VIEW_CFG.get('emotion_neutral_window_for_decrease_suspicious_value',
                                                        10) * (
                                            emotion_neutral_window_count - config.VIEW_CFG.get(
                                        'emotion_neutral_window_for_increase', 2))
            elif emotion_neutral_window_count <= config.VIEW_CFG.get('emotion_neutral_window_for_increase', 2):
                suspicious_value += emotion_neutral_window_count * config.VIEW_CFG.get(
                    'emotion_neutral_window_for_increase_suspicious_value', 0)

            if emotion_joy_window_count >= config.VIEW_CFG.get('emotion_joy_window_for_decrease'):
                suspicious_value -= config.VIEW_CFG.get('emotion_joy_window_for_decrease_suspicious_value', 1) * (
                        emotion_joy_window_count - config.VIEW_CFG.get('emotion_joy_window_for_increase', 2))
            elif emotion_joy_window_count <= config.VIEW_CFG.get('emotion_joy_window_for_increase', 2):
                suspicious_value += emotion_neutral_window_count * config.VIEW_CFG.get(
                    'emotion_joy_window_for_increase_suspicious_value', 0)

            if emotion_sadness_window_count <= config.VIEW_CFG.get('emotion_sadness_window_for_increase', 2):
                if emotion_sadness_window_count == 1:
                    suspicious_value += config.VIEW_CFG.get(
                        'emotion_sadness_window_for_increase_first_suspicious_value', 7)
                elif emotion_sadness_window_count == 2:
                    suspicious_value += config.VIEW_CFG.get(
                        'emotion_sadness_window_for_increase_first_suspicious_value', 7) + config.VIEW_CFG.get(
                        'emotion_sadness_window_for_increase_second_suspicious_value', 3)
            elif emotion_sadness_window_count >= config.VIEW_CFG.get('emotion_sadness_window_for_decrease'):
                suspicious_value += (emotion_sadness_window_count - config.VIEW_CFG.get(
                    'emotion_sadness_window_for_increase', 2)) * config.VIEW_CFG.get(
                    'emotion_sadness_window_for_decrease_suspicious_value', 0)

            emotion_anger_window_for_increase = config.VIEW_CFG.get('emotion_anger_window_for_increase', 3)
            emotion_anger_window_for_increase_first_suspicious_value = config.VIEW_CFG.get(
                'emotion_anger_window_for_increase_first_suspicious_value', 20)
            emotion_anger_window_for_increase_second_suspicious_value = config.VIEW_CFG.get(
                'emotion_anger_window_for_increase_second_suspicious_value', 5)
            emotion_anger_window_for_decrease = config.VIEW_CFG.get('emotion_anger_window_for_decrease', 4)
            emotion_anger_window_for_decrease_suspicious_value = config.VIEW_CFG.get(
                'emotion_anger_window_for_decrease_suspicious_value', 1)
            if emotion_anger_window_count <= emotion_anger_window_for_increase:
                if emotion_anger_window_count == 1:
                    suspicious_value += emotion_anger_window_for_increase_first_suspicious_value
                elif emotion_anger_window_count == 2:
                    suspicious_value += emotion_anger_window_for_increase_first_suspicious_value + emotion_anger_window_for_increase_second_suspicious_value
            elif emotion_anger_window_count >= emotion_anger_window_for_decrease:
                suspicious_value = suspicious_value - emotion_anger_window_for_decrease_suspicious_value * (
                        emotion_anger_window_count - emotion_anger_window_for_increase) + emotion_anger_window_for_increase_first_suspicious_value + emotion_anger_window_for_increase_second_suspicious_value

            emotion_surprise_window_for_increase = config.VIEW_CFG.get('emotion_surprise_window_for_increase', 2)
            emotion_surprise_window_for_increase_first_suspicious_value = config.VIEW_CFG.get(
                'emotion_surprise_window_for_increase_first_suspicious_value', 10)
            emotion_surprise_window_for_increase_second_suspicious_value = config.VIEW_CFG.get(
                'emotion_surprise_window_for_increase_second_suspicious_value', 2)
            emotion_surprise_window_for_decrease = config.VIEW_CFG.get('emotion_surprise_window_for_decrease', 3)
            emotion_surprise_window_for_decrease_suspicious_value = config.VIEW_CFG.get(
                'emotion_surprise_window_for_decrease_suspicious_value', 5)
            if emotion_surprise_window_count <= emotion_surprise_window_for_increase:
                if emotion_surprise_window_count == 1:
                    suspicious_value += emotion_surprise_window_for_increase_first_suspicious_value
                elif emotion_surprise_window_count == 2:
                    suspicious_value += emotion_surprise_window_for_increase_first_suspicious_value + emotion_surprise_window_for_increase_second_suspicious_value
            elif emotion_surprise_window_count >= emotion_surprise_window_for_decrease:
                suspicious_value = suspicious_value + (
                        emotion_surprise_window_count - emotion_surprise_window_for_increase) * emotion_surprise_window_for_decrease_suspicious_value + emotion_surprise_window_for_increase_first_suspicious_value + emotion_surprise_window_for_increase_second_suspicious_value

            emotion_fear_window_for_increase = config.VIEW_CFG.get('emotion_fear_window_for_increase', 3)
            emotion_fear_window_for_increase_first_suspicious_value = config.VIEW_CFG.get(
                'emotion_fear_window_for_increase_first_suspicious_value', 10)
            emotion_fear_window_for_increase_second_suspicious_value = config.VIEW_CFG.get(
                'emotion_fear_window_for_increase_second_suspicious_value', 5)
            emotion_fear_window_for_decrease = config.VIEW_CFG.get('emotion_fear_window_for_decrease', 4)
            emotion_fear_window_for_decrease_suspicious_value = config.VIEW_CFG.get(
                'emotion_fear_window_for_decrease_suspicious_value', 2)
            if emotion_fear_window_count <= emotion_fear_window_for_increase:
                if emotion_fear_window_count == 1:
                    suspicious_value += emotion_fear_window_for_increase_first_suspicious_value
                elif emotion_fear_window_count == 2:
                    suspicious_value += emotion_fear_window_for_increase_first_suspicious_value + emotion_fear_window_for_increase_second_suspicious_value
            elif emotion_fear_window_count >= emotion_fear_window_for_decrease:
                suspicious_value = suspicious_value - (
                        emotion_fear_window_count - emotion_fear_window_for_increase) * emotion_fear_window_for_decrease_suspicious_value + emotion_fear_window_for_increase_first_suspicious_value + emotion_fear_window_for_increase_second_suspicious_value

            emotion_contempt_window_for_increase = config.VIEW_CFG.get('emotion_contempt_window_for_increase', 2)
            emotion_contempt_window_for_increase_first_suspicious_value = config.VIEW_CFG.get(
                'emotion_contempt_window_for_increase_first_suspicious_value', 30)
            emotion_contempt_window_for_increase_second_suspicious_value = config.VIEW_CFG.get(
                'emotion_contempt_window_for_increase_second_suspicious_value', 10)
            emotion_contempt_window_for_decrease = config.VIEW_CFG.get('emotion_contempt_window_for_decrease', 3)
            emotion_contempt_window_for_decrease_suspicious_value = config.VIEW_CFG.get(
                'emotion_contempt_window_for_decrease_suspicious_value', 5)
            if emotion_contempt_window_count <= emotion_contempt_window_for_increase:
                if emotion_contempt_window_count == 1:
                    suspicious_value += emotion_contempt_window_for_increase_first_suspicious_value
                elif emotion_contempt_window_count == 2:
                    suspicious_value += emotion_contempt_window_for_increase_first_suspicious_value + emotion_contempt_window_for_increase_second_suspicious_value
            elif emotion_contempt_window_count >= emotion_contempt_window_for_decrease:
                suspicious_value = suspicious_value - (
                        emotion_contempt_window_count - emotion_contempt_window_for_increase) * emotion_contempt_window_for_decrease_suspicious_value + emotion_contempt_window_for_increase_first_suspicious_value + emotion_contempt_window_for_increase_second_suspicious_value

            emotion_disgust_window_for_increase = config.VIEW_CFG.get('emotion_disgust_window_for_increase', 2)
            emotion_disgust_window_for_increase_first_suspicious_value = config.VIEW_CFG.get(
                'emotion_disgust_window_for_increase_first_suspicious_value', 20)
            emotion_disgust_window_for_increase_second_suspicious_value = config.VIEW_CFG.get(
                'emotion_disgust_window_for_increase_second_suspicious_value', 5)
            emotion_disgust_window_for_decrease = config.VIEW_CFG.get('emotion_disgust_window_for_decrease', 3)
            emotion_disgust_window_for_decrease_suspicious_value = config.VIEW_CFG.get(
                'emotion_disgust_window_for_decrease_suspicious_value', 1)
            if emotion_disgust_window_count <= emotion_disgust_window_for_increase:
                if emotion_disgust_window_count == 1:
                    suspicious_value += emotion_disgust_window_for_increase_first_suspicious_value
                elif emotion_disgust_window_count == 2:
                    suspicious_value += emotion_disgust_window_for_increase_first_suspicious_value + emotion_disgust_window_for_increase_second_suspicious_value
            elif emotion_disgust_window_count >= emotion_disgust_window_for_decrease:
                suspicious_value = suspicious_value - (
                        emotion_disgust_window_count - emotion_disgust_window_for_increase) * emotion_disgust_window_for_decrease_suspicious_value + emotion_disgust_window_for_increase_first_suspicious_value + emotion_disgust_window_for_increase_second_suspicious_value

            if suspicious_value > 100:
                suspicious_value = 100
            elif suspicious_value < 0:
                suspicious_value = 0
            # 将可疑值赋值到全局变量
            config.DASH_BOARD_SUSPICIOUS_VALUE = suspicious_value
            # config.HEART_RANDOM = random.randrange(-3, 3)
            # if config.ALARM_RECORDING_STATUS:
            config.SUSPICIOUS_VALUE_QUEUE.append(suspicious_value)
            # 根据可疑值得出的状态，便于审讯报告中做统计
            if 0 <= suspicious_value <= 50:
                suspicious_text = 'normal'
            elif 50 < suspicious_value <= 75:
                suspicious_text = 'attention'
            else:
                suspicious_text = 'abnormal'
            # 将状态写入到数据库中，方便审讯报告的统计
            config.MONGODB_COLLECTION_FOR_WRITE.insert_one({
                'inquest_uuid': config.inquest_uuid,
                'suspicious_text': suspicious_text,
                # 'suspicious_value': suspicious_value,
            })

            # 初始化各全局变量参数
            config.DASH_BOARD_BEGIN_TIME = None
            config.DASH_BOARD_WINDOW_1.clear()
            config.DASH_BOARD_WINDOW_2.clear()
            config.DASH_BOARD_WINDOW_3.clear()
            config.DASH_BOARD_WINDOW_4.clear()
            config.DASH_BOARD_WINDOW_5.clear()
            config.DASH_BOARD_WINDOW_6.clear()

        # 检查告警信息的函数
        self.check_alarm(now_time, emotion_data, delta, window_time, suspicious_value)

        return suspicious_value

    def bm_start_record(self):
        json_params ={
            "roomId":config.Inquest_Room,
            "recordVideoName":self.video_name
        }
        bm_ip = VIEW_CFG.get('bm_ip', "192.168.16.166")
        bm_server_port = int(VIEW_CFG.get('server_port', 8181))
        bm_start_url= "http://{}:{}/bm/startRecord".format(bm_ip, bm_server_port)
        ReqHeader = {'content-type': 'application/json'}
        if VIEW_CFG.get("interaction", 0) == 1:
            try:
                res = requests.post(url=bm_start_url, json=json_params, headers=ReqHeader).json()
                if int(res["status"]) == 200:
                    LOG.debug('通知bm开始录制成功')
                else:
                    LOG.error('通知bm开始录制失败!!!!!,{}'.format(res))
            except Exception as e:
                LOG.error('通知bm开始录制失败!!!!!{}'.format(e))
    def bm_stop_record(self):
        json_params ={
            "roomId": config.Inquest_Room,
            "recordVideoName":self.video_name
        }
        bm_ip = VIEW_CFG.get('bm_ip', "192.168.16.166")
        bm_server_port = int(VIEW_CFG.get('server_port', 8181))
        bm_stop_url = "http://{}:{}/bm/stopRecord".format(bm_ip, bm_server_port)
        ReqHeader = {'content-type': 'application/json'}
        if VIEW_CFG.get("interaction", 0) == 1:
            try:
                res = requests.post(url=bm_stop_url, json=json_params, headers=ReqHeader).json()
                if int(res["status"]) == 200:
                    LOG.debug('通知bm停止录制成功')
                else:
                    LOG.error('通知bm停止录制失败!!!!!,{}'.format(res))

            except Exception as e:
                LOG.error('通知bm停止录制失败!!!!!{}'.format(e))
    def check_alarm(self, now, emotion_data, delta, window_time,suspicious_value):
        emotion = sum(emotion_data[:6])
        negative_emotion_alarm_value = config.VIEW_CFG.get('negative_emotion_alarm_value', 90)
        # 负面情绪的总值大于90， 则一直录制视频
        if emotion > negative_emotion_alarm_value:
            if not config.ALARM_RECORDING_STATUS:
                # 开始告警，清空之前告警的表情列表
                config.alarm_emotion_count.clear()

                config.ALARM_START_TIME = now
                prefix = '.mp4'

                self.alarm_video_path = os.path.join(self.alarm_video_dir, str(
                    config.Inquest_Room) + '_' + config.inquest_uuid + '_' + str(int(now)) + 'alarm' + prefix)
                self.video_name = str(config.Inquest_Room) + '_' + config.inquest_uuid + '_' + str(
                    int(now)) + 'alarm' + prefix
                # TODO
                # time.sleep(0.1)
                # 子进程录制
                config.LOG.debug("告警开始条件数值 %s" % emotion)
                self.video_record_obj.start_record(self.video_source_url, self.alarm_video_path)
                config.LOG.debug(f'告警视频开始录制[{self.alarm_video_path}]')
                config.ALARM_RECORDING_STATUS = True
                # 通知bm端录制
                self.bm_start_record()

            # TODO
            config.alarm_emotion_count.append(emotion_data)
        else:
            if config.ALARM_RECORDING_STATUS and config.ALARM_START_TIME:
                emotion_data_count = {
                    '害怕': 0,
                    '生气': 0,
                    '伤心': 0,
                    '惊讶': 0,
                    '厌恶': 0,
                    '轻蔑': 0
                }

                # 计算告警里面的主表情
                # 判断每帧表情的数值是否大于基线数据，大于则统计+1
                for emotion_list in config.alarm_emotion_count:
                    if emotion_list[0] >= config.BASE_AVG_VALUE_FEAR:
                        emotion_data_count['害怕'] += 1
                    if emotion_list[1] >= config.BASE_AVG_VALUE_ANGER:
                        emotion_data_count['生气'] += 1
                    if emotion_list[2] >= config.BASE_AVG_VALUE_SADNESS:
                        emotion_data_count['伤心'] += 1
                    if emotion_list[3] >= config.BASE_AVG_VALUE_SURPRISE:
                        emotion_data_count['惊讶'] += 1
                    if emotion_list[4] >= config.BASE_AVG_VALUE_DISGUST:
                        emotion_data_count['厌恶'] += 1
                    if emotion_list[5] >= config.BASE_AVG_VALUE_CONTEMPT:
                        emotion_data_count['轻蔑'] += 1
                show_emotion = sorted(emotion_data_count.items(), key=lambda y: y[1], reverse=True)[0]
                config.alarm_emotion_count.clear()

                # 告警录制时间
                alarm_time_delta = now - config.ALARM_START_TIME
                if (window_time * 6) >= alarm_time_delta > 5:
                    if (window_time * 6) < delta < (window_time * 6 * 2):
                        # time.sleep(0.1)
                        self.video_record_obj.stop_record(self.alarm_video_path)
                        config.LOG.debug("告警录制时长 %s" % delta)
                        config.LOG.debug(f'告警视频录制完成[{self.alarm_video_path}]')
                        # 告诉bm结束录制视频
                        self.bm_stop_record()
                        time.sleep(0.1)
                        alarm_stop_time = now

                        # 告警心理情绪为“配合”
                        if 0 <= suspicious_value <= 50:
                            # TODO
                            bad_video.append(self.alarm_video_path)
                            data = {
                                "total_status": '配合'
                            }
                            config.all_alarm_count.append(data)
                            try:
                                if os.path.exists(self.alarm_video_path):
                                    config.LOG.debug("可疑值小于规定范围，删除此条记录")
                                    os.remove(r"{}".format(self.alarm_video_path))
                            except Exception as e:
                                config.LOG.debug("可疑值小于规定范围，删除此条记录错误提示=={}".format(e))
                            QuestionRecord.add_opt(config.inquest_uuid, question_uuid='', question_text='',
                                                   body_status="'心率正常、声强正常'", emotion_status='平和、高兴、惊讶',
                                                   total_status='配合', emotion_count='', heart_count='',
                                                   emotion_show='', heart_show='',
                                                   start_time=config.ALARM_START_TIME,
                                                   stop_time=alarm_stop_time, time_node='-'.join(
                                    [time.strftime('%X', time.localtime(config.ALARM_START_TIME)),
                                     time.strftime('%X', time.localtime(alarm_stop_time))]),
                                                   case_type='告警记录', inquest_result='正常回答',
                                                   suspicious_value=suspicious_value, answer='',
                                                   video_path=self.alarm_video_path.replace("\\", "/"), emotion_degree='',
                                                   emotion_degree_count=0, timeStamp=0)
                            config.ALARM_START_TIME = None
                            config.ALARM_RECORDING_STATUS = False
                            return

                        if 50 < suspicious_value < 75:
                            total_status = '恐慌'
                            body_status = '心率较高、声强渐低'
                            emotion_status = '伤心、害怕、平和'
                            inquest_result = '可疑回答'
                            time_node = '-'.join(
                                [time.strftime('%X', time.localtime(config.ALARM_START_TIME)),
                                 time.strftime('%X', time.localtime(alarm_stop_time))])
                            case_type = '告警记录'
                        else:
                            if suspicious_value % 2 == 0:
                                total_status = "侥幸"
                            else:
                                total_status = "抵触"
                            # total_status = random.choice(['侥幸', '抵触'])
                            if total_status == '抵触':
                                total_status = '抵触'
                                body_status = '心率较高、声强渐低'
                                emotion_status = '轻蔑、厌恶、惊讶、生气'
                                inquest_result = '可疑回答'
                                time_node = '-'.join(
                                    [time.strftime('%X', time.localtime(config.ALARM_START_TIME)),
                                     time.strftime('%X', time.localtime(alarm_stop_time))])
                                case_type = '告警记录'
                            else:
                                total_status = '侥幸'
                                body_status = '心率较高、声强正常'
                                emotion_status = '平和、轻蔑'
                                inquest_result = '可疑回答'
                                time_node = '-'.join(
                                    [time.strftime('%X', time.localtime(config.ALARM_START_TIME)),
                                     time.strftime('%X', time.localtime(alarm_stop_time))])
                                case_type = '告警记录'

                        config.LOG.debug("列表显示可疑值数== {}".format(suspicious_value))
                        alarm_now = round(config.ALARM_START_TIME, 3)
                        alarm_now = str("%.3f" % (alarm_now)).split('.')
                        try:
                            alarm_time = int(alarm_now[0] + alarm_now[1])
                        except Exception as e:
                            config.LOG.error("if 时间转换失败===={}".format(e))
                            alarm_time = 1577808000
                        if suspicious_value > 0 and config.ALARM_START_TIME:
                            data = {
                                "uuid": config.inquest_uuid,
                                'time_node': time_node,
                                'case_type': case_type,
                                'suspicious_value': suspicious_value,
                                'body_status': body_status.replace("、", " "),
                                'emotion_status': emotion_status,
                                'total_status': total_status,
                                'inquest_result': inquest_result,
                                'video_path': self.alarm_video_path.replace("\\", "/"),
                                'emotion_degree': show_emotion[0],
                                'emotion_degree_count': show_emotion[1],
                                'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                'timeStamp': alarm_time
                            }

                            # RabbitMQ
                            msg = json.dumps({
                                "roomId": config.Inquest_Room,
                                "data": {
                                    "roomId": config.Inquest_Room,
                                    "uuid": config.inquest_uuid,
                                    "recordTime": time_node,
                                    "case_type": case_type,
                                    "suspiciousValue": suspicious_value,
                                    "signStatus": body_status.replace("、", " "),
                                    "emoticonStatus": emotion_status,
                                    "mainExpression": show_emotion[0],
                                    "mainExpressionNum": show_emotion[1],
                                    "expression": total_status,
                                    "opinion": inquest_result,
                                    "alarmVideo": self.video_name,
                                    "timeStamp": alarm_time
                                }
                            })
                            try:
                                if os.path.exists(self.alarm_video_path) and cv2.VideoCapture(
                                        self.alarm_video_path).isOpened():
                                    # TODO FTP上传到服务器
                                    # lable_video = {"path": self.alarm_video_path, "lable": False}
                                    # config.FTP_UPLOAD_FILE.put(lable_video)
                                    # config.ALARM_DATA_QUEUE.append(data)
                                    if len(config.ALARM_SESSION) > 0:
                                        # send alarm data to the client
                                        index_list = []
                                        for session in config.ALARM_SESSION:
                                            # sendData = msg
                                            sendData = json.dumps({
                                                "roomId": config.Inquest_Room,
                                                "data": {
                                                    "roomId": config.Inquest_Room,
                                                    "uuid": config.inquest_uuid,
                                                    "recordTime": data.get('time_node'),
                                                    "case_type": data.get('case_type'),
                                                    "suspiciousValue": data.get('suspicious_value'),
                                                    "signStatus": data.get('body_status'),
                                                    "emoticonStatus": data.get('emotion_status'),
                                                    "expression": data.get('total_status'),
                                                    "opinion": data.get('inquest_result'),
                                                    "alarmVideo": data.get('video_path'),
                                                    "timeStamp": data.get('timeStamp'),
                                                    "mainExpression": data.get('emotion_degree'),
                                                    "mainExpressionNum": data.get('emotion_degree_count')
                                                }
                                            })
                                            try:
                                                sendMessage(sendData, session)
                                            except Exception as e:
                                                index_list.append(config.ALARM_SESSION)
                                        # clear broken connection
                                        if index_list:
                                            for index in index_list:
                                                del config.ALARM_SESSION[index]

                                    config.alarm_data_count.append(data)
                                    config.all_alarm_count.append(data)
                                    all_video_path.append(self.alarm_video_path)
                                    QuestionRecord.add_opt(config.inquest_uuid, question_uuid='', question_text='',
                                                           body_status=body_status.replace("、", " "),
                                                           emotion_status=emotion_status,
                                                           total_status=total_status, emotion_count='', heart_count='',
                                                           emotion_show='', heart_show='',
                                                           start_time=config.ALARM_START_TIME,
                                                           stop_time=alarm_stop_time, time_node=time_node,
                                                           case_type=case_type, inquest_result=inquest_result,
                                                           suspicious_value=suspicious_value, answer='',
                                                           video_path=self.alarm_video_path.replace("\\", "/"),
                                                           emotion_degree=show_emotion[0],
                                                           emotion_degree_count=show_emotion[1], timeStamp=alarm_time)
                                    if VIEW_CFG.get("interaction", 0) == 1:
                                        try:
                                            conn, alarm_channel = self.init_alarm_queue()
                                            if alarm_channel:
                                                alarm_channel.basic_publish(
                                                    exchange="",  # 交换机
                                                    routing_key=RabbitMQ_alarm_queue,  # 需要绑定的队列
                                                    body=msg
                                                )
                                                conn.close()
                                                config.LOG.debug("告警数据传输成功@1——————————————")
                                            else:
                                                config.LOG.debug("告警数据传输失败@1——————————————")
                                        except Exception as e:
                                            config.LOG.debug(
                                                "RabbitMQ_alarm_queue is failed==={}!!!!!!!!!!!!!!!@1".format(e))
                                else:
                                    bad_video.append(self.alarm_video_path)
                            except Exception as e:
                                bad_video.append(self.alarm_video_path)
                                config.LOG.debug("{}".format(e))
                            config.ALARM_RECORDING_STATUS = False
                            config.ALARM_START_TIME = None
                        else:
                            config.ALARM_RECORDING_STATUS = False
                            config.ALARM_START_TIME = None
                            bad_video.append(self.alarm_video_path)
                elif (window_time * 6 * 5) > alarm_time_delta > (window_time * 6):
                    config.LOG.debug("告警录制时长 %s" % alarm_time_delta)
                    length = int(alarm_time_delta // (window_time * 6))
                    modulo = alarm_time_delta % (window_time * 6)
                    riskList = list(config.SUSPICIOUS_VALUE_QUEUE)
                    if modulo >= (window_time * 6 / 2) / 10:
                        rem = len(riskList) - length - 1
                    else:
                        rem = len(riskList) - length
                    if len(riskList) == 0:
                        suspicious_value = 0
                    else:
                        suspicious_value = int(sum(riskList[rem:]) / len(riskList[rem:]))
                        config.LOG.debug("告警可疑值单元数 {}".format(riskList[rem:]))
                    self.video_record_obj.stop_record(self.alarm_video_path)

                    config.LOG.debug(f'告警视频录制完成[{self.alarm_video_path}]')
                    # 告诉bm结束录制视频
                    self.bm_stop_record()

                    alarm_stop_time = now
                    if 0 <= suspicious_value <= 50:
                        bad_video.append(self.alarm_video_path)
                        try:
                            if os.path.exists(self.alarm_video_path):
                                config.LOG.debug("else可疑值小于规定范围，删除此条记录")
                                time.sleep(0.5)
                                os.remove(r"{}".format(self.alarm_video_path))
                        except Exception as e:
                            config.LOG.debug("else可疑值小于规定范围，删除此条记录错误提示=={}".format(e))
                        QuestionRecord.add_opt(config.inquest_uuid, question_uuid='', question_text='',
                                               body_status="'心率正常、声强正常'", emotion_status='平和、高兴、惊讶',
                                               total_status='配合', emotion_count='', heart_count='',
                                               emotion_show='', heart_show='',
                                               start_time=config.ALARM_START_TIME,
                                               stop_time=alarm_stop_time, time_node='-'.join(
                                [time.strftime('%X', time.localtime(config.ALARM_START_TIME)),
                                 time.strftime('%X', time.localtime(alarm_stop_time))]),
                                               case_type='告警记录', inquest_result='正常回答',
                                               suspicious_value=suspicious_value, answer='',
                                               video_path=self.alarm_video_path.replace("\\", "/"), emotion_degree='',
                                               emotion_degree_count=0, timeStamp=0)
                        data = {
                            "total_status": '配合'
                        }
                        config.all_alarm_count.append(data)
                        config.ALARM_START_TIME = None
                        config.ALARM_RECORDING_STATUS = False
                        return
                    if 50 < suspicious_value < 75:
                        total_status = '恐慌'
                        body_status = '心率较高、声强渐低'
                        emotion_status = '伤心、害怕、平和'
                        inquest_result = '可疑回答'
                        time_node = '-'.join(
                            [time.strftime('%X', time.localtime(config.ALARM_START_TIME)),
                             time.strftime('%X', time.localtime(alarm_stop_time))])
                        case_type = '告警记录'
                    else:
                        # total_status = random.choice(['侥幸', '抵触'])
                        if suspicious_value % 2 == 0:
                            total_status = "侥幸"
                        else:
                            total_status = "抵触"
                        if total_status == '抵触':
                            total_status = '抵触'
                            body_status = '心率较高、声强渐低'
                            emotion_status = '轻蔑、厌恶、惊讶、生气'
                            inquest_result = '可疑回答'
                            time_node = '-'.join(
                                [time.strftime('%X', time.localtime(config.ALARM_START_TIME)),
                                 time.strftime('%X', time.localtime(alarm_stop_time))])
                            case_type = '告警记录'
                        else:
                            total_status = '侥幸'
                            body_status = '心率较高、声强正常'
                            emotion_status = '平和、轻蔑'
                            inquest_result = '可疑回答'
                            time_node = '-'.join(
                                [time.strftime('%X', time.localtime(config.ALARM_START_TIME)),
                                 time.strftime('%X', time.localtime(alarm_stop_time))])
                            case_type = '告警记录'
                    config.LOG.debug("列表显示可疑值数== {}".format(suspicious_value))
                    alarm_now = round(config.ALARM_START_TIME, 3)
                    alarm_now = str("%.3f" % (alarm_now)).split('.')
                    try:
                        alarm_time = int(alarm_now[0] + alarm_now[1])
                    except Exception as e:
                        config.LOG.error("elif 时间转换失败===={}".format(e))
                        alarm_time = 1577808000
                    if suspicious_value > 100:
                        suspicious_value = 100
                    if suspicious_value > 0 and config.ALARM_START_TIME:
                        data = {
                            "uuid": config.inquest_uuid,
                            'time_node': time_node,
                            'case_type': case_type,
                            'suspicious_value': suspicious_value,
                            'body_status': body_status.replace("、", " "),
                            'emotion_status': emotion_status,
                            'total_status': total_status,
                            'inquest_result': inquest_result,
                            'video_path': self.alarm_video_path.replace("\\", "/"),
                            'emotion_degree': show_emotion[0],
                            'emotion_degree_count': show_emotion[1],
                            'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                            'timeStamp': alarm_time
                        }

                        msg = json.dumps({
                            "roomId": config.Inquest_Room,
                            "data": {
                                "roomId": config.Inquest_Room,
                                "uuid": config.inquest_uuid,
                                "recordTime": time_node,
                                "case_type": case_type,
                                "suspiciousValue": suspicious_value,
                                "signStatus": body_status.replace("、", " "),
                                "emoticonStatus": emotion_status,
                                "mainExpression": show_emotion[0],
                                "mainExpressionNum": show_emotion[1],
                                "expression": total_status,
                                "opinion": inquest_result,
                                "alarmVideo": self.video_name,
                                "timeStamp": alarm_time
                            }
                        })
                        try:
                            if os.path.exists(self.alarm_video_path) and cv2.VideoCapture(
                                    self.alarm_video_path).isOpened():
                                # TODO FTP上传到服务器
                                # lable_video = {"path": self.alarm_video_path, "lable": False}
                                # config.FTP_UPLOAD_FILE.put(lable_video)
                                # config.ALARM_DATA_QUEUE.append(data)
                                if len(config.ALARM_SESSION) > 0:
                                    # send alarm data to the client
                                    index_list = []
                                    for session in config.ALARM_SESSION:
                                        sendData = json.dumps({
                                            "roomId": config.Inquest_Room,
                                            "data": {
                                                "roomId": config.Inquest_Room,
                                                "uuid": config.inquest_uuid,
                                                "recordTime": data.get('time_node'),
                                                "case_type": data.get('case_type'),
                                                "suspiciousValue": data.get('suspicious_value'),
                                                "signStatus": data.get('body_status'),
                                                "emoticonStatus": data.get('emotion_status'),
                                                "expression": data.get('total_status'),
                                                "opinion": data.get('inquest_result'),
                                                "alarmVideo": data.get('video_path'),
                                                "timeStamp": data.get('timeStamp'),
                                                "mainExpression": data.get('emotion_degree'),
                                                "mainExpressionNum": data.get('emotion_degree_count')
                                            }
                                        })
                                        # sendData = msg
                                        try:
                                            sendMessage(sendData, session)
                                        except Exception as e:
                                            index_list.append(config.ALARM_SESSION)
                                    # clear broken connection
                                    if index_list:
                                        for index in index_list:
                                            del config.ALARM_SESSION[index]

                                config.alarm_data_count.append(data)
                                config.all_alarm_count.append(data)
                                all_video_path.append(self.alarm_video_path)
                                QuestionRecord.add_opt(config.inquest_uuid,
                                                       question_uuid='', question_text='',
                                                       body_status=body_status.replace("、", " "),
                                                       emotion_status=emotion_status,
                                                       total_status=total_status,
                                                       emotion_count='', heart_count='',
                                                       emotion_show='', heart_show='',
                                                       start_time=config.ALARM_START_TIME,
                                                       stop_time=alarm_stop_time,
                                                       time_node=time_node,
                                                       case_type=case_type,
                                                       inquest_result=inquest_result,
                                                       suspicious_value=suspicious_value,
                                                       answer='',
                                                       video_path=self.alarm_video_path.replace("\\", "/"), emotion_degree=show_emotion[0],
                                                       emotion_degree_count=show_emotion[1], timeStamp=alarm_time)
                                if VIEW_CFG.get("interaction", 0) == 1:
                                    try:
                                        conn, alarm_channel = self.init_alarm_queue()
                                        if alarm_channel:
                                            alarm_channel.basic_publish(
                                                exchange="",  # 交换机
                                                routing_key=RabbitMQ_alarm_queue,  # 需要绑定的队列
                                                body=msg
                                            )
                                            conn.close()
                                            config.LOG.debug("告警数据传输成功@2——————————————")
                                        else:
                                            config.LOG.debug("告警数据传输失败@2——————————————")
                                    except Exception as e:
                                        config.LOG.debug(
                                            "RabbitMQ_alarm_queue is failed===={}!!!!!!!!!!!!!!!@2".format(e))
                            else:
                                bad_video.append(self.alarm_video_path)
                        except Exception as e:
                            bad_video.append(self.alarm_video_path)
                            config.LOG.debug("{}".format(e))
                        config.ALARM_RECORDING_STATUS = False
                        config.ALARM_START_TIME = None
                    else:
                        config.ALARM_RECORDING_STATUS = False
                        config.ALARM_START_TIME = None
                        bad_video.append(self.alarm_video_path)
                        try:
                            if os.path.exists(self.alarm_video_path):
                                config.LOG.debug("告警可疑值为零，成功删除此纪录")
                                time.sleep(0.5)
                                os.remove(r"{}".format(self.alarm_video_path))
                        except Exception as e:
                            config.LOG.debug("告警可疑值为零，删除此纪录错误提示=={}".format(e))
                elif alarm_time_delta > (window_time * 6 * 5):
                    # self.video_record_obj.stop_record()
                    bad_video.append(self.alarm_video_path)
                    config.ALARM_START_TIME = None
                    config.ALARM_RECORDING_STATUS = False
                    try:
                        if os.path.exists(self.alarm_video_path):
                            config.LOG.debug("超出时间范围，删除此条记录")
                            time.sleep(0.5)
                            os.remove(r"{}".format(self.alarm_video_path))
                    except Exception as e:
                        config.LOG.debug("超出时间范围，删除此条记录错误提示=={}".format(e))


if __name__ == '__main__':
    pass
