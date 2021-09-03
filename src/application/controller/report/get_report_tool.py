# !/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from application.controller.config import MONGODB_COLLECTION_FOR_READ, LOG, alarm_data_count


def get_report_info(inquest_uuid):
    """
    ('AU1', 'AU2', 'AU4', 'AU5', 'AU6', 'AU7', 'AU9', 'AU10', 'AU12', 'AU14', 'AU15', 'AU17', 'AU20', 'AU23', 'AU25', 'AU26', 'AU45')
    :param inquest_uuid:
    :return:
    """

    heart_rate_low_count = 0  # 心率过低出现次数
    heart_rate_normal_count = 0  # 心率正常出现次数
    heart_rate_high_count = 0  # 心率过高出现次数

    au_dict = {
        'AU1': 0,
        'AU2': 0,
        'AU4': 0,
        'AU5': 0,
        'AU6': 0,
        'AU7': 0,
        'AU9': 0,
        'AU10': 0,
        'AU12': 0,
        'AU14': 0,
        'AU15': 0,
        'AU17': 0,
        'AU20': 0,
        'AU23': 0,
        'AU25': 0,
        'AU26': 0,
        'AU45': 0,
    }
    tmp_tuple = (
        'AU1', 'AU2', 'AU4', 'AU5', 'AU6', 'AU7', 'AU9', 'AU10', 'AU12', 'AU14', 'AU15', 'AU17', 'AU20', 'AU23', 'AU25',
        'AU26', 'AU45')

    documents = MONGODB_COLLECTION_FOR_READ.find({'inquest_uuid': inquest_uuid})
    for document in documents:
        """au、可疑值状态、正负面情绪次数统计、心率状态次数统计"""
        try:
            # 计算心率过缓、正常、过速的数量
            heart_rate_data = document.get('heart_rate_data')
            if 0 < heart_rate_data < 60:
                heart_rate_low_count += 1
            elif heart_rate_data <= 100:
                heart_rate_normal_count += 1
            else:
                heart_rate_high_count += 1

            # 计算每个au单元的数量
            au_data = document.get('au_data')
            for index, item in enumerate(au_data):
                if item > 3:
                    au_dict[tmp_tuple[index]] += 1
        except Exception as e:
            pass
            # VIEW_LOG.debug('0，因为关联此uuid的数据包含有可疑值相关的数据，此数据没有AU单元数据、心率数据、表情数据，对AU单元统计没有影响')
    try:
        if au_dict.get("AU45"):
            au_dict.pop("AU45")
    except Exception as e:
        LOG.debug("审讯报告删除AU45失败---{}".format(e))

    # 计算心率过缓、正常、过速的占比
    heart_rate_total_count = heart_rate_low_count + heart_rate_normal_count + heart_rate_high_count
    if heart_rate_total_count:
        heart_rate_low_percentage = round(heart_rate_low_count / heart_rate_total_count * 100, 2)
        heart_rate_normal_percentage = round(heart_rate_normal_count / heart_rate_total_count * 100, 2)
        heart_rate_high_percentage = round(heart_rate_high_count / heart_rate_total_count * 100, 2)
    else:
        heart_rate_low_percentage = 0
        heart_rate_normal_percentage = 0
        heart_rate_high_percentage = 0

    data = {
        'heart_rate_low_count': heart_rate_low_count,
        'heart_rate_normal_count': heart_rate_normal_count,
        'heart_rate_high_count': heart_rate_high_count,
        'heart_rate_low_percentage': '%s%%' % heart_rate_low_percentage,
        'heart_rate_normal_percentage': '%s%%' % heart_rate_normal_percentage,
        'heart_rate_high_percentage': '%s%%' % heart_rate_high_percentage,
        'au_dict': au_dict,
        'alarmNum': len(alarm_data_count),
    }
    return data


if __name__ == '__main__':
    os.chdir("../../../")
    print(os.getcwd())
    print(os.listdir(os.getcwd()))
    get_report_info('1bc8a59c-9231-11e9-b9d8-2cfda172c2e6')
