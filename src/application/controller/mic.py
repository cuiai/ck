#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""PyAudio example: Record a few seconds of audio and save to a WAVE file."""

import time
import ctypes
import pyaudio
import cv2, numpy
from PIL import Image
from copy import deepcopy
from threading import Thread
from application.controller import config
from vlc import MediaPlayer, CallbackDecorators
from application.controller.config import CFG, LOG

RATE = CFG.get('audio_rate', 48000)
CHANNELS = CFG.get('audio_channels', 2)
CHUNK = CFG.get('audio_chunk', 1024)
FORMAT = pyaudio.paInt16
RECORD_SECONDS = 1

url = CFG.get('dst_stream', 'rtsp://admin:1234qwer@192.168.16.51:554')
if not str(url).startswith("rtsp"):
    VIDEOWIDTH = 640
    VIDEOHEIGHT = 480
else:
    VIDEOWIDTH = 1280
    VIDEOHEIGHT = 720

# size in bytes when RV32
size = VIDEOWIDTH * VIDEOHEIGHT * 4

# allocate buffer
buf = (ctypes.c_ubyte * size)()
# get pointer to buffer
buf_p = ctypes.cast(buf, ctypes.c_void_p)

# vlc.CallbackDecorators.VideoLockCb is incorrect
CorrectVideoLockCb = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))


class EDAFrame:
    """
        带时间戳的视频帧类
    """
    frame = None  # 帧
    ts = None  # 时间戳

    def __init__(self, frame, ts):
        self.frame = frame
        self.ts = ts


class EDABuffer:
    """带时间戳的音频buffer类"""

    buffer = None
    ts = None

    def __init__(self, buffer, ts):
        self.buffer = buffer
        self.ts = ts


class AudioCollectThread(Thread):
    """Voice record class"""

    RECORD_FORMAT = FORMAT
    RECORD_CHANNELS = CHANNELS
    RECORD_RATE = RATE
    RECORD_SECONDS = RECORD_SECONDS
    RECORD_CHUNK = CHUNK
    MAX_QUEUE_NUM = RECORD_CHUNK * RECORD_SECONDS

    def __init__(self):
        super(AudioCollectThread, self).__init__()
        self.is_thread_exit = False
        self.audio_obj = None
        self.audio_stream = None
        self.audio_status = True
        self.is_collect_running = False

    def thread_exit(self):
        ret = False
        # close thread
        self.is_thread_exit = True
        ret = True
        return ret

    def setup_stream_resources(self):
        ret = False
        try:
            if self.audio_obj is None:
                self.audio_obj = pyaudio.PyAudio()
                self.audio_stream = self.audio_obj.open(format=self.RECORD_FORMAT,
                                                        channels=self.RECORD_CHANNELS,
                                                        rate=self.RECORD_RATE,
                                                        input=True,
                                                        frames_per_buffer=self.RECORD_CHUNK,
                                                        )
        except Exception as e:
            LOG.error("Failed to create audio && stream %s" % str(e))
            self.audio_status = False
            return ret
        try:
            self.audio_stream.start_stream()
        except Exception as e:
            LOG.error(".audio_stream.start_stream %s" % str(e))
            self.audio_status = False
            return ret
        ret = True
        return ret

    def clean_stream_resources(self):
        ret = False
        try:
            if self.audio_obj:
                if self.audio_stream:
                    self.audio_stream.close()
                    self.audio_stream = None
                self.audio_obj.terminate()
                self.audio_obj = None
        except Exception as e:
            LOG.error("_clean_resources %s" % str(e))
            return ret
        ret = True
        LOG.debug("audio_stream.close successfully!")
        return ret

    def run(self):
        LOG.info("音频解码线程已启动")
        while True:
            buffer = None
            if self.is_thread_exit is True:
                self.clean_stream_resources()
                break
            if self.is_collect_running is False:
                time.sleep(2)
                continue
            else:
                ret = self.setup_stream_resources()
                if ret is False:
                    time.sleep(1)
                    continue
            while not self.is_thread_exit:
                try:
                    if self.is_collect_running is True and self.audio_stream.is_active():
                        buffer = self.audio_stream.read(self.RECORD_CHUNK, exception_on_overflow=False)
                except Exception as e:
                    LOG.error(e)
                    time.sleep(1)
                    break
                time_stamp = time.time()
                try:
                    config.AUDIO_BUFFER = [EDABuffer(buffer, time_stamp)]
                except Exception as e:
                    LOG.error(e)
                time.sleep(0.005)
            self.clean_stream_resources()
            time.sleep(2)

    def start_collect(self):
        """Operation of start voice recording"""

        ret = None
        if self.audio_status is False:
            LOG.debug("audio_status is false, it will not start collect ")
            return ret
        if self.is_collect_running is False:
            self.is_collect_running = True
        ret = True
        return ret

    def stop_collect(self):
        """Operation of stop voice recording"""

        ret = False
        if self.audio_status is False:
            LOG.debug("audio_status is false, it should not start collect.")
            return ret
        if self.is_collect_running is True:
            self.is_collect_running = False
        ret = True
        LOG.debug("stop collect affair start")
        return ret


class AudioCollectVlc(object):
    ret = False

    def __init__(self, format_str="FL32", channels=1, rate=48000):
        super(AudioCollectVlc, self).__init__()
        self.url = CFG.get('dst_stream', 'rtsp://admin:1234qwer@192.168.16.51:554')
        if not str(self.url).startswith("rtsp"):
            AudioCollectVlc.ret = True
            self.url = "rtsp://127.0.0.1:554/live/999"
        self.format_str = format_str
        self.channels = channels
        self.rate = rate
        self.media_player = MediaPlayer(self.url)

    @staticmethod
    @CorrectVideoLockCb
    def _lockcb(opaque, planes):
        """必须添加，分配内存给vlc使用"""
        planes[0] = buf_p

    @staticmethod
    @CallbackDecorators.VideoDisplayCb
    def _display(opaque, picture):
        if AudioCollectVlc.ret:
            img = Image.frombuffer("RGBA", (VIDEOWIDTH, VIDEOHEIGHT), buf, "raw", "BGRA", 0, 1)
            img_buffer = cv2.cvtColor(numpy.array(img), cv2.COLOR_RGB2BGR)
            config.ORIGIN_FRAME = [EDAFrame(img_buffer, time.time())]

    @staticmethod
    @CallbackDecorators.AudioPlayCb
    def vlc_audio_play_cb(data, samples, count, pts):
        """ @param data: data pointer as passed to L{libvlc_audio_set_callbacks}() [IN].
            @param samples: pointer to a table of audio samples to play back [IN].
            @param count: number of audio samples to play back.
            @param pts: expected play time stamp (see libvlc_delay())."""
        buf_data = (ctypes.c_char * count * 2).from_address(samples)
        buffer = deepcopy(buf_data)
        time_stamp = time.time()
        try:
            if buffer is not None:
                config.AUDIO_BUFFER = [EDABuffer(buffer, time_stamp)]
        except Exception as e:
            LOG.error("update DATA_IMAGE_TO_VIDEO error %s" % str(e))

    def start_collect(self):
        """start parse and update the global"""

        """设置视频回调，不让出现vlc视频框"""
        self.media_player.video_set_callbacks(self._lockcb, None, self._display, None)
        self.media_player.video_set_format("RV32", VIDEOWIDTH, VIDEOHEIGHT, VIDEOWIDTH * 4)

        """设置音频回调及音频参数"""
        self.media_player.audio_set_callbacks(self.vlc_audio_play_cb, None, None, None, None, self.media_player)
        self.media_player.audio_set_format(self.format_str, self.rate, self.channels)

        """开始播放（解析）"""
        self.media_player.play()
        LOG.info("音频解码已开启")

    def stop(self):
        self.media_player.stop()
        LOG.info("音频解码已结束")

    def restart(self, url_str="rtsp://127.0.0.1:80/live/test", format_str="FL32", channels=1, rate=48000):
        LOG.debug('正在重启VLC音频解码...')
        self.url = CFG.get('dst_stream', 'rtsp://admin:1234qwer@192.168.16.51:554')
        if not str(self.url).startswith("rtsp"):
            self.url = "rtsp://127.0.0.1:554/live/999"
        self.stop()
        self.start_collect()


if __name__ == "__main__":
    audio_type = 1
    if audio_type == 0:
        audio = AudioCollectThread()
        audio.start_collect()
        audio.start()
    elif audio_type == 1:
        url = "rtsp://192.168.16.159:80/live/test"
        collect = AudioCollectVlc(format_str="FL32", channels=1, rate=48000)
        collect.start_collect()
        time.sleep(2)

    while True:
        try:
            buffer, timestamp = config.AUDIO_BUFFER
        except:
            LOG.error("get DATA_AUDIO_COLLECT error")
            continue
        time.sleep(0.05)
