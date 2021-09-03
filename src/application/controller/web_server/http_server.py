import socket
import re, json
import time
from threading import Thread
from application.controller import config
from application.controller.config import CFG, LOG
from application.controller.detail.history_data import HistoryDetail
from application.controller.web_server.server_logic import Inquest


class HttpServer(Thread):
    def __init__(self):
        super(HttpServer, self).__init__()
        self.setDaemon(True)
        self.http_ip = CFG.get("http_ip", '127.0.0.1')
        self.http_port = CFG.get("http_port", 8080)
        # self.http_ip = '192.168.16.106'
        # self.http_port = 8080
        self.pas = None
        self.addr = None
        self.server = None
        self.client = None
        self.is_exit = False
        self.person_info = Inquest()
        self.connect()

    def exit(self):
        self.is_exit = True

    def connect(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(
                      socket.SOL_SOCKET,
                      socket.SO_RCVBUF,
                      4096)
        self.server.bind((self.http_ip, self.http_port))
        self.server.listen(20)


    def run(self):
        self.pas = re.compile("{.*}")
        LOG.info("HTTP服务线程启动................")
        while True:
            try:
                if self.is_exit is True:
                    LOG.info("HTTP服务线程开始................")
                    return
                self.client, self.addr = self.server.accept()
                t1 = Thread(target=self.recv_, args=(self.client, self.addr, self.person_info))
                t1.setDaemon(True)
                t1.start()
                # TODO [Test]
                LOG.info("HTTP服务线程开始................")
            except Exception as e:
                config.LOG.error("HTTP服务线程异常")
                LOG.error(e)


    @staticmethod
    def recv_(client,addr,person_info):
        pas = re.compile("{.*}")
        lenth_ = b""
        LOG.debug("Accepted connection from: %s:%d" % (addr[0], addr[1]))
        while True:
            sentence = client.recv(2048)
            lenth_ += sentence
            if 'Content-Type' not in sentence.decode('utf-8'):
                LOG.info(sentence.decode('utf-8'))
                break
            print(len(sentence) > 300)
            if len(sentence) == 0 or len(sentence) > 300:
                LOG.info(str(len(sentence) ))
                break
        # try:
        # print(lenth_)
        if lenth_ == b'':
            LOG.info(str(len(lenth_)))
            return
        filename = lenth_.split()[1]
        LOG.debug(lenth_.decode('utf-8'))
        try:
            data = json.loads(re.search(pas, lenth_.decode()).group())
            print(data)
        except Exception as e:
            # LOG.debug("数据解析异常，等待数据再次解析......>>>{}".format(e))
            try:
                allay = lenth_.decode('utf-8').replace('\r', '').replace('\n', '').replace('\t', '')
                data = json.loads(re.findall(pas, allay)[0])
            except Exception as e:
                data = {}
                # LOG.error("数据再次解析失败......>>>{}".format(e))

        length = len(filename.decode('utf-8').split('/'))
        if length != 3:
            record = {"success": "false", "status": 500, "msg": "url出现错误"}
            HttpServer._client_(client, record)
            LOG.error("请求url不正确.........")
        name = filename.decode('utf-8').split('/')[2]
        if name == 'start_inquest' and len(data) == 0:
            record = {"success": "false", "status": 500, "msg": "未查找到请求参数"}
            HttpServer._client_(client, record)
            LOG.error("开始请求参数不正确.........")
            return
        LOG.debug("url：{} \n request：{}".format(name, data))
        if name == 'start_inquest':
            if config.report_ is True:
                record = {"success": "false", "status": 500, "msg": "正在生成报告，警告！！！"}
                HttpServer._client_(client, record)
                LOG.debug("start_inquest end")
                return
            if config.MONGOD_ != 0:
                record = {"success": "false", "status": 500, "msg": "mongodb服务未开启，警告！！！"}
                HttpServer._client_(client, record)
                LOG.debug("start_inquest end")
                return
            if config.DISK_FREE <= 1:
                record = {"success": "false", "status": 500, "msg": "磁盘空间不足，警告！！！"}
                HttpServer._client_(client, record)
                LOG.debug("start_inquest end")
                return
            if config.videoStream_obj is False:
                record = {"success": "false", "status": 500, "msg": "摄像头连接失败，警告！！！"}
                HttpServer._client_(client, record)
                LOG.debug("start_inquest end")
                return
            if not config.inquest_status:
                config.SOCKET_SERVER = True
                Thread(target=person_info.start_inquest, args=(data,)).start()
                HttpServer._client_(client)
            else:
                record = {"success": "false", "status": 500, "msg": "正在审讯中，警告！！！"}
                HttpServer._client_(client, record)
            LOG.debug("start_inquest end")
        # 停止审讯
        elif name == "stop_inquest":
            if person_info and config.inquest_status:
                config.SOCKET_SERVER = False
                person_info.stop_inquest()
                HttpServer._client_(client)
                config.get_report = None
                # person_info.get_alarm.cache_clear()
            else:
                record = {"success": "false", "status": 500, "msg": "未开启审讯，警告！！！"}
                HttpServer._client_(client, record)
            LOG.debug("stop_inquest end")
        # 关闭客户端
        elif name == "stop_cs":
            if person_info and config.inquest_status:
                record = {"success": "false", "status": 500, "msg": "正在审讯中，请先结束审讯"}
                HttpServer._client_(client, record)
            elif person_info.stop_cs():
                record = {"success": "true", "status": 200, "msg": "审讯报告结束"}
                HttpServer._client_(client, record)
            else:
                record = {"success": "false", "status": 500, "msg": "审讯报告正在生成，请稍后关闭"}
                HttpServer._client_(client, record)
            LOG.debug("stop_cs end")
        # 心跳接口
        elif name== "query_status":
            HttpServer._client_(client)
        # 审讯记录库列表页
        elif name == "inquestList":
            if len(data) == 0:
                record = {"success": "false", "status": 400, "msg": f"未查找到请求参数 + {data}"}
                HttpServer._client_(client, record)
                LOG.error("inquestList request parameter error <end>")
                return
            filter_date = data.get("inquestTime", "")
            filter_ask_name = data.get("inquester", None)
            filter_be_ask_name = data.get("inquestee", None)
            filter_be_ask_id_number = data.get("IDNumber", None)
            pageNum = int(data.get("pageNum", 1))
            pageSize = int(data.get("pageSize", 10))
            record = Inquest.inquest_record(filter_date, filter_ask_name, filter_be_ask_name, filter_be_ask_id_number, pageNum, pageSize)
            HttpServer._client_(client, record)
            LOG.debug("inquestList end")
        elif name == "removeInquest":
            # 重置审讯记录库的缓存
            Inquest.inquest_record.cache_clear()
            # 删除审讯记录
            record = Inquest.inquest_delete(data)
            if record:
                HttpServer._client_(client)
            else:
                record = {"success": "false", "status": 500, "msg": "删除此纪录失败，警告！！！"}
                HttpServer._client_(client, record)
            LOG.debug("removeInquest end ")
        # 开始审讯记录算法播放
        elif name == "playAlg":
            startTs = data.get("ts", None)
            # 客户端传入13位
            if isinstance(startTs, int) or isinstance(startTs, float):
                config.PLAYSTART = startTs/1000

            uuid = data.get("uuid", None)
            if not config.hd_thread:
                config.DETAIL_DATA.queue.clear()
                config.hd_thread = HistoryDetail(uuid)
                config.hd_thread.start()
            else:
                # 将uuid1传入到线程中
                config.hd_thread.uuid = uuid
                # 清空队列里面的数据
                config.DETAIL_DATA.queue.clear()
            config.IS_STOP = False
            HttpServer._client_(client)
            LOG.debug("playAlg end ")
        # 暂停审讯记录算法播放
        elif name == "pauseAlg":
            config.IS_STOP = True
            config.DETAIL_DATA.queue.clear()
            config.LOG.debug("暂停发送历史详情数据............")
            HttpServer._client_(client)
            LOG.debug("pauseAlg end ")
        # 结束审讯记录算法播放
        elif name == "stopAlg":
            # 结束审讯记录算法线程
            config.DETAIL_DATA.queue.clear()
            if config.hd_thread:
                config.hd_thread.is_exit = True
                config.hd_thread = None
            HttpServer._client_(client)
            LOG.debug("stopAlg end ")
        elif name == "open_report":
            report_path = data.get("report_path", "")
            record = ""
            if report_path:
                record = Inquest.openReport(data)

            HttpServer._client_(client, record)
        elif name == "check_mongo":
            if config.MONGOD_ != 0:
                record = {"success": "false", "status": 500, "msg": "mongodb服务未开启，警告！！！"}
                HttpServer._client_(client, record)
                return
            else:
                HttpServer._client_(client)
        elif name == "check_disk":
            config.LOG.debug("磁盘使用率： {}，磁盘可用空间： {}，活动线程数量： {}".format(config.DISK_RATE,config.DISK_FREE,data))
            record = {"success": "true", "status": 200, "result": {"rate": config.DISK_RATE, "free": config.DISK_FREE}}
            HttpServer._client_(client, record)
            LOG.debug("check_disk end ")
        # elif name == "keepAliveAlg":
        #     if not config.ALG_STATUS:
        #         record = {"success": "false", "status": 500, "msg": "未解析到算法数据，请查看摄像头"}
        #         HttpServer._client_(client, record)
        #     else:
        #         record = {"success": "true", "status": 200, "msg": " keepAliveAlg success"}
        #         HttpServer._client_(client, record)
        elif name == "getInquestAlarmData":
            uuid = data.get('uuid', '')
            pageNum = data.get('pageNum', None)
            pageSize = data.get('pageSize', None)
            ret = person_info.get_alarm(uuid, pageNum, pageSize)
            record = {"success": "true", "status": 200, "msg": "success", "obj": ret}
            HttpServer._client_(client, record)
            LOG.debug("getInquestAlarmData end ")
        elif name == "faceMaskControl":
            poses = data.get('poses', True)
            face = data.get('face', True)
            gaze = data.get('gaze', True)
            eyes = data.get('eyes', True)
            if poses or face or gaze or eyes:
                config.NAME_THREADS['put_frame'].pub_v = config.PUB_V
            else:
                config.NAME_THREADS['put_frame'].pub_v = 25
            config.IS_3D_MASK_DRAW = face
            config.IS_HEAD_POSE_ESTIMATION_DRAW = poses
            config.IS_EYE_POSE_ESTIMATION_DRAW = gaze
            config.IS_EYE_3D_MODEL_DRAW = eyes

            record = {"success": "true", "status": 200, "msg": "success"}
            HttpServer._client_(client, record)
            LOG.debug("faceMaskContro end ")
        else:
            HttpServer._client_(client)
        # except Exception as e:
        #     record = {"success": "false", "status": 500, "msg": "服务解析出错！！！"}
        #     HttpServer._client_(client, record)
        #     LOG.error("http请求访问失败......>>>{}".format(e))

    @staticmethod
    def _status_(result=None):
        info = json.dumps({"success": "true", "status": 200})
        if result:
            info = json.dumps(result, ensure_ascii=False)
        header = "HTTP/1.1 200 OK\r\nContent-type: text/html\r\n\r\n" + info
        return header.encode()

    @staticmethod
    def _client_(client, record=None):
        try:
            client.send(HttpServer._status_(record))
            client.close()
        except Exception as e:
            LOG.error("数据发送失败： {}".format(e))


if __name__ == '__main__':
    test = HttpServer()
    test.start()
