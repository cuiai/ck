import time
import threading
from application.controller import config
from application.model.model_data import QuestionRecord, InquestRecord


class HistoryDetail(threading.Thread):
    def __init__(self, uuid):
        super(HistoryDetail, self).__init__()
        self.setDaemon(True)
        self.setName("HistoryDetail")
        self.is_exit = False
        self.len = 1
        self.time = None
        self.uuid = uuid
        self.count_len()

    def run(self):
        self.get_time_func()
        print("发送历史详情数据线程开启")
        while True:
            if self.is_exit:
                config.LOG.debug("发送历史详情数据线程关闭............")
                config.hd_thread = None
                break
            if config.IS_STOP is True:
                config.DETAIL_DATA.queue.clear()
                time.sleep(0.01)
                continue
            if config.DETAIL_DATA.qsize() >= 200:
                time.sleep(0.02)
                continue
            startTime = config.PLAYSTART
            # 传参的开始时间为记录的开始时间
            if startTime == 0:
                startTime = config.LATES_TS
            else:
                config.PLAYSTART = 0
            try:
                self.read_data_from_mongodb(startTime)
            except Exception as e:
                pass
        if config.DETAIL_DATA.qsize() > 0:
            # config.DETAIL_DATA.queue.clear()
            config.IS_STOP = False
            config.PLAYSTART = 0
            config.LATES_TS = 0

    def count_len(self):
        if self.uuid:
            documents_ = config.MONGODB_COLLECTION_FOR_READ.find({
                'inquest_uuid': self.uuid
            })
            self.len = documents_.count()

    def get_time_func(self):
        ret = InquestRecord.get_one_record(self.uuid)
        if ret:
            startTime = ret[0][3]
            endTime = ret[0][4]
            seconds = startTime - endTime
            self.time = seconds/self.len

    # 获取审讯详情的告警
    @staticmethod
    def get_alarm(data):
        uuid = data.get('uuid', '')
        all_question = QuestionRecord.get_objects_by_inquest_uuid_start_time(inquest_uuid=uuid)
        list_ = []
        for question in all_question:
            sendData = {
                "roomId": config.Inquest_Room,
                "data": {
                    "roomId": config.Inquest_Room,
                    "uuid": uuid,
                    "recordTime": question.time_node,
                    "case_type": question.case_type,
                    "suspiciousValue": question.suspicious_value,
                    "signStatus": question.body_status,
                    "emoticonStatus": question.emotion_status,
                    "expression": question.total_status,
                    "opinion": question.inquest_result,
                    "alarmVideo": question.video_path,
                    "timeStamp": question.timeStamp,
                    "mainExpression": question.emotion_degree,
                    "mainExpressionNum": question.emotion_degree_count,
                    "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                }
            }
            list_.append(sendData)
        return list_

    # 获取审讯详情的算法数据
    def read_data_from_mongodb(self, start_time):
        print("start_time: ", start_time)
        documents = config.MONGODB_COLLECTION_FOR_READ.find({
            'inquest_uuid': self.uuid,
            'timestamp': {
                '$gt': start_time
            }
        }).limit(35)
        if documents.count() <= 0:
            print("documents.count() == ", documents.count())

            # time.sleep(0.02)
            self.is_exit = True
            config.hd_thread = None
            return
        for document in documents:
            if config.IS_STOP is True:
                break
            emotion_data = document.get('emotion_data')
            period = document.get('period')
            heart_rate_data = document.get('heart_rate_data')
            voice_data = document.get('voice_data')
            au_data = document.get('au_data')
            au_class = document.get('au_class')
            suspicious_value = document.get('suspicious_value')
            timestamp = document.get('timestamp')
            # print("mongo timestamp:", timestamp)

            tmp_list = {
                "emotion_data": emotion_data,
                "period": period,
                "heart_rate_data": heart_rate_data,
                "voice_data": voice_data,
                "au_data": au_data,
                "au_class": au_class,
                "timestamp": timestamp,
                "suspicious_value": suspicious_value
            }

            config.DETAIL_DATA.put(tmp_list)
            if self.time:
                time.sleep(self.time)
            config.LATES_TS = document.get('timestamp')
