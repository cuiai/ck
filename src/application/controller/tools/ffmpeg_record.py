#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess, time
from application.controller import config
from application.controller.tools.async_call import async_call

# 设置ffmpeg参数
# from application.view.view_tools.uploadFile import upload_video



# ffmpeg -y -i rtsp://admin:1234qwer@192.168.16.202/h264/ch1/main/ -vcodec copy -acodec copy -f mp4 e:\x.mp4
class VideoRecord(object):
    def __init__(self):
        super(VideoRecord, self).__init__()
        self.p_record = None
        self.command = None

    def start_record(self, video_source_url="", file_path=""):
        self.command = [config.FFMPEG_PATH,
                        '-loglevel', 'error',
                        '-rtsp_transport', 'tcp',
                        # '-rtbufsize', '96000',
                        '-y',
                        '-i', video_source_url,
                        '-vcodec', 'copy',
                        '-acodec', 'copy',
                        '-f', 'mp4',
                        file_path]
        try:
            self.p_record = subprocess.Popen(self.command,
                                             stdin=subprocess.PIPE,
                                             shell=True)
        except Exception as e:
            config.LOG.error("start_record subprocess.Popen error %s" % str(e))

    # @async_call
    def stop_record(self, video_path=""):
        out = None
        try:
            out = self.p_record.communicate(input='q'.encode("GBK"))
            config.LOG.debug("p_record.communicate successful close")
            if self.p_record.returncode != 0:
                config.LOG.error("p_record.communicate error")
            time.sleep(0.5)
            self.p_record.kill()
        except Exception as e:
            config.LOG.error("stop_record communicate error %s" % str(e))
            return False
        # wait_out = self.p_record.wait()
        # # TODO FTP上传到服务器
        # if video_path:
        #     print(video_path)
        #     upload_video(video_path)
        return out

    def offline_video_stop(self):
        a_wait = int(config.OFFLINE_VIDEO_TIME) - 6
        ret = True
        while ret:
            time.sleep(1)
            a_wait -= 1
            if a_wait == 0:
                self.stop_record()
                config.OFFLINE_VIDEO_SIGNALE = 1
                ret = False
