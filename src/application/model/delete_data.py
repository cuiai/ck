#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

import os
import time
from threading import Thread
from application.controller.config import LOG
from application.controller.common import resource_path


class EdaDeleteData(Thread):
    def __init__(self):
        super(EdaDeleteData, self).__init__()
        self.setName("EdaDeleteData")
        self.is_stop_flag = False
        self.is_run_flag = True
        self.is_close_flag = False
        self.is_time_out_flag = False
        self.setDaemon(True)

    def run(self):
        sleep_time = 100
        while True:
            if self.is_close_flag:
                self.delete_data()
                break
            elif self.is_time_out_flag:
                time.sleep(sleep_time)
                continue
            elif self.is_run_flag:
                self.delete_data()
                time.sleep(sleep_time)

    @staticmethod
    def delete_data():
        all_lying_video_image = EmotionWarnEveryVideo.get_opt_status(0)
        if all_lying_video_image is not None:
            if len(all_lying_video_image) > 210:
                all_lying_video_image_delete = all_lying_video_image[0:(len(all_lying_video_image) - 210)]
                for lying in all_lying_video_image_delete:
                    # 删除原图
                    image_path = lying.image_path
                    if image_path and os.path.exists(image_path):
                        try:
                            os.remove(resource_path(image_path))
                        except Exception as e:
                            LOG.error("删除原图出错:%s" % str(e))
                            continue
                    # 删除略缩图
                    if image_path:
                        thumb_image_path = os.path.splitext(lying.image_path)[0] + '_thumb' + \
                                           os.path.splitext(lying.image_path)[1]
                        if thumb_image_path and os.path.exists(thumb_image_path):
                            try:
                                os.remove(resource_path(thumb_image_path))
                            except Exception as e:
                                LOG.error("删除略缩图出错:%s" % str(e))
                                continue
                    video_path = lying.video_path
                    if video_path and os.path.exists(video_path):
                        try:
                            os.remove(video_path)
                        except Exception as e:
                            LOG.error("delete_video_path :%s" % str(e))
                            continue
                    lying_uuid = lying.warn_uuid
                    try:
                        EmotionWarnEveryTime.delete_by_lying_uuid(lying_uuid)
                    except Exception as e:
                        LOG.error("delete_LyingEveryDegreeTime :%s" % str(e))
                        continue
                EmotionWarnEveryVideo.delete()

    def thread_exit(self):
        self.is_close_flag = True

    def close(self):
        self.is_stop_flag = True

    def time_out(self):
        self.is_time_out_flag = True

    def open(self):
        self.is_close_flag = False
        self.is_stop_flag = False
        self.is_run_flag = True


if __name__ == '__main__':
    pass
