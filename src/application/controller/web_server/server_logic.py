import json
from copy import deepcopy
from threading import Thread
import time, uuid, os, requests
from functools import lru_cache

import psutil

from application.controller import config
from application.controller.config import text1
from application.controller.common import command
from application.controller.config import LOG
from application.controller.report.pdfmodule import generate_pdf
from application.controller.tools.ffmpeg_record import VideoRecord
from application.controller.report.get_report_tool import get_report_info
from application.model.model_data import PersonalManager, InquestRecord, QuestionRecord


class Inquest(object):
    def __init__(self):
        self.video_path = None
        # 引入录制视频模块
        self.video_record_tool = VideoRecord()
        # 引入mongodb写入线程
        self.view_subscriber_mongodb_handler = config.NAME_THREADS.get("mongo_")
        self.person_info = None

    @staticmethod
    def get_record_path():
        video_path = config.DEFAULT_INQUEST_VIDEO_DATA_DIR + "/" + str(
            config.Inquest_Room) + "_" + config.inquest_uuid + ".mp4"
        return video_path

    @staticmethod
    @lru_cache(maxsize=16)
    def inquest_record(filter_date, filter_ask_name, filter_be_ask_name, filter_be_ask_id_number, pageNum, pageSize):
        if len(filter_date) > 0:
            start_date = time.mktime(time.strptime(filter_date, '%Y-%m-%d'))
            end_date = start_date + 86400
            records = InquestRecord.get_record_by_filter(date_start=start_date,
                                                         date_end=end_date,
                                                         ask_name=filter_ask_name,
                                                         be_ask_name=filter_be_ask_name,
                                                         be_ask_id_number=filter_be_ask_id_number)
            LOG.debug("审讯记录: %s" % records)
        else:
            records = InquestRecord.get_record_by_filter(ask_name=filter_ask_name,
                                                         be_ask_name=filter_be_ask_name,
                                                         be_ask_id_number=filter_be_ask_id_number)
        # 如果第一条记录的报道没生成，则不显示

        list_data = []

        records = [record for record in records if record[-7]]
        # record_len = len(records)
        if len(records):
            all_list_count = len(records)
            begin_item_index = (pageNum - 1) * pageSize
            end_item_index = min(begin_item_index + pageSize, all_list_count)
            current_person_list = records[begin_item_index:end_item_index]
            for data in current_person_list:
                list_data.append(Inquest.transverter_data(data))

        temp_data = {"success": "true", "status": 200, "msg": "query inquest list success",
                     "obj": {"count": len(records), "list": list_data},
                     "errorNo": "null", "errorMsg": "null", "token": ""}
        return temp_data

    @staticmethod
    def inquest_delete(data):
        ret = False
        id = data.get("id", '')
        if id:
            if 0 == InquestRecord.delete_record_by_id(id):
                ret = True
                return ret
        return ret

    @staticmethod
    def transverter_data(data):
        """
           idType： 0-中国居民身份证，1-港澳居民来往内地通行证，2-台湾居民来往大陆通行证
        """
        data = {"inquestee": data[7], "code": "", "idType": data[-1],
                "videoUrl": data[5],
                "inquester": data[6], "alarmNum": data[-2],
                "startTime": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[3])),
                "id": data[0],
                "attachmentUrl": "file:///" + data[-7],
                "endTime": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[4])),
                "type": data[-6],
                "uuid": data[1],
                "IDNumber": data[8]}
        return data

    @staticmethod
    def openReport(report_path):
        ret = False
        if report_path is not None and len(report_path) > 0:
            LOG.debug("正在打开 %s" % report_path)
            try:
                cmd = 'start "" "%s"' % report_path
                command(cmd, is_shell=True)
                LOG.debug("成功打开 %s" % report_path)
                ret = True
                return ret
            except Exception as e:
                LOG.error("check_report_log_error %s" % str(e))
                return ret
        else:
            return ret


    @staticmethod
    @lru_cache(maxsize=16)
    def get_alarm(uuid, pageNum, pageSize):

        count, all_question = QuestionRecord.get_objects_by_inquest_uuid_start_time(inquest_uuid=uuid, pageNum=pageNum,
                                                                             pageSize=pageSize)
        list_ = []

        for question in all_question:
            data= {
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
                "mainExpressionNum": question.emotion_degree_count
                # "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            }
            list_.append(data)

        response = {
            "totalNum": count,
            "list": list_,
        }
        return response

    def start_inquest(self, person_info):
        config.report_ = True
        self.person_info = person_info
        person_id_number = self.person_info.get("idNumber", None)
        # 过滤掉身份证号中的空格
        # person_id_number = person_id_number.strip()
        inquester = self.person_info.get("inquester", None)
        answer = self.person_info.get("inquestee", None)
        sex = self.person_info.get("gender", None)
        idType = self.person_info.get("idType", None)
        caseType = self.person_info.get("caseType", None)
        subCaseType = self.person_info.get("subCaseType", None)
        if config.SUSPICIOUS_VALUE_QUEUE:
            config.SUSPICIOUS_VALUE_QUEUE.clear()
        config.inquest_status = True
        # 更新全局变量--审讯/谈话uuid
        config.inquest_uuid = str(uuid.uuid1())
        # print("uuid: ", config.inquest_uuid)
        # 更新全局变量--审讯/谈话开始时间
        config.START_TIME = config.inquest_start_time = time.time()
        try:
            self.video_path = self.get_record_path()
            LOG.info("开始录制************{}".format(self.video_path))
            self.video_record_tool.start_record(video_source_url=config.DST_STREAM,
                                                file_path=self.video_path)
            LOG.info("start record inquest video success")
        except Exception as e:
            LOG.error(e)
        # 生成审讯/谈话记录
        sex_people = deepcopy(sex)
        try:
            if sex == 0:
                sex = "男"
            elif sex == 1:
                sex = "女"
            """
            0-中国居民身份证，1-港澳居民来往内地通行证，2-台湾居民来往大陆通行证
            """
            person_opt = PersonalManager()
            person = person_opt.get_one_opt_by_number(person_id_number)
            if person:
                """搜索到了，修改"""
                LOG.debug("被询人员已存在，更新人员信息")
                action_time = time.time()
                person_opt.update_opt(person.id, answer, sex, person.nation, person.educational_level,
                                      person.marital_status, person.birthday, person.id_number,
                                      "", person.household_register, person.home_address, action_time)
                config.INQUEST_PERSON_ID = person.id
            else:
                """没有搜索到，添加"""
                LOG.debug("被询人第一次入库")
                action_time = time.time()
                inquest_person_id = person_opt.add_opt(answer, sex, "", "", "", "", person_id_number, "", "", "",
                                                       action_time, idType)
                config.INQUEST_PERSON_ID = inquest_person_id
            if config.VIEW_CFG.get("interaction", 0) == 1:
                config.LOG.info("开启审讯详情................")
                ReqUrl = "http://%s:%s/bm/beginInquest" % (
                    config.VIEW_CFG.get("server_ip", "192.168.16.104"),
                    config.VIEW_CFG.get("server_port", "8181"))
                ReqHeader = {'content-type': 'application/json'}
                if idType == "中国居民身份证":
                    idType = 0
                elif idType == "港澳居民来往内地通行证":
                    idType = 1
                elif idType == "台湾居民来往大陆通行证":
                    idType = 2
                inquest_data = {"roomId": config.Inquest_Room,
                                "uuid": config.inquest_uuid,
                                "askPeople": inquester,
                                "personRequested": answer,
                                "gender": sex_people,
                                "idType": idType,
                                "idNumber": person_id_number,
                                "caseType": caseType,
                                "subCaseType": subCaseType,
                                "startTime": time.strftime("%Y-%m-%d %H:%M:%S",
                                                           time.localtime(config.inquest_start_time))
                                }
                print(inquest_data)

                try:
                    requests.post(url=ReqUrl,
                                  json=inquest_data,
                                  headers=ReqHeader)
                except Exception as e:
                    LOG.warn("bm start_inquest connection failed")
            self.inquest_record_id = InquestRecord.add_opt(config.inquest_uuid,
                                                           video_file_path=self.video_path.replace("\\", "/"),
                                                           ask_name=inquester,
                                                           be_ask_name=answer,
                                                           be_ask_id_number=person_id_number,
                                                           id_type=idType,
                                                           inquest_type=1,
                                                           inquest_person_id=config.INQUEST_PERSON_ID,
                                                           report_info="",
                                                           case_number=self.person_info["caseType"],
                                                           case_type=self.person_info["subCaseType"],
                                                           classification="")
            LOG.info("add inquest record success")
        except Exception as e:
            LOG.error(e)

    def stop_cs(self):
        Inquest.inquest_record.cache_clear()
        return InquestRecord.get_no_attachment_url_filter()



    def stop_inquest(self):
        """
                {'inquester': '', 'answer': '1', 'sex': '男', 'id': '330781198509073835', 'inquest_mode': 1, 'template_mode': 1,
                     'case_number': '', 'case_type': '廉政谈话', 'classification': '实时谈话'}
               """
        # config.BASE_STOP_TIME = time.time()
        # 关闭ffmpeg
        ffmpeg_list = []
        # 更新全局变量--审讯状态--标记为停止审讯
        bm_end_data = {
            "roomId": config.Inquest_Room
        }
        if config.VIEW_CFG.get("interaction", 0) == 1:
            ReqUrl = "http://%s:%s/bm/endInquest" % (config.VIEW_CFG.get("server_ip", "192.168.16.104"),
                                                     config.VIEW_CFG.get("server_port", "8181"))
            ReqHeader = {'content-type': 'application/json'}
            try:
                requests.post(url=ReqUrl, json=bm_end_data, headers=ReqHeader)
                LOG.debug("停止审讯信息上传成功")
            except Exception as e:
                LOG.warn("停止审讯信息上传失败===={}".format(e))
        config.inquest_status = False
        config.inquest_data = False
        inquest_uuid = deepcopy(config.inquest_uuid)
        # 更新全局变量--审讯uuid
        config.ALARM_START_TIME = None
        config.ALARM_RECORDING_STATUS = False

        # 结束录制审讯视频
        self.video_record_tool.stop_record(self.video_path)
        # try:
        #     # 检测服务当前启动的数量，只保留最新启动的服务，节省内存使用率
        #     for proc in psutil.process_iter():
        #         if "ffmpeg.exe".lower() in proc.name().lower(): ffmpeg_list.append(proc)
        #     if len(ffmpeg_list) > 0:
        #         for i in ffmpeg_list: os.popen('taskkill -f -pid %s' % i.pid);LOG.debug("ffmpeg已关闭.......")
        # except Exception as e:
        #     LOG.error('ffmpeg关闭失败-->{}'.format(e))
        config.SUSPICIOUS_STATUS = None
        config.MONGODB_EMOTION_DATA = None
        config.DASH_BOARD_BEGIN_TIME = None
        config.heartbeatCnt = 0
        config.ALARM_DATA_QUEUE.clear()
        config.DASH_BOARD_WINDOW_1.clear()
        config.DASH_BOARD_WINDOW_2.clear()
        config.DASH_BOARD_WINDOW_3.clear()
        config.DASH_BOARD_WINDOW_4.clear()
        config.DASH_BOARD_WINDOW_5.clear()
        config.DASH_BOARD_WINDOW_6.clear()

        # 更新审讯/谈话记录信息,
        # 1. 更新结束时间
        # TODO 2. 更新inquest_person_id（人员入库是异步的，有可能出现审讯记录入库时config.INQUEST_PERSON_ID还未更新的情况）
        InquestRecord.update_opt(self.inquest_record_id, config.INQUEST_PERSON_ID)

        update_time = time.time()
        # 审讯信息上传到BM
        inq = InquestRecord.get_opt_all_by_id(inquest_id=self.inquest_record_id)
        try:
            bm_create_time = inq.create_time
            bm_end_time = inq.inquest_end_time
        except Exception as e:
            LOG.error("时间查询出现状况...........")
            bm_create_time = config.inquest_start_time
            bm_end_time = update_time
        bm_data = {
            "roomId": config.Inquest_Room,
            "uuid": config.inquest_uuid,
            "type": self.person_info["subCaseType"],
            "inquester": self.person_info["inquester"],
            "inquestee": self.person_info["inquestee"],
            "IDNumber": self.person_info["idNumber"],
            "startTime": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(bm_create_time)),
            "endTime": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(bm_end_time)),
            "alarmNum": 0
        }
        # 记录结束时间
        config.end_start_time = time.time()
        # print("{}: 生成审讯报告".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        Thread(target=self.gen_log,
               args=(self.inquest_record_id, inquest_uuid)).start()

        # TODO FTP上传到服务器
        # bm通信
        if self.video_path and config.VIEW_CFG.get("interaction", 0) == 1:
            lable_video = {"path": self.video_path, "lable": True}
            config.FTP_UPLOAD_FILE.put(lable_video)
            config.ADD_INQUEST_BM_DATA.put(bm_data)

        if config.last_video_path in config.all_video_path:
            aindex = config.all_video_path.index(config.last_video_path)
            if aindex:
                alist = config.all_video_path[(aindex + 1)::]
                for videopath in alist:
                    config.bad_video.append(videopath)
        # 初始化
        if config.VIEW_CFG.get("interaction", 0) == 1 and self.view_subscriber_mongodb_handler:
            try:
                self.view_subscriber_mongodb_handler.conn.close()
                self.view_subscriber_mongodb_handler.conn = None
                LOG.info("rabbitmq close the success")
            except Exception as e:
                self.view_subscriber_mongodb_handler.conn = None
                LOG.debug("rabbitmq close the failed=={}！！！！！！！".format(e))
        config.all_video_path.clear()
        config.bad_video.clear()


        try:
            # 查找告警录制失败的视频文件，删除
            if self.view_subscriber_mongodb_handler:
                if self.view_subscriber_mongodb_handler.video_record_obj:
                    if config.alarm_data_count:
                        alarm_path_list = []
                        for alarm in config.alarm_data_count:
                            alarm_path_list.append(alarm['video_path'])
                        if self.view_subscriber_mongodb_handler.alarm_video_path not in alarm_path_list:
                            config.bad_video.append(self.view_subscriber_mongodb_handler.alarm_video_path)
                    # self.view_subscriber_mongodb_handler.video_record_obj.stop_record()
        except Exception as e:
            LOG.error("关闭抛出异常》》》》》{}".format(e))

        # 删除无用视频
        try:
            for i in config.bad_video:
                if os.path.exists(i):
                    os.remove(i)
        except Exception as e:
            LOG.error("删除无用视频出现意外=={}！！！！！！！".format(e))

            # 筛选除去无用的告警
        # if config.last_alarm_data in config.alarm_data_count:
        #     bindex = config.alarm_data_count.index(config.last_alarm_data)
        #     if bindex:
        #         config.alarm_data_count = config.alarm_data_count[:(bindex + 1)]
                # todo:mongodb也要删除对应的数据
                # uuid = config.last_alarm_data["uuid"]
                # timeStamp =  config.last_alarm_data["timeStamp"]



    def gen_log(self, inquest_record_id, inquest_uuid):
        inquest = InquestRecord.get_opt_all_by_id(inquest_id=inquest_record_id)
        report_info = get_report_info(inquest_uuid)
        InquestRecord.update_opt_by_inquest_uuid(inquest_uuid,
                                                 report_info=json.dumps(
                                                     report_info))
        # 生成报告, 返回报告的路径
        # print("{}: 构建报告".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        try:
            report_path = generate_pdf(user_id_num=inquest.be_ask_id_number,
                                       report_id=inquest_record_id)
        except Exception as e:
            LOG.error("generate_pdf_error %s" % str(e))
        # print("{}: 构建结束".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        config.get_report = True
        Inquest.inquest_record.cache_clear()
        LOG.info("生成" + text1 + "报告成功>>并退出")
