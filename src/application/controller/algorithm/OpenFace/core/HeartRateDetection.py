"""
    Function: pre-processing prior to analysis of heart rate.

            (1) no detected face, using the previous one.
            (2) scale the face image with the center 60% width and full height of the box as the ROI
            (3) get a red, blue and green measurement point

            Reference:
            [1] Non-contact, automated cardiac pulse measurements using video imaging and blind source separation, Ming-Zher Poh, etc.


    Author: Bike Chen
    Email: chenbike@xinktech.com
    Date: 22-July-2019
"""

from application.controller.algorithm.HeartRateAnalyser import HeartRateAnalysis
from application.controller.algorithm.HRMConfig import parser
import cv2
import numpy as np


args = vars(parser.parse_args())


class HeartRateDetection(object):
    def __init__(self):
        self.heart_rate_analysis = HeartRateAnalysis()
        self.scale_height = args["scale_height"]
        self.scale_width = args["scale_width"]
        self.img = None
        self.default_bpm = args["default_bpm"]
        self.fps = args["fps"]
        self.increment = args["increment"] # 1s
        self.skip_frame = self.fps * self.increment # stride
        self.count_skip_frame = 0
        print("Initializing heart rate detection successfully!")

    def _scale_face_img(self, img):
        img_height, img_width, img_channel = img.shape

        scale_img_height = img_height * self.scale_height
        scale_img_width = img_width * self.scale_width

        img_height_top = int((img_height - scale_img_height) / 2)
        img_height_bottom = img_height_top + int(scale_img_height)

        img_width_left = int((img_width - scale_img_width) / 2)
        img_width_right = img_width_left + int(scale_img_width)

        img = img[img_height_top:img_height_bottom, img_width_left:img_width_right, :]
        return img

    def _cal_RGB(self, img):
        r_value = np.mean(img[:, :, 0])
        g_value = np.mean(img[:, :, 1])
        b_value = np.mean(img[:, :, 2])
        return {"Red": r_value, "Green": g_value, "Blue": b_value}

    def HeartRateDetector(self, img):
        if img is not None:
            self.img = np.asarray(img, dtype=np.float32)

        if self.img is None:
            return self.default_bpm

        if len(self.heart_rate_analysis.g_his_data) < self.heart_rate_analysis.len_his_data:
            scale_img = self._scale_face_img(self.img)
            rgb_value = self._cal_RGB(scale_img)
            r_value = rgb_value["Red"]
            g_value = rgb_value["Green"]
            b_value = rgb_value["Blue"]
            self.heart_rate_analysis.r_his_data.append(r_value)
            self.heart_rate_analysis.g_his_data.append(g_value)
            self.heart_rate_analysis.b_his_data.append(b_value)
            if len(self.heart_rate_analysis.g_his_data) == self.heart_rate_analysis.len_his_data:
                current_bpm = self.heart_rate_analysis.PredictHeartRate()
                self.count_skip_frame = self.count_skip_frame + 1
                return current_bpm
            else:
                return self.default_bpm
        else:
            del self.heart_rate_analysis.r_his_data[0]
            del self.heart_rate_analysis.g_his_data[0]
            del self.heart_rate_analysis.b_his_data[0]
            scale_img = self._scale_face_img(self.img)
            rgb_value = self._cal_RGB(scale_img)
            r_value = rgb_value["Red"]
            g_value = rgb_value["Green"]
            b_value = rgb_value["Blue"]
            self.heart_rate_analysis.r_his_data.append(r_value)
            self.heart_rate_analysis.g_his_data.append(g_value)
            self.heart_rate_analysis.b_his_data.append(b_value)
            self.count_skip_frame = self.count_skip_frame + 1
            if self.count_skip_frame < self.skip_frame:
                return self.heart_rate_analysis.previous_bpm
            else:
                current_bpm = self.heart_rate_analysis.PredictHeartRate()
                self.count_skip_frame = 0 # reset.
                return current_bpm


if __name__ == "__main__":
    heart_rate_det = HeartRateDetection()
    video_file = "video_example.mp4"
    fps = 30 # assume 30 fps.
    start_time = 0
    duration = 60 # 60s
    frames_to_read = fps * duration
    cap = cv2.VideoCapture(video_file)
    count_frame = 0
    while cap.isOpened(): # and count_frame < frames_to_read:
        count_frame = count_frame + 1
        print("count =", count_frame)
        ret, frame = cap.read()
        if ret is False:
            print("Warning: could not read an image from a video.")
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        bpm = heart_rate_det.HeartRateDetector(frame) # Do not average full image.
        print("bpm =", bpm)
    cap.release()




