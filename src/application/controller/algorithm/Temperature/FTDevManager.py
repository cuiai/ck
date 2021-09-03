#!/usr/bin/env python3
# -*- coding:utf-8 -*-


"""
    Ft device operation interface
"""

import time, copy
from datetime import datetime
from ctypes import *
from application.controller.config import LOG

IS_DEBUG = False

FT_OK = 0
FT_LIST_NUMBER_ONLY = 0x80000000
FT_LIST_ALL = 0x20000000
FT_OPEN_BY_DESCRIPTION = c_uint(2)
FLAG_LIST = 0x20000000 | 0x00000002

STARTAA = 0
START55 = 1
STATUS = 2
COMMAND = 3
LENGTH = 4
CRC1 = 5
DATA = 6
CRC2 = 7
END0D = 8
END0A = 9

PTR_NULL = POINTER(c_uint)()
DATA_PTR = POINTER(c_ubyte * 256)()


class USART_TR_DATA(Structure):
    _fields_ = [('frame_start', c_ushort),
                ('status', c_ubyte),
                ('command', c_ubyte),
                ('length', c_ushort),
                ('crc1', c_ushort),
                ('data', c_ushort * 244),
                ('crc2', c_ushort),
                ('frame_end', c_ushort)]


class Temperature(Structure):
    _fields_ = [('center_value', c_float),
                ('max_value', c_float),
                ('min_value', c_float)]


class SerialPortReceive:
    _fields_ = [('data', c_void_p), ('len', c_uint)]


class FTCamera(object):
    DLL_PATH = "ftd2xx.dll"
    BUFFER_LENGTH = 65536

    def __init__(self, log_output=print):
        super(FTCamera, self).__init__()
        self.lib = None
        self.log_output = log_output
        self.load_lib()
        self.ft_handle = c_void_p()
        self.RxBuffer = create_string_buffer(self.BUFFER_LENGTH)
        self.BytesReceived = c_uint(0)
        self.length = 0
        self.crc = c_uint(0xFFFF)
        self.crc1 = 0
        self.crc2 = 0
        self.count = 0
        self.current_temperature = 0
        self.state_transition = 0

    def load_lib(self):
        ret = False
        try:
            self.lib = windll.LoadLibrary(self.DLL_PATH)
            if not self.lib:
                LOG.error("Failed to load lib %s" % self.DLL_PATH)
                return ret
        except Exception as e:
            LOG.error("Failed to load lib %s" % self.DLL_PATH)
            return ret
        ret = True
        return ret

    def list_devices(self):
        """FT_ListDevices interface"""

        ret = None
        if not self.lib:
            return ret
        ftStatus_Search = c_uint(0)
        numDevs = c_uint(0)
        try:
            FT_ListDevices = self.lib.FT_ListDevices
            ftStatus_Search = FT_ListDevices(byref(numDevs), None, FT_LIST_NUMBER_ONLY)
            if ftStatus_Search != FT_OK:
                LOG.error("Failed to call FT_ListDevices")
                return ret
            devices_num = numDevs.value
            if devices_num == 0:
                return ret
        except Exception as e:
            LOG.error("Failed to load lib %s" % self.DLL_PATH)
            return ret
        if IS_DEBUG:
            LOG.debug("devices_num: %d" % devices_num)
        ret = devices_num
        return ret

    def set_baud_rate(self):
        ret = False
        if not self.lib:
            return ret
        FT_SetBaudRate = self.lib.FT_SetBaudRate
        try:
            rc = FT_SetBaudRate(self.ft_handle, 8000000)
            if rc != 0:
                LOG.error("Error FT_SetBaudRate() rc=%d" % rc)
                return ret
        except Exception as e:
            LOG.error("Error FT_SetBaudRate %s" % str(e))
            return ret
        if IS_DEBUG:
            LOG.debug("FT_SetBaudRate() rc=%d" % rc)
        ret = True
        return ret

    def open(self):
        """ FT_Open interface """

        ret = False
        if not self.lib:
            return ret
        deviceNumber = c_uint(0)
        FT_Open = self.lib.FT_Open
        try:
            rc = FT_Open(deviceNumber, byref(self.ft_handle))
            if rc != 0:
                LOG.error("Error FT_Open() rc=%d" % rc)
                return ret
        except Exception as e:
            LOG.error("Error FT_Open %s" % str(e))
            return ret
        if IS_DEBUG:
            LOG.debug("FT_Open() rc=%d" % rc)
        ret = True
        return ret

    def close(self):
        """ FT_Close interface """

        ret = False
        if not self.lib:
            return ret
        FT_Close = self.lib.FT_Close
        try:
            rc = FT_Close(self.ft_handle)
            if rc != 0:
                LOG.error("Error FT_Close() rc=%d" % rc)
                return ret
        except Exception as e:
            LOG.error("Error FT_Close %s" % str(e))
            return ret
        if IS_DEBUG:
            LOG.debug("FT_Close() rc = %d" % rc)
        ret = True
        return ret

    def send_usart_data(self):
        """
        Send usart data to start communication
        """

        ret = False
        if not self.lib:
            return ret
        my_buffer = create_string_buffer(13)
        BytesWritten = c_uint(0)
        ptr_bytes_written = POINTER(c_uint)
        crc = 0xFFFF
        tx_data = USART_TR_DATA()
        tx_data.frame_start = 0xaa55
        tx_data.status = 0x00
        tx_data.command = 0x00
        tx_data.length = 0x01
        tx_data.crc1 = crc & 0x00FF
        # tx_data.data = 0x00
        tx_data.crc2 = crc & 0x00FF
        tx_data.frame_end = 0x0d0a
        for i in range(tx_data.length + 12):
            if i == 0:
                my_buffer[i] = 0xaa  # start frame byte 1
            elif i == 1:
                my_buffer[i] = 0x55  # start frame byte 2
            elif i == 2:
                my_buffer[i] = 0x00  # status
            elif i == 3:
                my_buffer[i] = tx_data.command  # command
            elif i == 4:
                my_buffer[i] = 0x00  # data len byte 1
            elif i == 5:
                my_buffer[i] = 0x01  # data len byte 1
            elif i == 6:
                tx_data.crc1 = crc
                my_buffer[i] = 0x4F
            elif i == 7:
                my_buffer[i] = 0x7E
            elif i < tx_data.length + 8:
                my_buffer[i] = 0x00
            elif i == tx_data.length + 8:
                tx_data.crc2 = crc
                my_buffer[i] = 0x00
            elif i == tx_data.length + 9:
                my_buffer[i] = 0x00
            elif i == tx_data.length + 10:
                my_buffer[i] = 0x0d
            elif i == tx_data.length + 11:
                my_buffer[i] = 0x0a
            else:
                return ret
            if IS_DEBUG:
                # LOG.debug("{0} - {1}".format(i, my_buffer[i]))
                pass
        FT_Write = self.lib.FT_Write
        try:
            rc = FT_Write(self.ft_handle, my_buffer, sizeof(my_buffer), byref(BytesWritten))
            if rc != 0:
                LOG.error("Error FT_Write() rc=%d" % rc)
                return ret
        except Exception as e:
            LOG.error("Error FT_Write %s" % str(e))
            return ret
        if IS_DEBUG:
            LOG.debug("FT_Write() rc=%d" % rc)
        LOG.debug("\nsend command:\n%s" % str(my_buffer.raw))
        ret = True
        return ret

    def send_uart(self, data=0x00):
        ret = False
        BytesWritten = c_uint(0)
        my_buffer = create_string_buffer(1)
        my_buffer[0] = data
        FT_Write = self.lib.FT_Write
        try:
            rc = FT_Write(self.ft_handle, my_buffer, sizeof(my_buffer), byref(BytesWritten))
            if rc != 0:
                LOG.error("Error FT_Write() rc=%d" % rc)
                return ret
        except Exception as e:
            LOG.error("Error FT_Write %s" % str(e))
            return ret
        if IS_DEBUG:
            LOG.debug("FT_Write() rc=%d" % rc)
        ret = True
        return ret

    def send_usart_stop_data(self):
        """
        Send usart data to start communication
        """

        ret = False
        if not self.lib:
            return ret
        my_buffer = create_string_buffer(13)
        BytesWritten = c_uint(0)
        ptr_bytes_written = POINTER(c_uint)
        crc = 0xFFFF
        tx_data = USART_TR_DATA()
        tx_data.frame_start = 0xaa55
        tx_data.status = 0x00
        tx_data.command = 0x00
        tx_data.length = 0x01
        tx_data.crc1 = crc & 0x00FF
        # tx_data.data = 0xFF
        tx_data.crc2 = crc & 0x00FF
        tx_data.frame_end = 0x0d0a
        for i in range(tx_data.length + 12):
            if i == 0:
                my_buffer[i] = 0xaa  # start frame byte 1
            elif i == 1:
                my_buffer[i] = 0x55  # start frame byte 2
            elif i == 2:
                my_buffer[i] = 0x00  # status
            elif i == 3:
                my_buffer[i] = tx_data.command  # command
            elif i == 4:
                my_buffer[i] = 0x00  # data len byte 1
            elif i == 5:
                my_buffer[i] = 0x01  # data len byte 1
            elif i == 6:
                tx_data.crc1 = crc
                my_buffer[i] = 0x4F
            elif i == 7:
                my_buffer[i] = 0x7E
            elif i < tx_data.length + 8:
                my_buffer[i] = 0xFF
            elif i == tx_data.length + 8:
                tx_data.crc2 = crc
                my_buffer[i] = 0x1E
            elif i == tx_data.length + 9:
                my_buffer[i] = 0xF0
            elif i == tx_data.length + 10:
                my_buffer[i] = 0x0d
            elif i == tx_data.length + 11:
                my_buffer[i] = 0x0a
            else:
                return ret
            if IS_DEBUG:
                # LOG.debug("{0} - {1}".format(i, my_buffer[i]))
                pass
        FT_Write = self.lib.FT_Write
        try:
            rc = FT_Write(self.ft_handle, my_buffer, sizeof(my_buffer), byref(BytesWritten))
            if rc != 0:
                LOG.error("Error FT_Write() rc=%d" % rc)
                return ret
        except Exception as e:
            LOG.error("Error FT_Write %s" % str(e))
            return ret
        if IS_DEBUG:
            LOG.debug("FT_Write() rc=%d" % rc)
        ret = True
        return ret

    def get_queue_status(self):
        ret = None
        if not self.lib:
            return ret
        rx_bytes = c_uint(1)
        FT_GetQueueStatus = self.lib.FT_GetQueueStatus
        try:
            rc = FT_GetQueueStatus(self.ft_handle, byref(rx_bytes))
            if rc != 0:
                # LOG.error("Error FT_GetQueueStatus() rc=%d" % rc)
                return ret
        except Exception as e:
            LOG.error("Error FT_GetQueueStatus %s" % str(e))
            return ret
        if rx_bytes.value == 0:
            return ret
        if IS_DEBUG:
            # LOG.debug("FT_GetQueueStatus() rc = %d, rx_bytes=%d" % (rc, rx_bytes.value))
            pass
        ret = rx_bytes.value
        return ret

    def data_process(self, receive_data, rx_number):
        """Process data which got from FT camera device"""

        ret = False
        rx_data = USART_TR_DATA()
        recv_list = [hex(int(i)) for i in receive_data]
        recv_str = " ".join(recv_list)
        commands = recv_str.split("0xd 0xa")
        for item in commands:
            if item.startswith(" 0xaa 0x55 0x0 0xd") or item.startswith(" 0xaa 0x55 0x0 0xe"):
                item_data = item.split(" ")
                rx_data.frame_start = int(item_data[1], 16) << 8
                rx_data.frame_start |= int(item_data[2], 16)
                rx_data.status = int(item_data[3], 16)
                rx_data.command = int(item_data[4], 16)
                rx_data.length = int(item_data[5], 16) << 8
                rx_data.length |= int(item_data[6], 16)
                rx_data.crc1 = int(item_data[7], 16) << 8
                rx_data.crc1 |= int(item_data[8], 16)
                rx_data.crc2 = int(item_data[8 + rx_data.length + 1], 16) << 8
                rx_data.crc2 |= int(item_data[8 + rx_data.length + 2], 16)
                rx_data.frame_end = 0x0d0a
                try:
                    for i in range(rx_data.length):
                        rx_data.data[i] = int(item_data[9 + i], 16)
                except Exception as e:
                    LOG.error("error %s" % str(e))
                try:
                    self.Packet_analysis(rx_data)
                except Exception as e:
                    LOG.error("Packet_analysis error %s" % str(e))
                ret = True
        return ret

    def Packet_analysis(self, rx_data):
        temperature = Temperature()
        if rx_data.command == 0x00:
            pass
        # elif rx_data.command == 0x0D:       ## Get tempature data
        #     try:
        #         vc_data = rx_data.data[6] << 8
        #         vc_data |= rx_data.data[7]
        #         temperature.center_value = float('%.1f' % (vc_data/10 - 100))
        #
        #         vc_data = rx_data.data[2] << 8
        #         vc_data |= rx_data.data[3]
        #         temperature.max_value = float('%.1f' % (vc_data / 10 - 100))
        #
        #         vc_data = rx_data.data[4] << 8
        #         vc_data |= rx_data.data[5]
        #         temperature.min_value = float('%.1f' % (vc_data / 10 - 100))
        #     except Exception as e:
        #         LOG.error("Error calculate tc value %s" % str(e))
        #         temperature.center_value = 0.0
        #         temperature.min_value = 0.0
        #         temperature.max_value = 0.0
        #     if IS_DEBUG:
        #         LOG.debug(" **** > command: {0} - timestamp: {1}".format(rx_data.command, datetime.now()))
        #         LOG.debug("             Tc: {0:0.1f}".format(temperature.max_value))
        #
        #     ## Send data to Queue
        #     print("center:", temperature.center_value)
        #     print("max_value:", temperature.max_value)
        #     print("min_value:", temperature.min_value)
        #     self.current_temperature = temperature.max_value
        elif rx_data.command == 0x0E:  ## Get tempature data
            try:
                vc_data = rx_data.data[2] << 8
                vc_data |= rx_data.data[3]
                temperature.max_value = float('%.1f' % (vc_data / 10 - 100))
            except Exception as e:
                LOG.error("Error calculate tc value %s" % str(e))
                temperature.center_value = 0.0
                temperature.min_value = 0.0
                temperature.max_value = 0.0
            if IS_DEBUG:
                LOG.debug(" **** > command: {0} - timestamp: {1}".format(rx_data.command, datetime.now()))
                LOG.debug("             Tc: {0:0.1f}".format(temperature.max_value))

            ## Send data to Queue
            self.current_temperature = temperature.max_value
        elif rx_data.command == 0x24:  ## Get image data
            if IS_DEBUG:
                LOG.debug(" **** > command: {0} - timestamp: {1}".format(rx_data.command, datetime.now()))
            pass
        else:  ## Deal with the other type data
            pass

    def read(self, rx_bytes):
        ret = False
        if not self.lib:
            return ret
        rx_bytes = rx_bytes
        FT_Read = self.lib.FT_Read
        try:
            rc = FT_Read(self.ft_handle, pointer(self.RxBuffer), rx_bytes, pointer(self.BytesReceived))
            if rc != 0:
                LOG.error("Error FT_Read() rc=%d" % rc)
                return ret
            raw_data = copy.copy(self.RxBuffer.raw)
            rc = self.data_process(raw_data, self.BytesReceived.value)
            if not rc:
                return ret
            memset(pointer(self.RxBuffer), 0x00, self.BUFFER_LENGTH)
        except Exception as e:
            LOG.error("Error FT_Read %s" % str(e))
            return ret
        if IS_DEBUG:
            # LOG.debug("FT_Read() rc=%d, BytesReceived=%d" % (rc, BytesReceived.value))
            pass
        ret = True
        return ret

    def get_driver_version(self):
        ret = False
        if not self.lib:
            return ret
        drv_version = c_uint(0)
        FT_GetDriverVersion = self.lib.FT_GetDriverVersion
        try:
            rc = FT_GetDriverVersion(self.ft_handle, byref(drv_version))
            if rc != 0:
                LOG.error("Error FT_GetDriverVersion() rc=%d" % rc)
                return ret
        except Exception as e:
            LOG.error("Error FT_GetDriverVersion %s" % str(e))
            return ret
        if IS_DEBUG:
            LOG.debug("FT_GetDriverVersion() rc=%d, drv_version=%d" % (rc, drv_version.value))
        ret = True
        return ret

    def get_com_port_number(self):
        ret = False
        if not self.lib:
            return ret
        com_port_num = c_long(0)
        FT_GetComPortNumber = self.lib.FT_GetComPortNumber
        try:
            rc = FT_GetComPortNumber(self.ft_handle, byref(com_port_num))
            if rc != 0:
                LOG.error("Error FT_GetComPortNumber() rc=%d" % rc)
                return ret
        except Exception as e:
            LOG.error("Error FT_GetComPortNumber %s" % str(e))
            return ret
        if IS_DEBUG:
            LOG.debug("FT_GetComPortNumber() rc=%d, com_port_num=%d" % (rc, com_port_num.value))
        ret = True
        return ret

    def get_lib_version(self):
        ret = False
        if not self.lib:
            return ret
        lib_version = c_uint(0)
        FT_GetLibraryVersion = self.lib.FT_GetLibraryVersion
        try:
            rc = FT_GetLibraryVersion(self.ft_handle, byref(lib_version))
            if rc != 0:
                LOG.error("Error FT_GetLibraryVersion() rc=%d" % rc)
                return ret
        except Exception as e:
            LOG.error("Error FT_GetLibraryVersion %s" % str(e))
            return ret
        if IS_DEBUG:
            LOG.debug("FT_GetLibraryVersion() rc=%d, lib_version=%d" % (rc, lib_version.value))
        ret = True
        return ret

    def set_data_characteristics(self):
        ret = False
        FT_BITS_8 = c_ubyte(8)
        FT_STOP_BITS_1 = c_ubyte(0)
        FT_PARITY_NONE = c_ubyte(0)
        if not self.lib:
            return ret
        FT_SetDataCharacteristics = self.lib.FT_SetDataCharacteristics
        try:
            rc = FT_SetDataCharacteristics(self.ft_handle, FT_BITS_8, FT_STOP_BITS_1, FT_PARITY_NONE)
            if rc != 0:
                LOG.error("Error FT_SetDataCharacteristics() rc=%d" % rc)
                return ret
        except Exception as e:
            LOG.error("Error FT_SetDataCharacteristics %s" % str(e))
            return ret
        if IS_DEBUG:
            LOG.debug("FT_SetDataCharacteristics() rc=%d" % rc)
        ret = True
        return ret

    def set_timeout(self):
        ret = False
        if not self.lib:
            return ret
        FT_SetTimeouts = self.lib.FT_SetTimeouts
        try:
            rc = FT_SetTimeouts(self.ft_handle, 5000, 0)
            if rc != 0:
                LOG.error("Error FT_SetTimeouts() rc=%d" % rc)
                return ret
        except Exception as e:
            LOG.error("Error FT_SetTimeouts %s" % str(e))
            return ret
        if IS_DEBUG:
            LOG.debug("FT_SetTimeouts() rc=%d" % rc)
        ret = True
        return ret


def workflow():
    ret = False
    ft_obj = FTCamera()
    rc = ft_obj.list_devices()
    if rc is not None:
        rc = ft_obj.open()
        if not rc:
            return ret
        ft_obj.set_baud_rate()
        ft_obj.set_data_characteristics()
        ft_obj.set_timeout()
        # time.sleep(10)
        ft_obj.send_usart_data()
        while True:
            rx_bytes_len = ft_obj.get_queue_status()
            if rx_bytes_len:
                ft_obj.read(rx_bytes_len)
            time.sleep(0.01)
        ft_obj.close()


if __name__ == '__main__':
    workflow()
