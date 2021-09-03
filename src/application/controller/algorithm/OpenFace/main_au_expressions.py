from __future__ import division

import cv2
import math
import time
import copy
import pickle
import numpy as np
from scipy.spatial import Delaunay
from imutils.video import VideoStream

from application.controller.config import LOG
from application.controller.algorithm.OpenFace.core.pulse import Pulse
from application.controller.algorithm.OpenFace.core.heart_rate import HeartRateDetection
from application.controller.algorithm.OpenFace.core.generate_more_triangles import generate_more_triangles
from application.controller.algorithm.OpenFace.core.landmarkDetector import (
    Mat,
    CLNF,
    Vec2d,
    FaceModelParameters,
    FaceAnalyserParameters,
    FaceAnalyser, GetPose,
    Point3f,
    EstimateGaze,
    GetGazeAngle,
    DetectLandmarksInVideo,
)


class Average(object):
    def __init__(self):
        self.avg = {}
        self.n = {}

    def insert(self, v, name):
        if name in self.avg:
            self.avg[name] = (self.avg[name] * self.n[name] + v) / (self.n[name] + 1)
            self.n[name] += 1
        else:
            self.avg[name] = float(0)
            self.n[name] = 0

    def get_avg(self, name):
        if name in self.avg:
            return self.avg[name]
        else:
            return None


class AUDepression():
    def __init__(self):
        self.au12_lasts = [15, 0]

        self.au_lasts = 80

        self.au12_history = []
        self.au12_total = 0
        self.au14_history = []
        self.au14_total = 0

        self.au4_history = []
        self.au4_total = 0
        self.au4_freq_threshold = [0.3, 0.7]

        self.au14fre_minus_12 = 0.6

        self.au12_cla = False
        self.au14_cla = False
        self.au15_cla = False
        self.au4_cla = False

        self.cls_text = None

    def input(self, ausCla, cls_text):
        def get(aus, key):
            for tuple in aus:
                if tuple[0] == key:
                    return tuple[1]

        self.au12_cla = get(ausCla, 'AU12')
        self.au14_cla = get(ausCla, 'AU14')
        self.au15_cla = get(ausCla, 'AU15')
        self.au4_cla = get(ausCla, 'AU04')
        self.cls_text = cls_text

        def update(au_history, au_history_total, au_now):
            if len(au_history) < self.au_lasts:
                au_history.append(au_now)
                au_history_total += au_now
            else:
                au_history.append(au_now)
                au_history_total -= au_history[0]
                au_history_total += au_now
                au_history = au_history[1:]
            return au_history, au_history_total

        self.au14_history, self.au14_total = update(self.au14_history, self.au14_total, self.au14_cla)
        self.au12_history, self.au12_total = update(self.au12_history, self.au12_total, self.au12_cla)
        self.au4_history, self.au4_total = update(self.au4_history, self.au4_total, self.au4_cla)

    def _check_rule1(self):
        if self.au12_cla:
            self.au12_lasts[1] += 1
        else:
            self.au12_lasts[1] = 0

        if self.au12_lasts[1] > self.au12_lasts[0]:
            if self.au14_cla or self.au15_cla:
                return True
        return False

    def _check_rule2(self):

        if len(self.au14_history) < self.au_lasts:
            return False
        freq14 = self.au14_total / self.au_lasts
        freq12 = self.au12_total / self.au_lasts

        # print("freq", freq14, freq12)
        if freq14 > 0.9:
            return False
        if freq14 - freq12 > self.au14fre_minus_12:
            return True
        else:
            return False

    def _check_rule3(self):
        if len(self.au4_history) < self.au_lasts:
            return False
        au4_freq = self.au4_total / self.au_lasts
        # print(au4_freq)
        if au4_freq > self.au4_freq_threshold[0] and au4_freq < self.au4_freq_threshold[1]:
            return True
        else:
            return False

    def check(self):
        if self.cls_text == 'Joy':
            return False
        ret = self._check_rule3()
        # if ret: print(self._check_rule1(), self._check_rule2(), self._check_rule3())
        return ret


class ProcessSequenceImages(object):
    def __init__(self):
        LOG.debug("Load face landmark detector ...")
        self.det_parameters = FaceModelParameters()

        LOG.debug("Always track gaze in feature extraction ...")
        self.face_model = CLNF(self.det_parameters.model_location)
        if not self.face_model.loaded_successfully:
            LOG.debug("ERROR: Could not load the landmark detector.")

        LOG.debug("Load facial feature extractor and AU analyser ...")
        self.face_analysis_params = FaceAnalyserParameters()
        self.face_analysis_params.OptimizeForVideos()
        self.face_analyser = FaceAnalyser(self.face_analysis_params)

        if not self.face_model.eye_model:
            LOG.debug("WARNING: no eye model found.")

        if len(self.face_analyser.GetAUClassNames()) == 0:
            LOG.debug("WARNING: no Action Unit models found")

        # Camera parameters.
        self.fx = -1
        self.fy = -1
        self.cx = -1
        self.cy = -1

        # AU-> Expressions.
        au2exp_file = open("model/lr_model_average.pickle", 'rb')
        self.au2exp_model = pickle.load(au2exp_file)
        # self.index_emo_dict = {0:'neutral', 1:'anger', 2:'contempt', 3:'disgust', 4:'fear', 5:'happy', 6:'sadness', 7:'surprise'}
        self.index_emo_dict = {0: "Anger", 1: "Contempt", 2: "Disgust", 3: "Fear", 4: "Joy", 5: "Neutral", 6: "Sadness",
                               7: "Surprise"}

        self.average_calculator = Average()
        self.au_depression = AUDepression()
        self.au_values = []
        LOG.debug("Loading successfully!")

    def img2x(self, img, fx=-1, fy=-1, cx=-1, cy=-1):
        """
        Get fx, fy, cx, cy based on image sizes.
        """
        # if optical centers are not defined just use center of image.
        image_height = float(img.shape[0])
        image_width = float(img.shape[1])

        if cx == -1:
            cx = image_width / 2
            cy = image_height / 2
        else:
            cx = cx
            cy = cy

        # Use a rough guess-timate of focal length
        if fx == -1:
            fx = 500 * (image_width / 640)
            fy = 500 * (image_height / 480)

            fx = (fx + fy) / 2
            fy = fx
        else:
            fx = fx
            fy = fy

        return (fx, fy, cx, cy)

    def projection_with_fc(self, rot_box, fx, fy, cx, cy):
        dest = np.zeros((rot_box.shape[0], 2), np.float)
        for i in range(dest.shape[0]):
            X = rot_box[i][0]
            Y = rot_box[i][1]
            Z = rot_box[i][2]

            if Z != 0:
                x = ((X * fx / Z) + cx)
                y = ((Y * fy / Z) + cy)
            else:
                x = X
                y = Y
            dest[i][0] = x
            dest[i][1] = y
        return dest

    def projection(self, rot_box):
        dest = np.zeros((rot_box.shape[0], 2), np.float)
        for i in range(dest.shape[0]):
            X = rot_box[i][0]
            Y = rot_box[i][1]
            Z = rot_box[i][2]

            if Z != 0:
                x = ((X * self.fx / Z) + self.cx)
                y = ((Y * self.fy / Z) + self.cy)
            else:
                x = X
                y = Y
            dest[i][0] = x
            dest[i][1] = y
        return dest

    def euler_2_rotation_matrix(self, pose3, pose4, pose5):
        rotation_matrix = np.zeros((3, 3), np.float)
        s1 = math.sin(pose3)
        s2 = math.sin(pose4)
        s3 = math.sin(pose5)

        c1 = math.cos(pose3)
        c2 = math.cos(pose4)
        c3 = math.cos(pose5)

        rotation_matrix[0][0] = c2 * c3
        rotation_matrix[0][1] = -c2 * s3
        rotation_matrix[0][2] = s2
        rotation_matrix[1][0] = c1 * s3 + c3 * s1 * s2
        rotation_matrix[1][1] = c1 * c3 - s1 * s2 * s3
        rotation_matrix[1][2] = -c2 * s1
        rotation_matrix[2][0] = s1 * s3 - c1 * c3 * s2
        rotation_matrix[2][1] = c3 * s1 + c1 * s2 * s3
        rotation_matrix[2][2] = c1 * c2
        return rotation_matrix

    def calculate_box(self, pose, original_point):

        box = ((-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1), (1, -1, 1), (1, -1, -1), (-1, -1, -1), (-1, -1, 1))
        box = np.array(box, np.float) * 45
        edges = ((0, 3), (2, 3), (3, 7))

        rot = self.euler_2_rotation_matrix(pose[3], pose[4], pose[5])
        rot_box = np.dot(rot, box.T)
        rot_box[0] += pose[0]
        rot_box[1] += pose[1]
        rot_box[2] += pose[2]
        rot_box = rot_box.T
        rotBoxProj = self.projection(rot_box)
        lines = []
        previous_original_point = (rotBoxProj[3])

        shift0 = original_point[0] - previous_original_point[0]
        shift1 = original_point[1] - previous_original_point[1]
        for i in range(len(edges)):
            p1 = (int(rotBoxProj[edges[i][0]][0] + shift0), int(rotBoxProj[edges[i][0]][1] + shift1))
            p2 = (int(rotBoxProj[edges[i][1]][0] + shift0), int(rotBoxProj[edges[i][1]][1] + shift1))
            lines.append((p1, p2))

        return lines

    def calculate_box_with_fc(self, pose, original_point, fx, fy, cx, cy):

        box = ((-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1), (1, -1, 1), (1, -1, -1), (-1, -1, -1), (-1, -1, 1))
        box = np.array(box, np.float) * 45
        edges = ((0, 3), (2, 3), (3, 7))

        rot = self.euler_2_rotation_matrix(pose[3], pose[4], pose[5])
        rot_box = np.dot(rot, box.T)
        rot_box[0] += pose[0]
        rot_box[1] += pose[1]
        rot_box[2] += pose[2]
        rot_box = rot_box.T
        rotBoxProj = self.projection_with_fc(rot_box, fx, fy, cx, cy)
        lines = []
        previous_original_point = (rotBoxProj[3])

        shift0 = original_point[0] - previous_original_point[0]
        shift1 = original_point[1] - previous_original_point[1]
        for i in range(len(edges)):
            p1 = (int(rotBoxProj[edges[i][0]][0] + shift0), int(rotBoxProj[edges[i][0]][1] + shift1))
            p2 = (int(rotBoxProj[edges[i][1]][0] + shift0), int(rotBoxProj[edges[i][1]][1] + shift1))
            lines.append((p1, p2))

        return lines

    def calculate_all_landmarks(self, shape2D):
        landmarks = []

        if shape2D.shape[1] == 2:
            n = shape2D.shape[0]
        elif shape2D.shape[1] == 1:
            n = shape2D.shape[0] / 2
        else:
            assert False
        n = int(n)
        for i in range(n):
            if shape2D.shape[1] == 1:
                feature_point = (shape2D[i], shape2D[i + n])
            else:
                feature_point = (shape2D[i][0], shape2D[i][1])
            landmarks.append(feature_point)
        return landmarks

    def process_sequence_images(self, frame):
        """
        :param frame: ret, frame = cap.read() # BGR format
        :return:
        """
        self.fx, self.fy, self.cx, self.cy = self.img2x(frame)

        captured_image = Mat.from_array(frame)
        grayscale_image = Mat.from_array(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))

        is_has_face = DetectLandmarksInVideo(captured_image, self.face_model, self.det_parameters, grayscale_image)

        # Gaze tracking, absolute gaze direction
        gaze_direction_0 = Point3f(0, 0, -1)
        gaze_direction_1 = Point3f(0, 0, -1)
        gaze_angle = Vec2d(0, 0)
        if self.face_model.eye_model:
            EstimateGaze(self.face_model, gaze_direction_0, self.fx, self.fy, self.cx, self.cy, True)
            EstimateGaze(self.face_model, gaze_direction_1, self.fx, self.fy, self.cx, self.cy, False)
            gaze_angle = GetGazeAngle(gaze_direction_0, gaze_direction_1)

        # =============== Gaze Info =====================================================
        gaze_direction_0 = np.asarray(list(gaze_direction_0))
        gaze_direction_1 = np.asarray(list(gaze_direction_1))

        # Get the left eye's gaze information
        eye_0 = self.face_model.GetEyes0()
        pdm_0 = self.face_model.GetPdm0()
        params_local_0 = self.face_model.GetParamsLocal0()

        # Get the right eye's gaze information
        eye_1 = self.face_model.GetEyes1()
        pdm_1 = self.face_model.GetPdm1()
        params_local_1 = self.face_model.GetParamsLocal1()

        eye_landmarks_2d = [self.calculate_all_landmarks(np.asarray(eye_0)),
                            self.calculate_all_landmarks(np.asarray(eye_1))]
        x0 = np.asarray(self.face_model.GetShape(self.fx, self.fy, self.cx, self.cy, eye_0, params_local_0, pdm_0))
        x1 = np.asarray(self.face_model.GetShape(self.fx, self.fy, self.cx, self.cy, eye_1, params_local_1, pdm_1))
        eye_landmarks_3d = np.concatenate((x0.T, x1.T))

        camera_mat = ((self.fx, 0, self.cx), (0, self.fy, self.cy), (0, 0, 0))
        pupil_left = np.zeros(3, np.float)
        pupil_right = np.zeros(3, np.float)

        for i in range(8):
            pupil_left += eye_landmarks_3d[i]
            pupil_right += eye_landmarks_3d[i + int(eye_landmarks_3d.shape[0] / 2)]
        pupil_left /= 8
        pupil_right /= 8

        points_left = [pupil_left, pupil_left + gaze_direction_0 * 50]
        points_right = [pupil_right, pupil_right + gaze_direction_1 * 50]

        def project_2_line(mesh):
            proj_points = self.projection(mesh)
            return (int(proj_points[0][0] * 16 + 0.5), int(proj_points[0][1] * 16 + 0.5)), (
                int(proj_points[1][0] * 16 + 0.5), int(proj_points[1][1] * 16 + 0.5))

        mesh_left = np.array(((points_left[0][0], points_left[0][1], points_left[0][2]),
                              (points_left[1][0], points_left[1][1], points_left[1][2])))

        mesh_right = np.array(((points_right[0][0], points_right[0][1], points_right[0][2]),
                               (points_right[1][0], points_right[1][1], points_right[1][2])))

        line_left = project_2_line(mesh_left)
        line_right = project_2_line(mesh_right)

        # =============== End Gaze Info ==================================================
        # a bounding box on the face.
        bbox = list(self.face_model.GetBoundingBox())
        # all landmarks on the face.
        points = list(np.asarray(self.face_model.detected_landmarks)[:, 0])

        # Perform AU detection and HOG feature extraction, as this can be expensive only compute it if needed by output or visualization
        if not is_has_face:
            self.face_analyser.AddNextFrame(captured_image, self.face_model.detected_landmarks,
                                            self.face_model.detection_success, time.time(), True)
        # todo 已修改
        else:
            self.face_analyser.PredictStaticAUsAndComputeFeatures(captured_image, self.face_model.detected_landmarks)
        # Work out the pose of the head from the tracked model.
        pose_estimate = GetPose(self.face_model, self.fx, self.fy, self.cx, self.cy)

        ausReg = self.face_analyser.GetCurrentAUsReg()
        ausClass = self.face_analyser.GetCurrentAUsClass()
        fx, fy, cx, cy = self.fx, self.fy, self.cx, self.cy
        return (
            pose_estimate, line_left, line_right, gaze_angle, ausReg, ausClass, points, eye_landmarks_2d, bbox, fx, fy,
            cx,
            cy)

    def deep_think(self, pose):
        if abs(pose[3]) < 0.3:
            self.average_calculator.insert(pose[3], "pose3")

        pose3avg = self.average_calculator.get_avg("pose3")
        if pose3avg is None:
            pose3avg = 0
        if abs(pose[
                   3] - pose3avg) <= 0.785:  # PI/6 = 30 degrees = 0.524; PI/4 = 45 degrees = 0.785; PI/3 = 60 degrees = 1.047
            return True
        else:
            return False

    def shaking_head_left_right(self, pose):
        if abs(pose[4]) < 0.3:
            self.average_calculator.insert(pose[4], "shaking_head")

        pose4avg = self.average_calculator.get_avg("shaking_head")
        if pose4avg is None:
            pose4avg = 0
        if abs(pose[
                   4] - pose4avg) <= 0.785:  # PI/6 = 30 degrees = 0.524; PI/4 = 45 degrees = 0.785; PI/3 = 60 degrees = 1.047
            return True
        else:
            return False

    def judge_detectable(self, alg_result):
        points = alg_result.points
        pose = alg_result.pose_estimate
        """检测当前头部姿态是否利于检测"""
        if (
                sum(points) != 0
                and
                self.shaking_head_left_right(pose)
                and
                self.deep_think(pose)
        ):
            return True
        return False

    def is_looking_at_me(self, alg_result):
        gaze = alg_result.gaze_angle
        if abs(gaze[0]) < 0.3:
            self.average_calculator.insert(gaze[0], "gaze0")

        if abs(gaze[1]) < 0.3:
            self.average_calculator.insert(gaze[1], "gaze1")

        gaze0_avg = self.average_calculator.get_avg("gaze0")
        gaze1_avg = self.average_calculator.get_avg("gaze1")
        if gaze0_avg is None:
            gaze0_avg = 0
        if gaze1_avg is None:
            gaze1_avg = 0

        if abs(gaze[0] - gaze0_avg) > 0.2 or abs(gaze[1] - gaze1_avg) > 0.2:
            return False
        else:
            return True

    def au2emotions(self, aus_reg):
        current_au_value = []
        for au_value in aus_reg:
            current_au_value.append(au_value[1])
        self.au_values.append(current_au_value)
        if len(self.au_values) >= 5:
            del (self.au_values[0])
        np_au_values = np.asarray(self.au_values)
        avg_au_values = np.average(np_au_values, axis=0)
        output_cls, output_reg, cls_text = self.output_cls_reg_list_AUs(
            avg_au_values)
        return output_cls, output_reg, cls_text

    def output_cls_reg(self, ausReg):
        """
        :param x: (('AU04', 0.0), ('AU06', 2.1625195196993516), ..., ('AU45', 1.953866081989102))
        :return:
        """
        data = []
        for au_value in ausReg:
            data.append(au_value[1])

        data = tuple(data)
        data = np.array(data).reshape(1, -1)

        # predict classes.
        output_cls = self.au2exp_model.predict(data)
        # predict probability
        output_reg = self.au2exp_model.predict_proba(data)

        # get the corresponding text.
        cls_text = self.index_emo_dict[output_cls[0]]

        return (output_cls, output_reg, cls_text)

    def output_cls_reg_list_AUs(self, au_value):

        data = tuple(au_value)
        data = np.array(data).reshape(1, -1)

        # predict classes.
        output_cls = self.au2exp_model.predict(data)
        # predict probability
        output_reg = self.au2exp_model.predict_proba(data)

        # get the corresponding text.
        cls_text = self.index_emo_dict[output_cls[0]]

        return (output_cls, output_reg, cls_text)

    def state_of_mind(self, ausClass, output_reg, cls_text):
        micro_expression_values = output_reg[0]
        is_mind = {"nervous": False, "anxious": False, "resistance": False, "depressed": False}

        # nervous
        if micro_expression_values[0] >= 0.225 and micro_expression_values[0] < 0.305 and \
                micro_expression_values[2] >= 0.225 and micro_expression_values[2] < 0.305:
            is_mind["nervous"] = True

        # anxious
        if micro_expression_values[0] >= 0.305 and micro_expression_values[2] >= 0.305:
            is_mind["anxious"] = True

        # resistance
        if micro_expression_values[3] >= 0.45 and micro_expression_values[1] >= 0.45:
            is_mind["resistance"] = True

        # depressed
        # if micro_expression_values[6] >= 0.45 and micro_expression_values[2] >= 0.45:
        #     is_mind["depressed"] = True

        # cls_text参数
        self.au_depression.input(ausClass, cls_text)
        if self.au_depression.check():
            is_mind["depressed"] = True

        return is_mind


if __name__ == '__main__':
    import os

    os.chdir('../../../../')
    LOG.debug(os.getcwd())
    cap = VideoStream('rtsp://admin:1234qwer@192.168.16.51:554')
    cap.start()
    # Loading Micro Expressions.
    proc_seq_img = ProcessSequenceImages()

    # Loading Heart Rate Analysis Model
    pulse = Pulse()
    heart_rate_det = HeartRateDetection()

    # store all AU values.
    au_values = []

    while cap.stream.stream.isOpened():
        frame = cap.read()
        if frame is None:
            LOG.debug("WARNING: could not read an image.")
            break

        start_time = time.time()

        pose_estimate, line_left, line_right, gaze_angle, ausReg, ausClass, points, eye_landmarks_2d, face_bbox, fx, fy, cx, cy = proc_seq_img.process_sequence_images(
            frame)

        if sum(points) != 0:
            # Draw a bounding box on the face.
            # cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])), (int(bbox[0]+bbox[2]), int(bbox[1]+bbox[3])), (0, 255, 0), 1, 4, 0)

            # Heart rate analysis
            heart_rate_img = copy.deepcopy(frame)
            face_image = heart_rate_det.generate_face_image(heart_rate_img, face_bbox)
            heart_rate_value = pulse.heart_rate_detection(face_image)

            # cv2.rectangle(frame, (int(face_bbox[0]), int(face_bbox[1])), (int(face_bbox[0]+face_bbox[2]), int(face_bbox[1]+face_bbox[3])), (0, 255, 0), 1, 4, 0)
            # cv2.imshow("face_image", face_image)
            # LOG.debug('heart_rate {0}'.format(heart_rate_value))

            # Draw landmarks on the face
            points_delaunay = []
            for i in range(len(points) // 2):
                x = points[i]
                y = points[68 + i]
                cv2.circle(frame, (int(x), int(y)), 1, (0, 0, 255), 3, 8, 0)
                points_delaunay.append([x, y])

            # Draw triangles
            points_delaunay = generate_more_triangles(points_delaunay)
            tri = Delaunay(np.asarray(points_delaunay))
            simplices = tri.simplices

            for lines in simplices:
                cv2.line(np.asarray(frame), (points_delaunay[int(lines[0])][0], points_delaunay[int(lines[0])][1]),
                         (points_delaunay[int(lines[1])][0], points_delaunay[int(lines[1])][1]), (255, 255, 255), 1, 8,
                         0)

                cv2.line(np.asarray(frame), (points_delaunay[int(lines[1])][0], points_delaunay[int(lines[1])][1]),
                         (points_delaunay[int(lines[2])][0], points_delaunay[int(lines[2])][1]), (255, 255, 255), 1, 8,
                         0)

                cv2.line(np.asarray(frame), (points_delaunay[int(lines[2])][0], points_delaunay[int(lines[2])][1]),
                         (points_delaunay[int(lines[0])][0], points_delaunay[(lines[0])][1]), (255, 255, 255), 1, 8, 0)

            # Draw pose
            pose_lines = proc_seq_img.calculate_box(pose_estimate, (points[33], points[33 + 68]))
            LOG.debug("", proc_seq_img.fx)
            cv2.line(frame, pose_lines[0][0], pose_lines[0][1], (255, 0, 0), 2)
            cv2.line(frame, pose_lines[1][0], pose_lines[1][1], (0, 255, 0), 2)
            cv2.line(frame, pose_lines[2][0], pose_lines[2][1], (0, 0, 255), 2)

            # Draw gaze
            cv2.line(frame, line_left[0], line_left[1], (0, 0, 255), 2, shift=4)
            cv2.line(frame, line_right[0], line_right[1], (0, 0, 255), 2, shift=4)

            # Draw eyes
            for index in range(len(eye_landmarks_2d[0]) - 1):
                cv2.line(frame, (int(eye_landmarks_2d[0][index][0]), int(eye_landmarks_2d[0][index][1])),
                         (int(eye_landmarks_2d[0][index + 1][0]), int(eye_landmarks_2d[0][index + 1][1])), (255, 0, 0),
                         2)
            cv2.line(frame, (int(eye_landmarks_2d[0][-1][0]), int(eye_landmarks_2d[0][-1][1])),
                     (int(eye_landmarks_2d[0][0][0]), int(eye_landmarks_2d[0][0][1])), (255, 0, 0), 2)

            for index in range(len(eye_landmarks_2d[1]) - 1):
                cv2.line(frame, (int(eye_landmarks_2d[1][index][0]), int(eye_landmarks_2d[1][index][1])),
                         (int(eye_landmarks_2d[1][index + 1][0]), int(eye_landmarks_2d[1][index + 1][1])), (255, 0, 0),
                         2)
            cv2.line(frame, (int(eye_landmarks_2d[1][-1][0]), int(eye_landmarks_2d[1][-1][1])),
                     (int(eye_landmarks_2d[1][0][0]), int(eye_landmarks_2d[1][0][1])), (255, 0, 0), 2)

            # TODO: AU -> Expressions
            # ausReg: (('AU04', 0.0), ('AU06', 2.1625195196993516), ..., ('AU45', 1.953866081989102))
            # ausClass: (('AU04', 0.0), ('AU06', 1.0), ...,('AU45', 0.0))
            current_au_value = []
            for au_value in ausReg:
                current_au_value.append(au_value[1])
            au_values.append(current_au_value)

            if len(au_values) >= 5:
                del (au_values[0])

            np_au_values = np.asarray(au_values)
            avg_au_values = np.average(np_au_values, axis=0)

            output_cls, output_reg, cls_text = proc_seq_img.output_cls_reg_list_AUs(avg_au_values)

            # {0:"Anger", 1:"Contempt", 2:"Disgust", 3:"Fear", 4:"Joy", 5:"Neutral", 6:"Sadness", 7:"Surprise"}
            # Show expressions on the image.
            text_class = "Class: {}".format(cls_text)
            cv2.putText(frame, text_class, (40, 25), cv2.FONT_HERSHEY_PLAIN, 2.0, (0, 0, 255), 2)

            text_neutral = "neutral: {:.2f}".format(output_reg[0][5])
            cv2.putText(frame, text_neutral, (40, 50), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 255), 2)

            text_anger = "anger: {:.2f}".format(output_reg[0][0])
            cv2.putText(frame, text_anger, (40, 80), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 255), 2)

            text_contempt = "contempt: {:.2f}".format(output_reg[0][1])
            cv2.putText(frame, text_contempt, (40, 110), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 255), 2)

            text_disgust = "disgust: {:.2f}".format(output_reg[0][2])
            cv2.putText(frame, text_disgust, (40, 140), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 255), 2)

            text_fear = "fear: {:.2f}".format(output_reg[0][3])
            cv2.putText(frame, text_fear, (40, 170), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 255), 2)

            text_happy = "joy: {:.2f}".format(output_reg[0][4])
            cv2.putText(frame, text_happy, (40, 200), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 255), 2)

            text_sadness = "sadness: {:.2f}".format(output_reg[0][6])
            cv2.putText(frame, text_sadness, (40, 230), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 255), 2)

            text_surprise = "surprise: {:.2f}".format(output_reg[0][7])
            cv2.putText(frame, text_surprise, (40, 260), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 255), 2)

            # TODO: face up to, or eye diversion

            # TODO: 8 micro expressions -> resistant, nervous, or deep thinking.

            # TODO: status, normal or abnormal.

        key = cv2.waitKey(1) & 0xFF
        cv2.imshow('frame', frame)
        if key == ord("q"):
            break

        LOG.debug("FPS = {}".format(1 / (time.time() - start_time)))
    cv2.destroyAllWindows()
