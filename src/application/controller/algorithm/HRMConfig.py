"""
    Function: configure hyper-parameters for heart rate measurement.

    Author: Bike Chen
    Email: chenbike@xinkteck.com
    Date: 19-July-2019
"""

import argparse


parser = argparse.ArgumentParser(description="Hyper parameters for heart rate measurement.")

parser.add_argument("--fps", type=int, default=30, help="25 frames per seconds (fps)")
parser.add_argument("--FS", type=int, default=30, help="the sample rate of the bvp time series (Hz/fps).")

parser.add_argument("--scale_width", type=float, default=0.6, help="the center 60% width of the box as the ROI width.")
parser.add_argument("--scale_height", type=float, default=1.0, help="full height of the box as the ROI height.")

parser.add_argument("--moving_win", type=int, default=60, help="using a 30s moving window with 96.7% overlap.")
parser.add_argument("--increment", type=int, default=1, help="using a 30s moving window with 96.7% overlap (1s increment).")

parser.add_argument("--FResBPM", type=float, default=0.5, help="resolution (bpm) of bins in power spectrum used to determine PR and SNR.")

parser.add_argument("--LPF", type=float, default=0.7, help="low cutoff frequency (Hz) - 0.7 Hz in reference (corresponding to [45, 240]bpm)")
parser.add_argument("--HPF", type=float, default=2.5, help="high cutoff frequency (Hz) - 4.0 Hz in reference (corresponding to [45, 240]bpm)")

parser.add_argument("--LL_PR", type=int, default=40, help="the lower limit for pulse rate (bpm).")
parser.add_argument("--UL_PR", type=int, default=240, help="the upper limit for pulse rate (bpm).")

parser.add_argument("--bpm_threshold", type=int, default=12, help="a threshold of 12 bpm in our experiments.")
parser.add_argument("--base_bpm", type=int, default=60, help="frequency(Hz) x base_bpm = bpm.")
parser.add_argument("--default_bpm", type=int, default=72, help="default bpm: 72")

parser.add_argument("--param_lambda", type=int, default=100, help="for custom detrend")
parser.add_argument("--max_iter", type=int, default=200, help="max iteration for ICA")

if __name__ == "__main__":
    args = vars(parser.parse_args())
    fps = args["fps"]
    print("FPS =", fps)
