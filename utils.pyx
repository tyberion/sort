import numpy as np
cimport cython

cimport numpy as np

DTYPE = np.float32

ctypedef np.float32_t DTYPE_t


@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def iou(np.ndarray[DTYPE_t, ndim=1] bb_test,
        np.ndarray[DTYPE_t, ndim=1] bb_gt):
    """
    Computes IUO between two bboxes in the form [x1,y1,x2,y2]
    """
    assert bb_test.dtype == DTYPE and bb_gt.dtype == DTYPE
    
    cdef DTYPE_t xx1, yy1, xx2, yy2, w, h, wh, o
    
    xx1 = max(bb_test[0], bb_gt[0])
    yy1 = max(bb_test[1], bb_gt[1])
    xx2 = min(bb_test[2], bb_gt[2])
    yy2 = min(bb_test[3], bb_gt[3])
    w = max(0., xx2 - xx1)
    h = max(0., yy2 - yy1)
    wh = w * h
    o = wh / ((bb_test[2] - bb_test[0]) * (bb_test[3] - bb_test[1])
        + (bb_gt[2] - bb_gt[0]) * (bb_gt[3] - bb_gt[1]) - wh)
    return o


@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def convert_bbox_to_z(np.ndarray[DTYPE_t, ndim=1] bbox):
    """
    Takes a bounding box in the form [x1,y1,x2,y2] and returns z in the form
        [x,y,s,r] where x,y is the centre of the box and s is the scale/area and r is
        the aspect ratio
    """
    
    cdef DTYPE_t w, h, x, y, s, r
    cdef np.ndarray[DTYPE_t, ndim=2] result
    
    result = np.zeros([4, 1], dtype='float32')
    
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = bbox[0] + w / 2.
    y = bbox[1] + h / 2.
    s = w * h   #scale is just area
    r = w / h
    result[0, 0] = x
    result[1, 0] = y
    result[2, 0] = s
    result[3, 0] = r
    return result


@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def convert_x_to_bbox(np.ndarray[DTYPE_t, ndim=2] x, DTYPE_t score=-1):
    """
    Takes a bounding box in the centre form [x,y,s,r] and returns it in the form
        [x1,y1,x2,y2] where x1,y1 is the top left and x2,y2 is the bottom right
    """
    cdef DTYPE_t w, h, x1, x2, y1, y2
    cdef np.ndarray[DTYPE_t, ndim=2] result, result_score
    
    result = np.zeros([1, 4], dtype='float32')
    result_score = np.zeros([1, 5], dtype='float32')
    
    w = np.sqrt(x[2, 0] * x[3, 0])
    h = x[2, 0] / w
    
    x1 = x[0, 0] - w / 2
    y1 = x[1, 0] - h / 2
    x2 = x[0, 0] + w / 2
    y2 = x[1, 0] + h / 2
    
    if(score==-1):
        result[0, 0] = x1
        result[0, 1] = y1
        result[0, 2] = x2
        result[0, 3] = y2
        return result
    else:
        result_score[0, 0] = x1
        result_score[0, 1] = y1
        result_score[0, 2] = x2
        result_score[0, 3] = y2
        result_score[0, 4] = score
        return result_score
