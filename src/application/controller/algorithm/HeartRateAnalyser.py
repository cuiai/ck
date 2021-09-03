"""
    Function: analyse heart rate.

            Input: RGB signals
            Output: heart rate (bpm)

            Reference:
            [1] Non-contact, automated cardiac pulse measurements using video imaging and blind source separation, Ming-Zher Poh, etc.

    Author: Bike Chen
    Email: chenbike@xinktech.com
    Date: 20-July-2019
    Revised: 22-July-2019
"""

from application.controller.algorithm.HRMConfig import parser
from application.controller.algorithm.RGBDetrend import Detrend

import numpy as np
import cv2
import scipy.signal as Signal
import numpy.fft as fft
from sklearn.decomposition import FastICA
from sklearn import preprocessing
import matplotlib.pyplot as plt

args = vars(parser.parse_args())


class HeartRateAnalysis(object):
    def __init__(self):
        # historical r, g, and b values respectively.
        self.r_his_data = []
        self.g_his_data = []
        self.b_his_data = []
        self.fps = args["fps"]
        self.FS = args["FS"] # the sample rate of the bvp time series (Hz/fps).
        self.moving_win = args["moving_win"]
        self.FResBPM = args["FResBPM"]
        self.len_his_data = self.fps * self.moving_win # the length of historical data (30s)
        self.base_bpm = args["base_bpm"]
        self.LPF = args["LPF"]
        self.HPF = args["HPF"]
        self.LL_PR = args["LL_PR"]
        self.UL_PR = args["UL_PR"]
        self.param_lambda = args["param_lambda"]
        self.ica = FastICA(n_components=3, whiten=True, max_iter=args["max_iter"])
        self.previous_bpm = args["default_bpm"] # during 1s (using the previous bpm instead of the current bpm.)
        self.bpm_threshold = args["bpm_threshold"]
        print("Initializing successfully!")

    def PredictHeartRate(self):
        rgb_data = np.asarray([self.r_his_data, self.g_his_data, self.b_his_data])
        # Detrend
        rgb_detrend = []
        for i in range(3):
            rgb_detrend.append(Detrend(rgb_data[i, :], self.param_lambda))
        rgb_detrend = np.squeeze(np.asarray(rgb_detrend))
        # Z-Score
        rgb_norm = preprocessing.scale(rgb_detrend, axis=1) # (3, N)
        rgb_norm = rgb_norm.T # (N, 3)
        # FastICA
        rgb_ica = self.ica.fit_transform(rgb_norm)
        mixing_matrix = self.ica.mixing_
        assert np.allclose(rgb_norm, np.dot(rgb_ica, mixing_matrix.T) + self.ica.mean_)
        # Select the best signal
        max_px = np.zeros(3)
        for c in range(3):
            ff = fft.fft(rgb_ica[:, c])
            ff[0] = 0
            N = len(ff)
            px = abs(ff[0:int(np.floor(N/2))])**2
            px = px / np.sum(px)
            max_px[c] = np.max(px)
        max_comp = np.argmax(max_px)
        bvp_I = rgb_ica[:, max_comp]
        # Filter
        nyquist_F = 1/2 * self.FS # sampling rate is equal to the fps?
        B, A = Signal.butter(3, [self.LPF/nyquist_F, self.HPF/nyquist_F], "bandpass") # Butterworth 3rd order filter
        bvp_F = Signal.filtfilt(B, A, bvp_I)
        bvp = bvp_F # a bvp time series.
        # Calculate bpm
        nfft = self.moving_win * 2 * nyquist_F / self.FResBPM
        freq, Pxx = Signal.periodogram(x=bvp, fs=self.FS, window=Signal.get_window("hamming", len(bvp)), nfft=nfft) # Construct periodogram
        freq_mask = np.where((freq >= (self.LL_PR/self.base_bpm)) & (freq <= (self.UL_PR/self.base_bpm)))
        freq_range = freq[freq_mask]
        pxx_range = Pxx[freq_mask]
        max_ind = np.argmax(pxx_range)
        bpm_freq = freq_range[max_ind]
        bpm_pxx = pxx_range[max_ind]
        bpm = bpm_freq * self.base_bpm
        # Is over threshold
        if abs(bpm - self.previous_bpm) > self.bpm_threshold:
            second_freq_mask = np.where((freq >= ((self.previous_bpm - self.bpm_threshold)/self.base_bpm)) &
                                        (freq <= ((self.previous_bpm + self.bpm_threshold)/self.base_bpm)))
            second_freq_range = freq[second_freq_mask]
            second_pxx_range = Pxx[second_freq_mask]
            second_max_ind = np.argmax(second_pxx_range)
            second_bpm_freq = second_freq_range[second_max_ind]
            second_bpm_pxx = second_pxx_range[second_max_ind]
            second_bpm = second_bpm_freq * self.base_bpm
            self.previous_bpm = second_bpm
            # PlotHeartRateDetection(second_bpm, second_bpm_freq, second_bpm_pxx, freq, Pxx)
            return second_bpm
        else:
            self.previous_bpm = bpm
            # PlotHeartRateDetection(bpm, bpm_freq, bpm_pxx, freq, Pxx)
            return bpm


def PlotHeartRateDetection(bpm, bpm_freq, bpm_pxx, freq, Pxx):
    fig = plt.figure()
    plt.plot(freq, Pxx)
    plt.plot(bpm_freq, bpm_pxx, color="red", marker="*")
    plt.text(bpm_freq, bpm_pxx, "%3.2f Hz; %4.1f bpm"%(bpm_freq, bpm))
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Power (a.u.)")
    plt.xlim([0, 4.5])
    plt.title("Power Spectrum and Peak Frequency")
    plt.show()


if __name__ == "__main__":
    heart_rate_ana = HeartRateAnalysis()
    video_file = "video_example.mp4"
    fps = 30 # assume 30 fps.
    start_time = 0
    duration = 60 # 60s
    frames_to_read = fps * duration
    cap = cv2.VideoCapture(video_file)
    count_frame = 0
    while cap.isOpened() and count_frame < frames_to_read:
        count_frame = count_frame + 1
        ret, frame = cap.read()
        if ret is False:
            print("Warning: could not read an image from a video.")
            break
        # get r, g, and b values respectively. (BGR format provided by OpenCV)
        heart_rate_ana.r_his_data.append(np.sum(frame[:, :, 2]))
        heart_rate_ana.g_his_data.append(np.sum(frame[:, :, 1]))
        heart_rate_ana.b_his_data.append(np.sum(frame[:, :, 0]))
    cap.release()
    # bpm, bpm_freq, bpm_pxx, freq, Pxx = heart_rate_ana.PredictHeartRate()
    bpm = heart_rate_ana.PredictHeartRate()
    print("bpm =", bpm)
    # PlotHeartRateDetection(bpm, bpm_freq, bpm_pxx, freq, Pxx)


