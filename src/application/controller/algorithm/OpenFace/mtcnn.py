import cv2

from .core.landmarkDetector import FaceDetectorMTCNN, Mat, DetectFacesMTCNN, FloatRectVector, _floatArray, \
    FaceModelParameters


class FaceDetect(object):
    def __init__(self):
        self.det_parameters = FaceModelParameters()
        self.face_detector_mtcnn = None
        self.load()

    def load(self):
        self.face_detector_mtcnn = FaceDetectorMTCNN(self.det_parameters.mtcnn_face_detector_location)

    @staticmethod
    def get_face(image, face_rect):
        """
        :param image:np.array; bgr image (h, w, 3) or gray img (h, w)
        :param face_rect: list; location of face regions [left,top,right,bottom]
        :return: np.array; bgr image or gray img
        """
        face = None
        if face_rect is not None:
            face = image[face_rect[1]:face_rect[3], face_rect[0]:face_rect[2]]
        return face

    def predict(self, image):
        rgb_image = Mat.from_array(image)
        face_detections = FloatRectVector()
        confidences = _floatArray()
        DetectFacesMTCNN(face_detections, rgb_image, self.face_detector_mtcnn, confidences)
        # face_rect = list()
        # for rect in face_detections:
        #     rect_list = list(rect)
        #     face_rect.append([int(rect_list[0]), int(rect_list[1]), int(rect_list[0] + rect_list[2]),
        #                       int(rect_list[1] + rect_list[3])])
        return face_detections
