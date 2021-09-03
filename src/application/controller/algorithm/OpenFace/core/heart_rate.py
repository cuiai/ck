from .pulse import Pulse
import cv2
import numpy as np

class HeartRateDetection(object):
    # def __init__(self):
        # self.pulse = Pulse()
        # pass


    def get_face(self, frame, face_rect):
        """
        :param image:np.array; bgr image (h, w, 3) or gray img (h, w)
        :param face_rect: list; location of face regions [left,top,right,bottom]
        :return: np.array; bgr image or gray img
        """
        face = None
        if face_rect is not None:
            face = frame[face_rect[1]:face_rect[3], face_rect[0]:face_rect[2]]
        return face


    def get_forehead_rect(self, face_rect):
        forehead_rect=None
        if face_rect is not None:
            fh_x = 0.52
            fh_y = 0.18
            fh_w = 0.65
            fh_h = 0.08
            #fh_h = 0.15
            x = face_rect[0]
            y = face_rect[1]
            w = face_rect[2] - face_rect[0]
            h = face_rect[3] - face_rect[1]
            forehead_rect = [int(x + w * fh_x - (w * fh_w / 2.0)),
                             int(y + h * fh_y - (h * fh_h / 2.0)),
                             int(x + w * fh_x - (w * fh_w / 2.0)) + int(w * fh_w),
                             int(y + h * fh_y - (h * fh_h / 2.0)) + int(h * fh_h)]
        return forehead_rect

    def get_eyes_rect(self, face_rect):
        eyes_rect=None
        if face_rect is not None:
            fh_x = 0.5
            fh_y = 0.18 # adapt the value to find eye regions.
            fh_w = 1
            fh_h = 0.25
            x = face_rect[0]
            y = face_rect[1]
            w = face_rect[2] - face_rect[0]
            h = face_rect[3] - face_rect[1]
            eyes_rect = [int(x + w * fh_x - (w * fh_w / 2.0)),
                         int(y + h * fh_y - (h * fh_h / 2.0)),
                         int(x + w * fh_x - (w * fh_w / 2.0)) + int(w * fh_w),
                         int(y + h * fh_y - (h * fh_h / 2.0)) + int(h * fh_h)]
            # print("w:{},h:{}".format(int(w * fh_w), int(h * fh_h)))
        return eyes_rect

    def get_mouth_rect(self, face_rect):
        mouth_rect=None
        if face_rect is not None:
            fh_x = 0.50
            fh_y = 0.75
            fh_w = 0.5
            fh_h = 0.18
            x = face_rect[0]
            y = face_rect[1]
            w = face_rect[2] - face_rect[0]
            h = face_rect[3] - face_rect[1]
            mouth_rect = [int(x + w * fh_x - (w * fh_w / 2.0)),
                          int(y + h * fh_y - (h * fh_h / 2.0)),
                          int(x + w * fh_x - (w * fh_w / 2.0)) + int(w * fh_w),
                          int(y + h * fh_y - (h * fh_h / 2.0)) + int(h * fh_h)]
            # print("w:{},h:{}".format(int(w * fh_w), int(h * fh_h)))

        return mouth_rect

    def generate_face_image(self, frame, face_bbox):
        """
        Generate a processed face image.
        :return face_region:
        """
        # cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])), (int(bbox[0]+bbox[2]), int(bbox[1]+bbox[3])), (0, 255, 0), 1, 4, 0)
        face_rect = [int(face_bbox[0]), int(face_bbox[1]), int(face_bbox[0]+face_bbox[2]), int(face_bbox[1]+face_bbox[3])]

        # ==================================================================
        # remove eye regions.
        eyes_rect = self.get_eyes_rect(face_rect)
        frame[eyes_rect[1]:eyes_rect[3], eyes_rect[0]:eyes_rect[2]] = 0

        # remove mouth region
        mouth_rect = self.get_mouth_rect(face_rect)
        frame[mouth_rect[1]:mouth_rect[3], mouth_rect[0]:mouth_rect[2]] = 0

        # get the rest face region.
        face_img = self.get_face(frame, face_rect)
        # ==================================================================

        # frame_height, frame_width = frame.shape[:2]
        #
        # diff_left = face_rect[0]
        # diff_top = face_rect[1]
        # # diff_right = frame_width - face_rect[2]
        # # diff_bottom = frame_height - face_rect[3]
        #
        # # get the rest face region.
        # face_img = self.get_face(frame, face_rect)
        #
        # # remove eye regions.
        # eyes_rect = self.get_eyes_rect(face_rect)
        # eyes_rect = [eyes_rect[0]-diff_left, eyes_rect[1]-diff_top, eyes_rect[2], eyes_rect[3]]
        # face_img[eyes_rect[1]:eyes_rect[3], eyes_rect[0]:eyes_rect[2]] = 0
        #
        # # remove mouth region
        # mouth_rect = self.get_mouth_rect(face_rect)
        # mouth_rect = [mouth_rect[0]-diff_left, mouth_rect[1]-diff_top, mouth_rect[2], mouth_rect[3]]
        # face_img[mouth_rect[1]:mouth_rect[3], mouth_rect[0]:mouth_rect[2]] = 0

        return face_img

if __name__ == '__main__':

    face_bbox = [100, 100, 300, 300] # [x, y, w, h] constant value just for the test.
    cap = cv2.VideoCapture(0)

    pulse = Pulse()
    heart_rate_det = HeartRateDetection()

    frame_num = 0
    hr_all = []
    while cap.isOpened():
        ret, frame = cap.read()
        frame_num += 1
        # print(frame_num, frame.shape)

        if ret:
            face_image = heart_rate_det.generate_face_image(frame, face_bbox)
            heart_rate_value = pulse.heart_rate_detection(face_image)

            # TODO: show the face image
            cv2.rectangle(frame, (int(face_bbox[0]), int(face_bbox[1])),
                          (int(face_bbox[0]+face_bbox[2]), int(face_bbox[1]+face_bbox[3])), (0, 255, 0), 1, 4, 0)

            cv2.imshow("face_image", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

        else:
            break

    cap.release()
    cv2.destroyAllWindows()
