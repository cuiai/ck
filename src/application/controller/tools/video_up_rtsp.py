import os
import subprocess
import threading
import time
from threading import Thread

import psutil

from application.controller import config
from application.controller.algorithm.OpenFace.main_au_expressions import generate_more_triangles, Delaunay
import numpy as np
from application.controller.camera import CAMERA_FREQUENCY
import collections
import cv2
import copy

from application.controller.tools import async_call
from application.controller.tools.async_call import async_call

class PutFrameRtsp(Thread):
    def __init__(self):
        super(PutFrameRtsp, self).__init__()
        self.setDaemon(True)
        self.setName("put_frame_rtsp")
        self.is_connect = False
        self.p_rtsp = ""
        # cap = cv2.VideoCapture(config.DST_STREAM)
        # Get video information
        # fps = int(cap.get(cv2.CAP_PROP_FPS))

        # self.width = 640
        # self.height = 360
        self.pub_url = config.PUB_URL
        self.pub_v = config.PUB_V
        self.rate = 25
        self.frame_list = collections.deque(maxlen=2)
        self.insert_orm_t = 0
        self.last_frame = None
        self.frame_ts = 0
        self.intelligent_time = 0
        # raise Exception("异常")


    def init_subprocess(self):
        ret = False
        while True:
            self.width = config.FRAME_WIDTH
            self.height = config.FRAME_HEIGHT
            if self.width and self.height:
                break
            time.sleep(0.04)
        self.command = [config.FFMPEG_PATH2,
                       '-re',
                       '-f', 'rawvideo',
                       '-pix_fmt', 'bgr24',
                       '-s', '%dx%d' % (self.width, self.height),
                       '-fflags', 'nobuffer',
                       '-i', '-',
                       '-loglevel', 'info',
                       '-r', '%d' % self.rate,
                       '-b:v', '1500k',

                        '-vcodec', 'h264',
                       # '-vcodec', 'libx264',
                       '-pix_fmt', 'yuv420p',
                       '-preset', 'ultrafast',
                       '-tune', 'zerolatency',
                       # '-f', 'flv',
                       '-rtsp_transport', "tcp",
                        '-g', '20',
                       '-f', 'rtsp',

                       # '-b', '3700000',
                       self.pub_url]
        try:
            self.p_rtsp = subprocess.Popen(self.command,
                                           stdin=subprocess.PIPE,
                                           shell=True)
        except Exception as e:
            config.LOG.error("Failed to up frame stream %s" % str(e))
            return ret
        self.is_connect = True
        ret = True
        return ret

    @staticmethod
    def is_zero(num):
        if num:
            return True
        else:
            return False

    def deal_ori_frame(self):
        while True:
            try:
                arg_data = copy.deepcopy(config.EMOTION_DATA_OBJECT)
                request= copy.deepcopy(config.ORIGIN_FRAME[0])
                if request and arg_data:
                    self.paint_frame(request, arg_data)
                else:
                    time.sleep(0.01)
                time.sleep(0.005)
            except Exception as e:
                config.LOG.error("frame绘制图像线程异常")
                config.LOG.error(e)
    @staticmethod
    def is_zero(num):
        if num:
            return True
        else:
            return False

    @async_call
    def paint_frame(self,request,arg_data):
        frame = request.frame
        ts = request.ts
        try:
            is_show = list(filter(self.is_zero,arg_data.aus_reg))
            if not is_show:
                self.frame_list.append(request)
                time.sleep(0.001)
                return
            frame = self.draw_face_mask_manage(frame, arg_data)
            request.frame = frame
        except Exception as e:
            config.LOG.error("Failed to up paint %s" % str(e))
        self.frame_list.append(request)
        if len(self.frame_list) > 1:
            self.frame_list.popleft()
        time.sleep(0.001)


    def put_frame(self):
        invalid_frame = 0
        while True:
            try:
                if self.frame_list:
                    request = self.frame_list.popleft()
                    frame = request.frame
                    ts = request.ts
                    if ts >self.intelligent_time:
                        try:
                            self.intelligent_time = ts
                            self.p_rtsp.stdin.write(frame.tobytes())
                        except Exception as e:
                            invalid_frame += 1
                            time.sleep(0.04)
                            config.LOG.error("Failed to put frame %s" % str(e))
                time.sleep(0.04)
                #重启推流服务
                if invalid_frame>=5:
                    config.LOG.info("写入管道失败，重启推流服务")
                    self.stop_put_ffmpeg()
                    invalid_frame = 0
                    ret = self.init_subprocess()
                    if ret is False:
                        time.sleep(0.05)
            except Exception as e:
                config.LOG.error("推送frame至流媒体线程异常")
                config.LOG.error(e)


    @async_call
    def stop_put_ffmpeg(self, video_path=""):
        ffmpeg_put_list = []
        try:
            # 检测服务当前启动的数量，只保留最新启动的服务，节省内存使用率
            for proc in psutil.process_iter():
                if "ffmpeg_put.exe".lower() in proc.name().lower(): ffmpeg_put_list.append(proc)
            if len(ffmpeg_put_list) > 0:
                for i in ffmpeg_put_list: os.popen('taskkill -f -pid %s' % i.pid);config.LOG.debug(
                    "ffmpeg_put已关闭.......")
        except Exception as e:
            config.LOG.error('ffmpeg_put关闭失败-->{}'.format(e))

    def run(self):
        if not self.is_connect:
            ret = self.init_subprocess()
            if ret is False:
                time.sleep(1)
        config.LOG.info('推流已成功')
        threading.Thread(target=self.deal_ori_frame).start()
        threading.Thread(target=self.put_frame).start()


    def draw_landmarks(self, frame,arg_data):
        points = arg_data.points
        points_delaunay = []
        for i in range(len(points) // 2):
            x = points[i]
            y = points[68 + i]
            cv2.circle(frame, (int(x), int(y)), 1, (0, 0, 255), 3, 8, 0)
            points_delaunay.append([x, y])

        points_delaunay = generate_more_triangles(points_delaunay)
        tri = Delaunay(np.asarray(points_delaunay))
        simplices = tri.simplices

        for lines in simplices:
            cv2.line(np.asarray(frame),
                     (points_delaunay[int(lines[0])][0], points_delaunay[int(lines[0])][1]),
                     (points_delaunay[int(lines[1])][0], points_delaunay[int(lines[1])][1]), (255, 255, 255), 1,
                     8,
                     0)

            cv2.line(np.asarray(frame),
                     (points_delaunay[int(lines[1])][0], points_delaunay[int(lines[1])][1]),
                     (points_delaunay[int(lines[2])][0], points_delaunay[int(lines[2])][1]), (255, 255, 255), 1,
                     8,
                     0)

            cv2.line(np.asarray(frame),
                     (points_delaunay[int(lines[2])][0], points_delaunay[int(lines[2])][1]),
                     (points_delaunay[int(lines[0])][0], points_delaunay[(lines[0])][1]), (255, 255, 255), 1, 8,
                     0)
        return frame

    def draw_pose(self, frame,arg_data):
        pose_lines = arg_data.pose_lines
        cv2.line(frame, pose_lines[0][0], pose_lines[0][1], (255, 0, 0), 2)
        cv2.line(frame, pose_lines[1][0], pose_lines[1][1], (0, 255, 0), 2)
        cv2.line(frame, pose_lines[2][0], pose_lines[2][1], (0, 0, 255), 2)
        return frame

    def draw_gaze(self, frame,arg_data):
        line_left = arg_data.line_left
        line_right = arg_data.line_right
        cv2.line(frame, line_left[0], line_left[1], (0, 0, 255), 2, shift=4)
        cv2.line(frame, line_right[0], line_right[1], (0, 0, 255), 2, shift=4)
        return frame

    def draw_eyes(self, frame,arg_data):
        eye_landmarks_2d = arg_data.eye_landmarks_2d
        for index in range(len(eye_landmarks_2d[0]) - 1):
            cv2.line(frame, (int(eye_landmarks_2d[0][index][0]), int(eye_landmarks_2d[0][index][1])),
                     (int(eye_landmarks_2d[0][index + 1][0]), int(eye_landmarks_2d[0][index + 1][1])),
                     (255, 0, 0),
                     2)
        cv2.line(frame, (int(eye_landmarks_2d[0][-1][0]), int(eye_landmarks_2d[0][-1][1])),
                 (int(eye_landmarks_2d[0][0][0]), int(eye_landmarks_2d[0][0][1])), (255, 0, 0), 2)

        for index in range(len(eye_landmarks_2d[1]) - 1):
            cv2.line(frame, (int(eye_landmarks_2d[1][index][0]), int(eye_landmarks_2d[1][index][1])),
                     (int(eye_landmarks_2d[1][index + 1][0]), int(eye_landmarks_2d[1][index + 1][1])),
                     (255, 0, 0),
                     2)
        cv2.line(frame, (int(eye_landmarks_2d[1][-1][0]), int(eye_landmarks_2d[1][-1][1])),
                 (int(eye_landmarks_2d[1][0][0]), int(eye_landmarks_2d[1][0][1])), (255, 0, 0), 2)
        return frame

    def draw_face_mask_manage(self, frame,arg_data):
        # TODO 判断是否画框、面罩、姿态等
        if config.IS_3D_MASK_DRAW is True:
            """画3D_MASK"""
            # try:
            frame = self.draw_landmarks(frame,arg_data)
            # self.draw_triangles()
            # except Exception as e:
            #     config.LOG.error("draw 3d mask error %s" % str(e))
        if config.IS_HEAD_POSE_ESTIMATION_DRAW is True:
            """画头部姿态估计"""
            try:
                frame = self.draw_pose(frame,arg_data)
            except Exception as e:
                config.LOG.error("draw head pose error %s" % str(e))
        if config.IS_EYE_POSE_ESTIMATION_DRAW is True:
            """画眼部姿态估计"""
            try:
                frame = self.draw_gaze(frame,arg_data)
            except Exception as e:
                config.LOG.error("draw gaze error %s" % str(e))
        if config.IS_EYE_3D_MODEL_DRAW is True:
            """画眼部姿3D模型"""
            try:
                frame = self.draw_eyes(frame,arg_data)
            except Exception as e:
                config.LOG.error("draw_eyes error %s " % str(e))
        return frame
