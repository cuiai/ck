#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
    后台公用文件，存放通用工具
    command： 新建进程运行终端命令
    EDAThread： 多线程类模板
    check_id_card：身份证校验

"""

import socket, os, re
import subprocess, sys
from threading import Thread
from application.controller import config
from application.controller.config import LOG, CFG


def command(cmd, is_shell=False):
    """Command function"""

    ret = None
    try:
        process = subprocess.Popen(cmd,
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   shell=is_shell)
        out, err = process.communicate()
        rc = process.returncode
    except Exception as e:
        LOG.error("command %s" % str(e))
        return ret
    return rc, out, err

def cs_command(cmd, is_shell=False):
    """Command function"""

    ret = None
    try:
        process = subprocess.Popen(cmd,
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   shell=is_shell)
        ret =True
    except Exception as e:
        LOG.error("command %s" % str(e))
        return ret
    return ret

class EDAThread(Thread):
    def __init__(self, thread_name):
        super(EDAThread, self).__init__()
        self.setDaemon(True)
        self.setName(thread_name)
        self.is_running = True
        self.is_exit = False

    def open(self):
        self.is_running = True

    def stop(self):
        self.is_running = False

    def thread_exit(self):
        self.is_exit = True


def get_path():
    path = eval(repr(os.path.dirname(__file__).split("application")[0]).replace('\\', '/'))
    return path


def get_video_size():
    """
    解析配置文件分辨率字符串
    :return: (width, height):tuple
    """
    ret = (None, None)
    size_str = CFG.get('video_size', '1280x720')
    try:
        r = size_str.split('x')
        ret = int(r[0]), int(r[1])
    except Exception as e:
        LOG.error('解析视频大小(VIDEO_SIZE)配置错误：{}'.format(e))
        return ret
    return ret


def get_ip():
    """获取IP"""
    ips = []
    addrs = socket.getaddrinfo(socket.gethostname(), None)

    for item in addrs:
        ips = [item[4][0] for item in addrs if ':' not in item[4][0]]
    return ips[0]


def init_resources():
    """Init local directory resources"""
    ret = False
    resource_dir_list = [config.DEFAULT_VIDEO_DATA_DIR, config.DEFAULT_PLOT_DATA_DIR,
                         config.DEFAULT_REPORT_DATA_DIR, config.DEFAULT_DEMO_DATA_DIR,
                         config.DEFAULT_PIC_DATA_DIR, config.DEFAULT_TEMPLATE_DATA_DIR,
                         config.DEFAULT_UPLOAD_VIDEO_DIR, config.DEFAULT_ALARM_VIDEO_DATA_DIR,
                         config.DEFAULT_INQUEST_VIDEO_DATA_DIR]
    if not os.path.isdir(config.DEFAULT_DATA_BACKUP_DIR):
        try:
            os.mkdir(config.DEFAULT_DATA_BACKUP_DIR)
        except Exception as e:
            LOG.error("%s %s" % (config.DEFAULT_DATA_BACKUP_DIR, str(e)))
            return ret
    for resource_dir in resource_dir_list:
        path = os.path.join(config.DEFAULT_DATA_BACKUP_DIR, resource_dir)
        if not os.path.isdir(path):
            try:
                os.mkdir(path)
            except Exception as e:
                LOG.error("%s %s" % (path, str(e)))
                return ret
    if not os.path.isdir(config.CACHE_DIR):
        try:
            os.mkdir(config.CACHE_DIR)
        except Exception as e:
            LOG.error("%s %s" % (config.CACHE_DIR, str(e)))
            return ret
    ret = True
    return ret


def resource_path(relative_path):
    """Convert relative resource path to the real path"""

    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(relative_path)


def check_id_card(identity_card):
    """
    校验身份证号合法性
    :param identity_card: 待校验身份证号
    :return: '': 校验通过 0~4：相应的错误信息
    """

    errors = ["", "身份证号码位数不对!", "身份证号码出生日期超出范围或含有非法字符!", "身份证号码校验错误!", "身份证地区非法!", "请输入二代身份证号"]
    area = {
        "11": "北京",
        "12": "天津",
        "13": "河北",
        "14": "山西",
        "15": "内蒙古",
        "21": "辽宁",
        "22": "吉林",
        "23": "黑龙江",
        "31": "上海",
        "32": "江苏",
        "33": "浙江",
        "34": "安徽",
        "35": "福建",
        "36": "江西",
        "37": "山东",
        "41": "河南",
        "42": "湖北",
        "43": "湖南",
        "44": "广东",
        "45": "广西",
        "46": "海南",
        "50": "重庆",
        "51": "四川",
        "52": "贵州",
        "53": "云南",
        "54": "西藏",
        "61": "陕西",
        "62": "甘肃",
        "63": "青海",
        "64": "宁夏",
        "65": "新疆",
        "71": "台湾",
        "81": "香港",
        "82": "澳门",
        "91": "国外",
    }
    identity_card = str(identity_card).strip()
    card_id_list = list(identity_card)
    if len(identity_card) == 18:
        # 出生日期的合法性检查
        # 闰年月日:((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|[1-2][0-9]))
        # 平年月日:((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|1[0-9]|2[0-8]))
        if int(identity_card[6:10]) % 4 == 0 or (
                int(identity_card[6:10]) % 100 == 0 and int(identity_card[6:10]) % 4 == 0
        ):
            ereg = re.compile(
                "[1-9][0-9]{5}(19[0-9]{2}|20[0-9]{2})((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|"
                "(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|[1-2][0-9]))[0-9]{3}[0-9Xx]$"
            )  # 闰年出生日期的合法性正则表达式
        else:
            ereg = re.compile(
                "[1-9][0-9]{5}(19[0-9]{2}|20[0-9]{2})((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|"
                "(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|1[0-9]|2[0-8]))[0-9]{3}[0-9Xx]$"
            )  # 平年出生日期的合法性正则表达式
        # 测试出生日期的合法性
        if re.match(ereg, identity_card):
            # 计算校验位
            S = (
                    (int(card_id_list[0]) + int(card_id_list[10])) * 7
                    + (int(card_id_list[1]) + int(card_id_list[11])) * 9
                    + (int(card_id_list[2]) + int(card_id_list[12])) * 10
                    + (int(card_id_list[3]) + int(card_id_list[13])) * 5
                    + (int(card_id_list[4]) + int(card_id_list[14])) * 8
                    + (int(card_id_list[5]) + int(card_id_list[15])) * 4
                    + (int(card_id_list[6]) + int(card_id_list[16])) * 2
                    + int(card_id_list[7]) * 1
                    + int(card_id_list[8]) * 6
                    + int(card_id_list[9]) * 3
            )
            Y = S % 11
            M = "F"
            JYM = "10X98765432"
            M = JYM[Y]  # 判断校验位
            if M == card_id_list[17]:  # 检测ID的校验位
                return errors[0]
            else:
                return errors[3]
        else:
            return errors[2]
    else:
        return errors[1]




