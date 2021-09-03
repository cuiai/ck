import os
import requests, time
from ftplib import FTP
from threading import Thread

from application.controller import config
from application.controller.config import bm_ip, bm_port, bm_user, bm_password, bm_videoPath, LOG, bm_server_port, \
    FTP_UPLOAD_FILE, ADD_INQUEST_BM_DATA, VIEW_CFG, ADD_REPORT_BM_DATA


"""
服务启动的时候就启动
作用:向bm上传全程视频、上传审讯记录、上传审讯报告

需要优化
"""
class Upload_File(Thread):
    def __init__(self):
        super(Upload_File, self).__init__()
        self.setDaemon(True)
        self.setName('Upload_File')
        self.is_exit = False
        self.f = None
        self.time = time.time()
        self.is_update = None

    def exit(self):
        self.is_exit = True

    def run(self):
        LOG.info("Thread ftp_upload_file started")
        while True:
            try:
                if self.is_exit:
                    LOG.debug("退出....................................")
                    break
                if FTP_UPLOAD_FILE.qsize():
                    # lable_video = {"path": self.alarm_video_path, "lable": False}
                    lable_video = FTP_UPLOAD_FILE.get()
                    file_path = lable_video.get("path")
                    lable_ = lable_video.get("lable")
                    LOG.debug("得到一条====={}".format(file_path))
                    if ADD_INQUEST_BM_DATA.qsize():
                        if lable_:
                            # LOG.debug("总视频上传成功，开始上传审讯记录与报告.......{}".format(lable_))
                            bm_data = ADD_INQUEST_BM_DATA.get()
                            ReqUrl = "http://%s:%s/bm/addInquest" % (
                                VIEW_CFG.get("server_ip", "192.168.16.104"),
                                VIEW_CFG.get("server_port", "8181"))
                            ReqHeader = {'content-type': 'application/json'}
                            try:
                                requests.post(url=ReqUrl, json=bm_data, headers=ReqHeader)
                                LOG.debug("结束审讯详情上传成功")
                            except Exception as e:
                                LOG.warn("结束审讯详情上传失败===={}".format(e))
                            self.is_update = True
                if ADD_REPORT_BM_DATA.qsize():
                    if self.is_update:
                        bm_report_data = ADD_REPORT_BM_DATA.get()
                        # bm_report_data格式 {"path": html_path, "uuid": config.inquest_uuid}
                        LOG.debug("bm_report_data  ", bm_report_data)
                        data = {"uuid": bm_report_data.get("uuid")}
                        report_file_path = bm_report_data.get("path")
                        Report_ReqUrl = "http://{}:{}/bm/standard/uploadFile".format(bm_ip, bm_server_port)
                        try:
                            report_files = {"file": open(report_file_path, "rb")}
                            r = requests.post(url=Report_ReqUrl, data=data, files=report_files)
                            LOG.info("rrrrrr: %s" % r.text)
                            LOG.debug("审讯报告上传成功........")
                        except Exception as e:
                            LOG.error('审讯报告上传失败!!!!!{}'.format(e))
                        self.is_update = None
                elif time.time() - self.time >= 5:
                    self.time = time.time()
                time.sleep(0.05)
            except Exception as e:
                config.LOG.error("Openface算法处理线程异常")
                LOG.error(e)
