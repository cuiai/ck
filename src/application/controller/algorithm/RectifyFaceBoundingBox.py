"""
    Function: rectify the shift bounding box predicted by MTCNN.
            (1) face detection, MTCNN
            (2) heart rate measurement, Non-contact, automated cardiac pulse measurements using video imaging and blind source separation, Ming-Zher Poh, etc.


    Author: Bike Chen
    Email: chenbike@xinktech.com
    Date: 19-July-2019
"""

def RectifyFaceBoundingBox(bbox, img):
    HYPER_PARAM_SCALE = [0.8924, 0.8676] # scale for width and height.
    HYPER_PARAM_SHIFT = [0.0578, 0.2166] # slightly to the right, and shift face down.

    img_height, img_width, _ = img.shape

    # left
    if bbox[0] < 0:
        bbox[0] = 0

    # top
    height = bbox[3] - bbox[1]
    if (bbox[1] - HYPER_PARAM_SHIFT[1] * height) >= 0:
        bbox[1] = int(bbox[1] - HYPER_PARAM_SHIFT[1] * height)
    else:
        bbox[1] = 0

    # right
    if bbox[2] > img_width:
        bbox[2] = img_width

    # bottom
    if bbox[3] > img_height:
        bbox[3] = img_height

    # Should be an integer.
    bbox[0] = int(bbox[0])
    bbox[1] = int(bbox[1])
    bbox[2] = int(bbox[2])
    bbox[3] = int(bbox[3])