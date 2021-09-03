# coding: utf-8
import time
import socket
import struct
import threading, json
import hashlib, base64
import asyncio

import requests

from application.controller import config
from application.controller.config import connectionlist, LOG, CFG
from application.controller.web_server.server_logic import Inquest


from application.controller.tools.utils import NumpyEncoder
# 调用socket的send方法发送str信息给web端
from application.model.model_data import InquestRecord


def sendMessage(msg, connection):
    send_msg = b""
    send_msg += b"\x81"
    back_str = []
    back_str.append('\x81')
    data_length = len(msg.encode())
    # 数据长度的三种情况
    if data_length <= 125:
        send_msg += str.encode(chr(data_length))
    elif data_length <= 65535:
        send_msg += struct.pack("b", 126)
        send_msg += struct.pack(">h", data_length)
    elif data_length <= (2 ^ 64 - 1):
        send_msg += struct.pack("b", 127)
        send_msg += struct.pack(">q", data_length)
    else:
        LOG.info(u'数据传输量过大..................')
    send_message = send_msg + msg.encode("utf-8")
    if send_message != None and len(send_message) > 0:
        try:
            connection.send(send_message)
        except Exception as e:
            LOG.info(e)
            pass


# 定义WebSocket对象(基于线程对象)
class WebSocket(threading.Thread):
    def __init__(self, conn, index, name, remote,path=""):
        # 初始化线程
        threading.Thread.__init__(self)
        # 初始化数据,全部存储到自己的数据结构中self
        self.is_exit = False
        self.conn = conn
        self.index = index
        self.name = name
        self.remote = remote
        self.path = path
        self.GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        self.buffer = ""
        self.client_name = ""
        self.buffer_utf8 = b""
        self.length_buffer = 0
        self.g_code_length = 0
        self.g_header_length = 0

        # 计算10分钟是否有人脸
        self.no_face_time = None

        self.detail_thread = None

    def generate_token(self, WebSocketKey):
        WebSocketKey = WebSocketKey + self.GUID
        Ser_WebSocketKey = hashlib.sha1(WebSocketKey.encode(encoding='utf-8')).digest()
        WebSocketToken = base64.b64encode(Ser_WebSocketKey)  # 返回的是一个bytes对象
        return WebSocketToken.decode('utf-8')

    # 运行线程
    def run(self):
        # Log输出,套接字index启动
        LOG.info("websocket {} 套接字启动 -------->".format(self.index))
        self.handshaken = False  # Socket是否握手的标志,初始化为false
        while True:
            if self.is_exit:
                break
            if self.handshaken == False:  # 如果没有进行握手
                self.buffer = self.conn.recv(4096).decode(
                    'utf-8')
                LOG.info("INFO: Socket %s self.buffer is {%s}" % (self.index, self.buffer))
                try:
                    self.client_name = self.buffer.split("/")[2]
                except Exception as e:
                    pass
                if self.buffer.find('\r\n\r\n') != -1:
                    headers = {}
                    header, data = self.buffer.split('\r\n\r\n', 1)
                    for line in header.split("\r\n")[1:]:
                        key, value = line.split(": ", 1)
                        headers[key] = value
                    try:
                        WebSocketKey = headers["Sec-WebSocket-Key"]
                    except KeyError:
                        LOG.debug("Socket %s Handshaken Failed!" % (self.index))
                        self.deleteconnection(str(self.index))
                        self.conn.close()
                        break
                    WebSocketToken = self.generate_token(WebSocketKey)
                    headers["Location"] = ("ws://%s%s" % (headers["Host"], self.path))
                    handshake = "HTTP/1.1 101 Switching Protocols\r\n" \
                                "Connection: Upgrade\r\n" \
                                "Sec-WebSocket-Accept: " + WebSocketToken + "\r\n" \
                                                                            "Upgrade: websocket\r\n\r\n"
                    self.conn.send(handshake.encode(encoding='utf-8'))
                    self.handshaken = True
                    self.g_code_length = 0
                else:
                    LOG.debug("websocket 请求头接收错误， 关闭服务！！！！！")
                    self.deleteconnection(str(self.index))
                    self.conn.close()
                    break
            else:
                try:
                    self.buffer_utf8 = self.conn.recv(4096)
                except Exception as e:
                    self.is_exit = True
                    LOG.debug("ws已断开==============================")
                    self.deleteconnection(str(self.index))
                    self.conn.close()
                    break
                LOG.info("self.g_code_length:   {}".format(self.g_code_length))
                LOG.info("INFO Line 204: Recv信息 %s,长度为 %d:" % (self.buffer_utf8, len(self.buffer_utf8)))
                if not self.buffer_utf8:
                    break
                # 报错 b'\x82\xbc\xb2\x9f\t\xff\xc9\xbd}\x86\xc2\xfa+\xc5\x90\xfee\x98\x90\xb3+\x8a\xc7\xf6m\xdd\x88\xbd;\xca\x83\xa8l\xcd\x81\xa9$\x9e\xd6\xaa=\xd2\x83\xael\x9e\x9f\xa6=\xcd\xd3\xb2;\x9c\xd4\xfbh\xce\x85\xadj\xcc\x8b\xa9+\x82\x88\x82\xa5n\x9d\xf6\xa6\x86'
                #
                try:
                    recv_message = self.parse_data(self.buffer_utf8)
                except UnicodeDecodeError as e:
                    self.deleteconnection(str(self.index))
                    self.conn.close()
                    break
                if not recv_message:
                    self.deleteconnection(str(self.index))
                    self.conn.close()
                LOG.debug("接口名：{} ，收到数据： {}".format(self.client_name, recv_message))
                if self.client_name == "quit":
                    LOG.debug("Socket %s Logout!" % (self.index))
                    self.deleteconnection(str(self.index))
                    self.conn.close()
                # 实时算法数据
                elif self.client_name == "client":
                    t1 = threading.Thread(target=self.send1, args=(self.client_name,))
                    t1.setDaemon(True)
                    t1.start()
                elif self.client_name == "alarm":
                    # t2 = threading.Thread(target=self.send1, args=(self.client_name,))
                    # t2.setDaemon(True)
                    # t2.start()
                    config.ALARM_SESSION.append(self.conn)
                elif self.client_name == "detail":
                    print(recv_message)
                    try:
                        uuid = json.loads(recv_message).get("uuid")
                        messtype = json.loads(recv_message).get("type")
                    except Exception as e:
                        LOG.error("detail 参数错误")
                        sendMessage("400", self.conn)
                        continue
                    if self.detail_thread:
                        pass

                    # 计算算法推送的时间
                    block_time = InquestRecord.get_inquest_time(uuid)
                    data_count = config.MONGODB_COLLECTION_FOR_READ.find({
                        'inquest_uuid': uuid
                    }).count()
                    if data_count == 0:
                        LOG.error("uuid <{}> not found data".format(uuid))
                        sendMessage("400", self.conn)
                        continue
                    sleep_time = block_time / data_count
                    t3 = threading.Thread(target=self.send2, args=(messtype,sleep_time))
                    t3.setDaemon(True)
                    t3.start()
                self.g_code_length = 0
                self.length_buffer = 0
                self.buffer_utf8 = b""

    def get_datalength(self, msg):
        try:
            self.g_code_length = msg[1] & 127
        except Exception as e:
            self.g_code_length = 1
            LOG.error(e)
        if self.g_code_length == 126:
            self.g_code_length = struct.unpack('>H', msg[2:4])[0]
            self.g_header_length = 8
        elif self.g_code_length == 127:
            self.g_code_length = struct.unpack('>Q', msg[2:10])[0]
            self.g_header_length = 14
        else:
            self.g_header_length = 6
        self.g_code_length = int(self.g_code_length)
        return self.g_code_length

    def parse_data(self, msg):
        self.g_code_length = msg[1] & 127
        if self.g_code_length == 126:
            self.g_code_length = struct.unpack('>H', msg[2:4])[0]
            masks = msg[4:8]
            data = msg[8:]
        elif self.g_code_length == 127:
            self.g_code_length = struct.unpack('>Q', msg[2:10])[0]
            masks = msg[10:14]
            data = msg[14:]
        else:
            masks = msg[2:6]
            data = msg[6:]
        en_bytes = b""
        cn_bytes = []
        for i, d in enumerate(data):
            nv = chr(d ^ masks[i % 4])
            nv_bytes = nv.encode()
            nv_len = len(nv_bytes)
            if nv_len == 1:
                en_bytes += nv_bytes
            else:
                en_bytes += b'%s'
                cn_bytes.append(ord(nv_bytes.decode()))
        if len(cn_bytes) > 2:
            cn_str = ""
            clen = len(cn_bytes)
            count = int(clen / 3)
            for x in range(count):
                i = x * 3
                b = bytes([cn_bytes[i], cn_bytes[i + 1], cn_bytes[i + 2]])
                cn_str += b.decode()
            new = en_bytes.replace(b'%s%s%s', b'%s')
            new = new.decode()
            res = (new % tuple(list(cn_str)))
        else:
            res = en_bytes.decode()
        return res

    def deleteconnection(self, item):
        del connectionlist['connection' + item]
    @staticmethod
    def set_heart(heart):
        fakeHeartbeatCnt = config.heartbeatCnt % 10
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
        config.heartbeatCnt += 1
        if config.heartbeatCnt >= 1000:
            config.heartbeatCnt = 0
        return new_heart

    @staticmethod
    def is_zero(num):
        if num:
            return True
        else:
            return False

    @staticmethod
    def set_zero(items):
        if isinstance(items,list):
            zero_list = []
            for i in range(0,len(items)):
                zero_list.append(0)
            return zero_list
        elif isinstance(items, tuple):
            zero_tuple = ()
            for i in range(0, len(items)):
                zero_tuple+=(0,)
            return zero_tuple
        else:
            return items

    def send1(self, mess):

        while True:
            if self.is_exit:
                print("is_exit退出")
                break
            if not config.SOCKET_SERVER:
                break
            if config.inquest_status and config.inquest_data:
                now = time.time()
                if mess == 'client':
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
                    )
                    add_aus_reg = config.API_AU_DATA_INTENSITIES
                    if len(add_aus_reg) < 16:
                        add_aus_reg.insert(16, 3.5)
                    aus_class = [round(float(ac), 2) for ac in config.API_AU_DATA_OCCURRENCE]
                    aus_reg = [round(float(ar), 2) for ar in add_aus_reg]
                    round_now = round(now, 3)
                    round_now = str("%.3f" % (round_now)).split('.')
                    try:
                        # 转换为毫秒单位
                        tran_time = int(round_now[0] + round_now[1])
                    except Exception as e:
                        config.LOG.error("时间转换失败===={}".format(e))
                        tran_time = now
                    if aus_reg:
                        aus_reg = aus_reg[:16]

                    # 视频分辨率
                    shape = config.STREAM_SHAPE

                    # 3d面罩
                    points = config.WS_3D_MARK_DATA['points']  # 3D Mask
                    line_left = config.WS_3D_MARK_DATA['line_left']  # 左眼眼线
                    line_right = config.WS_3D_MARK_DATA['line_right']  # 右眼眼线
                    eye_landmarks_2d = config.WS_3D_MARK_DATA['eye_landmarks_2d']  # 3d眼部模型
                    pose_lines = config.WS_3D_MARK_DATA['pose_lines']  # 头部姿态估计
                    # 判断表情数据是不是全为0，当表情数据为0时，声强数据，3D面罩数据置0
                    is_show = list(filter(self.is_zero,config.RabbitMQ_ALG_RESULT))
                    audioString = []
                    if config.MONGODB_VOICE_DATA:
                        for auto in config.MONGODB_VOICE_DATA:
                            audioString.append(int(auto))
                    if not is_show:
                        # 没人脸的时候十分钟结束线程
                        audioString = self.set_zero(audioString)
                        points = self.set_zero(points)
                        line_left = self.set_zero(line_left)
                        line_right = self.set_zero(line_right)
                        eye_landmarks_2d = self.set_zero(eye_landmarks_2d)
                        pose_lines = self.set_zero(pose_lines)

                        if not self.no_face_time:
                            self.no_face_time = time.time()
                        else:
                            if now - self.no_face_time >= 600: # ；十分钟
                                # 调用stopInquest
                                data = {
                                    "faceMoodList": [{'mood': index, 'value': value} for index, value in
                                                     enumerate(config.RabbitMQ_ALG_RESULT)],
                                    "heartBeat": config.CLIENT_CURRENT_HEART_RATE_DATA,
                                    "auList": [
                                        {'auValue': au_dict_temp[index], 'strength': value,
                                         'classification': aus_class[index]}
                                        for index, value in enumerate(aus_reg)],
                                    "audioString": json.dumps(audioString),
                                    "timeStamp": tran_time,
                                    "riskIndex": config.DASH_BOARD_SUSPICIOUS_VALUE,
                                    "points": points,
                                    "line_left": line_left,
                                    "line_right": line_right,
                                    "eye_landmarks_2d": eye_landmarks_2d,
                                    "pose_lines": pose_lines,
                                    "shape": shape,
                                    "isInquest": 0
                                }
                                sendMessage(json.dumps(data, ensure_ascii=False), self.conn)

                                # 向http server 发送结束指令
                                data = {"a":"b"}
                                url = 'http://localhost:8080/xink-analyze/stop_inquest'
                                header = {"Content-Type": "application/json"}
                                requests.post(url=url, json=data, headers=header)
                                self.is_exit = True
                                break
                    else:
                        self.no_face_time = None

                    data = {
                        "faceMoodList": [{'mood': index, 'value': value} for index, value in
                                         enumerate(config.RabbitMQ_ALG_RESULT)],
                        "heartBeat": self.set_heart(config.CLIENT_CURRENT_HEART_RATE_DATA),
                        "auList": [
                            {'auValue': au_dict_temp[index], 'strength': value,
                             'classification': aus_class[index]}
                            for index, value in enumerate(aus_reg)],
                        "audioString": json.dumps(audioString),
                        "timeStamp": tran_time,
                        "riskIndex": config.DASH_BOARD_SUSPICIOUS_VALUE,
                        "points": points,
                        "line_left": line_left,
                        "line_right": line_right,
                        "eye_landmarks_2d": eye_landmarks_2d,
                        "pose_lines": pose_lines,
                        "shape": shape,
                        "isInquest": 1
                    }
                    sendMessage(json.dumps(data, ensure_ascii=False, cls=NumpyEncoder), self.conn)
                elif mess == 'alarm':
                    alarm_data = config.ALARM_DATA_QUEUE
                    if len(alarm_data) > 0:
                        data = alarm_data.popleft()
                        config.last_alarm_data = data
                        sendData = {
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
                        }

                        sendMessage(json.dumps(sendData, ensure_ascii=False), self.conn)
                else:
                    data = {}
                time.sleep(0.06)

    def send2(self, mess, sleep_time):
        while True:
            if self.is_exit:
                break
            if config.DETAIL_DATA.qsize():
                now = time.time()
                if mess == 'alg':
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
                    )
                    # TODO 查找当前线程数据为什么发送的慢  怎么解决等等
                    record_alg_data = config.DETAIL_DATA.get()
                    # print("record_alg_data: ",record_alg_data)
                    is_show = list(filter(self.is_zero,record_alg_data["emotion_data"]))
                    audioString = []
                    zero_list = []
                    if record_alg_data["voice_data"]:
                        for auto in record_alg_data["voice_data"]:
                            audioString.append(int(auto))
                    if not is_show:
                        audioString = self.set_zero(audioString)
                    # 删除au45
                    record_alg_data["au_data"].pop()
                    if len(record_alg_data["au_data"]) < 16:
                        record_alg_data["au_data"].insert(16, 3.5)
                    if record_alg_data["au_data"]:
                        record_alg_data["au_data"] = record_alg_data["au_data"][:16]
                    try:
                        data = {
                            "faceMoodList": [{'mood': index, 'value': value} for index, value in
                                             enumerate(record_alg_data["emotion_data"])],
                            "heartBeat": record_alg_data["heart_rate_data"],
                            "auList": [
                                {'auValue': au_dict_temp[index], 'strength': value, 'classification': record_alg_data["au_class"][index]}
                                for index, value in enumerate(record_alg_data["au_data"])],
                            "audioString": json.dumps(audioString),
                            "timeStamp": record_alg_data["timestamp"],
                            "riskIndex": record_alg_data["suspicious_value"],
                        }
                    except Exception as e:
                        LOG.error("推送历史数据出现error%s"%(e,))
                        continue
                    time.sleep(sleep_time)
                    sendMessage(json.dumps(data, ensure_ascii=False), self.conn)
                else:
                    data = {}

                # time.sleep(0.04)
            else:
                time.sleep(0.004)


# WebSocket服务器对象()
class WebSocketServer(object):
    def __init__(self):
        self.socket = None
        self.is_exit = False
        self.i = 0
        self.ws_ip = CFG.get("ws_ip", "127.0.0.1")
        self.ws_port = CFG.get("ws_port", 8000)
        # self.ws_ip = "192.168.16.106"
        # self.ws_port = 8000
        self.recv = threading.Thread(target=self.begin)
        self.recv.setDaemon(True)
        self.recv.start()

    # 开启操作
    def begin(self):
        LOG.info('WebSocketServer Start!')
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.ws_ip, self.ws_port))
        self.socket.listen(20)
        # 全局连接集合
        while True:
            try:
                if self.is_exit is True:
                    break
                connection, address = self.socket.accept()
                newSocket = WebSocket(connection, self.i, address[0], address)
                # 线程启动
                newSocket.start()
                connectionlist['connection' + str(self.i)] = connection
                self.i += 1
            except Exception as e:
                config.LOG.error("WebSocketServer线程异常")
                LOG.error(e)


    def exit(self):
        self.is_exit = True


if __name__ == "__main__":
    server = WebSocketServer()
    server.begin()
