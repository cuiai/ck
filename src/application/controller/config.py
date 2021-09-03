#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""
    后台存放全局变量文件
"""

import os
import yaml
import logging
import platform
import threading
import collections
from queue import Queue
from pymongo import MongoClient, ASCENDING, DESCENDING

# =============================================== #
# ------------------  配置文件  ------------------ #
# =============================================== #

'''
    ## 使用方法
        - 引入全局变量"CFG(字典)"，在字典里get(选项，默认值)
    ## 注意
        - 无需像以往项目那样给默认值
'''
CFG = {}
CONF_PATH = './conf/main.yaml'
if os.path.exists(CONF_PATH):
    try:
        with open(CONF_PATH, 'r', encoding='utf-8') as f:
            CFG = yaml.safe_load(f)
    except OSError:
        print('无法读取配置文件"{}"'.format(CONF_PATH))

VIEW_CFG = {}
CONF_PATH = './conf/view.yaml'
if os.path.exists(CONF_PATH):
    try:
        with open(CONF_PATH, 'r', encoding='utf-8') as f:
            VIEW_CFG = yaml.safe_load(f)
    except OSError:
        print('无法读取配置文件"{}"'.format(CONF_PATH))
# =========================================== #
# -----------------  main日志  ------------------ #
# =========================================== #
'''
    ## 使用方法
        - 在需要记录日志的地方引入全局变量"LOG"
'''
LOG_LEVEL = CFG.get('log_level', 'debug')
log_level = logging.ERROR
if LOG_LEVEL == 'debug':
    log_level = logging.DEBUG
elif LOG_LEVEL == 'warning':
    log_level = logging.WARN
elif LOG_LEVEL == 'error':
    log_level = logging.ERROR
LOG = logging.getLogger('config')
LOG.setLevel(log_level)
FORMAT = logging.Formatter('%(asctime)-15s %(module)s.%(funcName)s[%(lineno)d] %(levelname)s %(message)s')
sh = logging.StreamHandler()
sh.setFormatter(FORMAT)
sh.setLevel(log_level)
fh = logging.FileHandler('./EDA-QDJC_main.log', mode='a', encoding='utf-8')
fh.setFormatter(FORMAT)
fh.setLevel(log_level)
LOG.addHandler(sh)
LOG.addHandler(fh)

# =========================================== #
# -----------------  view日志  ------------------ #
# =========================================== #
# log_level = logging.ERROR
# if LOG_LEVEL == 'debug':
#     log_level = logging.DEBUG
# elif LOG_LEVEL == 'warning':
#     log_level = logging.WARN
# elif LOG_LEVEL == 'error':
#     log_level = logging.ERROR
# VIEW_LOG = logging.getLogger('view') # logger的名称 view
# # VIEW_LOG.handlers.clear()
# VIEW_LOG.setLevel(log_level)
# FORMAT = logging.Formatter('%(asctime)-15s %(module)s.%(funcName)s[%(lineno)d] %(levelname)s %(message)s')
# sh = logging.StreamHandler()
# sh.setFormatter(FORMAT)
# sh.setLevel(log_level)
# fh = logging.FileHandler('./EDA-QDJC_view.log', mode='a', encoding='utf-8')
# fh.setFormatter(FORMAT)
# fh.setLevel(log_level)
# VIEW_LOG.addHandler(sh)
# VIEW_LOG.addHandler(fh)

# =========================================== #
# -----------------  数据库配置  ------------------ #
# =========================================== #
MONGODB_COLLECTION_FOR_WRITE = MongoClient().get_database('eda').get_collection('alg_data')
MONGODB_COLLECTION_FOR_READ = MongoClient().get_database('eda').get_collection('alg_data')
try:
    len_ = len(list(MONGODB_COLLECTION_FOR_READ.index_information()))
    if len_ < 9:
        MONGODB_COLLECTION_FOR_READ.create_index([('inquest_uuid', ASCENDING), ('period', ASCENDING)])
        MONGODB_COLLECTION_FOR_READ.create_index([('inquest_uuid', ASCENDING), ('time', ASCENDING)])
        MONGODB_COLLECTION_FOR_READ.create_index([('inquest_uuid', ASCENDING), ('timeStamp', ASCENDING)])
        MONGODB_COLLECTION_FOR_READ.create_index([('period', ASCENDING)])
        MONGODB_COLLECTION_FOR_READ.create_index([('period', DESCENDING)])
        MONGODB_COLLECTION_FOR_READ.create_index([('time', ASCENDING)])
        MONGODB_COLLECTION_FOR_READ.create_index([('time', DESCENDING)])
        MONGODB_COLLECTION_FOR_READ.create_index([('timeStamp', ASCENDING)])
        MONGODB_COLLECTION_FOR_READ.create_index([('timeStamp', DESCENDING)])
except Exception as e:
    print("创建索引失败..............{}".format(e))


# =========================================== #
# -----------------  config变量设置  ------------------ #
# =========================================== #

# OS platform "Windows", "Linux", "Darwin"
os_type = platform.system()

if os_type == 'Windows':
    FFMPEG_PATH = 'ffmpeg.exe'
    FFMPEG_PATH2 = 'ffmpeg_put.exe'
elif os_type == 'Linux':
    # Need pre-installed command: wkhtmltopdf and ffmpeg
    FFMPEG_PATH = '/usr/bin/ffmpeg'
    FFMPEG_PATH2 = '/usr/bin/ffmpeg_put'

# Global config and database files
DB_DATA_PATH = "./data_client.db"
CACHE_DIR = "./Cache"

# audio device white list
AUDIO_DEVICE_WHITE_LIST = ["AF FULL HD 1080P Webcam: USB Audio",
                           "USB2.0 PC CAMERA: Audio",
                           "USB Device 0x46d:0x825: Audio",
                           "USB2.0 MIC",  # X-LSwab audio
                           "HD Webcam C270",  # Logic audio
                           "Realtek USB2.0 MIC",  # Aoni audio
                           "INANDON USB 2.0 Microphone",  # 1080p HD ANC
                           ]

# temperature FTCamera stat
# FTCAMERA_STAT = None

# Eda data server thread controller
# EDA_DATA_SERVER_IS_CLOSE = False
# EDA_DATA_SERVER_FLAG_STOP = False

# Global Data For Server And Client
# EMOTION_DATA_MUTEX = threading.Lock()
# VOICE_DATA = None
# RAW_IMG_STR = None
# RAW_IMG_STR_MUTEX = threading.Lock()

# TEMPERATURE_DATA = None
# TEMPERATURE_DATA_MUTEX = threading.Lock()

# SPEECH_EM_TEXT = None
# SPEECH_SIGN = None

# Batch Writing Model Data Queue
MAX_QUEUE_NUM = 100
QUEUE_EMOTION_DATA = collections.deque(maxlen=MAX_QUEUE_NUM)
QUEUE_HEART_RATE_DATA = collections.deque(maxlen=MAX_QUEUE_NUM)
QUEUE_VOICE_DATA = collections.deque(maxlen=MAX_QUEUE_NUM)

# 用于让各设备模块汇报状态给设备看门狗（DevWatchDog）
# RRP stands for 'report'
# QUEUE_RPT = Queue(50)
# 摄像头、麦克风硬件统一状态
# CAMERA_MIC_STAT = True
# 实时说谎程度
# LIE_DEGREE = None
# 表情特征数据
# EMOTION_FEATURE = None
# 保存异常图片的队列
# QUEUE_IM = collections.deque(maxlen=1000)

# 提示音频路径
# INITIATING = 'application/resources/audio/initiating.wav'
# INITIATED = 'application/resources/audio/initiated.wav'

# MEDIA_SERVER_PATH = 'application/resources/tools/mediaServer'
# 把ServerManager实例注册到全局
# SERVER_MANAGER = None
# VLC Audio注册到全局
# VLC_AUDIO = None

ORIGIN_FRAME = [None]  # 原始帧
AUDIO_BUFFER = [None]  # 音频buffer

# 看门狗对象
WATCH_DOG = None
IS_EXIT = False  # 程序退出标识
MAIN_PID = None  # 主进程Pid
USB_VIDEO = None  # 推流服务的进程对象
STREAM_SERVER = None  # 流媒体服务进程对象
NAME_THREADS = {}  # 全局线程对象

# 摄像头或USB
DST_STREAM = CFG.get('dst_stream', 'rtsp://admin:1234qwer@192.168.16.51:554')

# 推流rtsp地址
PUB_URL = CFG.get('pub_url', 'rtsp://127.0.0.1:554/live/111')
# 推流速度
PUB_V = CFG.get('pub_v', 25)
# =============================================== #
# ------------------  mainServer配置  ------------------ #
# =============================================== #

ALG_STATUS = False # 算法状态 没有作用

# 算法数据与声强数据赋值对象
EMOTION_DATA_OBJECT = None  # algresult实体对象

# # 声强数据列表
VOICE_DATA_OBJECT = None

# 判断摄像头是否正常打开
videoStream_obj = None

# 表情数据
MONGODB_EMOTION_DATA = None
RabbitMQ_ALG_RESULT = None

# 3d面罩
WS_3D_MARK_DATA = None

# 心率数据
CLIENT_CURRENT_HEART_RATE_DATA = None

# 声强数据
MONGODB_VOICE_DATA = None

# AU 数据
API_AU_DATA_OCCURRENCE = None
API_AU_DATA_INTENSITIES = None

# 智能帧
QUEUE_FACE_IMAGE = collections.deque(maxlen=10)

# 磁盘使用率
DISK_RATE = 0.0
# 磁盘可用空间（单位：G）
DISK_FREE = 0

# mongod 服务状态
MONGOD_ = None

# =============================================== #
# ------------------  websocket配置  ------------------ #
# =============================================== #
connectionlist = {}  # 存放链接客户fd,元组

# =============================================== #
# ------------------  viewServer配置  ------------------ #
# =============================================== #

# bm配置
Inquest_Room = VIEW_CFG.get('Inquest_room', '1')
LOG_LEVEL = VIEW_CFG.get('pro_log_level', 'error')

# rabbitMQ信息
RabbitMQ_host = VIEW_CFG.get('RabbitMQ_host', '192.168.16.155')
RabbitMQ_port = VIEW_CFG.get('RabbitMQ_port', 5672)
RabbitMQ_virtualHost = VIEW_CFG.get('RabbitMQ_virtualHost', '/')
RabbitMQ_username = VIEW_CFG.get('RabbitMQ_username', 'guest')
RabbitMQ_password = VIEW_CFG.get('RabbitMQ_password', 'guest')
RabbitMQ_alg_queue = VIEW_CFG.get('RabbitMQ_alg_queue', 'alg-data-queue-in')
RabbitMQ_alarm_queue = VIEW_CFG.get('RabbitMQ_alarm_queue', 'alarm-data-queue-in')

# BMSERVER
bm_ip = VIEW_CFG.get('bm_ip', "192.168.16.166")
bm_port = int(VIEW_CFG.get('bm_port', 21))
bm_server_port = int(VIEW_CFG.get('server_port', 8181))
bm_user = VIEW_CFG.get("bm_user", "uftp")
bm_password = str(VIEW_CFG.get("bm_password", "123456"))
bm_videoPath = VIEW_CFG.get("bm_videoPath", "/home/zhangye/testVideoPath")

# view变量设置
####################################################

EMOTION_PLOT_SHOW_DATA_NUM = 32  # showing the number of plot data

# emotion checkbox 样式切换， false 为默认模式， true 为彩色模式
EMOTION_CHECKBOX_QSS_SWITCH = False

# 是否添加新的三个表情
IS_ADD_ANOTHER_THREE_EMOTIONS = False

DEFAULT_WARN_RULE = {
    # TODO: default emotion warn rules
    "emojis_enable": {'angry': True, 'disgusted': True, 'fearful': True, 'happy': False,
                      'sad': False, 'surprised': False, 'neutral': False, 'contempt': False, 'test': False},
    "emoji_warn_max_number": [80],
    "heart_rate_warn_range": [50, 90],
    "camera_rule": ["all_cameras"],  # key: (all_cameras, current_camera)
}

if IS_ADD_ANOTHER_THREE_EMOTIONS is False:
    EMOJI_NAME_SEQ = ['angry', 'fearful', 'sad', 'surprised', 'disgusted', 'contempt', 'happy', 'neutral']
else:
    EMOJI_NAME_SEQ = ['meditative', 'nervous', 'inimical', 'angry', 'fearful', 'sad', 'surprised', 'disgusted',
                      'contempt', 'happy', 'neutral']

HEART_RATE_PLOT_SHOW_DATA_NUM = 24

EMOTION_PLOT_SHOW_DATA_NUM = 24  # showing the number of plot data

HEART_CHECKBOX_STATE = {'heart_rate': True}
HEART_RATE_RANGE = (20, 140)  # 心率展示范围
HEART_RATE_WARN_UPPER_LIMIT = 80  # 心率告警上限
HEART_RATE_WARN_LOWER_LIMIT = 40  # 心率告警下限

# todo
VOICE_PLOT_SHOW_DATA_NUM = 96 * 24

TEMPERATURE_PLOT_SHOW_DATA_NUM = 100

UPLOAD_VIDEO_IS_OVER = False
DETAIL_WIDGET_SHOW_FLAG = True

# 折线图展示的时间长度  (s)
GRAPH_SHOW_TIME = 5

# 声强折线图展示的时间长度  (s)
AUDIO_INTENSITY_GRAPH_SHOW_TIME = 1

# 温度折线图展示的时间长度  (s)
TEMPERATURE_GRAPH_SHOW_TIME = 3

# 审讯UUID
UUID = None

# Batch Writing Model Data Queue  批处理缓存队列
MAX_QUEUE_NUM = 10
QUEUE_EMOTION_DATA = collections.deque(maxlen=MAX_QUEUE_NUM)

# AU 是否当作有/无型显示
AU_RULER = eval(VIEW_CFG.get("au_rule", "(13, 16, 17)"))
# 每个位置的数值代表同位置AU 显示的最小数值
AU_MIN_TO_SHOW_VALUES = eval(VIEW_CFG.get("au_min_to_show_values",
                                          "(3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, "
                                          "3.0, 3.0, 3.0)"))

# 审讯详情AU 数据occurrence
API_AU_DATA_CLASS = None
# 审讯详情AU 数据 intensities
API_AU_DATA_REG = None

FACE_COORDINATES = [None, None]
FACE_IMAGE = [None, None]
QUEUE_FACE_COORDINATES = collections.deque(maxlen=500)

# 瞳孔视线角度（Gaze角度值）
GAZE_ANGLE = None
IS_LOOK_AT_ME_TEXT = None

# 人脸网格连接规则， 数字代表第多少个点
tmp_rule = """[(0, 1), (0, 17), (0, 36), (1, 2), (2, 3), (2, 17), (2, 36), (2, 31), (3, 31), (3, 48), (3, 4),
                   (4, 5), (4, 48), (5, 6), (5, 48), (6, 7), (6, 48), (6, 58), (7, 8), (8, 9),
                   (8, 56), (8, 58), (9, 10), (10, 11), (10, 54), (10, 56), (11, 12), (11, 54), (12, 13), (12, 54),
                   (13, 14), (13, 54), (13, 35), (14, 15), (14, 26), (14, 35), (14, 45), (15, 16),
                   (16, 26), (16, 45), (17, 18), (17, 36), (18, 19), (19, 36), (19, 39), (19, 20), (20, 21),
                   (21, 22), (21, 39), (22, 23), (22, 42), (23, 24), (24, 25), (24, 45), (24, 42), (25, 26),
                   (26, 45),
                   (27, 28), (27, 39), (27, 42), (28, 29), (29, 30), (30, 33), (30, 31), (30, 35), (31, 32),
                   (31, 33), (31, 36), (32, 33), (33, 34), (33, 39), (33, 42), (33, 50), (33, 51), (33, 52),
                   (34, 35), (35, 42), (35, 45),
                   (36, 37), (36, 41), (37, 38), (38, 39), (39, 40), (40, 41), (42, 43), (43, 44), (44, 45),
                   (45, 46), (46, 47), (47, 42),
                   (48, 49), (49, 50), (50, 51), (51, 52), (52, 53), (53, 54), (54, 55), (55, 56), (56, 57),
                   (57, 58), (58, 59), (59, 60), (60, 61), (61, 62), (62, 63), (63, 64), (64, 65), (65, 66),
                   (66, 67)]"""
FACE_LINE_RULES = eval(VIEW_CFG.get('face_line_rule', tmp_rule))

# 人脸特征点点（圆）半径
FACE_POINT_RADIUS = VIEW_CFG.get('face_point_radius', 2)

# 人脸特征点颜色(BGR)
FACE_POINT_COLOR = eval(VIEW_CFG.get('face_point_color', '(255, 222, 167)'))

# 人脸网格线宽
FACE_LINE_THICKNESS = VIEW_CFG.get('face_line_thickness', 1)

# 人脸网格颜色(BGR)
FACE_LINE_COLOR = eval(VIEW_CFG.get('face_line_color', '(245, 245, 245)'))

# 告警阈值
alarm_value = VIEW_CFG.get('alarm_value', 90)
normal_value = VIEW_CFG.get('normal_value', 10)

# 3D Mask, 头部姿态估计，眼部姿态估计，眼部3D模型
# 勾选项为4个
IS_3D_MASK_DRAW = True
IS_HEAD_POSE_ESTIMATION_DRAW = True
IS_EYE_POSE_ESTIMATION_DRAW = True
IS_EYE_3D_MODEL_DRAW = True

# 回溯表情数据 ["生气", "害怕", "伤心", "惊讶", "厌恶", "轻蔑", "高兴", "平和"]
REVIEW_CURRENT_EMOTION_DATA = None
# 回溯心率数据
REVIEW_CURRENT_HEART_RATE_DATA = None

VIDEO_SIZE = '1280x720'

INQUEST_PERSON_ID = None

TIME_OFFSET = None

# AU 文本提示内容
AU_TEXT_TIPS = VIEW_CFG.get("au_text_tip", """
              平和 无
              愤怒 AU单元：4+5+24
              轻蔑 AU单元：10+15+17
              厌恶 AU单元：9+10
              害怕 AU单元：1+2+4+5+7+20
              快乐 AU单元：6+12
              悲伤 AU单元：1或1+15
              惊讶 AU单元：1+2+5+25+26
              """)

EMOTION_DEQUE = collections.deque(maxlen=2)  # 首页左侧, 保存算法给出的表情数据

is_entry_problem = False  # 首页左侧, 录入问题模块, 标记当前录入问题的状态

current_question_id = None  # 首页左侧, 录入问题模块, 标记当前录入问题的id

warn_id = 0  # 首页左侧记录当前面告警快照的id

warn_status = "stop"  # 首页左侧记录当前告警状态

inquest_status = False  # 审讯状态

heartbeatCnt = 0

heartbeatCntBm = 0

inquest_data = False

inquest_uuid = None  # 审讯uuid

inquest_start_time = None  # 审讯开始时间
end_start_time = None  # 审讯结束时间

# 全局告警状态，用于悬浮标签显示
IS_ALARM = None

# 当前窗口标题
WINDOW_TITLE = None

############################################################
# 文档存放路径
############################################################
DEFAULT_DATA_ROOT_PATH = os.path.abspath("..")
DEFAULT_DATA_BACKUP_DIR = os.path.join(DEFAULT_DATA_ROOT_PATH, "DOCUMENT")
DEFAULT_VIDEO_DATA_DIR = os.path.join(DEFAULT_DATA_BACKUP_DIR, "VIDEO")
DEFAULT_PLOT_DATA_DIR = os.path.join(DEFAULT_DATA_BACKUP_DIR, "TABLE")
DEFAULT_REPORT_DATA_DIR = os.path.join(DEFAULT_DATA_BACKUP_DIR, "REPORT")
DEFAULT_DEMO_DATA_DIR = os.path.join(DEFAULT_DATA_BACKUP_DIR, "SAMPLE")
DEFAULT_PIC_DATA_DIR = os.path.join(DEFAULT_DATA_BACKUP_DIR, "IMAGE")
DEFAULT_TEMPLATE_DATA_DIR = os.path.join(DEFAULT_DATA_BACKUP_DIR, "TEMPLATE")
DEFAULT_UPLOAD_VIDEO_DIR = os.path.join(os.getcwd(), "UPLOAD_VIDEO")
DEFAULT_ALARM_VIDEO_DATA_DIR = os.path.join(DEFAULT_VIDEO_DATA_DIR, "alarm_video")
DEFAULT_INQUEST_VIDEO_DATA_DIR = os.path.join(DEFAULT_VIDEO_DATA_DIR, "inquest_video")

PATH_HTML2PDF = 'application/resources/tools/PDF/wkhtmltopdf.exe'  # 审讯报告工具

# 审讯报告使用的模板
PEIZHI = VIEW_CFG.get("text_config", 0)
if PEIZHI == 1:
    REPORT_TEMPLATE = 'jiwei.html'
else:
    REPORT_TEMPLATE = 'gongan.html'
PDF_TEMPLATE = 'application/resources/report_files/templates/{}'.format(REPORT_TEMPLATE)  # 报告模板

LICENSE_FILE_PATH = './conf/tiger.dll'
LICENSE_MATCH_SWITCH = True
DOOR_PWD = VIEW_CFG.get('door', None)
LICENSE_EXPIRE_DATA = " "
SOFT_VERSION = "QDJCWV1.3"
DEVICE_TYPE = VIEW_CFG.get('client_device_type', 0x6101)

# 用户手动选择情绪强度值
emotion_warn_intensity = {"contempt": 1, "disgusted": 1, "surprised": 1, "sad": 1, "fearful": 1, "angry": 1}

# 心理状态列表配置
mind_status_list = eval(VIEW_CFG.get('mind_status', '(("nervous","紧张"), ("anxious", "焦虑"), ("resistance", "抵触"), '
                                                    '("depressed", "抑郁"))'))
# 实时显示的心理状态
mind_status = "正常"

# 实时系统状态（网络延时，视频帧率，内存使用率，（程序所在盘符的）磁盘使用率）
current_system_status = None

IS_OFFLINE_VIDEO = False

TEMPLATE_TYPE = ""

REAL_DETECT = False

START_TIME = None

# 审讯模板窗口是否关闭
TEMPLATE_IS_CLOSE = True

# 记录基线起始时间
# BASE_START_TIME = None

# 记录基线终止时间
# BASE_STOP_TIME = None

# 每个问题开始时间
QUESTION_START_TIME = None

# 每个问题结束时间
QUESTION_STOP_TIME = None

# 基线数据平均值
BASE_AVG_VALUE_ANGER = VIEW_CFG.get('anger_base_value', 20)
BASE_AVG_VALUE_FEAR = VIEW_CFG.get('fear_base_value', 25)
BASE_AVG_VALUE_SADNESS = VIEW_CFG.get('sadness_base_value', 20)
BASE_AVG_VALUE_SURPRISE = VIEW_CFG.get('surprise_base_value', 10)
BASE_AVG_VALUE_DISGUST = VIEW_CFG.get('disgust_base_value', 30)
BASE_AVG_VALUE_CONTEMPT = VIEW_CFG.get('contempt_base_value', 10)
BASE_AVG_VALUE_JOY = VIEW_CFG.get('joy_base_value', 30)
BASE_AVG_VALUE_NEUTRAL = VIEW_CFG.get('neutral_base_value', 50)

review_emotion_data_lines = collections.deque(maxlen=5)

DEVIDE_QUESTION_SIGN = False

# 仪表盘开始变更的时间戳
DASH_BOARD_BEGIN_TIME = None

# 告警时长时间记录值
RECORD_START_BEGIN_TIME = None

# 每个窗口所对应的间隔时间
# window_time = VIEW_CFG.get('window_time')
# DASH_BOARD_TIMEDELTA_1 = 1 * window_time
# DASH_BOARD_TIMEDELTA_2 = 2 * window_time
# DASH_BOARD_TIMEDELTA_3 = 3 * window_time
# DASH_BOARD_TIMEDELTA_4 = 4 * window_time
# DASH_BOARD_TIMEDELTA_5 = 5 * window_time
# DASH_BOARD_TIMEDELTA_6 = 6 * window_time

# 每个窗口所存储的表情数据
DASH_BOARD_WINDOW_1 = []
DASH_BOARD_WINDOW_2 = []
DASH_BOARD_WINDOW_3 = []
DASH_BOARD_WINDOW_4 = []
DASH_BOARD_WINDOW_5 = []
DASH_BOARD_WINDOW_6 = []

# 仪表盘可疑数值
DASH_BOARD_SUSPICIOUS_VALUE = 0


# 界面状态(实时监测0 仪表盘2)
INTERFACE_STAUS = 0

# 告警开始时间
ALARM_START_TIME = None
# 告警结束时间
# ALARM_STOP_TIME = None
# 告警视频录制状态
ALARM_RECORDING_STATUS = False
# 告警数据全局变量
ALARM_DATA_QUEUE = collections.deque(maxlen=50)
# ftp上传视频的队列
FTP_UPLOAD_FILE = Queue()
# 审讯信息上传到BM
ADD_INQUEST_BM_DATA = Queue()
# 审讯报告上传到BM
ADD_REPORT_BM_DATA = Queue()
# 可疑值数据缓存
SUSPICIOUS_VALUE_QUEUE = collections.deque(maxlen=5)

# 审讯详情可疑值
DETAIL_SUSPICIOUS_VALUE = None

# 审讯笔录开始录屏时间
LAST_TIME = 1

# 视频对应告警记录的状态
VIDEO_FOR_RECORD = 0

# 视频时长秒数
VIDEO_TIME = 0

# 视频当前时间
VIDEO_LOCAL_TIME = 0

# 存储客户端告警数据
alarm_data_count = []

# 存储全局告警数据
all_alarm_count = []

# 存储告警时的表情数据
alarm_emotion_count = []
# 谈话阶段告警统计
time_phasing = []
# 时间段表情统计
time_emotion_count = []

# 当前审讯的告警视频路径
all_video_path = []

# 最后一条客户端显示的告警
last_alarm_data = None

# 最后一条告警视频路径
last_video_path = None

# 删除无用视频路径列表
bad_video = []

# 审讯详情表情值列表
EMOTION_DATA = []

# 审讯详情心率值列表
HEART_DATA = []

# 审讯详情声强值列表
VOICE_DATA = []

# 审讯详情三种表情值显示开关
DETAIL_START_STOP = None

# 赋值于审讯详情查找出来的最新一条数据的时间戳
DETAIL_LAST_TIME = 0
# 记录于当前进度条的时间戳变化程度
DETAIL_NOW_TIME = 0
# 对比当前查出数据的对比点
COMPARISON_TIME = 0

# 文字配置
##################################################
ProjectID = VIEW_CFG.get("text_config", 0)
if ProjectID == 0:
    # 公安
    text1 = "审讯"
    text2 = "嫌疑"
    text3 = "被询"
    text4 = "案件"
    text5 = "问询"
else:
    # 纪委
    text1 = "谈话"
    text2 = "被谈话"
    text3 = "被谈话"
    text4 = "谈话"
    text5 = "谈话"

get_report = None

####################历史详情表情数据#################################
# 历史详情算法数据线程对象
hd_thread = None

# 详情播放视频的开始时间
PLAYSTART = 0

LATES_TS = 0

# 详情播放视频的结束时间
ENDPLAY = None

# 暂停算法数据
IS_STOP = False # False:算法暂停

# 历史算法数据队列
DETAIL_DATA = Queue(maxsize=300)

# 详情表情数据
DETAIL_EMOTION_DATA = None
DETAIL_ALG_RESULT = None

# 心率数据
DETAIL_HEART_RATE_DATA = None

# 声强数据
DETAIL_VOICE_DATA = None

# AU 数据
DETAIL_AU_DATA_OCCURRENCE = None
DETAIL_AU_DATA_INTENSITIES = None

# 查看报告的信息
report_ = None

# 模板对象
BS4_object = None

# 视频流分辨率
STREAM_SHAPE = None

SOCKET_SERVER = False


# 告警数据的session
ALARM_SESSION = []

IS_3D_MASK_DRAW = True
IS_HEAD_POSE_ESTIMATION_DRAW = True
IS_EYE_POSE_ESTIMATION_DRAW = True
IS_EYE_3D_MODEL_DRAW = True

FRAME_WIDTH = 0
FRAME_HEIGHT = 0