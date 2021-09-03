#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import ctypes
import os
from ctypes import *
from application.controller.config import LOG
# 机器码最大长度
LICENSE_MAC_MAX_LEN = 64
# 截至日期最大长度
LICENSE_EXPIRE_DATA_MAX_LEN = 128
# 备注最大长度
LICENSE_REMARK_MAX_LEN = 128
LICENSE_IPV4_MAX_LEN = 16
LICENSE_SOFT_VERSION_MAX_LEN = 64


class LicenseInfo(Structure):
    _fields_ = [('deviceMAC', c_char * (LICENSE_MAC_MAX_LEN + 1)),  # 机器码
                ('expireData', c_char * (LICENSE_EXPIRE_DATA_MAX_LEN + 1)),  # 截至日期
                ('enableIPAddr', c_int),  # IP地址使能
                ('ip', c_char * (LICENSE_IPV4_MAX_LEN + 1)),  # IP地址
                ('softVersion', c_char * (LICENSE_SOFT_VERSION_MAX_LEN + 1)),  # 版本号
                ('deviceType', c_uint),  # 产品型号（等待产品组把公司目前所有的产品型号全都列举出来）
                ('remark', c_char * (LICENSE_REMARK_MAX_LEN + 1)),  # 备注
                ('reserved', c_uint)]  # 预留字段（可以用于加密版本的变化版本）


class EncryptManager(object):
    DLL_PATH = "liblicense.dll"

    def __init__(self):
        super(EncryptManager, self).__init__()
        self.lib = None
        self.load_lib()

    def load_lib(self):
        ret = False
        try:
            self.lib = windll.LoadLibrary(self.DLL_PATH)
            if not self.lib:
                LOG.error("Failed to load lib %s" % self.DLL_PATH)
                return ret
        except Exception as e:
            LOG.error("Failed to load lib {} : {}".format(self.DLL_PATH, e))
            return ret
        ret = True
        return ret

    def GenLicenseFile(self, licenseInfo, filePath):
        """生成license文件
        int LICENSE_APICALL GenLicenseFile(const LicenseInfo* licenseInfo,char* filePath);"""
        pass

    def GetLicenseInfo(self, filePath, licenseInfo):
        """获取license文件信息
        LICENSE_API int LICENSE_APICALL GetLicenseInfo(const char* filePath,LicenseInfo* licenseInfo);"""

        gen_license_file = self.lib.GetLicenseInfo
        gen_license_file(filePath, licenseInfo)


if __name__ == "__main__":
    test = "测试加密库"
    # test = "测试普通的dll动态库"
    # test = "zl"
    if test == "测试加密库":
        info = LicenseInfo()

        encrypt_manager = EncryptManager()
        genetate_file_path = b"2019012402.lic"
        # 生成license 文件
        # encrypt_manager.GenLicenseFile(byref(info), genetate_file_path)
        info_recv = LicenseInfo()
        # 获取license 文件信息
        encrypt_manager.GetLicenseInfo(genetate_file_path, byref(info_recv))

        print("deviceMAC", info_recv.deviceMAC)
        print("expireData:", info_recv.expireData)
        print("ip:", info_recv.ip)
        print("softVersion:", info_recv.softVersion)
        print("deviceType:0x%x" % info_recv.deviceType)
        from application.view.view_common import get_host_name, get_ip, get_mac_address

        print("\n本机获得信息：\n")
        print("mac:", get_mac_address())
        print("ip:", get_ip())
        print("host name:", get_host_name())
    elif test == "测试普通的dll动态库":

        DLL_PATH = "test_dll.dll"
        try:
            lib = windll.LoadLibrary(DLL_PATH)

        except Exception as e:
            print("Failed to load lib %s" % DLL_PATH)
        # add = lib.add
        # print("1 + 2:", add(1, 2))

        """struct MyStruct
        {
        	int result;
		double double_res;
		float float_res;
		int age;
        };"""


        class MyStruct(Structure):
            _fields_ = [('result', c_int),
                        ('double_res', c_double),
                        ('float_res', c_float),
                        ('age', c_int),
                        ]


        class Person(object):
            def __init__(self):
                self.obj = lib.person_new()
                self.age = None

            def get_health_data(self, name, height, weight):
                return lib.get_health_data(self.obj, name, height, weight)

            def add(self, a, b, res):
                return lib.add(self.obj, a, b, res)


        person = Person()
        health_data = person.get_health_data(bytes("Curry", 'utf-8'), 175, 70)
        print("health_data:", health_data)
        res = MyStruct()
        print("add result:", person.add(2, 4, byref(res)))
        print("res.double_res:", res.double_res)
        print("res.float_res:", res.float_res)
        print("res.age:", res.age)
        # print(person.obj.age)

    elif test == "zl":
        DLL_PATH = "mydll(5).dll"
        try:
            lib = windll.LoadLibrary(DLL_PATH)
        except Exception as e:
            print("Failed to load lib %s" % DLL_PATH)
        print(dir(lib))


        # MyMathFuncs = lib.sub
        class MyMathFuncs(object):
            def __init__(self):
                self.obj = lib.create_MyMathFuncs()

            """create_MyMathFuncs
            myMathFuncs_Add
            myMathFuncs_Divide
            myMathFuncs_Multiply
            myMathFuncs_Subtract"""

            def Add(self):
                # lib.myMathFuncs_Add.restype = c_float
                # lib.myMathFuncs_Add.argtypes = [type(self.obj), c_float, c_float]
                return lib.myMathFuncs_Add(self.obj, 2, 3)


        func = MyMathFuncs()
        print(func.Add())
