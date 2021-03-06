import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
import os
import sys
import time
import io
import click
from logbook import Logger, FileHandler

import numpy as np
from itertools import product
import scipy.io as sio
import tensorflow as tf
from tensorflow.contrib.tensorboard.plugins import projector
import tensorflow.contrib.rnn as rnn_cell
import tensorflow.contrib.legacy_seq2seq as seq2seq
from tensorflow.python.keras.layers import Reshape, Dense
from tensorflow.python.keras.layers import Dense, TimeDistributed, Flatten, RepeatVector, Dropout
from tensorflow.python.keras.layers import Concatenate, Reshape, Activation, Permute
from tensorflow.python.keras.layers import Conv2D, SeparableConv2D, LocallyConnected2D
from tensorflow.python.keras.layers import GlobalAveragePooling1D, AveragePooling2D, MaxPooling2D
from tensorflow.python.keras.layers import LSTM, GRU, Bidirectional
from tensorflow.python.keras.layers import BatchNormalization

class HParam():

    def __init__(self,subject, predir, pretrain_dir, predict_dir, window_length, window_step, batch_size, signal_image, dim_emg, dim_glove, max_epoch):
        self.batch_size = batch_size
        self.learning_rate = 0.1
        self.decay_steps = 200

        self.decay_rate = 0.1
        self.grad_clip = 1

        self.state_size = 512
        # self.state_size = 256
        
        # self.gestures = list(range(13,21))
        self.gestures = list(range(1,53))

        self.num_layers = 1
        # self.log_dir = './logs-meanrest-radian/S{s:d}'.format(s=subject)
        if len(window_length)==1:
            self.log_dir = predir+'/S{s:d}'.format(s=subject)
            self.loss_dir = predir+'/S{s:d}/loss.txt'.format(s=subject)
        else:
            self.log_dir = predir+'/S{s:d}'.format(s=subject)
            self.loss_dir = predir+'/S{s:d}/loss.txt'.format(s=subject)
        # self.predict_dir = './logs-meanrest-signalimage-raw-pretrain-g52-2018.5.26-net2-mix-w4-s1/S{s:d}'.format(s=subject)
        # self.predict_dir = './logs-meanrest-signalimage-raw-pretrain-g52-2018.6.6-net2-mix-w4-s1/S{s:d}'.format(s=subject)
        self.predict_dir = predict_dir # './logs-meanrest-lowpass-signalimage-raw-pretrain-g52-2018.6.6-net2-mix-w4-s1/S{s:d}'.format(s=subject)

        # self.recognize_dir = './logs-real-signalimage-premeanrestraw-rec-pretrain-g52-2018.5.26-w1-s1/S{s:d}'.format(s=subject)
        # self.recognize_dir = './logs-real-signalimage-premeanrestraw-rec-pretrain-g52-2018.5.26-traingroundtruth-w1-s1/S{s:d}'.format(s=subject)
        self.recognize_dir = pretrain_dir # './logs-meanrest-lowpass-signalimage-raw-pre-rec-fix-pretrain-randominit-g52-net2-w1-s1/S27'
        # self.recognize_dir = './logs-gengnet-semi-signalimage-abslowpass-pretrain-momentum-wd1-db1-g52-w1-s1/S{s:d}'.format(s=subject)

        self.gen_num = 500 # how many chars to generate
        self.dim_emg = dim_emg
        self.dim_glove = dim_glove
        # self.dim_glove = 5

        self.window_length = window_length
        self.window_step = window_step
        self.pretrain_dir = pretrain_dir
        self.signal_image = signal_image
        self.max_epoch = max_epoch
        print 'dim_emg:', self.dim_emg
        print 'dim_glove:', self.dim_glove


class Dataset(object):

#     framerate = FRAMERATE
#     num_semg_row = NUM_SEMG_ROW
#     num_semg_col = NUM_SEMG_COL
#     subjects = list(range(27))
#     gestures = list(range(53))

    def __init__(self, root, coroot, subjects, args, preprocess=True):
        self.root = root
        self.coroot = coroot
        self.preprocess = preprocess
        self.train_begin = 0
        self.val_begin = 0
        self.test_begin = 0
        self.gen_begin = 0
        self.val_data_num = 500
        # self.gen_begin = 1620

        self.gestures = args.gestures
        self.trials = list(range(10))
        self.subjects = subjects
        self.window_length = args.window_length
        self.window_step = args.window_step
        self.signal_image = args.signal_image
        self.train_pred_glove = None


    def get_one_fold_intra_subject_trials(self):
        return [0, 2, 3, 5, 7, 8, 9], [1, 4, 6]

    def get_gen_trials(self):
        return range(10)

    def get_trial_func(self, *args, **kargs):
        return GetTrial(*args, **kargs)

    def tozero(self, vector):
        print vector.shape
        b = list(set(vector))
        return np.array([x if x < 0 else b.index(x) for x in vector.ravel()]).reshape(vector.shape)
    def gen_to_zero(self, matrix):
        b=list(set(np.hstack(matrix)))
        a=[]
        for i in range(len(matrix)):
            raw_a = []
            for j in range(len(matrix[i])):
                raw_a.append(b.index(matrix[i][j]))
            a.append(raw_a)
            # print raw_a
        return np.array(a)

    def balance_gesture(self, index, label):
        num_gesture = len(list(set(label)))
        num_sample_per_gesture = int(np.round(len(index) / num_gesture))
        choice = []
        for gesture in set(label):
            mask = label[index] == gesture
            choice.append(self.random_state.choice(np.where(mask)[0], num_sample_per_gesture))
        choice = np.hstack(choice)
        return index[choice]

    def genIndex(self, chanums):
        
        index = []
        i = 1
        j = i+1
          
        if (chanums % 2) == 0:
            Ns = chanums+1 
        else:      
            Ns = chanums
          
        index.append(1)
        t = chr(i+ord('A'))
        while(i!=j):
            l = ""
            l = l+chr(i+ord('A'))
            l = l+chr(j+ord('A'))
            r = ""
            r = r+chr(j+ord('A'))
            r = r+chr(i+ord('A'))
            if(j>Ns):
                j = 1
            elif(t.find(l)==-1 and t.find(r)==-1):
                index.append(j)
                t = t+chr(j+ord('A'))
                i = j
                j = i+1
            else:
                j = j+1 
        new_index = []
        if (chanums % 2) == 0:
            for i in range(len(index)):
                if index[i] != chanums+1:
                    new_index.append(index[i])  
            index = np.array(new_index)  
        index = np.array(index)  
        index = index-1
        return index

    def get_train_data(self):
        train_emg = []
        train_glove = []
        train_label = []
        train_seg_start =[0]
        index = []
        iidex = 0
        for subject in self.subjects:
            for gesture in self.gestures:
                for trial in self.get_one_fold_intra_subject_trials()[0]:
                    emg_path = self.get_path(self.root, subject, gesture, trial)
    #                 print emg_path
                    emg_data = _get_data_aux(emg_path, self.preprocess)
                    glove_path = self.get_glove_path(self.coroot, subject, gesture, trial)
                    glove_data = _get_glove_aux(glove_path)
                    # print 'glove_data:', glove_data
                    label = np.repeat(gesture, len(emg_data))
                    train_emg.append(emg_data)
                    train_glove.append(glove_data)
                    train_label.append(label)

                    index.append(np.arange(0,len(emg_data)-self.window_length[-1]+1,self.window_step)+iidex)
                    train_seg_start.append(len(emg_data))
                    iidex = iidex+len(emg_data)

        self.train_emg = np.vstack(train_emg)

        if self.signal_image:
            self.train_emg = self.train_emg[:,self.genIndex(self.train_emg.shape[1])]

        self.train_glove = np.vstack(train_glove)
        self.train_label = self.tozero(np.hstack(train_label)).astype(np.float32)
        self.train_seg_start = np.array(train_seg_start)
        assert(len(self.train_emg) == iidex)
        print '**************************************'

        # all_index = np.hstack(index)
        # print 'all_index:', len(all_index)
        # self.val_data_num = len(all_index)/20

        # val_part = np.arange(0,len(all_index),int(len(all_index)/self.val_data_num))[0:self.val_data_num]
        # self.val_index = all_index[val_part]
        # print 'val_index_length:', len(self.val_index)
        # self.train_index = np.delete(all_index, val_part)
        # print 'train_index_length:', len(self.train_index)

        self.train_index = np.hstack(index)
        print len(self.train_index)
        self.random_state = np.random.RandomState(667)

        self.train_index = self.balance_gesture(self.train_index, self.train_label)

        # self.val_index = np.hstack(index)
        # self.val_data_num = len(self.val_index)

        self.train_data_num = len(self.train_index)
        # print len(self.train_emg)
        # print self.train_data_num
        # print self.train_index
        sample = range(len(self.train_index))
        self.random_state.shuffle(sample)
        self.train_index = self.train_index[sample]
        # self.val_index = self.val_index[sample]
        print self.train_index
        print 'train_num:', len(self.train_index)



#     def get_val_data(self, subject):
#         val_emg = []
#         val_glove = []
#         val_label = []
#         val_seg_start = [0]
#         index = []
#         iidex = 0
#         for gesture in self.gestures:
#             for trial in self.get_one_fold_intra_subject_trials()[1]:
#                 emg_path = self.get_path(self.root, subject, gesture, trial)
# #                 print emg_path
#                 emg_data = _get_data_aux(emg_path, self.preprocess)
#                 glove_path = self.get_glove_path(self.coroot, subject, gesture, trial)
#                 glove_data = _get_glove_aux(glove_path)
#                 # print 'glove_data:', glove_data
#                 label = np.repeat(gesture, len(emg_data))
#                 val_emg.append(emg_data)
#                 val_glove.append(glove_data)
#                 val_label.append(label)
#                 index.append(np.arange(0,len(emg_data)-self.window_length+1,self.window_step)+iidex)
#                 val_seg_start.append(len(emg_data))
#                 iidex = iidex+len(emg_data)
#         self.val_emg = np.vstack(val_emg)
#         self.val_glove = np.vstack(val_glove)
#         self.val_label = np.hstack(val_label)
#         self.val_seg_start = np.array(val_seg_start)
#         assert(len(self.val_emg) == iidex)

#         self.val_index = np.hstack(index)
#         self.val_data_num = len(self.val_index)
#         sample = range(len(self.val_index))
#         np.random.RandomState(667).shuffle(sample)
#         self.val_index = self.val_index[sample]
#         print len(self.val_index)

    # def get_val_data(self, subject):
    #     val_emg = []
    #     val_glove = []
    #     val_label = []
    #     val_seg_start = [0]
    #     index = []
    #     iidex = 0
    #     self.val_emg = np.vstack(val_emg)
    #     self.val_glove = np.vstack(val_glove)
    #     self.val_label = np.hstack(val_label)
    #     self.val_seg_start = np.array(val_seg_start)
    #     assert(len(self.val_emg) == iidex)

    #     self.val_index = np.hstack(index)
    #     self.val_data_num = len(self.val_index)
    #     sample = range(len(self.val_index))
    #     np.random.RandomState(667).shuffle(sample)
    #     self.val_index = self.val_index[sample]
    #     print len(self.val_index)      

    def get_test_data(self):
        test_emg = []
        test_glove = []
        test_label = []
        test_seg_start = [0]
        index = []
        iidex = 0
        for subject in self.subjects:
            for gesture in self.gestures:
                for trial in self.get_one_fold_intra_subject_trials()[1]:
                    emg_path = self.get_path(self.root, subject, gesture, trial)
    #                 print emg_path
                    emg_data = _get_data_aux(emg_path, self.preprocess)
                    glove_path = self.get_glove_path(self.coroot, subject, gesture, trial)
                    glove_data = _get_glove_aux(glove_path)
                    label = np.repeat(gesture, len(emg_data))
                    test_emg.append(emg_data)
                    test_glove.append(glove_data)
                    test_label.append(label)
                    index.append(np.arange(0,len(emg_data)-self.window_length[-1]+1,self.window_step)+iidex)
                    test_seg_start.append(len(emg_data))
                    iidex = iidex+len(emg_data)
        self.test_emg = np.vstack(test_emg)

        if self.signal_image:
            self.test_emg = self.test_emg[:,self.genIndex(self.test_emg.shape[1])]


        self.test_glove = np.vstack(test_glove)
        self.test_label = self.tozero(np.hstack(test_label)).astype(np.float32)
        self.test_seg_start = np.array(test_seg_start)
        assert(len(self.test_emg) == iidex)

        self.test_index = np.hstack(index)
        self.test_data_num = len(self.test_index)
        # print self.test_data_num

#     def get_genera_data(self,subject):
#         gen_emg = []
#         gen_glove = []
#         gen_label = []
#         index = []
#         iidex = 0
#         for gesture in self.gestures:
#             for trial in self.get_gen_trials():
#                 emg_path = self.get_path(self.root, subject, gesture, trial)
# #                 print emg_path
#                 emg_data = _get_data_aux(emg_path, self.preprocess)
#                 glove_path = self.get_glove_path(self.coroot, subject, gesture, trial)
#                 glove_data = _get_glove_aux(glove_path)
#                 label = np.repeat(gesture, len(emg_data))
#                 gen_emg.append(emg_data)
#                 gen_glove.append(glove_data)
#                 gen_label.append(label)
#                 index.append(np.arange(0,len(emg_data)-self.window_length+1,self.window_step)+iidex)
#                 iidex = iidex + len(emg_data)
#         self.gen_emg = np.vstack(gen_emg)
#         self.gen_glove = np.vstack(gen_glove)
#         self.gen_label = np.hstack(gen_label)
#         assert(len(self.gen_emg)==iidex)

#         self.gen_index = np.hstack(index)
#         self.gen_data_num = len(self.gen_index)
#         print self.gen_data_num

    def get_genera_data(self):
        gen_emg = []
        gen_glove = []
        gen_label = []
        for subject in self.subjects:
            for gesture in self.gestures:
                for trial in self.get_gen_trials():
                    emg_path = self.get_path(self.root, subject, gesture, trial)
    #                 print emg_path
                    emg_data = _get_data_aux(emg_path, self.preprocess)
                    glove_path = self.get_glove_path(self.coroot, subject, gesture, trial)
                    glove_data = _get_glove_aux(glove_path)
                    label = np.repeat(gesture, len(emg_data))
                    gen_emg.append(emg_data)
                    gen_glove.append(glove_data)
                    gen_label.append(label)
        self.gen_emg = np.array(gen_emg)
        if self.signal_image:
            self.gen_emg = np.array([self.gen_emg[i][:,self.genIndex(self.gen_emg[i].shape[1])] for i in range(len(self.gen_emg))])

        self.gen_glove = np.array(gen_glove)
        self.gen_label = self.gen_to_zero(np.array(gen_label))
        # self.gen_label = np.array(gen_label)

        self.gen_data_num = self.gen_emg.shape[0]
        self.gen_index = np.arange(self.gen_data_num)

    def next_batch(self, num_batch, set_type):
        a=[]
        b=[]
        c=[]
        d=[]
        max_batch_length=0
        if set_type == 'train':
            if (self.train_begin+num_batch)> self.train_data_num:
                tmp_index = np.array(list(self.train_index[self.train_begin:]) + list(self.train_index[0:(self.train_begin+num_batch-self.train_data_num)]))
                self.train_begin = 0
            else:
                tmp_index = self.train_index[self.train_begin:(self.train_begin+num_batch)]
                # print 'tmp_index:', tmp_index.shape
                # print self.train_index[self.train_begin:(self.train_begin+num_batch)]
                self.train_begin = self.train_begin+num_batch
        elif set_type == 'test':
            if (self.test_begin+num_batch)> self.test_data_num:
                tmp_index = np.array(list(self.test_index[self.test_begin:]) + list(self.test_index[0:(self.test_begin+num_batch-self.test_data_num)]))
                self.test_begin=0
            else:
                tmp_index = self.test_index[self.test_begin:(self.test_begin+num_batch)]
                # print 'test_tmp_index:', tmp_index.shape
                self.test_begin = self.test_begin+num_batch
        # elif set_type == 'val':
        #     if (self.val_begin+num_batch)> self.val_data_num:
        #         tmp_index = np.array(list(self.val_index[self.val_begin:]) + list(self.val_index[0:(self.val_begin+num_batch-self.val_data_num)]))
        #         self.val_begin=0
        #     else:
        #         tmp_index = self.val_index[self.val_begin:(self.val_begin+num_batch)]
        #         # print 'val_tmp_index:', tmp_index.shape
        #         self.val_begin = self.val_begin+num_batch      
        else:
            if (self.gen_begin+num_batch)> self.gen_data_num:
                tmp_index = np.array(list(self.gen_index[self.gen_begin:]) + list(self.gen_index[0:(self.gen_begin+num_batch-self.gen_data_num)]))
                self.gen_begin=0
            else:
                tmp_index = self.gen_index[self.gen_begin:(self.gen_begin+num_batch)]
                # print 'gen_tmp_index:', tmp_index.shape
                self.gen_begin = self.gen_begin+num_batch
            # if (self.gen_begin+num_batch)> self.gen_data_num:
            #     tmp_index = np.array(list(self.gen_index[self.gen_begin:]) + list(self.gen_index[0:(self.gen_begin+num_batch-self.gen_data_num)]))
            #     self.gen_begin=0
            # else:
            #     tmp_index = self.gen_index[self.gen_begin:(self.gen_begin+num_batch)]
            #     # print 'gen_tmp_index:', tmp_index.shape
            #     self.gen_begin = self.gen_begin+num_batch

        # prime = 0.01*np.array([129.59580994, 112.42184448, 112.27864838, 137.90840149, 114.439888, 83.87464142, 77.66155243, 101.59606171, 93.66666412, 68.2119751, 153.35644531, 112.37625122, 94.74073792, 71.11283112, 158.03703308, 112.94902802, 104.66666412, 91.54741669, 143.52468872, 149.53184509, 141.222229, 115.2272644]) # glove rest
        # prime = np.array([129.59580994, 112.42184448, 112.27864838, 137.90840149, 114.439888, 83.87464142, 77.66155243, 101.59606171, 93.66666412, 68.2119751, 153.35644531, 112.37625122, 94.74073792, 71.11283112, 158.03703308, 112.94902802, 104.66666412, 91.54741669, 143.52468872, 149.53184509, 141.222229, 115.2272644]) # glove rest
        prime = 0.01*np.array([141.42471313, 112.83409119, 113.78411865, 129.12123108, 125.65979767, 119.64640045, 95.61739349, 112.13970184, 128.75344849, 81.33988953, 150.52861023, 123.24646759, 113.32148743, 77.64886475, 150.32717896, 124.62281036, 146.92736816, 101.37089539, 138.00967407, 130.77967834, 146.80603027, 118.58580017])
        
        prime = prime[0:19]

        # prime = prime[np.array([2,6,10,14,18])]
        if set_type == 'train':
            # print 'max_batch_length:', max_batch_length

            selected_window_length = 0
            if len(self.window_length)==1:
                selected_window_length = self.window_length[0]
            else:
                selected_window_length = self.window_length[np.random.randint(0,len(self.window_length))]
            # print 'selected_window_length:', selected_window_length
            max_batch_length = selected_window_length

            for i in range(len(tmp_index)):
                emg_col = self.train_emg.shape[1]
                glove_col = self.train_glove.shape[1]
                a.append(self.train_emg[tmp_index[i]:(tmp_index[i]+selected_window_length)])
                if tmp_index[i] in self.train_seg_start:
                    b.append(np.vstack((prime.reshape(1,glove_col),self.train_glove[tmp_index[i]:(tmp_index[i]+selected_window_length-1)])))
                else:
                    b.append(self.train_glove[(tmp_index[i]-1):(tmp_index[i]+selected_window_length-1)])
                # print b[-1].shape
                c.append(self.train_glove[tmp_index[i]:(tmp_index[i]+selected_window_length)])
                d.append(self.train_label[tmp_index[i]:(tmp_index[i]+selected_window_length)])
          
            X_length = [a[i].shape[0] for i in range(len(tmp_index))]
        elif set_type == 'test':
            # print max_batch_length
            selected_window_length = 0
            if len(self.window_length)==1:
                selected_window_length = self.window_length[0]
            else:
                selected_window_length = self.window_length[np.random.randint(0,len(self.window_length))]
            # print 'selected_window_length:', selected_window_length
            max_batch_length = selected_window_length

            # print 'selected_window_length:', selected_window_length
            for i in range(len(tmp_index)):
                emg_col = self.test_emg.shape[1]
                glove_col = self.test_glove.shape[1]
                a.append(self.test_emg[tmp_index[i]:(tmp_index[i]+selected_window_length)])

                if tmp_index[i] in self.test_seg_start:
                    b.append(np.vstack((prime.reshape(1,glove_col),self.test_glove[tmp_index[i]:(tmp_index[i]+selected_window_length-1)])))
                else:
                    b.append(self.test_glove[(tmp_index[i]-1):(tmp_index[i]+selected_window_length-1)])
                c.append(self.test_glove[tmp_index[i]:(tmp_index[i]+selected_window_length)])
                d.append(self.test_label[tmp_index[i]:(tmp_index[i]+selected_window_length)])

            X_length = [a[i].shape[0] for i in range(len(tmp_index))]
        elif set_type == 'val':
            # print max_batch_length
            selected_window_length = 0
            if len(self.window_length)==1:
                selected_window_length = self.window_length[0]
            else:
                selected_window_length = self.window_length[np.random.randint(0,len(self.window_length))]
            # print 'selected_window_length:', selected_window_length
            max_batch_length = selected_window_length

            # print 'selected_window_length:', selected_window_length
            for i in range(len(tmp_index)):
                emg_col = self.train_emg.shape[1]
                glove_col = self.train_glove.shape[1]
                a.append(self.train_emg[tmp_index[i]:(tmp_index[i]+selected_window_length)])

                if tmp_index[i] in self.train_seg_start:
                    b.append(np.vstack((prime.reshape(1,glove_col),self.train_glove[tmp_index[i]:(tmp_index[i]+selected_window_length-1)])))
                else:
                    b.append(self.train_glove[(tmp_index[i]-1):(tmp_index[i]+selected_window_length-1)])
                c.append(self.train_glove[tmp_index[i]:(tmp_index[i]+selected_window_length)])
                d.append(self.train_label[tmp_index[i]:(tmp_index[i]+selected_window_length)])

            X_length = [a[i].shape[0] for i in range(len(tmp_index))]
        else:
            # max_batch_length = self.window_length
            # print 'max_batch_length:', max_batch_length
            # for i in range(len(tmp_index)):
            #     emg_col = self.gen_emg.shape[1]
            #     glove_col = self.gen_glove.shape[1]
            #     a.append(self.gen_emg[tmp_index[i]:(tmp_index[i]+self.window_length)])
            #     if tmp_index[i]==0:
            #         b.append(np.vstack((prime.reshape(1,glove_col),self.gen_glove[tmp_index[i]:(tmp_index[i]+self.window_length-1)])))
            #     else:
            #         b.append(self.gen_glove[(tmp_index[i]-1):(tmp_index[i]+self.window_length-1)])
            #     c.append(self.gen_glove[tmp_index[i]:(tmp_index[i]+self.window_length)])
            #     d.append(self.gen_label[tmp_index[i]:(tmp_index[i]+self.window_length)]) 
            # X_length = [a[i].shape[0] for i in range(len(tmp_index))]  


            max_batch_length = np.max([self.gen_emg[tmp_index[i]].shape[0] for i in range(len(tmp_index))])
            # print max_batch_length
            for i in range(len(tmp_index)):
                clen = max_batch_length-self.gen_emg[tmp_index[i]].shape[0]
                emg_col = self.gen_emg[tmp_index[i]].shape[1]
                glove_col = self.gen_glove[tmp_index[i]].shape[1]
                if clen>0:
                    a.append(np.vstack((self.gen_emg[tmp_index[i]], np.zeros((clen,emg_col)))))
                    b.append(np.vstack((prime.reshape(1,glove_col),self.gen_glove[tmp_index[i]], np.zeros((clen-1,glove_col)))))
                    c.append(np.vstack((self.gen_glove[tmp_index[i]], np.zeros((clen,glove_col)))))
                    d.append(np.hstack((self.gen_label[tmp_index[i]], -1*np.ones(clen)))) 
                else:
                    a.append(self.gen_emg[tmp_index[i]])
                    b.append(np.vstack((prime.reshape(1,glove_col),self.gen_glove[tmp_index[i]][:-1,:])))
                    c.append(self.gen_glove[tmp_index[i]])
                    d.append(self.gen_label[tmp_index[i]])
            X_length = [self.gen_emg[tmp_index[i]].shape[0] for i in range(len(tmp_index))] 

        # print len(a)
        # assert len(X_length) == num_batch == len(a)
        # aff = np.eye(np.vstack(a).shape[0]).astype(np.bool)
        
        # print X_length
        # print len(b)
        self.a = np.array(a)
        # print self.a.shape
        self.b = np.array(b)

        self.c = np.array(c)
        self.d = np.hstack(d)
        self.max_batch_length = max_batch_length
        self.X_length = X_length
        # self.aff = aff
        # return np.array(a), np.array(b), np.array(c), np.array(d), max_batch_length, X_length, aff
        # print '********************', a.shape, b.shape, c.shape, d.shape
        return self.a, self.b, self.c, self.d, self.max_batch_length, self.X_length
    def next_rec_batch(self, num_batch, set_type):
        # assert(self.train_pred_glove != None)
        a=[]
        c=[]
        d=[]
        # print self.train_pred_glove
        tmp_index =[]
        if set_type == 'train':
            if (self.train_begin+num_batch)> self.train_data_num:
                tmp_index = np.array(list(self.train_index[self.train_begin:]) + list(self.train_index[0:(self.train_begin+num_batch-self.train_data_num)]))
                self.train_begin = 0
            else:
                tmp_index = self.train_index[self.train_begin:(self.train_begin+num_batch)]
                self.train_begin = self.train_begin+num_batch
        else:
            pass

        if set_type == 'train':

            selected_window_length = 0
            if len(self.window_length)==1:
                selected_window_length = self.window_length[0]
            else:
                selected_window_length = self.window_length[np.random.randint(0,len(self.window_length))]

            for i in range(len(tmp_index)):
                emg_col = self.train_emg.shape[1]
                glove_col = self.train_pred_glove.shape[1]
                a.append(self.train_emg[tmp_index[i]:(tmp_index[i]+selected_window_length)])
                c.append(self.train_pred_glove[tmp_index[i]:(tmp_index[i]+selected_window_length)])
                d.append(self.train_label[tmp_index[i]:(tmp_index[i]+selected_window_length)])          
        else:
            pass

        self.a = np.array(a)
        self.c = np.array(c)
        self.d = np.hstack(d)
        # print self.a.shape, self.c.shape, self.d.shape
        return self.a, self.c, self.d

    def get_path(self, root, subject, gesture, trial):
        return os.path.join(
            root,
            '{subject:03d}',
            '{gesture:03d}',
            '{subject:03d}_{gesture:03d}_{trial:03d}.mat').format(subject=subject, gesture=gesture, trial=trial)

    def get_glove_path(self, coroot, subject, gesture, trial):
        return os.path.join(
            coroot,
            '{subject:03d}',
            '{gesture:03d}',
            '{subject:03d}_{gesture:03d}_{trial:03d}.mat').format(subject=subject, gesture=gesture, trial=trial)


def add_noise(data):
    m,n = data.shape
    noise = np.random.normal(0,0.1,m)
    for i in range(n):
        data[:,i] = data[:,i]+noise
    return data

def _get_glove(paths):
    res = [_get_glove_aux(path) for path in paths]
    return res

def _get_glove_aux(path):
    # tmp=np.array([2,6,10,14,18])
    # glove = sio.loadmat(path)['data'][:,tmp].astype(np.float32)
    glove = 0.01*sio.loadmat(path)['data'][:,0:19].astype(np.float32)
    # glove = sio.loadmat(path)['data'].astype(np.float32)

    # print '******************glove shape:', glove.shape
    return glove

def _get_data(paths, preprocess):
    return [_get_data_aux(path, preprocess) for path in paths]



def _get_data_aux(path, preprocess=True):
    data = sio.loadmat(path)['data'].astype(np.float32)
    if preprocess:
        data = Preprocess(data, 100).astype(np.float32)
    return data

def butter_lowpass_filter(data, cut, fs, order, zero_phase=False):
    from scipy.signal import butter, lfilter, filtfilt

    nyq = 0.5 * fs
    cut = cut / nyq

    b, a = butter(order, cut, btype='low')
    if len(data)<10:
        return data
    else:
        y = (filtfilt if zero_phase else lfilter)(b, a, data)
        return y
def Preprocess(data,framerate):
#     print 'hello'
    return np.transpose([butter_lowpass_filter(ch, 1, framerate, 1, zero_phase=True) for ch in data.T]).astype(np.float32)


class Model():
    """
    The core recurrent neural network model.
    """

    def __init__(self, args, data, infer=False):

        
        self.state_size = args.state_size


        with tf.variable_scope('generator'):
            self.input_data0 = tf.placeholder(
                tf.float32, [None, None, args.dim_emg])
            self.input_data = tf.placeholder(
                tf.float32, [None, None, args.dim_glove])
            self.target_data = tf.placeholder(
                tf.float32, [None, None, args.dim_glove])
            self.X_lengths = tf.placeholder(tf.float32, [None])
            self.max_batch_length = tf.placeholder(tf.int32)
            self.istraining= tf.placeholder(tf.bool)
            self.batch_size = tf.placeholder(tf.int32)
            self.initial_state_c = tf.placeholder(tf.float32, [None, self.state_size])
            self.initial_state_h = tf.placeholder(tf.float32, [None, self.state_size])

            def generate(emg, glove, name, reuse=False):
            
            
                with tf.variable_scope(name) as scope:
                    if reuse:
                        scope.reuse_variables()
                    emg = Reshape([args.dim_emg])(emg)        
                    emg = Reshape((1,args.dim_emg,1))(emg)
                    emg = Conv2D(64, [3,3], padding='same', activation='relu')(emg)
                    emg = Conv2D(64, [3,3], padding='same', activation='relu')(emg)
                    emg = Conv2D(64, [3,3], padding='same', activation='relu')(emg)
                    emg = Conv2D(64, [3,3], padding='same', activation='relu')(emg)
                    emg = Flatten()(emg)
                    emg = Dense(512)(emg)
                    emg = Dense(512)(emg)
                    emg = Dense(128)(emg)
                    emg = Dense(self.state_size/2)(emg)

                    glove = Reshape([args.dim_glove])(0.01*glove)        
                    glove = Dense(self.state_size/2)(glove)

                    emg_rnn=Reshape((self.max_batch_length, emg.get_shape().as_list()[1]))(emg)
                    glove_rnn=Reshape((self.max_batch_length, glove.get_shape().as_list()[1]))(glove)
                    inputs_rnn = Concatenate()([emg_rnn, glove_rnn])

                    self.cell = rnn_cell.BasicLSTMCell(self.state_size)
                    self.initial_state=rnn_cell.LSTMStateTuple(self.initial_state_c,self.initial_state_h)
                    outputs, last_state = tf.nn.dynamic_rnn(
                        cell=self.cell,
                        dtype = np.float32,
                        sequence_length=self.X_lengths,
                        inputs = inputs_rnn, 
                        initial_state=self.initial_state)
                    res_last_state = last_state
                    outputs = Reshape([outputs.get_shape().as_list()[2]])(outputs)
                    outputs = Dense(256)(outputs)
                    outputs = Dense(128)(outputs)
                    outputs = Dense(args.dim_glove)(outputs)
                    outputs = tf.stop_gradient(outputs)
                    return outputs, res_last_state

            self.outputs, self.last_state = generate(self.input_data0, self.input_data, 'gen', reuse=False)

        with tf.variable_scope('rec_model'):
        
            self.label = tf.placeholder(
                tf.int32, [None])
            self.rec_target_data = tf.placeholder(
                tf.float32, [None, None, args.dim_glove])

            print('emg')
            print(self.input_data0.get_shape())  
            emg = Reshape([args.dim_emg])(self.input_data0)
            # glove = self.rec_target_data*0.01 

            # glove = self.outputs*0.01 
            # glove = Reshape([args.dim_glove])(glove) 
            glove = self.rec_target_data*0.01 
            # glove = self.rec_target_data

            glove = Reshape([args.dim_glove])(glove)      

            print(emg.get_shape())  
            print(emg.name)

            emg = Concatenate()([emg,glove])

            emg = Reshape((1,args.dim_emg+args.dim_glove,1))(emg)
            print(emg.get_shape())  
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            print(emg.get_shape())  


            # print(emg.get_shape())       
            emg = Conv2D(64, [3,3], padding='same', use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)
            print(emg.get_shape())

            emg = Conv2D(64, [3,3], padding='same', use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)
            print(emg.get_shape())

            emg = LocallyConnected2D(64, [1,1], padding='valid', use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)
            print(emg.get_shape())

            emg = LocallyConnected2D(64, [1,1], padding='valid', use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)
            print(emg.get_shape())

            emg = tf.contrib.layers.dropout(emg, is_training=self.istraining)
            print(emg.get_shape())

            emg = Flatten()(emg)
            print(emg.get_shape())

            emg = Dense(512, use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)  
            emg = tf.contrib.layers.dropout(emg, is_training=self.istraining)
            print(emg.get_shape())

            emg = Dense(512, use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)  
            emg = tf.contrib.layers.dropout(emg, is_training=self.istraining)           
            print(emg.get_shape())

            emg = Dense(128, use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)             
            print(emg.get_shape())

            emg = Dense(len(args.gestures))(emg)
            print(emg.get_shape())

            logits = emg
            # logits = tf.stop_gradient(logits)
            print(logits.name)


        with tf.variable_scope('rec_loss'):
            # emg = Activation('softmax')(emg)
            # print self.label.shape
            # print emg.get_shape()
            onehot_label = tf.one_hot(self.label, emg.get_shape()[1])
            # print onhot_label.get_shape()
            cross_entropy = tf.nn.softmax_cross_entropy_with_logits(labels=onehot_label,
                                                                           logits=logits)

            # cross_entropy_mean = tf.reduce_sum(cross_entropy, name='cross_entropy')
            print cross_entropy.get_shape()
            cross_entropy_mean = tf.reduce_mean(cross_entropy, name='cross_entropy')
            print 'cross_entropy_shape:', cross_entropy_mean.get_shape()
            # cross_entropy_mean = -tf.reduce_sum(onehot_label*tf.log(tf.nn.softmax(logits)))
            self.classification_loss = cross_entropy_mean

            self.pred_label = tf.argmax(tf.nn.softmax(logits, name='predicted_value'),axis=1)

            l2_regularizer = tf.contrib.layers.l2_regularizer(scale=0.0001, scope=None)
            weights = tf.trainable_variables()
            reg_weights = [weight for weight in weights if 'rec' in weight.name and 'optimize' not in weight.name]
            # print reg_weights
            self.regularization_loss = tf.contrib.layers.apply_regularization(l2_regularizer, reg_weights)


            self.cost = self.classification_loss+self.regularization_loss
            # self.cost = self.classification_loss

            tf.summary.scalar('loss', self.cost)

            self.merged_op_loss = tf.summary.merge_all()

        with tf.variable_scope('rec_optimize'):
            self.lr = tf.placeholder(tf.float32, [])

            update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
            with tf.control_dependencies(update_ops):
                optimizer = tf.train.MomentumOptimizer(self.lr, momentum=0.9, use_nesterov=True)
                
                tvars = tf.trainable_variables()

                grads,tvars = zip(*optimizer.compute_gradients(self.cost))
                # rescale_grad = 1.0/args.batch_size
                # grads = [grad*rescale_grad for grad in grads]
                # grads = [tf.clip_by_value(grad,-args.grad_clip, args.grad_clip) for grad in grads]

                # grads, _ = tf.clip_by_global_norm(grads, args.grad_clip)
                # grads, _ = [tf.clip_by_norm(grad,-args.grad_clip, args.grad_clip) for grad in grads]

                self.train_op = optimizer.apply_gradients(zip(grads, tvars))
                # self.train_op = optimizer.minimize(self.cost)

                tf.summary.scalar('learning_rate', self.lr)

class TestModel():
    """
    The core recurrent neural network model.
    """

    def __init__(self, args, data, infer=False):

        
        self.state_size = args.state_size


        with tf.variable_scope('generator'):
            self.input_data0 = tf.placeholder(
                tf.float32, [None, None, args.dim_emg])
            self.input_data = tf.placeholder(
                tf.float32, [None, None, args.dim_glove])
            self.target_data = tf.placeholder(
                tf.float32, [None, None, args.dim_glove])
            self.X_lengths = tf.placeholder(tf.float32, [None])
            self.max_batch_length = tf.placeholder(tf.int32)
            self.istraining= tf.placeholder(tf.bool)
            self.batch_size = tf.placeholder(tf.int32)
            self.initial_state_c = tf.placeholder(tf.float32, [None, self.state_size])
            self.initial_state_h = tf.placeholder(tf.float32, [None, self.state_size])

            def generate(emg, glove, name, reuse=False):
            
            
                with tf.variable_scope(name) as scope:
                    if reuse:
                        scope.reuse_variables()
                    emg = Reshape([args.dim_emg])(emg)        
                    emg = Reshape((1,args.dim_emg,1))(emg)
                    emg = Conv2D(64, [3,3], padding='same', activation='relu')(emg)
                    emg = Conv2D(64, [3,3], padding='same', activation='relu')(emg)
                    emg = Conv2D(64, [3,3], padding='same', activation='relu')(emg)
                    emg = Conv2D(64, [3,3], padding='same', activation='relu')(emg)
                    emg = Flatten()(emg)
                    emg = Dense(512)(emg)
                    emg = Dense(512)(emg)
                    emg = Dense(128)(emg)
                    emg = Dense(self.state_size/2)(emg)

                    glove = Reshape([args.dim_glove])(0.01*glove)        
                    glove = Dense(self.state_size/2)(glove)

                    emg_rnn=Reshape((self.max_batch_length, emg.get_shape().as_list()[1]))(emg)
                    glove_rnn=Reshape((self.max_batch_length, glove.get_shape().as_list()[1]))(glove)
                    inputs_rnn = Concatenate()([emg_rnn, glove_rnn])

                    self.cell = rnn_cell.BasicLSTMCell(self.state_size)
                    self.initial_state=rnn_cell.LSTMStateTuple(self.initial_state_c,self.initial_state_h)
                    outputs, last_state = tf.nn.dynamic_rnn(
                        cell=self.cell,
                        dtype = np.float32,
                        sequence_length=self.X_lengths,
                        inputs = inputs_rnn, 
                        initial_state=self.initial_state)
                    res_last_state = last_state
                    outputs = Reshape([outputs.get_shape().as_list()[2]])(outputs)
                    outputs = Dense(256)(outputs)
                    outputs = Dense(128)(outputs)
                    outputs = Dense(args.dim_glove)(outputs)
                    outputs = tf.stop_gradient(outputs)
                    return outputs, res_last_state

            self.outputs, self.last_state = generate(self.input_data0, self.input_data, 'gen', reuse=False)

        with tf.variable_scope('rec_model'):
            
            self.label = tf.placeholder(
                tf.int32, [None])

            print('emg')
            print(self.input_data0.get_shape())  
            emg = Reshape([args.dim_emg])(self.input_data0)
            # glove = self.rec_target_data*0.01 

            glove = self.outputs*0.01 
            glove = Reshape([args.dim_glove])(glove) 
            # glove = self.rec_target_data*0.01 
            # glove = Reshape([args.dim_glove])(glove)      

            print(emg.get_shape())  
            print(emg.name)

            emg = Concatenate()([emg,glove])

            emg = Reshape((1,args.dim_emg+args.dim_glove,1))(emg)
            print(emg.get_shape())  
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            print(emg.get_shape())  


            # print(emg.get_shape())       
            emg = Conv2D(64, [3,3], padding='same', use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)
            print(emg.get_shape())

            emg = Conv2D(64, [3,3], padding='same', use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)
            print(emg.get_shape())

            emg = LocallyConnected2D(64, [1,1], padding='valid', use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)
            print(emg.get_shape())

            emg = LocallyConnected2D(64, [1,1], padding='valid', use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)
            print(emg.get_shape())

            emg = tf.contrib.layers.dropout(emg, is_training=self.istraining)
            print(emg.get_shape())

            emg = Flatten()(emg)
            print(emg.get_shape())

            emg = Dense(512, use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)  
            emg = tf.contrib.layers.dropout(emg, is_training=self.istraining)
            print(emg.get_shape())

            emg = Dense(512, use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)  
            emg = tf.contrib.layers.dropout(emg, is_training=self.istraining)           
            print(emg.get_shape())

            emg = Dense(128, use_bias=False)(emg)
            emg = tf.contrib.layers.batch_norm(emg, decay=0.9, center=True, scale=True, epsilon=1e-3, is_training=self.istraining)
            emg = Activation('relu')(emg)             
            print(emg.get_shape())

            emg = Dense(len(args.gestures))(emg)
            print(emg.get_shape())

            logits = emg
            # logits = tf.stop_gradient(logits)
            print(logits.name)


        with tf.variable_scope('rec_loss'):
            # emg = Activation('softmax')(emg)
            # print self.label.shape
            # print emg.get_shape()
            onehot_label = tf.one_hot(self.label, emg.get_shape()[1])
            # print onhot_label.get_shape()
            cross_entropy = tf.nn.softmax_cross_entropy_with_logits(labels=onehot_label,
                                                                           logits=logits)

            # cross_entropy_mean = tf.reduce_sum(cross_entropy, name='cross_entropy')
            print cross_entropy.get_shape()
            cross_entropy_mean = tf.reduce_mean(cross_entropy, name='cross_entropy')
            print 'cross_entropy_shape:', cross_entropy_mean.get_shape()
            # cross_entropy_mean = -tf.reduce_sum(onehot_label*tf.log(tf.nn.softmax(logits)))
            self.classification_loss = cross_entropy_mean

            self.pred_label = tf.argmax(tf.nn.softmax(logits, name='predicted_value'),axis=1)

            l2_regularizer = tf.contrib.layers.l2_regularizer(scale=0.0001, scope=None)
            weights = tf.trainable_variables()
            reg_weights = [weight for weight in weights if 'rec' in weight.name and 'optimize' not in weight.name]
            self.regularization_loss = tf.contrib.layers.apply_regularization(l2_regularizer, reg_weights)


            self.cost = self.classification_loss+self.regularization_loss
            # self.cost = self.classification_loss

            tf.summary.scalar('loss', self.cost)

            self.merged_op_loss = tf.summary.merge_all()

        with tf.variable_scope('rec_optimize'):
            self.lr = tf.placeholder(tf.float32, [])

            update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
            with tf.control_dependencies(update_ops):
                optimizer = tf.train.MomentumOptimizer(self.lr, momentum=0.9, use_nesterov=True)
                
                tvars = tf.trainable_variables()

                grads,tvars = zip(*optimizer.compute_gradients(self.cost))
                # rescale_grad = 1.0/args.batch_size
                # grads = [grad*rescale_grad for grad in grads]
                # grads = [tf.clip_by_value(grad,-args.grad_clip, args.grad_clip) for grad in grads]

                # grads, _ = tf.clip_by_global_norm(grads, args.grad_clip)
                # grads, _ = [tf.clip_by_norm(grad,-args.grad_clip, args.grad_clip) for grad in grads]

                self.train_op = optimizer.apply_gradients(zip(grads, tvars))
                # self.train_op = optimizer.minimize(self.cost)

                tf.summary.scalar('learning_rate', self.lr)

def train(data, model, args):
    losss = []
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.7)
    saver = tf.train.Saver()
    with tf.Session(config=tf.ConfigProto(gpu_options=gpu_options)) as sess:
        train_writer = tf.summary.FileWriter(args.log_dir+'/train', sess.graph)
        val_writer = tf.summary.FileWriter(args.log_dir+'/val', sess.graph)

        sess.run(tf.global_variables_initializer())
        # sess.run(tf.local_variables_initializer())

        vals = tf.global_variables()
        pre_val = [val for val in vals if 'gen' in val.name and 'optimize' not in val.name]
        # print pre_val
        rec_val = [val for val in vals if 'rec' in val.name and 'optimize' not in val.name]
        # rec_val = [val for val in vals if 'rec' in val.name and 'dense_' in val.name and 'optimize' not in val.name]
        # print rec_val

        pre_saver = tf.train.Saver(pre_val)
        print tf.train.latest_checkpoint(args.predict_dir)
        pre_saver.restore(sess, tf.train.latest_checkpoint(args.predict_dir))
        
        if args.recognize_dir != None:
            rec_saver = tf.train.Saver(rec_val)
            print tf.train.latest_checkpoint(args.recognize_dir)
            rec_saver.restore(sess, tf.train.latest_checkpoint(args.recognize_dir))

        handler = FileHandler(args.log_dir+'/result.log')
        handler.push_application()
        logger = Logger('train-test')


        test_pre_loss = []
        pre_labels = []
        true_labels = []
        train_pred_glove = []

        for i in range(len(data.subjects)*len(data.gestures)*len(data.trials)):
        # for i in range(10):
            x0_batch, x_batch, y_batch, label, max_batch_length, X_lengths = data.next_batch(1, 'gen')
            if i%len(data.trials) in data.get_one_fold_intra_subject_trials()[0]:

                # print x0_batch.shape, x_batch.shape, y_batch.shape, max_batch_length 
                state = sess.run(model.cell.zero_state(1, tf.float32))
                prime = 0.01*np.array([141.42471313, 112.83409119, 113.78411865, 129.12123108, 125.65979767, 119.64640045, 95.61739349, 112.13970184, 128.75344849, 81.33988953, 150.52861023, 123.24646759, 113.32148743, 77.64886475, 150.32717896, 124.62281036, 146.92736816, 101.37089539, 138.00967407, 130.77967834, 146.80603027, 118.58580017])
                word = prime[0:19]
                for j in range(X_lengths[0]):
                    x = word.reshape((1,1,args.dim_glove))
                    feed_dict = {model.input_data0: x0_batch[:,j,:].reshape((1,1,args.dim_emg)), 
                                 model.input_data: x,  
                                 model.target_data:y_batch[:,j,:].reshape((1,1,args.dim_glove)),
                                 model.X_lengths: [1],
                                 model.max_batch_length:1, 
                                 model.istraining:0,
                                 model.initial_state_c:state.c,
                                 model.initial_state_h:state.h}
                    outputs, state = sess.run([model.outputs, model.last_state], feed_dict)                

                    word = outputs
                    train_pred_glove.append(word)
        train_pred_glove = np.vstack(train_pred_glove)
        print 'train_pred_glove:', train_pred_glove.shape

        if data.train_pred_glove == None:
            data.train_pred_glove = train_pred_glove
        # print data.train_pred_glove
        summary_loss = []

        iter_of_epoch = int(data.train_data_num/args.batch_size)+1
        for i in range(args.max_epoch):
            lr1 = 16
            lr2 = 24
            if i<16:
                learning_rate = args.learning_rate
            elif i>=16 and i<24:
                learning_rate = args.learning_rate * args.decay_rate
            else:
                learning_rate = args.learning_rate * (args.decay_rate**2)

            for j in range(iter_of_epoch):

                # x0_batch, x_batch, y_batch,label,max_batch_length, X_lengths = data.next_rec_batch(args.batch_size, 'train')

                # feed_dict = {model.input_data0: x0_batch,
                #              model.input_data: x_batch,
                #              model.target_data: y_batch, 
                #              model.label: label,
                #              model.lr: learning_rate,
                #              model.X_lengths: X_lengths,
                #              model.max_batch_length:max_batch_length,
                #              model.istraining:1,
                #              model.batch_size: args.batch_size}
                x0_batch, x1_batch, label = data.next_rec_batch(args.batch_size, 'train')
                # x0_batch, x_batch, x1_batch, label, max_batch_length, X_lengths = data.next_batch(args.batch_size, 'train')
                # print x0_batch[0]
                # print x1_batch[0]
                # print label
                # print x0_batch.shape, x1_batch.shape, label.shape
                feed_dict = {model.input_data0: x0_batch,
                             model.rec_target_data: x1_batch, 
                             model.label: label,
                             model.lr: learning_rate,
                             model.istraining:1,
                             model.batch_size: args.batch_size}

                train_loss, pre_label, _ = sess.run([model.classification_loss, model.pred_label, model.train_op], feed_dict)
                losss.append(train_loss)
                # print pre_label, label
                train_acc = list(np.array(pre_label)==label).count(1)*1.0/len(label)
                if j % 100 == 0:
                    print('Epoch:{}, Step:{}/{}, training_loss:{:4f}, training_accuracy:{:4f}'.format(i, j, iter_of_epoch, train_loss, train_acc))
                    logger.info('Epoch:{}, Step:{}/{}, training_loss:{:4f}, training_accuracy:{:4f}', i, j, iter_of_epoch, train_loss, train_acc)

        saver.save(sess, os.path.join(
            args.log_dir, 'lyrics_model.ckpt'), global_step=args.max_epoch)


def test(data, model, subject, args):
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.7)
    test_loss=[]
    saver = tf.train.Saver()
    with tf.Session(config=tf.ConfigProto(gpu_options=gpu_options)) as sess:
    
        train_writer = tf.summary.FileWriter(args.log_dir, sess.graph)
    
        sess.run(tf.global_variables_initializer())
        sess.run(tf.local_variables_initializer())

        # ckpt = tf.train.latest_checkpoint(args.log_dir)
        # print(ckpt)
        # saver.restore(sess, ckpt)
        
        
        vals = tf.global_variables()
        pre_val = [val for val in vals if 'gen' in val.name and 'optimize' not in val.name]
        # print pre_val
        rec_val = [val for val in vals if 'rec' in val.name and 'optimize' not in val.name]
        # rec_val = [val for val in vals if 'rec' in val.name and 'dense_' in val.name and 'optimize' not in val.name]
        # print rec_val

        pre_saver = tf.train.Saver(pre_val)
        print tf.train.latest_checkpoint(args.predict_dir)
        pre_saver.restore(sess, tf.train.latest_checkpoint(args.predict_dir))
        
        if args.recognize_dir != None:
            rec_saver = tf.train.Saver(rec_val)
            print tf.train.latest_checkpoint(args.recognize_dir)
            rec_saver.restore(sess, tf.train.latest_checkpoint(args.recognize_dir))


        # vals = tf.global_variables()
        # pre_val = [val for val in vals if 'pre' in val.name and 'optimize' not in val.name]
        # rec_val = [val for val in vals if 'rec' in val.name and 'optimize' not in val.name]

        # pre_saver = tf.train.Saver(pre_val)
        # print tf.train.latest_checkpoint(args.predict_dir)
        # pre_saver.restore(sess, tf.train.latest_checkpoint(args.predict_dir))
        # rec_saver = tf.train.Saver(rec_val)
        # print tf.train.latest_checkpoint(args.recognize_dir)
        # rec_saver.restore(sess, tf.train.latest_checkpoint(args.recognize_dir))

        handler = FileHandler(args.log_dir+'/result.log')
        handler.push_application()
        logger = Logger('train-test')


        test_pre_loss = []
        pre_labels = []
        true_labels = []
        for i in range(len(data.subjects)*len(data.gestures)*10):
        # for i in range(2):
            x0_batch, x_batch, y_batch, label, max_batch_length, X_lengths = data.next_batch(1, 'gen')
            if i%10 in data.get_one_fold_intra_subject_trials()[1]:

                # print x0_batch.shape, x_batch.shape, y_batch.shape, max_batch_length 
                state = sess.run(model.cell.zero_state(1, tf.float32))
                prime = 0.01*np.array([141.42471313, 112.83409119, 113.78411865, 129.12123108, 125.65979767, 119.64640045, 95.61739349, 112.13970184, 128.75344849, 81.33988953, 150.52861023, 123.24646759, 113.32148743, 77.64886475, 150.32717896, 124.62281036, 146.92736816, 101.37089539, 138.00967407, 130.77967834, 146.80603027, 118.58580017])
                word = prime[0:19]
                lyrics = []
                for j in range(X_lengths[0]):
                    # print y_batch[:,j,:]
                    # print x0_batch[:,j,:]
                    x = word.reshape((1,1,args.dim_glove))
                    feed_dict = {model.input_data0: x0_batch[:,j,:].reshape((1,1,args.dim_emg)), 
                                 model.input_data: x,  
                                 model.target_data:y_batch[:,j,:].reshape((1,1,args.dim_glove)),
                                 # model.rec_target_data:y_batch[:,j,:].reshape((1,1,args.dim_glove)),
                                 model.label: [label[j]],
                                 model.X_lengths: [1],
                                 model.max_batch_length:1, 
                                 model.istraining:0,
                                 model.initial_state_c:state.c,
                                 model.initial_state_h:state.h}
                    # outputs, state, pre_label, pre_loss = sess.run([model.outputs, model.last_state, model.pred_label, model.classification_loss], feed_dict)     
                    outputs, state, pre_label, pre_loss = sess.run([model.outputs, model.last_state, model.pred_label, model.cost], feed_dict)                
                    # pre_label, pre_loss = sess.run([model.pred_label, model.classification_loss], feed_dict)     

                    word = outputs
                    lyrics.append(word)
                    pre_labels.append(pre_label)
                # print pre_labels
                true_labels.append(label)
                test_pre_loss.append(np.mean((np.squeeze(lyrics)-np.squeeze(y_batch))**2))
                # print test_pre_loss[-1]
              
        # print test_pre_loss
        test_pre_loss = np.mean(test_pre_loss)
        print test_pre_loss

        pre_labels = np.hstack(pre_labels)
        true_labels = np.hstack(true_labels)
        print pre_labels
        print true_labels
        acc=[]
        good = pre_labels==true_labels
        for sing_label in set(true_labels):
            # print 'sing_label', sing_label
            mask = np.array(true_labels==sing_label)
            # print mask
            acc.append(np.sum(good[mask])*1.0/np.sum(mask))
            # print np.sum(good[mask]), np.sum(mask), acc[-1]
        test_acc = np.mean(acc)
        print('test_pre_loss:{:4f}, test_accuracy:{:4f}'.format(test_pre_loss, test_acc))
        logger.info('test_pre_loss:{:4f}, test_accuracy:{:4f}', test_pre_loss, test_acc)       


# def sample(data, model, subject, args):
#     gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.7)

#     saver = tf.train.Saver()
#     with tf.Session(config=tf.ConfigProto(gpu_options=gpu_options)) as sess:
#         ckpt = tf.train.latest_checkpoint(args.log_dir)
#         print(ckpt)
#         saver.restore(sess, ckpt)


#         test_loss=[]
#         test_loss0=[]
#         test_loss1=[]
#         #save test data
#         for i in range(80):
#             x0_batch, x_batch, y_batch,_,max_batch_length, X_lengths, aff = data.next_batch(1, 'gen')
#             # prime = np.zeros(22).reshape((1,1,args.dim_glove)) # replace
#             prime = np.array([0.78691131,  0.29444289,  0.39459214, -0.59867328,  0.64712667, 0.48408264,  0.08347759,  0.72374099,  0.48228815, -0.25643679, -0.10339925,  0.65559345,  0.48133588,  0.09558067, -0.08043436, 0.60212082,  0.65581518,  0.1535355 , -0.05444708]).reshape((1,1,args.dim_glove)) # glove raw
            
#             state = sess.run(model.cell.zero_state(1, tf.float32))

#             word = prime
#             lyrics = []

#             for j in range(X_lengths[0]):
#                 x = word.reshape((1,1,args.dim_glove))
#                 feed_dict = {model.input_data0: x0_batch[:,j,:].reshape((1,1,args.dim_emg)), 
#                              model.input_data: x, 
#                              model.initial_state: state, 
#                              model.X_lengths: [1],
#                              model.max_batch_length:1, 
#                              model.aff_xy:aff, 
#                              model.istraining:0}
#                 outputs, state = sess.run([model.outputs, model.last_state], feed_dict)
#                 # test_loss.append(sess.run(model.cost, feed_dict))
#                 # test_loss0.append(sess.run(model.cost0, feed_dict))
#                 # test_loss1.append(sess.run(model.cost1, feed_dict))

#                 word = outputs
#                 lyrics.append(word)
#             lyrics = np.squeeze(lyrics)
#             print np.squeeze(lyrics).shape
#             print np.squeeze(y_batch).shape
#             test_loss.append(np.mean((np.squeeze(lyrics)-np.squeeze(y_batch))**2))
            
#             test_trial = data.get_gen_trials()
#             save_root = '../data/ninapro-db1-preglove-radian-meanrest/data'
#             save_path = os.path.join(save_root, '{s:03d}', '{g:03d}').format(s=subject,g=i/len(test_trial)+13)
#             if os.path.isdir(save_path) is False:
#                 os.makedirs(save_path)
#             save_file = os.path.join(save_path, '{s:03d}_{g:03d}_{t:03d}.mat').format(s=subject,g=i/len(test_trial)+13,t=test_trial[i%len(test_trial)])

#             sio.savemat(save_file, {'data':lyrics})
#         # print test_loss
#         print np.mean(test_loss)




        # print 'test_loss:{:4f}, test_loss0:{:4f}, test_loss1:{:4f}'.format(np.mean(test_loss), np.mean(test_loss0). np.mean(test_loss1))

        # for i in range(56):
        #     x0_batch, x_batch, y_batch,_,max_batch_length, X_lengths, aff = data.next_batch(1, 'train')

        #     # prime = np.zeros(22).reshape((1,1,args.dim_glove))  # replace with the rest   
        #     prime = np.array([129.59580994, 112.42184448, 112.27864838, 137.90840149, 114.439888, 83.87464142, 77.66155243, 101.59606171,    93.66666412, 68.2119751, 153.35644531, 112.37625122, 94.74073792, 71.11283112, 158.03703308, 112.94902802, 104.66666412, 91.54741669, 143.52468872, 149.53184509, 141.222229 ,115.2272644]).reshape((1,1,args.dim_glove)) # glove raw

        #     state = sess.run(model.cell.zero_state(1, tf.float32))

        #     word = prime
        #     lyrics = []
        #     print X_lengths[0]
        #     for j in range(X_lengths[0]):
        #         x = word.reshape((1,1,args.dim_glove))
        #         feed_dict = {model.input_data0: x0_batch[:,j,:].reshape((1,1,args.dim_emg)), 
        #                      model.input_data: x, 
        #                      model.initial_state: state, 
        #                      model.X_lengths: [1],
        #                      model.max_batch_length:1, 
        #                      model.aff_xy:aff, 
        #                      model.istraining:0}
        #         outputs, state = sess.run([model.outputs, model.last_state], feed_dict)
        #         word = outputs
        #         lyrics.append(word)
        #     lyrics = np.array(lyrics)
        #     print lyrics.shape
            
        #     test_trial = [0, 2, 3, 5, 7, 8, 9]
        #     save_root = '../data/ninapro-db1-preglove-meanrest/data'
        #     save_path = os.path.join(save_root, '{s:03d}', '{g:03d}').format(s=subject,g=i/7+13)
        #     if os.path.isdir(save_path) is False:
        #         os.makedirs(save_path)
        #     save_file = os.path.join(save_path, '{s:03d}_{g:03d}_{t:03d}.mat').format(s=subject,g=i/7+13,t=test_trial[i%7])

        #     sio.savemat(save_file, {'data':lyrics})


def sample(data, model, subject, args):
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.7)

    saver = tf.train.Saver()
    with tf.Session(config=tf.ConfigProto(gpu_options=gpu_options)) as sess:
        ckpt = tf.train.latest_checkpoint(args.log_dir)
        print args.log_dir
        print(ckpt)
        saver.restore(sess, ckpt)


        test_loss=[]
        test_loss0=[]
        test_loss1=[]
        #save test data
        for i in range(80):
            # x0_batch, x_batch, y_batch,_,max_batch_length, X_lengths, aff = data.next_batch(1, 'gen')
            x0_batch, x_batch, y_batch,_,max_batch_length, X_lengths = data.next_batch(1, 'gen')

            # prime = np.zeros(22).reshape((1,1,args.dim_glove)) # replace
            # prime = np.array([0.78691131,  0.29444289,  0.39459214, -0.59867328,  0.64712667, 0.48408264,  0.08347759,  0.72374099,  0.48228815, -0.25643679, -0.10339925,  0.65559345,  0.48133588,  0.09558067, -0.08043436, 0.60212082,  0.65581518,  0.1535355 , -0.05444708]).reshape((1,1,args.dim_glove)) # glove raw
            # prime = 0.01*np.array([129.59580994, 112.42184448, 112.27864838, 137.90840149, 114.439888, 83.87464142, 77.66155243, 101.59606171, 93.66666412, 68.2119751, 153.35644531, 112.37625122, 94.74073792, 71.11283112, 158.03703308, 112.94902802, 104.66666412, 91.54741669, 143.52468872, 149.53184509, 141.222229, 115.2272644])
            prime = x_batch[:,0,:]
            state = sess.run(model.cell.zero_state(1, tf.float32))

            word = prime
            lyrics = []

            for j in range(X_lengths[0]):
                x = word.reshape((1,1,args.dim_glove))
                feed_dict = {model.input_data0: x0_batch[:,j,:].reshape((1,1,args.dim_emg)), 
                             model.input_data: x,  
                             model.X_lengths: [1],
                             model.max_batch_length:1, 
                             model.istraining:0,
                             model.initial_state_c:state.c,
                             model.initial_state_h:state.h}
                outputs, state = sess.run([model.outputs, model.last_state], feed_dict)
                # test_loss.append(sess.run(model.cost, feed_dict))
                # test_loss0.append(sess.run(model.cost0, feed_dict))
                # test_loss1.append(sess.run(model.cost1, feed_dict))

                word = outputs
                lyrics.append(word)
            lyrics = np.squeeze(lyrics)
            print np.squeeze(lyrics).shape
            print np.squeeze(y_batch).shape
            if i%10 in [1,4,6]:
                test_loss.append(np.mean((np.squeeze(lyrics)-np.squeeze(y_batch))**2))
            
            test_trial = data.get_gen_trials()
            save_root = '../data/ninapro-db1-preglove-firstframe/data'
            save_path = os.path.join(save_root, '{s:03d}', '{g:03d}').format(s=subject,g=i/len(test_trial)+13)
            if os.path.isdir(save_path) is False:
                os.makedirs(save_path)
            save_file = os.path.join(save_path, '{s:03d}_{g:03d}_{t:03d}.mat').format(s=subject,g=i/len(test_trial)+13,t=test_trial[i%len(test_trial)])

            sio.savemat(save_file, {'data':lyrics})
        print test_loss
        print np.mean(test_loss)

 

@click.command()
@click.option('--infer', type=int, help='train 0, test-gen-zero 1, test-gen-pre 2')
@click.option('--subject', type=int, help='subject id')
@click.option('--window-length', type=int, multiple=True, help='window length for sample')
@click.option('--window-step', type=int, help='window step')
@click.option('--batch-size', type=int)
@click.option('--emg-dir')
@click.option('--glove-dir')
@click.option('--predir')
@click.option('--pretrain-dir',default=None)
@click.option('--predict-dir',default=None)
@click.option('--signal-image',type=bool, help='True is using signal image, False is using raw image')
@click.option('--dim-emg', type=int)
@click.option('--dim-glove', type=int)
@click.option('--max-epoch', type=int, default=28)
def main(infer, subject, window_length, window_step, emg_dir, glove_dir, predir, pretrain_dir, predict_dir, batch_size, signal_image, dim_emg, dim_glove, max_epoch):
    # args = HParam(subject)
    # data = Dataset(root='../data/ninapro-db1/data', coroot='../data/ninapro-db1-glove-radian/data', subject=subject, args=args)

    # model = Model(args, data, infer=infer)
    subjects = 0
    if subject>=27:
        subjects=np.arange(subject)
    else:
        subjects = [subject]
    if infer==1:
        
        args = HParam(subject, predir, pretrain_dir, predict_dir, window_length, window_step, batch_size, signal_image, dim_emg, dim_glove, max_epoch)
        data = Dataset(root=emg_dir, coroot=glove_dir, subjects=subjects, args=args)
        model = TestModel(args, data, infer=infer)
        rnn_fn = test
        data.get_train_data()
        # data.get_val_data(subject)

        data.get_test_data()
        data.get_genera_data()

        rnn_fn(data, model, subject, args) 

    elif infer==0:
        print dim_emg
        args = HParam(subject, predir, pretrain_dir, predict_dir, window_length, window_step, batch_size, signal_image, dim_emg, dim_glove, max_epoch)
        data = Dataset(root=emg_dir, coroot=glove_dir, subjects=subjects, args=args)
        model = Model(args, data, infer=infer)
        rnn_fn = train
        data.get_train_data()
        # data.get_val_data(subject)

        data.get_test_data()
        data.get_genera_data()

        rnn_fn(data, model, args)
    else:
        args = HParam(subject, predir, pretrain_dir, predict_dir, window_length, window_step, batch_size, signal_image, dim_emg, dim_glove, max_epoch)
        data = Dataset(root=emg_dir, coroot=glove_dir, subjects=subjects, args=args)
        model = Model(args, data, infer=infer)
        rnn_fn = sample
        data.get_train_data()
        # data.get_val_data(subject)

        data.get_test_data()
        data.get_genera_data()

        rnn_fn(data, model, subject, args) 


if __name__ == '__main__':
    # msg = """
    # Usage:
    # Training: 
    #     python3 gen_lyrics.py 0 subject-id
    # Sampling:
    #     python3 gen_lyrics.py 1 subject-id
    # """
    # if len(sys.argv) == 3:
    #     infer = int(sys.argv[1])
    #     subject = int(sys.argv[2])

    #     print '--Sampling--' if infer else '--Training--'
    #     main(infer,subject)
    # else:
    #     print msg
    #     sys.exit(1)
    main()