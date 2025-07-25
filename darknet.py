#!/usr/bin/env python3

"""
Python 3 wrapper for identifying objects in images

Running the script requires opencv-python to be installed (`pip install opencv-python`)
Directly viewing or returning bounding-boxed images requires scikit-image to be installed (`pip install scikit-image`)
Use pip3 instead of pip on some systems to be sure to install modules for python3
"""

import ctypes as ct
import random
import os
import cv2
import numpy as np


class BOX(ct.Structure):
    _fields_ = (
        ("x", ct.c_float),
        ("y", ct.c_float),
        ("w", ct.c_float),
        ("h", ct.c_float),
    )


FloatPtr = ct.POINTER(ct.c_float)
IntPtr = ct.POINTER(ct.c_int)


class DETECTION(ct.Structure):
    _fields_ = (
        ("bbox", BOX),
        ("classes", ct.c_int),
        ("best_class_idx", ct.c_int),
        ("prob", FloatPtr),
        ("mask", FloatPtr),
        ("objectness", ct.c_float),
        ("sort_class", ct.c_int),
        ("uc", FloatPtr),
        ("points", ct.c_int),
        ("embeddings", FloatPtr),
        ("embedding_size", ct.c_int),
        ("sim", ct.c_float),
        ("track_id", ct.c_int),
    )


DETECTIONPtr = ct.POINTER(DETECTION)


class DETNUMPAIR(ct.Structure):
    _fields_ = (
        ("num", ct.c_int),
        ("dets", DETECTIONPtr),
    )


DETNUMPAIRPtr = ct.POINTER(DETNUMPAIR)


class IMAGE(ct.Structure):
    _fields_ = (
        ("w", ct.c_int),
        ("h", ct.c_int),
        ("c", ct.c_int),
        ("data", FloatPtr),
    )


class METADATA(ct.Structure):
    _fields_ = (
        ("classes", ct.c_int),
        ("names", ct.POINTER(ct.c_char_p)),
    )


def network_width(net):
    return lib.network_width(net)


def network_height(net):
    return lib.network_height(net)


def bbox2points(bbox):
    """
    From bounding box yolo format
    to corner points cv2 rectangle
    """
    x, y, w, h = bbox
    xmin = round(x - (w / 2))
    xmax = round(x + (w / 2))
    ymin = round(y - (h / 2))
    ymax = round(y + (h / 2))
    return xmin, ymin, xmax, ymax


def class_colors(names):
    """
    Create a dict with one random BGR color for each
    class name
    """
    return {name: (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)) for name in names}


def load_network(config_file, data_file, weights, batch_size=1):
    """
    load model description and weights from config files
    args:
        config_file (str): path to .cfg model file
        data_file (str): path to .data model file
        weights (str): path to weights
    returns:
        network: trained model
        class_names
        class_colors
    """
    network = load_net_custom(
        config_file.encode("ascii"),
        weights.encode("ascii"), 0, batch_size)
    metadata = load_meta(data_file.encode("ascii"))
    class_names = [metadata.names[i].decode("ascii") for i in range(metadata.classes)]
    colors = class_colors(class_names)
    return network, class_names, colors


def print_detections(detections, coordinates=False):
    print("\nObjects:")
    for label, confidence, bbox in detections:
        x, y, w, h = bbox
        if coordinates:
            print("{}: {}%    (left_x: {:.0f}   top_y:  {:.0f}   width:   {:.0f}   height:  {:.0f})".format(label, confidence, x, y, w, h))
        else:
            print("{}: {}%".format(label, confidence))

def draw_boxes(detections, image, colors):
    import cv2
    for label, confidence, bbox in detections:
        left, top, right, bottom = bbox2points(bbox)
        cv2.rectangle(image, (left, top), (right, bottom), colors[label], 1)
        cv2.putText(image, "{} [{:.2f}]".format(label, float(confidence)),
                    (left, top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    colors[label], 2)
    return image
    
def draw_boxes_video(detections, image, colors, width, height):
    import cv2
    origin_height, origin_width = image.shape[0], image.shape[1]
    ratio_width = origin_width / width
    ratio_height = origin_height / height
    for label, confidence, bbox in detections:
        left, top, right, bottom = bbox2points(bbox)
        left = int(left * ratio_width)
        right = int(right * ratio_width)
        top = int(top * ratio_height)
        bottom = int(bottom * ratio_height)
        cv2.rectangle(image, (left, top), (right, bottom), colors[label], 1)
        cv2.putText(image, "{} [{:.2f}]".format(label, float(confidence)),
                    (left, top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    colors[label], 2)
    return image


def decode_detection(detections):
    decoded = []
    for label, confidence, bbox in detections:
        confidence = str(round(confidence * 100, 2))
        decoded.append((str(label), confidence, bbox))
    return decoded


# https://www.pyimagesearch.com/2015/02/16/faster-non-maximum-suppression-python/
# Malisiewicz et al.
def non_max_suppression_fast(detections, overlap_thresh):
    boxes = []
    for detection in detections:
        _, _, _, (x, y, w, h) = detection
        x1 = x - w / 2
        y1 = y - h / 2
        x2 = x + w / 2
        y2 = y + h / 2
        boxes.append(np.array([x1, y1, x2, y2]))
    boxes_array = np.array(boxes)

    # initialize the list of picked indexes
    pick = []
    # grab the coordinates of the bounding boxes
    x1 = boxes_array[:, 0]
    y1 = boxes_array[:, 1]
    x2 = boxes_array[:, 2]
    y2 = boxes_array[:, 3]
    # compute the area of the bounding boxes and sort the bounding
    # boxes by the bottom-right y-coordinate of the bounding box
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(y2)
    # keep looping while some indexes still remain in the indexes
    # list
    while len(idxs) > 0:
        # grab the last index in the indexes list and add the
        # index value to the list of picked indexes
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)
        # find the largest (x, y) coordinates for the start of
        # the bounding box and the smallest (x, y) coordinates
        # for the end of the bounding box
        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])
        # compute the width and height of the bounding box
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)
        # compute the ratio of overlap
        overlap = (w * h) / area[idxs[:last]]
        # delete all indexes from the index list that have
        idxs = np.delete(idxs, np.concatenate(([last],
                                               np.where(overlap > overlap_thresh)[0])))
        # return only the bounding boxes that were picked using the
        # integer data type
    return [detections[i] for i in pick]


def remove_negatives(detections, class_names, num):
    """
    Remove all classes with 0% confidence within the detection
    """
    predictions = []
    for j in range(num):
        for idx, name in enumerate(class_names):
            if detections[j].prob[idx] > 0:
                bbox = detections[j].bbox
                bbox = (bbox.x, bbox.y, bbox.w, bbox.h)
                predictions.append((name, detections[j].prob[idx], (bbox)))
    return predictions


def remove_negatives_faster(detections, class_names, num):
    """
    Faster version of remove_negatives (very useful when using yolo9000)
    """
    predictions = []
    for j in range(num):
        if detections[j].best_class_idx == -1:
            continue
        name = class_names[detections[j].best_class_idx]
        bbox = detections[j].bbox
        bbox = (bbox.x, bbox.y, bbox.w, bbox.h)
        predictions.append((name, detections[j].prob[detections[j].best_class_idx], bbox))
    return predictions


def detect_image(network, class_names, image, thresh=.5, hier_thresh=.5, nms=.45):
    """
        Returns a list with highest confidence class and their bbox
    """
    pnum = ct.pointer(ct.c_int(0))
    predict_image(network, image)
    detections = get_network_boxes(network, image.w, image.h,
                                   thresh, hier_thresh, None, 0, pnum, 0)
    num = pnum[0]
    if nms:
        do_nms_sort(detections, num, len(class_names), nms)
    predictions = remove_negatives(detections, class_names, num)
    predictions = decode_detection(predictions)
    free_detections(detections, num)
    return sorted(predictions, key=lambda x: x[1])


if os.name == "posix":
    cwd = os.path.dirname(__file__)
    lib = ct.CDLL(cwd + "/libdarknet.so", ct.RTLD_GLOBAL)
elif os.name == "nt":
    cwd = os.path.dirname(__file__)
    os.environ["PATH"] = os.path.pathsep.join((cwd, os.environ["PATH"]))
    lib = ct.CDLL("darknet.dll", winmode = 0, mode = ct.RTLD_GLOBAL)
else:
    lib = None  # Intellisense
    print("Unsupported OS")
    exit()

lib.network_width.argtypes = (ct.c_void_p,)
lib.network_width.restype = ct.c_int
lib.network_height.argtypes = (ct.c_void_p,)
lib.network_height.restype = ct.c_int

copy_image_from_bytes = lib.copy_image_from_bytes
copy_image_from_bytes.argtypes = (IMAGE, ct.c_char_p)

predict = lib.network_predict_ptr
predict.argtypes = (ct.c_void_p, FloatPtr)
predict.restype = FloatPtr

set_gpu = lib.cuda_set_device
init_cpu = lib.init_cpu

make_image = lib.make_image
make_image.argtypes = (ct.c_int, ct.c_int, ct.c_int)
make_image.restype = IMAGE

get_network_boxes = lib.get_network_boxes
get_network_boxes.argtypes = (ct.c_void_p, ct.c_int, ct.c_int, ct.c_float, ct.c_float, IntPtr, ct.c_int, IntPtr,
                              ct.c_int)
get_network_boxes.restype = DETECTIONPtr

make_network_boxes = lib.make_network_boxes
make_network_boxes.argtypes = (ct.c_void_p,)
make_network_boxes.restype = DETECTIONPtr

free_detections = lib.free_detections
free_detections.argtypes = (DETECTIONPtr, ct.c_int)

free_batch_detections = lib.free_batch_detections
free_batch_detections.argtypes = (DETNUMPAIRPtr, ct.c_int)

free_ptrs = lib.free_ptrs
free_ptrs.argtypes = (ct.POINTER(ct.c_void_p), ct.c_int)

network_predict = lib.network_predict_ptr
network_predict.argtypes = (ct.c_void_p, FloatPtr)

reset_rnn = lib.reset_rnn
reset_rnn.argtypes = (ct.c_void_p,)

load_net = lib.load_network
load_net.argtypes = (ct.c_char_p, ct.c_char_p, ct.c_int)
load_net.restype = ct.c_void_p

load_net_custom = lib.load_network_custom
load_net_custom.argtypes = (ct.c_char_p, ct.c_char_p, ct.c_int, ct.c_int)
load_net_custom.restype = ct.c_void_p

free_network_ptr = lib.free_network_ptr
free_network_ptr.argtypes = (ct.c_void_p,)
free_network_ptr.restype = ct.c_void_p

do_nms_obj = lib.do_nms_obj
do_nms_obj.argtypes = (DETECTIONPtr, ct.c_int, ct.c_int, ct.c_float)

do_nms_sort = lib.do_nms_sort
do_nms_sort.argtypes = (DETECTIONPtr, ct.c_int, ct.c_int, ct.c_float)

free_image = lib.free_image
free_image.argtypes = (IMAGE,)

letterbox_image = lib.letterbox_image
letterbox_image.argtypes = (IMAGE, ct.c_int, ct.c_int)
letterbox_image.restype = IMAGE

load_meta = lib.get_metadata
lib.get_metadata.argtypes = (ct.c_char_p,)
lib.get_metadata.restype = METADATA

load_image = lib.load_image_color
load_image.argtypes = (ct.c_char_p, ct.c_int, ct.c_int)
load_image.restype = IMAGE

rgbgr_image = lib.rgbgr_image
rgbgr_image.argtypes = (IMAGE,)

predict_image = lib.network_predict_image
predict_image.argtypes = (ct.c_void_p, IMAGE)
predict_image.restype = FloatPtr

predict_image_letterbox = lib.network_predict_image_letterbox
predict_image_letterbox.argtypes = (ct.c_void_p, IMAGE)
predict_image_letterbox.restype = FloatPtr

network_predict_batch = lib.network_predict_batch
network_predict_batch.argtypes = (ct.c_void_p, IMAGE, ct.c_int, ct.c_int, ct.c_int,
                                  ct.c_float, ct.c_float, IntPtr, ct.c_int, ct.c_int)
network_predict_batch.restype = DETNUMPAIRPtr
