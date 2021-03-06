"""
    SORT: A Simple, Online and Realtime Tracker
    Copyright (C) 2016 Alex Bewley alex@dynamicdetection.com

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import print_function

import numpy as np
from sklearn.utils.linear_assignment_ import linear_assignment

from filterpy.kalman import KalmanFilter

from .utils import iou, convert_bbox_to_z, convert_x_to_bbox

DIM_X = 7
DIM_Z = 4


def associate_detections_to_trackers(detections, trackers, iou_threshold = 0.3):
    """
    Assigns detections to tracked object (both represented as bounding boxes)

    Returns 3 lists of matches, unmatched_detections and unmatched_trackers
    """
    
    lendet = len(detections)
    lentrk = len(trackers)

    if(lentrk==0):
        return np.empty((0,2),dtype=int), np.arange(lendet), np.empty((0,5),dtype=int)
    iou_matrix = np.zeros((lendet,lentrk),dtype=np.float32)

    for d,det in enumerate(detections):
        for t,trk in enumerate(trackers):
            iou_matrix[d,t] = iou(det,trk)
    iou_matrix[iou_matrix < iou_threshold] = 0.
    matched_indices = linear_assignment(-iou_matrix)

    costs = iou_matrix[tuple(matched_indices.T)] # select values from cost matrix by matched indices
    matches = matched_indices[np.where(costs)[0]] # remove zero values from matches
    unmatched_detections = np.where(np.in1d(range(lendet), matches[:,0], invert=True))[0]
    unmatched_trackers = np.where(np.in1d(range(lentrk), matches[:,1], invert=True))[0]

    if(len(matches)==0):
        matches = np.empty((0,2),dtype=int)

    return matches, unmatched_detections, unmatched_trackers


class KalmanBoxTracker(object):
    """
    This class represents the internel state of individual tracked objects observed as bbox.
    """
    count = 0
    def __init__(self, bbox):
        """
        Initialises a tracker using initial bounding box.
        """
        
        #define constant velocity model
        self.kf = KalmanFilter(dim_x=DIM_X, dim_z=DIM_Z)
        
        self.kf.F = np.eye(DIM_X)
        self.kf.F[:DIM_X - DIM_Z, DIM_Z - DIM_X:] = np.eye(3)
        
        self.kf.H = np.zeros((DIM_Z, DIM_X))
        self.kf.H[:DIM_Z, :DIM_Z] = np.eye(DIM_Z)

        self.kf.R[2:,2:] *= 10.
        self.kf.P[4:,4:] *= 1000. #give high uncertainty to the unobservable initial velocities
        self.kf.P *= 10.
        self.kf.Q[-1,-1] *= 0.01
        self.kf.Q[4:,4:] *= 0.01

        self.kf.x[:4] = convert_bbox_to_z(bbox)
        self.time_since_update = 0
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1
        self.history = []
        self.hits = 0
        self.hit_streak = 0
        self.age = 0

    def update(self, bbox):
        """
        Updates the state vector with observed bbox.
        """
        self.time_since_update = 0
        self.history = []
        self.hits += 1
        self.hit_streak += 1
        z = convert_bbox_to_z(bbox)
        self.kf.update(z)

    def predict(self):
        """
        Advances the state vector and returns the predicted bounding box estimate.
        """
        if((self.kf.x[6] + self.kf.x[2]) <= 0):
            self.kf.x[6] *= 0.0
        self.kf.predict()
        self.age += 1
        if(self.time_since_update > 0):
            self.hit_streak = 0
        self.time_since_update += 1
        bbox = convert_x_to_bbox(self.kf.x.astype('float32'))
        self.history.append(bbox)
        return self.history[-1]

    def get_state(self):
        """
        Returns the current bounding box estimate.
        """
        return convert_x_to_bbox(self.kf.x.astype('float32'))


class Sort(object):
    def __init__(self, max_age=1, min_hits=3):
        """
        Sets key parameters for SORT
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.trackers = []
        self.frame_count = 0

    def update(self, dets):
        """
        Params:
            dets - a numpy array of detections in the format [[x1,y1,x2,y2,score],[x1,y1,x2,y2,score],...]
        Requires: this method must be called once for each frame even with empty detections.
        Returns the a similar array, where the last column is the object ID.

        NOTE: The number of objects returned may differ from the number of detections provided.
        """
        self.frame_count += 1
        #get predicted locations from existing trackers.
        trks = np.zeros((len(self.trackers), 5), dtype='float32')
        to_del = []
        ret = []
        for t, trk in enumerate(trks):
            pos = self.trackers[t].predict()[0]
            trk[:] = [pos[0], pos[1], pos[2], pos[3], 0]
            if(np.any(np.isnan(pos))):
                to_del.append(t)
        trks = np.ma.compress_rows(np.ma.masked_invalid(trks))
        for t in reversed(to_del):
            self.trackers.pop(t)
        matched, unmatched_dets, unmatched_trks = associate_detections_to_trackers(dets, trks)

        #update matched trackers with assigned detections
        for m in matched:
            self.trackers[m[1]].update(dets[m[0],:])    

        #create and initialise new trackers for unmatched detections
        for i in unmatched_dets:
                trk = KalmanBoxTracker(dets[i, :]) 
                self.trackers.append(trk)
        i = len(self.trackers)
        for trk in reversed(self.trackers):
                d = trk.get_state()[0]
                if((trk.time_since_update < 1) and (trk.hit_streak >= self.min_hits or
                                                    self.frame_count <= self.min_hits)):
                    ret.append(np.concatenate((d, [trk.id + 1])).reshape(1, -1)) # +1 as MOT benchmark requires positive
                i -= 1
                #remove dead tracklet
                if(trk.time_since_update > self.max_age):
                    self.trackers.pop(i)
        if(len(ret) > 0):
            return np.concatenate(ret)
        return np.empty((0, 5))


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from skimage import io
    import os.path
    import time
    import argparse
    
    def parse_args():
            """Parse input arguments."""
            parser = argparse.ArgumentParser(description='SORT demo')
            parser.add_argument('--display', dest='display', help='Display online tracker output (slow) [False]',action='store_true')
            args = parser.parse_args()
            return args
        
    # all train
    sequences = ['PETS09-S2L1', 'TUD-Campus', 'TUD-Stadtmitte', 'ETH-Bahnhof', 'ETH-Sunnyday', 'ETH-Pedcross2', 'KITTI-13', 'KITTI-17', 'ADL-Rundle-6', 'ADL-Rundle-8', 'Venice-2']
    args = parse_args()
    display = args.display
    phase = 'train'
    total_time = 0.0
    total_frames = 0
    colours = np.random.rand(32, 3) #used only for display
    if(display):
        if not os.path.exists('mot_benchmark'):
            print('\n\tERROR: mot_benchmark link not found!\n\n    Create a symbolic link to the MOT benchmark\n    (https://motchallenge.net/data/2D_MOT_2015/#download). E.g.:\n\n    $ ln -s /path/to/MOT2015_challenge/2DMOT2015 mot_benchmark\n\n')
            exit()
        plt.ion()
        fig = plt.figure() 
    
    if not os.path.exists('output'):
        os.makedirs('output')
    
    for seq in sequences:
        mot_tracker = Sort() #create instance of the SORT tracker
        seq_dets = np.loadtxt('data/%s/det.txt' % (seq), delimiter=',').astype('float32') #load detections
        with open('output/%s.txt' % (seq), 'w') as out_file:
            print("Processing %s." % (seq))
            for frame in range(int(seq_dets[:, 0].max())):
                frame += 1 #detection and frame numbers begin at 1
                dets = seq_dets[seq_dets[:, 0]==frame, 2:7]
                dets[:, 2:4] += dets[:, 0:2] #convert to [x1, y1, w, h] to [x1, y1, x2, y2]
                total_frames += 1

                if(display):
                    ax1 = fig.add_subplot(111, aspect='equal')
                    fn = 'mot_benchmark/%s/%s/img1/%06d.jpg' % (phase, seq, frame)
                    im =io.imread(fn)
                    ax1.imshow(im)
                    plt.title(seq+' Tracked Targets')

                start_time = time.time()
                trackers = mot_tracker.update(dets)
                cycle_time = time.time() - start_time
                total_time += cycle_time

                for d in trackers:
                    print('%d, %d, %.2f, %.2f, %.2f, %.2f, 1, -1, -1, -1' % (frame, d[4], d[0], d[1], d[2]-d[0], d[3]-d[1]), file=out_file)
                    if(display):
                        d = d.astype(np.int32)
                        ax1.add_patch(patches.Rectangle((d[0], d[1]), d[2]-d[0], d[3]-d[1], fill=False, lw=3, ec=colours[d[4]%32, :]))
                        ax1.set_adjustable('box-forced')

                if(display):
                    fig.canvas.flush_events()
                    plt.draw()
                    ax1.cla()

    print("Total Tracking took: %.3f for %d frames or %.1f FPS" % (total_time, total_frames, total_frames / total_time))
    if(display):
        print("Note: to get real runtime results run without the option: --display")
    


