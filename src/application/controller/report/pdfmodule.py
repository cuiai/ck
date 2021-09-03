#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import codecs
import pdfkit
import time, re
import os, copy
import subprocess
import datetime, math
from pdfkit import PDFKit
from bs4 import BeautifulSoup
from collections import Counter
from application.controller import config
from application.controller.config import text1
from application.controller.common import resource_path
from application.controller.config import DEFAULT_TEMPLATE_DATA_DIR
from application.model.model_data import InquestRecord, PersonalManager
from application.controller.config import PATH_HTML2PDF, PDF_TEMPLATE, LOG


def timestamp_to_date(time_stamp, format_string="%Y-%m-%d %H:%M:%S"):
    time_array = time.localtime(time_stamp)
    str_date = time.strftime(format_string, time_array)
    return str_date


class CustomPDFKit(PDFKit):

    def __init__(self, *args, **kwargs):
        super(CustomPDFKit, self).__init__(*args, **kwargs)

    def to_pdf(self, path=None):
        args = self.command(path)

        result = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=True)

        # If the source is a string then we will pipe it into wkhtmltopdf.
        # If we want to add custom CSS to file then we read input file to
        # string and prepend css to it and then pass it to stdin.
        # This is a workaround for a bug in wkhtmltopdf (look closely in README)
        if self.source.isString() or (self.source.isFile() and self.css):
            input = self.source.to_s().encode('utf-8')
        elif self.source.isFileObj():
            input = self.source.source.read().encode('utf-8')
        else:
            input = None
        stdout, stderr = result.communicate(input=input)
        stderr = stderr or stdout
        try:
            stderr = stderr.decode('utf-8')
        except UnicodeDecodeError:
            stderr = ''
        exit_code = result.returncode

        if 'cannot connect to X server' in stderr:
            raise IOError('%s\n'
                          'You will need to run wkhtmltopdf within a "virtual" X server.\n'
                          'Go to the link below for more information\n'
                          'https://github.com/JazzCore/python-pdfkit/wiki/Using-wkhtmltopdf-without-X-server' % stderr)

        if 'Error' in stderr:
            raise IOError('wkhtmltopdf reported an error:\n' + stderr)

        if exit_code != 0:
            raise IOError("wkhtmltopdf exited with non-zero code {0}. error:\n{1}".format(exit_code, stderr))

        # Since wkhtmltopdf sends its output to stderr we will capture it
        # and properly send to stdout
        if '--quiet' not in args:
            sys.stdout.write(stderr)

        if not path:
            return stdout
        else:
            try:
                with codecs.open(path, encoding='utf-8') as f:
                    # read 4 bytes to get PDF signature '%PDF'
                    text = f.read(4)
                    if text == '':
                        raise IOError('Command failed: %s\n'
                                      'Check whhtmltopdf output without \'quiet\' '
                                      'option' % ' '.join(args))
                    return True
            except IOError as e:
                raise IOError('Command failed: %s\n'
                              'Check whhtmltopdf output without \'quiet\' option\n'
                              '%s ' % (' '.join(args)), e)

    def to_pdf_quiet(self, path=None):
        args = self.command(path)

        result = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=True)

        # If the source is a string then we will pipe it into wkhtmltopdf.
        # If we want to add custom CSS to file then we read input file to
        # string and prepend css to it and then pass it to stdin.
        # This is a workaround for a bug in wkhtmltopdf (look closely in README)
        if self.source.isString() or (self.source.isFile() and self.css):
            input = self.source.to_s().encode('utf-8')
        elif self.source.isFileObj():
            input = self.source.source.read().encode('utf-8')
        else:
            input = None
        stdout, stderr = result.communicate(input=input)
        stderr = stderr or stdout
        try:
            stderr = stderr.decode('utf-8')
        except UnicodeDecodeError:
            stderr = ''
        exit_code = result.returncode

        if 'cannot connect to X server' in stderr:
            raise IOError('%s\n'
                          'You will need to run wkhtmltopdf within a "virtual" X server.\n'
                          'Go to the link below for more information\n'
                          'https://github.com/JazzCore/python-pdfkit/wiki/Using-wkhtmltopdf-without-X-server' % stderr)

        if 'Error' in stderr:
            raise IOError('wkhtmltopdf reported an error:\n' + stderr)

        if exit_code != 0:
            raise IOError("wkhtmltopdf exited with non-zero code {0}. error:\n{1}".format(exit_code, stderr))

        # Since wkhtmltopdf sends its output to stderr we will capture it
        # and properly send to stdout
        if '--quiet' not in args:
            sys.stdout.write(stderr)

        if not path:
            return stdout
        else:
            try:
                with codecs.open(path, encoding='utf-8') as f:
                    # read 4 bytes to get PDF signature '%PDF'
                    text = f.read(4)
                    if text == '':
                        raise IOError('Command failed: %s\n'
                                      'Check whhtmltopdf output without \'quiet\' '
                                      'option' % ' '.join(args))
                    return True
            except IOError as e:
                raise IOError('Command failed: %s\n'
                              'Check whhtmltopdf output without \'quiet\' option\n'
                              '%s ' % (' '.join(args)), e)


def generate_pdf(user_id_num, report_id=1, save_path=None):
    # 获取数据以及生成报告路径
    ret = None
    report_log = None
    try:
        report_log = InquestRecord.get_opt_all_by_id(report_id)
    except Exception as e:
        LOG.debug(e)
    if report_log is None:
        LOG.error('report_log is None')
        return ret
    pdf = PdfTool()
    inquest_uuid = config.inquest_uuid
    config.inquest_uuid = None
    # 更新全局变量--审讯开始时间
    config.inquest_start_time = None
    config.alarm_data_count.clear()
    config.all_alarm_count.clear()
    config.report_ = False
    user = PersonalManager.get_one_opt_by_number(user_id_num)
    if not user:
        LOG.error('未查询到人员，可能是没有关联')
        return ret

    # 开始生成报告
    # print("{}: 生成开始".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
    html_path = pdf.generate_pdf(user, report_log)
    if html_path is None:
        return ret
    # 上传审讯报告
    if config.VIEW_CFG.get("interaction", 0) == 1:
        try:
            bm_report_data = {"path": html_path, "uuid": inquest_uuid}
            config.ADD_REPORT_BM_DATA.put(bm_report_data)
        except Exception as e:
            LOG.error("上传审讯报告出现错误======={}".format(e))
    LOG.debug('generate pdf ok, path:' + html_path)
    InquestRecord.update_opt_report_path(report_id, html_path)
    # print("{}: 生成结束".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
    return html_path


class PdfTool:
    def __init__(self, template=None):
        self.path_html2pdf = resource_path(PATH_HTML2PDF)
        self.template = resource_path(PDF_TEMPLATE)
        self.html_path = ''
        self.time_emotion_count = []
        self.time_phasing = []
        self.alarm_data_count = copy.deepcopy(config.alarm_data_count)
        self.all_alarm_count = copy.deepcopy(config.all_alarm_count)
        self.inquest_uuid = copy.deepcopy(config.inquest_uuid)
        self.inquest_start_time = copy.deepcopy(config.inquest_start_time)
        if template:
            self.template = template

    def check(self):
        ret = self.path_html2pdf
        if not os.path.exists(self.path_html2pdf):
            return ret
        if not os.path.exists(self.template):
            return ret
        ret = True
        return ret

    # 写入报告的数据到html文件
    def _fill_content(self, user, report_log):
        # print("{}: 11111111".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        create_time = timestamp_to_date(report_log.create_time)
        end_time = timestamp_to_date(report_log.inquest_end_time)
        tran_create_time = time.mktime(time.strptime(create_time, "%Y-%m-%d %H:%M:%S"))
        tran_end_time = time.mktime(time.strptime(end_time, "%Y-%m-%d %H:%M:%S"))
        report_log_dict = json.loads(report_log.report_info)
        # 计算全局总时长
        time_list = str(datetime.timedelta(seconds=tran_end_time - tran_create_time)).split(':')
        # print("{}: 22222222".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        try:
            pattern = re.compile(r'\d+')
            time_result = pattern.findall(time_list[0])
            if len(time_result) > 1:
                hours = int(time_result[0]) * 24 + int(time_result[1])
            else:
                hours = time_list[0]
        except Exception as e:
            time_list = [0, 0, 0]
            hours = 0
            config.LOG.error("时间计算错误===={}".format(e))
        trial_time = ''
        if len(time_list) == 3:
            trial_time = str(hours) + '小时' + str(time_list[1]) + '分钟' + str(round(float(time_list[2]))) + '秒'
        elif len(time_list) == 2:
            trial_time = str(time_list[0]) + '分钟' + str(round(float(time_list[2]))) + '秒'
        else:
            trial_time = str(round(float(time_list[2]))) + '秒'
        # print("time_list", time_list)
        # 计算告警情绪值最多者
        status_count = []
        # print("{}: 333333333".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        for alarm in self.all_alarm_count:
            if alarm:
                status_count.append(alarm['total_status'])
        first_status_count = []
        # print("{}: 444444444".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        for alarm_one in self.alarm_data_count:
            if alarm_one:
                first_status_count.append(alarm_one['total_status'])
        # 告警情绪值最多者
        mood_state_sum = ' '
        # 告警情绪值最多者的数量
        fluke_mind_alarm = 0
        # 情绪状态的次数与比率统计
        emotion_peihe_count = 0
        emotion_peihe_percentage = '0%'
        emotion_jiaoxing_count = 0
        emotion_jiaoxing_percentage = '0%'
        emotion_dichu_count = 0
        emotion_dichu_percentage = '0%'
        emotion_konghuang_count = 0
        emotion_konghuang_percentage = '0%'
        abnormal_count = 0
        abnormal_percentage = '0%'
        if len(status_count) and len(first_status_count):
            mood_state_sum = Counter(first_status_count).most_common(1)[0][0]
            fluke_mind_alarm = Counter(first_status_count).most_common(1)[0][1]
            emotion_peihe_count_list = Counter(status_count).most_common()
            for count_list in emotion_peihe_count_list:
                try:

                    if count_list[0] == '配合':
                        emotion_peihe_count = count_list[1]
                        emotion_peihe_percentage = str(
                            round(float(emotion_peihe_count / sum([i[1] for i in emotion_peihe_count_list]) * 100),
                                  2)) + '%'
                    elif count_list[0] == '侥幸':
                        emotion_jiaoxing_count = count_list[1]
                        emotion_jiaoxing_percentage = str(round(
                            float(emotion_jiaoxing_count / sum([i[1] for i in emotion_peihe_count_list]) * 100),
                            2)) + '%'

                    elif count_list[0] == '抵触':
                        emotion_dichu_count = count_list[1]
                        emotion_dichu_percentage = str(round(
                            float(emotion_dichu_count / sum([i[1] for i in emotion_peihe_count_list]) * 100), 2)) + '%'
                    elif count_list[0] == '恐慌':
                        emotion_konghuang_count = count_list[1]
                        emotion_konghuang_percentage = str(round(
                            float(emotion_konghuang_count / sum([i[1] for i in emotion_peihe_count_list]) * 100),
                            2)) + '%'
                except Exception as e:
                    emotion_peihe_percentage = "0%"
                    emotion_jiaoxing_percentage = "0%"
                    emotion_dichu_percentage = "0%"
                    emotion_konghuang_percentage = "0%"
            abnormal_count = emotion_jiaoxing_count + emotion_dichu_count + emotion_konghuang_count
            abnormal_percentage = str(
                round(float((1 - emotion_peihe_count / sum([i[1] for i in emotion_peihe_count_list])) * 100),
                      2)) + '%'
            # 进行排序规整
            for i in range(len(self.alarm_data_count)):
                for j in range(len(self.alarm_data_count) - i - 1):
                    if self.alarm_data_count[j]['suspicious_value'] > self.alarm_data_count[j + 1][
                        'suspicious_value']:
                        self.alarm_data_count[j + 1], self.alarm_data_count[j] = \
                            self.alarm_data_count[j], \
                            self.alarm_data_count[j + 1]
                    else:
                        pass
        time_node = ' '
        total_status = ' '
        emotion_degree = ' '
        alarm_suspicious = 0
        emotion_degree_count = 0
        # 告警数据最高可疑前十条
        mood_state_list = []
        # print("{}: 555555555".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        if len(self.alarm_data_count):
            if len(self.alarm_data_count) <= 10:
                mood_state_list = self.alarm_data_count[::-1]
            else:
                mood_state_list = self.alarm_data_count[::-1][:10]
            if self.alarm_data_count[-1].get('time_node'):
                time_node = self.alarm_data_count[-1]['time_node']
                alarm_suspicious = self.alarm_data_count[-1]['suspicious_value']
                total_status = self.alarm_data_count[-1]['total_status']
                emotion_degree = self.alarm_data_count[-1]['emotion_degree']
                emotion_degree_count = self.alarm_data_count[-1]['emotion_degree_count']
        # 计算全局的表情频率
        # mood_count = self.documents_()
        # 告警统计与表情统计
        try:
            echarts_emotion_time = self.countData(tran_create_time, tran_end_time)
        except Exception as e:
            echarts_emotion_time = []
            config.LOG.error("告警统计时间段出错===={}".format(e))
        if echarts_emotion_time:
            echarts_emotion_legend = ','.join([str(k) for k in echarts_emotion_time])
        else:
            echarts_emotion_legend = '第一阶段,第二阶段,第三阶段,第四阶段'
        # print("report_log_dict", report_log_dict)
        # print('mood_count', mood_count)
        # 计算出生日期
        situation_databirth = user.id_number[6:14][:4] + '-' + user.id_number[6:14][4:][:2] + '-' + user.id_number[
                                                                                                    6:14][4:][2:]
        info_person = report_log.ask_name
        if not info_person:
            info_person = '- -'
        msg_map = {
            'total_hour': int(hours),
            'total_minute': int(time_list[1]),
            'total_second': round(float(time_list[2])),
            'alarm_count': len(self.alarm_data_count),
            'mood_state_sum': mood_state_sum,
            'fluke_mind_alarm': fluke_mind_alarm,
            'emotion_anomaly_time': time_node,
            'emotion_anomaly_value': alarm_suspicious,
            'emotion_mentality': total_status,
            'emotion_degree': emotion_degree,
            'emotion_degree_count': emotion_degree_count,
            'case_type': str(report_log.case_number) + '-' + str(report_log.case_type),
            'trial_time': trial_time,
            'emotion_peihe_count': emotion_peihe_count,
            'emotion_peihe_percentage': emotion_peihe_percentage,
            'emotion_jiaoxing_count': emotion_jiaoxing_count,
            'emotion_jiaoxing_percentage': emotion_jiaoxing_percentage,
            'emotion_dichu_count': emotion_dichu_count,
            'emotion_dichu_percentage': emotion_dichu_percentage,
            'emotion_konghuang_count': emotion_konghuang_count,
            'emotion_konghuang_percentage': emotion_konghuang_percentage,
            'echarts_emotion_jiaoxing_count': emotion_jiaoxing_count,
            'echarts_emotion_konghuang_count': emotion_konghuang_count,
            'echarts_emotion_peihe_count': emotion_peihe_count,
            'echarts_emotion_dichu_count': emotion_dichu_count,
            'situation_person': report_log.be_ask_name,
            'situation_time': create_time,
            'situation_sex': user.sex,
            'situation_ethnic': user.nation,
            'situation_id': user.id_number,
            'situation_databirth': situation_databirth,
            'info_person': info_person,
            'info_start': create_time,
            'info_end': end_time,
            'abnormal_count': abnormal_count,
            "total_abnormal_count": abnormal_count,
            'normal_count': emotion_peihe_count,
            'abnormal_percentage': abnormal_percentage,
            'normal_percentage': emotion_peihe_percentage,
            'bradycardia_count': report_log_dict['heart_rate_low_count'],
            "total_heart_rate_low_count": report_log_dict['heart_rate_low_count'],
            'heartbeatNormal_count': report_log_dict['heart_rate_normal_count'],
            'tachycardia_count': report_log_dict['heart_rate_high_count'],
            'total_heart_rate_high_count': report_log_dict['heart_rate_high_count'],
            'bradycardia_rate': report_log_dict['heart_rate_low_percentage'],
            'heartbeatMormal_rate': report_log_dict['heart_rate_normal_percentage'],
            'tachycardia_rate': report_log_dict['heart_rate_high_percentage'],
            'echarts_emotion_legend': echarts_emotion_legend
        }
        # 告警统计数据插入
        english_dict = {0: "one", 1: "two", 2: "three", 3: "four", 4: "five", 5: "six", 6: "seven", 7: "eight",
                        8: "nine"}
        # print("{}: 6666666".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        for data_1 in range(len(self.time_phasing)):
            alarm_dict = {
                "{}_time".format(english_dict[data_1]): self.time_phasing[data_1]["alarm_time"],
                "{}_alarmNum".format(english_dict[data_1]): self.time_phasing[data_1]["count"],
                "{}_rate".format(english_dict[data_1]): self.time_phasing[data_1]["rate"]
            }
            msg_map.update(alarm_dict)
        jiaoxing_list = []
        dichu_list = []
        konghuang_list = []
        three_mood_count = []
        three_time_count = []
        # print("{}: 77777777777".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        if len(self.time_phasing):
            alarem_all_list = self.time_phasing[:3]
            for three_emotion in range(len(alarem_all_list)):
                jiaoxing_list.append(alarem_all_list[three_emotion].get("fluke", 0))
                dichu_list.append(alarem_all_list[three_emotion].get("contradict", 0))
                konghuang_list.append(alarem_all_list[three_emotion].get("panic", 0))
                three_time_count.append(alarem_all_list[three_emotion].get("alarm_time", 0))
            try:
                for f in range(3):
                    three_mood_count.append(sum([jiaoxing_list[f], dichu_list[f], konghuang_list[f]]))
                max_mood_value = max(three_mood_count)
                max_mood_value = str(max_mood_value)
                str_max_mood = max_mood_value[:-1] + '.' + max_mood_value[-1]
                y_max_mood = int(str(math.ceil(float(str_max_mood))) + '0')
            except Exception as e:
                y_max_mood = 100
                config.LOG.error("y 轴自适应出现意外=={}".format(e))
            jdk_list = {
                "echarts_alarm_jiaoxing": ','.join([str(r) for r in jiaoxing_list]),
                "echarts_alarm_dichu": ','.join([str(f) for f in dichu_list]),
                "echarts_alarm_konghuang": ','.join([str(v) for v in konghuang_list]),
                "y_max_mood": y_max_mood,
                "echarts_alarm_yText": ','.join([str(v) for v in three_time_count]),
            }
            msg_map.update(jdk_list)

        # 告警TOP10
        alarm_ten_list = []
        # print("{}: 88888888888".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        for data in range(len(mood_state_list)):
            # print("11111111")
            alarm_ten_dict = {
                "alarm_suspicious": mood_state_list[data]['suspicious_value'],
                "alarm_timeNode": mood_state_list[data]['time_node'],
                "alarm_express": mood_state_list[data]['emotion_status'],
                "alarm_emotion": mood_state_list[data]['total_status'],
            }
            alarm_ten_list.append(alarm_ten_dict)
        msg_map.update({"TOP10_data": json.dumps(alarm_ten_list)})
        font_list = ["平和", "高兴", "轻蔑", "厌恶", "惊讶", "伤心", "害怕", "生气"]
        # rate_list = ["fear_rate", "anger_rate", "sadness_rate", "surprise_rate", "disgust_rate", "contempt_rate",
        #              "joy_rate", "neutral_rate"]
        rate_list = ["neutral_rate", "joy_rate", "contempt_rate", "disgust_rate", "surprise_rate", "sadness_rate",
                     "fear_rate", "anger_rate"]

        # 表情统计数据插入
        # print("33333333333333")
        # print("{}: 9999999999999999999".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        for data_2 in range(len(self.time_emotion_count)):
            msg_map.update({
                "emotion_{}".format(data_2 + 1): self.time_emotion_count[data_2].get('alarm_time'),
                "nine_{}".format(data_2 + 1): self.time_emotion_count[data_2].get('count')
            })
            for data_3 in range(8):
                emotion_data_dict = {
                    "{}_{}_1".format(english_dict[data_3], data_2 + 1): self.time_emotion_count[data_2][
                        font_list[data_3]],
                    "{}_{}_2".format(english_dict[data_3], data_2 + 1): self.time_emotion_count[data_2][
                        rate_list[data_3]]
                }
                msg_map.update(emotion_data_dict)
        # Echarts 所需功能
        a_list = []
        b_list = []
        echarts_list = ["平和", "生气", "害怕", "伤心", "惊讶", "厌恶", "轻蔑", "高兴"]
        negative_list = ["生气", "害怕", "伤心", "惊讶", "厌恶", "轻蔑"]
        # print("{}: 121212121212".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        for stage in self.time_emotion_count:
            for e_list in echarts_list:
                b_list.append(stage.get(e_list, 0))
            a_list.append(b_list)
            b_list = []
        # print("self.time_emotion_count:   ",self.time_emotion_count)
        # print("a_list      ",a_list)
        # print("{}: 开始耗时".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        if len(a_list) == 4:
            positive_count = int(a_list[3][0]) + int(a_list[3][-1])
            negative_count = sum(a_list[3]) - positive_count
            if sum(a_list[3]):
                positive_rate = str(round(
                    float(positive_count / sum(a_list[3]) * 100), 2)) + '%'
                negative_rate = str(round(
                    float(negative_count / sum(a_list[3]) * 100), 2)) + '%'
            else:
                positive_rate = '0.0%'
                negative_rate = '0.0%'
            try:
                # 计算全局的表情频率
                negative_mood_count = copy.deepcopy(a_list[3])
                if negative_mood_count:
                    negative_mood_count.remove(negative_mood_count[0])
                    negative_mood_count.remove(negative_mood_count[-1])
                mood_value_one = negative_list[negative_mood_count.index(max(negative_mood_count))]
                mood_value_one_count = max(negative_mood_count)
                mood_second_list = copy.deepcopy(negative_mood_count)
                negative_second_list = copy.copy(negative_list)
                negative_second_list.remove(mood_value_one)
                mood_second_list.remove(max(mood_second_list))
                mood_value_second = negative_second_list[mood_second_list.index(max(mood_second_list))]
                mood_value_second_count = max(mood_second_list)
                max_ = max(a_list[3])
            except Exception as e:
                config.LOG.debug(" 计算全局的表情频率出现错误===》{}".format(e))
                mood_value_one = ''
                mood_value_one_count = 0
                mood_value_second = ''
                mood_value_second_count = 0
                max_ = 1000

            echarts_emotion = {
                "echarts_emotion_one": ','.join([str(r) for r in a_list[0]]),
                "echarts_emotion_two": ','.join([str(f) for f in a_list[1]]),
                "echarts_emotion_three": ','.join([str(v) for v in a_list[2]]),
                "echarts_emotion_four": ','.join([str(b) for b in a_list[3]]),
                "positive_count": positive_count,
                "positive_rate": positive_rate,
                "negative_count": negative_count,
                "negative_rate": negative_rate,
                "max_value": max_,
                "emotion_negative_percentage": negative_rate,
                "echarts_negative_count": negative_count,
                "echarts_positive_count": positive_count,
                "mood_value_one": mood_value_one,
                "mood_value_one_count": mood_value_one_count,
                "mood_value_second": mood_value_second,
                "mood_value_second_count": mood_value_second_count
            }
            # print("report_log_dict['emotion_positive_count']", report_log_dict['emotion_positive_count'])
            msg_map.update(echarts_emotion)

        # print("4444444444444444444444444444")
        au_dict_temp = report_log_dict['au_dict']
        au_dict = {i[0]: i[1] for i in sorted(au_dict_temp.items(), key=lambda item: item[1], reverse=True)}
        # au波动最大
        au_max_data = sorted(au_dict_temp.items(), key=lambda item: item[1], reverse=True)[0]
        # text = self.au_introduce(au_max_data[0])
        # print("{}: AU".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        au_highest_description = self.au_annotation(au_max_data[0])
        msg_map.update({
            'au_highest': str(au_max_data[0]),
            'au_highest_count': au_max_data[1],
            'au_highest_description': au_highest_description
        })
        msg_map.update(au_dict)
        msg_map.update({
            'echarts_au': ','.join([str(i) for i in au_dict_temp.values()]),
            'echarts_heart_rate_low': report_log_dict['heart_rate_low_count'],
            'echarts_heart_rate_normal': report_log_dict['heart_rate_normal_count'],
            'echarts_heart_rate_high': report_log_dict['heart_rate_high_count'],
            'heart_rate_high_count': report_log_dict['heart_rate_high_count'],
            'heart_rate_low_count': report_log_dict['heart_rate_low_count'],
            'echarts_abnormal_count': abnormal_count,
            'echarts_normal_count': emotion_peihe_count,
        })
        if config.BS4_object is None:
            LOG.debug("{}: 重新加载打开模板".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
            f = open(self.template, 'rb')
            s = BeautifulSoup(f, "lxml")
            f.close()
        else:
            s = config.BS4_object
        # print("{}: 写入".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        # print("{}: 232323232323232323".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        for key, value in msg_map.items():
            try:
                # 'NoneType' object has no attribute 'string'
                s.find('', {'id': key}).string = str(value)
            except Exception as e:
                # 因为有些字段没有数据，为None
                # print(key, ":", value)
                LOG.error('in pdf:%s' % str(e))
                continue
        # print("{}: 写入结束".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        html_bytes = s.encode('utf-8')
        return html_bytes

    # 生成报告, 并转换为pdf文件
    def generate_pdf(self, user, report_log, file_path='report.pdf'):
        if not self.html_path:
            # 将报告统计的数据内容, 填充到html文件
            file_path = self.generate_html(user, report_log)
        # 将html文件转为pdf文件
        return file_path

    # 跟新html文件, 将数据写入
    def generate_html(self, user, report_log):
        self.html_path = 'tmp.html'
        # print("{}: 开始计算".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        html_bytes = self._fill_content(user, report_log)
        try:
            file_path = os.path.join(DEFAULT_TEMPLATE_DATA_DIR, '%s.html' % int(report_log.create_time))
            with open(file_path, "wb") as file:
                file.write(html_bytes)
            # print("{}: 结束计算".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
            return file_path
        except Exception as e:
            LOG.error("generate_html %s" % str(e))
            return None

    def pdf_from_file(self, input, output_path, configuration):
        """
        Convert HTML file or files to PDF document
        :param input: path to HTML file or list with paths or file-like object
        :param output_path: path to output PDF file. False means file will be returned as string.
        :param options: (optional) dict with wkhtmltopdf options, with or w/o '--'
        :param toc: (optional) dict with toc-specific wkhtmltopdf options, with or w/o '--'
        :param cover: (optional) string with url/filename with a cover html page
        :param css: (optional) string with path to css file which will be added to a single input file
        :param configuration: (optional) instance of pdfkit.configuration.Configuration()
        :param configuration_first: (optional) if True, cover always precedes TOC
        Returns: True on success
        """
        pdfkit.from_file(input, output_path, configuration=configuration)

    def au_introduce(self, text):
        au_dict_temp = {
            'AU1': '抬起眉毛内角',
            'AU2': '抬起眉毛外角',
            'AU4': '皱眉（降低眉毛)',
            'AU5': '上眼睑上升',
            'AU6': '脸颊提升和眼轮匝肌外圈收紧',
            'AU7': '眼轮匝肌内圈收紧',
            'AU9': '皱鼻',
            'AU10': '拉动上嘴唇向上运动',
            'AU11': '拉动人中部位的皮肤向上',
            'AU12': '拉动嘴角倾斜向上',
            'AU13': '急剧的嘴唇拉动',
            'AU14': '收紧嘴角',
            'AU15': '拉动嘴角向下倾斜',
            'AU16': '拉动下唇向下',
            'AU17': '推动下唇向上',
            'AU18': '噘嘴',
            'AU20': '嘴角拉伸',
            'AU22': '收紧双唇向外翻',
            'AU23': '收紧嘴唇',
            'AU24': '嘴唇相互按压',
            'AU25': '嘴部放松',
            'AU26': '张嘴',
            'AU27': '张嘴',
            'AU28': '吸唇',
            'AU43': '闭眼、眨眼',
            'AU45': '闭眼、眨眼'
        }
        if text in au_dict_temp:
            return au_dict_temp[text]
        else:
            return ''

    def au_annotation(self, text):
        au_dict_annotation = {
            'AU1': 'AUI的产生往往伴有悲伤的情绪。',
            'AU2': 'AU2的产生往往伴有悲伤的情绪。',
            'AU4': 'AU4的产生往往伴有思考、生气、愤怒、疼痛、焦虑、困惑的情绪。',
            'AU5': 'AU5的产生往往伴有惊讶、愤怒、恐惧的情绪。',
            'AU6': 'AU6的产生往往伴有极度悲伤的情绪。',
            'AU7': 'AU7的产生往往伴有恐惧、愤怒的情绪。',
            'AU9': 'AU9的产生往往伴有厌恶、强烈愤怒的情绪。',
            'AU10': 'AU10的产生往往伴有厌恶的情绪。',
            'AU11': 'AU11的产生往往伴有恐惧的情绪。',
            'AU12': 'AU12的产生往往伴有开心的情绪。',
            'AU13': 'AU13的产生往往伴有开心的情绪。',
            'AU14': 'AU14的产生往往伴有思考的情绪。',
            'AU15': 'AU15的产生往往伴有悲伤的情绪。',
            'AU16': 'AU15的产生往往伴有悲伤的情绪。',
            'AU17': 'AU17的产生往往伴有悲伤、愤怒的情绪。',
            'AU18': 'AU18的产生往往伴有委屈的情绪。',
            'AU20': 'AU20的产生往往伴有恐惧的情绪。',
            'AU22': 'AU22的产生往往伴有厌恶、愤怒的情绪。',
            'AU23': 'AU23的产生往往伴有愤怒的情绪。',
            'AU24': 'AU23的产生往往伴有焦虑、担忧的情绪。',
            'AU25': 'AU25的产生往往伴有惊讶的情绪。',
            'AU26': 'AU26的产生往往伴有惊讶的情绪。',
            'AU27': 'AU27的产生往往伴有惊讶的情绪。',
            'AU28': 'AU28的产生往往伴有犹豫不决、担忧的情绪。',
            'AU43': 'AU43的产生往往伴有恐惧的情绪。',
            'AU45': 'AU45的产生往往伴有恐惧的情绪。'
        }
        if text in au_dict_annotation:
            return au_dict_annotation[text]
        else:
            return ''

    def au_change(self, au):
        if au == "AU45" or au == "AU43":
            return "AU43、AU45"
        if au == "AU25" or au == "AU26" or au == "AU27":
            return "AU25、AU26、AU27"
        return au

    def countData(self, tran_create_time=config.inquest_start_time, tran_end_time=config.end_start_time):
        # echarts表情统计时间段
        echarts_time_list = []
        status_count = {}
        status_count['1'] = []
        status_count['2'] = []
        status_count['3'] = []
        num_dict = {"0": u"零", "1": u"一", "2": u"二", "3": u"三"}
        fluke = 0  # 侥幸
        contradict = 0  # 抵触
        panic = 0  # 恐慌
        all_alarm_count = 0
        # 计算总时长
        total_time = tran_end_time - tran_create_time
        # 分三个阶段的平均时间(分钟)
        mean_time = round(total_time / 60 / 3)
        # 第一时间阶段的开始和结束时间
        start_time_1, all_start_time_1, start_time_1_second = self.change_time(tran_create_time)
        end_time_1, all_end_time_1, end_time_1_second = self.change_time(tran_create_time + mean_time * 60)
        echarts_time_one = '第一时间段：{}-{}'.format(start_time_1_second, end_time_1_second)
        echarts_time_list.append(echarts_time_one)
        # 第二时间阶段的开始和结束时间
        start_time_2, all_start_time_2, start_time_2_second = self.change_time(tran_create_time + mean_time * 60)
        end_time_2, all_end_time_2, end_time_2_second = self.change_time(tran_create_time + mean_time * 60 * 2)
        echarts_time_two = '第二时间段：{}-{}'.format(start_time_2_second, end_time_2_second)
        echarts_time_list.append(echarts_time_two)
        # 第三时间阶段的开始和结束时间
        start_time_3, all_start_time_3, start_time_3_second = self.change_time(tran_create_time + mean_time * 60 * 2)
        end_time_3, all_end_time_3, end_time_3_second = self.change_time(
            tran_create_time + mean_time * 60 * 2 + (total_time / 60 - mean_time * 2) * 60)
        echarts_time_three = '第三时间段：{}-{}'.format(start_time_3_second, end_time_3_second)
        echarts_time_list.append(echarts_time_three)

        for alarm in self.alarm_data_count:
            if alarm and alarm['time'] <= all_end_time_1:
                status_count['1'].append(alarm['total_status'])
            if alarm and all_end_time_1 < alarm['time'] <= all_end_time_2:
                status_count['2'].append(alarm['total_status'])
            if alarm and all_end_time_2 < alarm['time'] <= all_end_time_3:
                status_count['3'].append(alarm['total_status'])
        # print("status_count   ",status_count)
        # print("阶段的告警情况：{}".format(status_count))
        for s, v in status_count.items():
            alarm_count_list = Counter(v).most_common()
            for count_list in alarm_count_list:
                if count_list[0] == '侥幸':
                    fluke = count_list[1]
                elif count_list[0] == '抵触':
                    contradict = count_list[1]
                elif count_list[0] == '恐慌':
                    panic = count_list[1]
            if s == '1':
                start_timer = start_time_1_second
                end_timer = end_time_1_second
            elif s == '2':
                start_timer = start_time_2_second
                end_timer = end_time_2_second
            else:
                start_timer = start_time_3_second
                end_timer = end_time_3_second

            if len(self.alarm_data_count) * 100 != 0:
                rate = str(round(
                    float(len(v) / len(self.alarm_data_count) * 100), 2)) + '%'
            else:
                rate = 0
            count_dict = {
                "alarm_time": '第{}阶段：{}'.format(num_dict[s], start_timer + '-' + end_timer),
                'fluke': fluke,
                'contradict': contradict,
                'panic': panic,
                'count': len(v),
                'statr_timer': start_timer,
                'end_timer': end_timer,
                'rate': rate
            }
            all_alarm_count += len(v)
            self.time_phasing.append(count_dict)
            # 重置
            fluke = 0
            contradict = 0
            panic = 0
        alarm_dict = {
            'alarm_time': '{}时间：{}'.format(text1, start_time_1_second + '-' + end_time_3_second),
            'count': all_alarm_count,
            'rate': '100%',
            'end': True
        }
        # print("status_count  ", status_count)
        echarts_time_all = '{}总时间：{}-{}'.format(text1, start_time_1_second, end_time_3_second)
        echarts_time_list.append(echarts_time_all)
        self.time_phasing.append(alarm_dict)
        self.emotion_count(start_time_1_second, start_time_2_second, start_time_3_second, end_time_1_second,
                           end_time_2_second, end_time_3_second, all_start_time_1, all_start_time_2,
                           all_start_time_3, all_end_time_1, all_end_time_2, all_end_time_3)
        return echarts_time_list

    def emotion_count(self, start_time_1, start_time_2, start_time_3, end_time_1, end_time_2, end_time_3,
                      all_start_time_1, all_start_time_2,
                      all_start_time_3, all_end_time_1, all_end_time_2, all_end_time_3):
        num_dict_1 = {0: u"零", 1: u"一", 2: u"二", 3: u"三"}
        emotion_time_list = [(start_time_1, end_time_1), (start_time_2, end_time_2), (start_time_3, end_time_3)]
        all_emotion_time_list = [(all_start_time_1, all_end_time_1), (all_start_time_2, all_end_time_2),
                                 (all_start_time_3, all_end_time_3)]
        # print("时间阶段：{}".format([(start_time_1, end_time_1), (start_time_2, end_time_2), (start_time_3, end_time_3)]))
        emotion_count_data = 0
        t = 0
        v = 0
        # print("{}: 查询数据".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        # print("emotion_time_list   ",emotion_time_list)
        for i in emotion_time_list:
            documents = config.MONGODB_COLLECTION_FOR_READ.find({
                'inquest_uuid': self.inquest_uuid,
                'time': {
                    '$gte': all_emotion_time_list[v][0],
                    '$lte': all_emotion_time_list[v][1]
                }
            })
            v += 1
            emotion_data_dict = self.emotion_dict(documents)
            # 计算表情
            for j in emotion_data_dict:
                emotion_count_data += emotion_data_dict[j]
            if emotion_count_data != 0:
                emotion_dict = {
                    "alarm_time": '第{}阶段'.format(num_dict_1[t + 1]),
                    '害怕': emotion_data_dict['害怕'],
                    '生气': emotion_data_dict['生气'],
                    '伤心': emotion_data_dict['伤心'],
                    '惊讶': emotion_data_dict['惊讶'],
                    '厌恶': emotion_data_dict['厌恶'],
                    '轻蔑': emotion_data_dict['轻蔑'],
                    '高兴': emotion_data_dict['高兴'],
                    '平和': emotion_data_dict['平和'],
                    'fear_rate': str(round(
                        float((emotion_data_dict['害怕'] / emotion_count_data) * 100), 2)) + '%',
                    'anger_rate': str(round(
                        float((emotion_data_dict['生气'] / emotion_count_data) * 100), 2)) + '%',
                    'sadness_rate': str(round(
                        float((emotion_data_dict['伤心'] / emotion_count_data) * 100), 2)) + '%',
                    'surprise_rate': str(round(
                        float((emotion_data_dict['惊讶'] / emotion_count_data) * 100), 2)) + '%',
                    'disgust_rate': str(round(
                        float((emotion_data_dict['厌恶'] / emotion_count_data) * 100), 2)) + '%',
                    'contempt_rate': str(round(
                        float((emotion_data_dict['轻蔑'] / emotion_count_data) * 100), 2)) + '%',
                    'joy_rate': str(round(
                        float((emotion_data_dict['高兴'] / emotion_count_data) * 100), 2)) + '%',
                    'neutral_rate': str(round(
                        float((emotion_data_dict['平和'] / emotion_count_data) * 100), 2)) + '%',
                    'count': emotion_count_data,
                    'start_time': i[0],
                    'end_time': i[1]
                }
                self.time_emotion_count.append(emotion_dict)
                emotion_count_data = 0
                t += 1
            else:
                emotion_count_data = 1
                emotion_dict = {
                    "alarm_time": '第{}阶段'.format(num_dict_1[t + 1]),
                    '害怕': emotion_data_dict['害怕'],
                    '生气': emotion_data_dict['生气'],
                    '伤心': emotion_data_dict['伤心'],
                    '惊讶': emotion_data_dict['惊讶'],
                    '厌恶': emotion_data_dict['厌恶'],
                    '轻蔑': emotion_data_dict['轻蔑'],
                    '高兴': emotion_data_dict['高兴'],
                    '平和': emotion_data_dict['平和'],
                    'fear_rate': str(round(
                        float((emotion_data_dict['害怕'] / emotion_count_data) * 100), 2)) + '%',
                    'anger_rate': str(round(
                        float((emotion_data_dict['生气'] / emotion_count_data) * 100), 2)) + '%',
                    'sadness_rate': str(round(
                        float((emotion_data_dict['伤心'] / emotion_count_data) * 100), 2)) + '%',
                    'surprise_rate': str(round(
                        float((emotion_data_dict['惊讶'] / emotion_count_data) * 100), 2)) + '%',
                    'disgust_rate': str(round(
                        float((emotion_data_dict['厌恶'] / emotion_count_data) * 100), 2)) + '%',
                    'contempt_rate': str(round(
                        float((emotion_data_dict['轻蔑'] / emotion_count_data) * 100), 2)) + '%',
                    'joy_rate': str(round(
                        float((emotion_data_dict['高兴'] / emotion_count_data) * 100), 2)) + '%',
                    'neutral_rate': str(round(
                        float((emotion_data_dict['平和'] / emotion_count_data) * 100), 2)) + '%',
                    'count': emotion_count_data,
                    'start_time': i[0],
                    'end_time': i[1]
                }
                self.time_emotion_count.append(emotion_dict)
                emotion_count_data = 0
                t += 1

        emotion_dict_ = {
            '害怕': 0,
            '生气': 0,
            '伤心': 0,
            '惊讶': 0,
            '厌恶': 0,
            '轻蔑': 0,
            '高兴': 0,
            '平和': 0
        }
        all_emotion_data = 0
        for data_emotion in self.time_emotion_count:
            all_emotion_data += data_emotion["count"]
            for num_data in data_emotion:
                if num_data == '害怕' or num_data == '生气' or num_data == '伤心' or num_data == '惊讶' \
                        or num_data == '厌恶' or num_data == '轻蔑' \
                        or num_data == '高兴' or num_data == '平和':
                    emotion_dict_[num_data] += data_emotion[num_data]
        if all_emotion_data == 0:
            all_emotion_data = 1
        emotion_dict_["fear_rate"] = str(round(
            float((emotion_dict_['害怕'] / all_emotion_data) * 100), 2)) + '%'
        emotion_dict_["anger_rate"] = str(round(
            float((emotion_dict_['生气'] / all_emotion_data) * 100), 2)) + '%'
        emotion_dict_["sadness_rate"] = str(round(
            float((emotion_dict_['伤心'] / all_emotion_data) * 100), 2)) + '%'
        emotion_dict_["surprise_rate"] = str(round(
            float((emotion_dict_['惊讶'] / all_emotion_data) * 100), 2)) + '%'
        emotion_dict_["disgust_rate"] = str(round(
            float((emotion_dict_['厌恶'] / all_emotion_data) * 100), 2)) + '%'
        emotion_dict_["contempt_rate"] = str(round(
            float((emotion_dict_['轻蔑'] / all_emotion_data) * 100), 2)) + '%'
        emotion_dict_["joy_rate"] = str(round(
            float((emotion_dict_['高兴'] / all_emotion_data) * 100), 2)) + '%'
        emotion_dict_["neutral_rate"] = str(round(
            float((emotion_dict_['平和'] / all_emotion_data) * 100), 2)) + '%'
        emotion_dict_["count"] = all_emotion_data
        emotion_dict_['alarm_time'] = '{}总时间'.format(text1)
        self.time_emotion_count.append(emotion_dict_)
        # print("{}: 查询结束".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))

    def change_time(self, now_time):
        switch_time = time.strftime("%H:%M", time.localtime(now_time))
        all_switch_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_time))
        switch_time_second = time.strftime("%H:%M:%S", time.localtime(now_time))
        return switch_time, all_switch_time, switch_time_second

    def emotion_dict(self, documents):
        # print("{}: 表情查询开始".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        emotion_data_count = {
            '害怕': 0,
            '生气': 0,
            '伤心': 0,
            '惊讶': 0,
            '厌恶': 0,
            '轻蔑': 0,
            '高兴': 0,
            '平和': 0,
        }
        for document in documents:
            if document.get('emotion_data'):
                emotion_num = document.get('emotion_data')
                # 判断每帧表情的数值是否大于基线数据，大于则统计+1
                if emotion_num.index(max(emotion_num)) == 0:
                    emotion_data_count['害怕'] += 1
                if emotion_num.index(max(emotion_num)) == 1:
                    emotion_data_count['生气'] += 1
                if emotion_num.index(max(emotion_num)) == 2:
                    emotion_data_count['伤心'] += 1
                if emotion_num.index(max(emotion_num)) == 3:
                    emotion_data_count['惊讶'] += 1
                if emotion_num.index(max(emotion_num)) == 4:
                    emotion_data_count['厌恶'] += 1
                if emotion_num.index(max(emotion_num)) == 5:
                    emotion_data_count['轻蔑'] += 1
                if emotion_num.index(max(emotion_num)) == 6:
                    emotion_data_count['高兴'] += 1
                if emotion_num.index(max(emotion_num)) == 7:
                    emotion_data_count['平和'] += 1
        # print("{}: 表情查询结束".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        return emotion_data_count