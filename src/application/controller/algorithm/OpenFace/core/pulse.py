import numpy as np
import numpy.fft as fft
from scipy.stats import pearsonr
from scipy.signal import detrend
import scipy.signal as signal
from sklearn.decomposition import FastICA
from matplotlib.pyplot import plot, subplot, show

from application.controller.config import LOG


class Pulse(object):
    def __init__(self):
        self.data_buffer = []
        self.length = 600
        self.fps = 60

        self.heart_rate = None
        self.heart_rate = 72
        self.avg_hr = [1, 72]
        self.pre_heart_rate = None
        self.info_need = []
        self.fluctuation_threshold = 100
        self.steady_score_record = []
        self.steady_num = (200, 2000)

    def cal_steady_score(self, x):
        stride1 = max(abs(x[1:] - x[:-1]))
        stride4 = max(abs(x[4:] - x[:-4]))
        std = x.std()
        return std + 0.3 * (stride1 + stride4)

    def check_steady(self):
        if self.steady_score_record[-1] < 0.7:
            return True
        if len(self.steady_score_record) > 2000:
            self.steady_score_record = self.steady_score_record[-2000:]
        if len(self.steady_score_record) > 50 and self.steady_score_record[-1] < 0.9 * np.array(
                self.steady_score_record).mean():
            return True
        else:
            return False

    def _cal_hr(self, x):
        fft_res = fft.fft(x)
        transformed = np.abs(fft_res)
        frequencies = np.fft.fftfreq(len(transformed), d=1.0 / self.fps)
        ids = np.where((frequencies > 0.83) & (frequencies < 2))
        transformed = transformed[ids]
        if len(transformed) == 0:
            return None
        frequencies = frequencies[ids]
        index = np.argmax(transformed, axis=0)
        return frequencies[index] * 60

    def _refresh(self):
        self.data_buffer = []
        self.steady_score_record = []

    def heart_rate_detection(self, frame, show_freq=False):
        """
        :param frame: np.array;face detection method to obtain face area
        :return: BPM value of heart rate detection
        """
        if frame is not None:
            g_mean = np.mean(frame[:, :, 1])
            if np.isnan(g_mean):
                self._refresh()
                return 0
            self.data_buffer.append(g_mean)

            if len(self.data_buffer) > self.length:
                self.data_buffer = self.data_buffer[-self.length:]
            if len(self.data_buffer) > self.steady_num[0]:
                samples = np.array(self.data_buffer)
                x = samples - samples.mean()
                self.steady_score_record.append(self.cal_steady_score(x))
                if self.check_steady():
                    hr = self._cal_hr(x)
                    if hr is not None:
                        self.avg_hr[1] = (self.avg_hr[1] * self.avg_hr[0] + hr) / (self.avg_hr[0] + 1)
                        self.avg_hr[0] += 1

                        self.heart_rate = hr
                else:
                    self.heart_rate = self.avg_hr[1]
        else:
            LOG.error('frame is none')
            self._refresh()


        return self.heart_rate
