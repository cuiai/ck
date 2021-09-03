#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import time
import numpy as np
from threading import Thread

from application.controller import config
from application.controller.config import LOG, CFG
from application.controller.mic import EDABuffer, CHUNK, RATE

class IntensityThread(Thread):
    sample_interval = 32

    def __init__(self):
        super(IntensityThread, self).__init__()
        self.setDaemon(True)
        self.setName("IntensityThread")
        self.is_running = True
        self.label = None
        self.is_thread_exit = False

    def resume(self):
        self.is_running = True

    def stop(self):
        self.is_running = False

    def exit(self):
        self.is_thread_exit = True

    def run(self):
        LOG.info("声强线程已启动")
        repetition_count = 0  # 重复值计数
        last_ts = time.time()
        while True:
            # Thread control
            try:
                if self.is_thread_exit is True:
                    LOG.warning("声强线程停止...................")
                    break
                if self.is_running is False:
                    time.sleep(0.04)
                    continue
                # Business
                try:
                    audio: EDABuffer = config.AUDIO_BUFFER[0]
                except Exception as e:
                    LOG.error(e)
                    time.sleep(0.04)
                    continue
                if audio is None:
                    time.sleep(0.04)
                    continue
                start_timestamp = audio.ts
                if audio.ts == last_ts:
                    repetition_count += 1
                    if repetition_count >= 200:
                        LOG.warning("音频流已断，即将重启声强线程...")
                        self.exit()
                else:
                    repetition_count = 0
                last_ts = audio.ts
                seconds_per_buffer = float(CHUNK) / RATE  # time of per buffer
                data = np.fromstring(audio.buffer, dtype=np.int16)
                size = data.size
                buffer_size = int(size / CHUNK)
                data = data[0:: self.sample_interval]
                datetime_arr = []
                for i in range(0, buffer_size):
                    data_for_str = i * self.sample_interval * seconds_per_buffer + start_timestamp
                    datetime_arr.append(
                        data_for_str
                    )
                datetime_arr = np.repeat(
                    np.array(datetime_arr), int(CHUNK / self.sample_interval)
                )
                data = data[:len(datetime_arr)]
                try:
                    # combine timestamp and freq_data
                    data_with_timestamp = np.vstack((data, datetime_arr))
                    data_with_timestamp = np.transpose(data_with_timestamp)
                    data_list = data_with_timestamp.tolist()
                    config.VOICE_DATA_OBJECT = data_list
                except Exception as e:
                    LOG.error(e)
                    time.sleep(0.04)
                    continue
                # Must delay
                time.sleep(0.04)
            except Exception as e:
                config.LOG.error("声强算法处理线程异常")
                LOG.error(e)
