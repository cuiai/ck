#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

import time
import datetime
import os.path
import sqlite3, json
from sqlalchemy import not_
from sqlalchemy.sql import func
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import between, and_, or_
from sqlalchemy.ext.declarative import declarative_base
from application.controller import config
from application.controller.config import DB_DATA_PATH, LOG
from sqlalchemy import Column, Integer, String, FLOAT, Boolean, TIMESTAMP, Index


def clean_db_file():
    ret = False
    db_path = DB_DATA_PATH
    try:
        os.remove(db_path)
    except Exception as e:
        LOG.error(str(e))
        return ret
    ret = True
    return ret


engine = create_engine('sqlite:///%s?check_same_thread=False' % DB_DATA_PATH, echo=False)
Base = declarative_base()
db_session = sessionmaker(bind=engine)


def init_data_database():
    ret = False
    try:
        # TODO: create database file
        if os.path.isfile(DB_DATA_PATH) is False:
            Base.metadata.create_all(engine)
    except Exception as e:
        LOG.error("init data database %s" % str(e))
        return ret
    ret = True
    return ret


def update_field():
    if os.path.isfile(DB_DATA_PATH):
        conn = sqlite3.connect(DB_DATA_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT *  from personal_manager")
            person_list = [per[0] for per in cursor.description]
            if 'id_type' not in person_list:
                sql = 'ALTER TABLE personal_manager ADD COLUMN id_type Integer'
                cursor.execute(sql)
                LOG.debug("同步老版本数据库 id_type 字段成功......................")
            cursor.execute("SELECT *  from inquest_record")
            inquest = [inq[0] for inq in cursor.description]
            if 'alarmNum' not in inquest:
                sql = 'ALTER TABLE inquest_record ADD COLUMN alarmNum Integer DEFAULT 0'
                cursor.execute(sql)
                LOG.debug("同步老版本数据库 alarmNum 字段成功......................")
            if 'id_type' not in inquest:
                sql = 'ALTER TABLE inquest_record ADD COLUMN id_type Integer'
                cursor.execute(sql)
                LOG.debug("同步老版本数据库 id_type 字段成功......................")
            cursor.execute("SELECT *  from question_record")
            question = [inq[0] for inq in cursor.description]
            if 'emotion_degree' not in question:
                sql = 'ALTER TABLE question_record ADD COLUMN emotion_degree VARCHAR DEFAULT ""'
                cursor.execute(sql)
                LOG.debug("同步老版本数据库 emotion_degree 字段成功......................")
            if 'emotion_degree_count' not in question:
                sql = 'ALTER TABLE question_record ADD COLUMN emotion_degree_count Integer DEFAULT 0'
                cursor.execute(sql)
                LOG.debug("同步老版本数据库 emotion_degree_count 字段成功......................")
            if 'timeStamp' not in question:
                sql = 'ALTER TABLE question_record ADD COLUMN timeStamp Integer DEFAULT 0'
                cursor.execute(sql)
                LOG.debug("同步老版本数据库 timeStamp 字段成功......................")
        except Exception as e:
            LOG.error(e)
        cursor.close()
        conn.close()


class PersonalManager(Base):
    """   人员管理
    ------------------------------------------------------
    id                 : 主键，索引
    inquirer           : 询问人姓名
    sex                : 性别
    nation             : 国籍
    educational_level  : 学历
    marital_status     : 婚姻状况
    birthday           ：生日
    id_number          ：身份证号
    face_image         ：照片路径
    household_register : 户籍
    use_flag           :
    create_time        : 创建时间
    update_time        ：更新时间
    id_type            ：证件类型
    -----------------------------------------------------
    """

    __tablename__ = 'personal_manager'
    id = Column(Integer, primary_key=True)
    inquirer = Column(String)
    sex = Column(String)
    nation = Column(String)
    educational_level = Column(String)
    marital_status = Column(String)
    birthday = Column(String)
    id_number = Column(String)
    face_image = Column(String, default="")
    household_register = Column(String)
    home_address = Column(String)
    use_flag = Column(Boolean)
    create_time = Column(FLOAT)
    update_time = Column(FLOAT)
    id_type = Column(Integer)

    @staticmethod
    def add_opt(inquirer, sex, nation, educational_level, marital_status, birthday, number,
                face_image, household_register, home_address, create_time, id_type, use_flag=True):
        ret = False
        session = db_session()
        try:
            personal_manager = PersonalManager(inquirer=inquirer,
                                               sex=sex,
                                               nation=nation,
                                               educational_level=educational_level,
                                               marital_status=marital_status,
                                               birthday=birthday,
                                               id_number=number,
                                               face_image=face_image,
                                               household_register=household_register,
                                               home_address=home_address,
                                               use_flag=use_flag,
                                               create_time=create_time,
                                               id_type=id_type
                                               )
            session.add(personal_manager)
            session.commit()
            ret = personal_manager.id
            session.close()
        except Exception as e:
            session.rollback()
            LOG.error("add_opt %s" % str(e))
            return ret
        return ret

    @staticmethod
    def get_all_opt(*args, **kwargs):
        ret = []
        session = db_session()
        try:
            name = kwargs.get('name', '')
            number = kwargs.get('number', '')
            sex = kwargs.get('sex', '')
            filter_list = []
            if name:
                name_filter = PersonalManager.inquirer.ilike('%' + name + '%')
                filter_list.append(name_filter)
            if number:
                number_filter = PersonalManager.id_number.ilike('%' + number + '%')
                filter_list.append(number_filter)
            if sex:
                sex_filter = PersonalManager.sex.ilike('%' + sex + '%')
                filter_list.append(sex_filter)
            if len(filter_list) == 0:
                records = session.query(PersonalManager).filter_by(use_flag=True).order_by(
                    PersonalManager.id.desc()).all()
            elif len(filter_list) == 1:
                records = session.query(PersonalManager).filter(
                    and_(filter_list[0], PersonalManager.use_flag == True)).order_by(PersonalManager.id.desc()).all()
            elif len(filter_list) == 2:
                records = session.query(PersonalManager).filter(
                    and_(filter_list[0], filter_list[1], PersonalManager.use_flag == True)).order_by(
                    PersonalManager.id.desc()).all()
            else:
                records = session.query(PersonalManager).filter(
                    and_(filter_list[0], filter_list[1], filter_list[2], PersonalManager.use_flag == True)).order_by(
                    PersonalManager.id.desc()).all()
            session.close()
            if records is not []:
                ret = records
        except Exception as e:
            session.rollback()
            LOG.error("get_all %s" % str(e))
            return ret
        return ret

    @staticmethod
    def get_one_opt(person_id):
        ret = None
        session = db_session()
        try:
            per = session.query(PersonalManager).filter_by(id=person_id, use_flag=True).first()
        except Exception as e:
            session.rollback()
            LOG.error("get personal %s" % str(e))
            return ret
        finally:
            session.close()
        ret = per
        return ret

    @staticmethod
    def get_one_opt_by_number(number, use_flag=True):
        ret = None
        session = db_session()
        try:
            if use_flag:
                per = session.query(PersonalManager).filter_by(id_number=number, use_flag=use_flag).first()
            else:
                per = session.query(PersonalManager).filter_by(id_number=number).first()
            session.close()
        except Exception as e:
            session.rollback()
            LOG.error("get personal %s" % str(e))
            return ret
        ret = per
        return ret

    @staticmethod
    def get_one_opt_by_name(name):
        session = db_session()
        ret = None
        try:
            per = session.query(PersonalManager).filter_by(interrogator=name, use_flag=True).first()
            session.close()
        except Exception as e:
            session.rollback()
            LOG.error("get personal %s" % str(e))
            return ret
        ret = per
        return ret

    @staticmethod
    def del_opt(id):
        session = db_session()
        ret = False
        try:
            if id is not None:
                per = session.query(PersonalManager).filter_by(id=id).first()
            else:
                per = session.query(PersonalManager).all()
            session.delete(per)
            session.commit()
            session.close()
        except Exception as e:
            session.rollback()
            LOG.error("del_opt %s" % str(e))
            return ret
        ret = True
        return ret

    @staticmethod
    def del_opt_by_use_flag():
        session = db_session()
        ret = False
        try:
            per_all = session.query(PersonalManager).filter_by(use_flag=False).all()
            for per in per_all:
                session.delete(per)
            session.commit()
            session.close()
        except Exception as e:
            session.rollback()
            LOG.error("del_opt %s" % str(e))
            return ret
        ret = True
        return ret

    @staticmethod
    def update_opt(person_id, inquirer, sex, nation, education, marital, birthday, number, image, household,
                   home_address, update_time):
        ret = False
        session = db_session()
        try:
            update_person = session.query(PersonalManager).filter_by(id=person_id).first()
            if inquirer:
                update_person.inquirer = inquirer
            if sex:
                update_person.sex = sex
            if nation:
                update_person.nation = nation
            if education:
                update_person.educational_level = education
            if marital:
                update_person.marital_status = marital
            if birthday:
                update_person.birthday = birthday
            if image:
                update_person.face_image = image
            if household:
                update_person.household_register = household
            if home_address:
                update_person.home_address = home_address
            if number:
                update_person.id_number = number
            if update_time:
                update_person.update_time = update_time
            session.commit()
            session.close()
        except Exception as e:
            session.rollback()
            LOG.error("update %s" % str(e))
            return ret
        ret = True
        return ret

    @staticmethod
    def update_opt_by_use_flag():
        ret = False
        session = db_session()
        try:
            update_person = session.query(PersonalManager).filter_by(use_flag=False).all()
            for person in update_person:
                person.use_flag = True
            session.commit()
            session.close()
        except Exception as e:
            session.rollback()
            LOG.error("update %s" % str(e))
            return ret
        ret = True
        return ret

    @staticmethod
    def update_opt_by_id_number(id_card_num, inquest_name, sex, nation, birthday, education, household_registration,
                                current_address):
        ret = None
        session = db_session()
        try:
            update_person = session.query(PersonalManager).filter_by(id_number=id_card_num).all()
            if len(update_person):
                if inquest_name:
                    update_person[0].inquirer = inquest_name
                if sex:
                    update_person[0].sex = sex
                if nation:
                    update_person[0].nation = nation
                if birthday:
                    update_person[0].birthday = birthday
                if education:
                    update_person[0].educational_level = education
                if household_registration:
                    update_person[0].household_register = household_registration
                if current_address:
                    update_person[0].home_address = current_address
                session.commit()
            else:
                personal_manager = PersonalManager(inquirer=inquest_name,
                                                   sex=sex,
                                                   nation=nation,
                                                   educational_level=education,
                                                   marital_status='',
                                                   birthday=birthday,
                                                   id_number=id_card_num,
                                                   face_image='',
                                                   household_register=household_registration,
                                                   home_address=current_address,
                                                   use_flag=True,
                                                   create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f")
                                                   )
                session.add(personal_manager)
                session.commit()
                ret = personal_manager.id
            session.close()
        except Exception as e:
            session.rollback()
            LOG.error("update %s" % str(e))
            return ret
        ret = True
        return ret

    @staticmethod
    def get_opt_by_number(number):
        ret = []
        conn = sqlite3.connect(DB_DATA_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT *  from personal_manager WHERE id_number = ?", (number,))
            ret = cursor.fetchall()
        except Exception as e:
            LOG.error("get_opt_by_number error:%s" % str(e))
        cursor.close()
        conn.close()
        return ret


class EmotionData(Base):
    """        表情数据
    ------------------------------------------------------
    id            : 主键，索引
    inquest_uuid  : 审讯 uuid
    question_uuid : 审讯问题 uuid
    em_composite  : 综合 表情概率值 0-100
    em_angry      ：生气 表情概率值 0-100
    em_disgusted  ：厌恶 表情概率值 0-100
    em_fearful    ：害怕 表情概率值 0-100
    em_happy      ：高兴 表情概率值 0-100
    em_sad        ：伤心 表情概率值 0-100
    em_surprised  ：惊讶 表情概率值 0-100
    em_neutral    ：平和 表情概率值 0-100
    em_contempt   ：轻蔑 表情概率值 0-100
    create_time   ：时间戳  Float
    mood          : 正面 (0)/负面 (1)
    degree        : 程度值 Float  [-50 , 50]
    -----------------------------------------------------
    """

    # TODO: Emotion list ['angry', 'disgusted', 'fearful', 'happy', 'sad', 'surprised', 'neutral']
    __tablename__ = 'emotion_data'
    id = Column(Integer, primary_key=True)
    inquest_uuid = Column(String, default="")
    question_uuid = Column(String, default="")
    em_composite = Column(Integer)
    em_angry = Column(Integer)
    em_disgusted = Column(Integer)
    em_fearful = Column(Integer)
    em_happy = Column(Integer)
    em_sad = Column(Integer)
    em_surprised = Column(Integer)
    em_neutral = Column(Integer)
    em_contempt = Column(Integer)
    create_time = Column(Integer)
    mood = Column(Integer)
    degree = Column(FLOAT)
    heart_rate = Column(Integer)
    temperature = Column(FLOAT)
    voice_data = Column(String)
    __table_args__ = (Index("iu_ct", "inquest_uuid", "create_time"),)

    @staticmethod
    def add_items_opt(data_list):
        ret = False
        session = db_session()
        items_obj = list()
        for data in data_list:
            em_angry = data[0]
            em_disgusted = data[4]
            em_fearful = data[1]
            em_happy = data[6]
            em_sad = data[2]
            em_surprised = data[3]
            em_neutral = data[7]
            em_contempt = data[5]
            create_time = data[8]
            inquest_uuid = data[9]
            heart_rate = data[10][0]
            voice_data = data[10][1]
            temperature = data[10][2]
            item = EmotionData(em_angry=em_angry,
                               em_disgusted=em_disgusted,
                               em_fearful=em_fearful,
                               em_happy=em_happy,
                               em_sad=em_sad,
                               em_surprised=em_surprised,
                               em_neutral=em_neutral,
                               em_contempt=em_contempt,
                               create_time=create_time,
                               inquest_uuid=inquest_uuid,
                               heart_rate=heart_rate,
                               temperature=temperature,
                               voice_data=voice_data)
            items_obj.append(item)
        try:
            session.add_all(items_obj)
            session.commit()
            session.close()
        except Exception as e:
            session.rollback()
            session.close()
            LOG.error("Emotion_Data_add_items_opt %s" % str(e))
            return ret
        return ret

    @staticmethod
    def get_page_data(page_num, page_size):
        ret = None
        conn = sqlite3.connect(DB_DATA_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT *  from emotion_data order by id desc LIMIT ? OFFSET ? ",
                           (page_size, (page_num - 1) * page_size))
            ret = cursor.fetchall()
        except Exception as e:
            LOG.error("Emotion_Data_get_page_data %s" % str(e))
        cursor.close()
        conn.close()
        return ret

    @staticmethod
    def get_data_by_time(inquest_uuid, time_start, time_end):
        ret = None
        conn = sqlite3.connect(DB_DATA_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT *  from emotion_data WHERE inquest_uuid = ? "
                           "AND create_time > ? AND create_time <= ? ",
                           (inquest_uuid, time_start, time_end))
            ret = cursor.fetchall()
        except Exception as e:
            LOG.error("EmotionData_get_data_by_time %s" % str(e))
        cursor.close()
        conn.close()
        return ret

    @staticmethod
    def get_all():
        ret = None
        session = db_session()
        try:
            records = session.query(EmotionData).all()
            if records != []:
                ret = records
            session.close()
        except Exception as e:
            session.close()
            LOG.error("get_all %s" % str(e))
            return ret
        return ret

    @staticmethod
    def get_data_num(uuid):
        ret = None
        session = db_session()
        try:
            data_counter = session.query(func.count(EmotionData.id)).filter_by(inquest_uuid=uuid).one()
            if data_counter is not None:
                ret = data_counter
            session.close()
        except Exception as e:
            session.close()
            LOG.error("get data num %s" % str(e))
            return ret
        return ret

    @staticmethod
    def get_emotion_data(uuid):
        ret = None
        session = db_session()
        try:
            # {0: '综合', 1: u'平和', 2: u'高兴', 3: u'轻蔑', 4: u'厌恶', 5: u'惊讶', 6: u'伤心',  7: u'害怕', 8: u'生气'}
            data = session.query(
                EmotionData.em_composite,
                EmotionData.em_neutral,
                EmotionData.em_happy,
                EmotionData.em_contempt,
                EmotionData.em_disgusted,
                EmotionData.em_surprised,
                EmotionData.em_sad,
                EmotionData.em_fearful,
                EmotionData.em_angry,
                EmotionData.create_time,
                EmotionData.question_uuid).filter_by(inquest_uuid=uuid).order_by(EmotionData.create_time).all()
            if data is not None and len(data) > 0:
                ret = data
            session.close()
        except Exception as e:
            session.close()
            LOG.error("get emotion data %s" % str(e))
            return ret
        return ret

    @staticmethod
    def get_emotion_data_by_time(uuid, start_time, end_time):
        ret = None
        session = db_session()
        try:
            data = session.query(
                EmotionData.em_composite,
                EmotionData.em_neutral,
                EmotionData.em_happy,
                EmotionData.em_contempt,
                EmotionData.em_disgusted,
                EmotionData.em_surprised,
                EmotionData.em_sad,
                EmotionData.em_fearful,
                EmotionData.em_angry,
                EmotionData.create_time,
                EmotionData.question_uuid).filter(
                and_(EmotionData.inquest_uuid == uuid, between(EmotionData.create_time, start_time, end_time))) \
                .order_by(EmotionData.create_time).all()

            if data is not None and len(data) > 0:
                ret = data
            session.close()
        except Exception as e:
            session.close()
            LOG.error("get emotion data by time %s" % str(e))
            return ret
        return ret

    @staticmethod
    def get_data_by_inquest_uuid(inquest_uuid):
        ret = []
        conn = sqlite3.connect(DB_DATA_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM emotion_data WHERE inquest_uuid = ?", (inquest_uuid,))
            ret = cursor.fetchall()
        except Exception as e:
            LOG.error("emotion_warn_every_time %s" % str(e))
        cursor.close()
        conn.close()
        return ret


class InquestRecord(Base):
    """  审讯记录  """

    __tablename__ = 'inquest_record'
    id = Column(Integer, primary_key=True)
    inquest_uuid = Column(String, default="")
    create_time = Column(FLOAT)
    inquest_start_time = Column(FLOAT)
    inquest_end_time = Column(FLOAT)
    inquest_video_file_path = Column(String)
    ask_name = Column(String)
    be_ask_name = Column(String)
    be_ask_id_number = Column(String)
    inquest_type = Column(Integer)
    inquest_person_id = Column(Integer)
    report_info = Column(String)
    report_path = Column(String, default="")
    case_number = Column(String)
    case_type = Column(String)
    bilu_path = Column(String)
    classification = Column(String)
    alarmNum = Column(Integer, default=0)
    id_type = Column(Integer)

    @staticmethod
    def add_opt(uuid, video_file_path="", ask_name="", be_ask_name="", be_ask_id_number="", inquest_type=0,
                inquest_person_id=0, report_info="", case_number="", case_type="", bilu_path="",
                classification='', alarmNum=0, id_type=0):

        """
        :param uuid: 审讯uuid
        :param video_file_path: 审讯录像文件路径
        :param ask_name: 问询人姓名
        :param be_ask_name: 被询人姓名
        :param be_ask_id_number: 被询人身份证号
        :param inquest_type: 审讯类型  0：普通模式， 1：标准模式
        :param inquest_person_id: 被审讯人的id
        :param report_info: 审讯报告信息
        :param alarmNum: 告警次数
        :param id_type 证件类型
        :return: id 主键索引
        """
        session = db_session()
        try:
            new_report_log = InquestRecord(
                inquest_uuid=uuid,
                create_time=time.time(),
                inquest_start_time=time.time(),
                inquest_video_file_path=video_file_path,
                ask_name=ask_name,
                be_ask_name=be_ask_name,
                be_ask_id_number=be_ask_id_number,
                inquest_type=inquest_type,
                inquest_person_id=inquest_person_id,
                report_info=report_info,
                case_number=case_number,
                case_type=case_type,
                bilu_path=bilu_path, classification=classification, alarmNum=alarmNum, id_type=id_type)
            session.add(new_report_log)
            session.commit()
            report_id = new_report_log.id
            session.close()
        except Exception as e:
            session.rollback()
            LOG.error("add_opt %s" % str(e))
            return None
        return report_id

    @staticmethod
    def get_inquest_time(uuid):
        session = db_session()
        try:
            records = session.query(InquestRecord.inquest_start_time, InquestRecord.inquest_end_time)\
                .filter(InquestRecord.inquest_uuid==uuid).all()
        except Exception as e:
            LOG.error("get inquest time error： uuid ==%s" % uuid)
            return None
        # 返回全程时间
        block_time = records[0][1] - records[0][0]
        return block_time

    @staticmethod
    def get_all_record_filter(*args, **kwargs):
        ret = []
        session = db_session()
        try:
            date = kwargs.get('date', '')
            filter_list = []
            if date:
                date_filter = InquestRecord.create_time.ilike('%' + date + '%')
                filter_list.append(date_filter)
            if len(filter_list) == 0:
                records = session.query(InquestRecord).filter(not_(InquestRecord.inquest_end_time is None)).order_by(
                    InquestRecord.id.desc()).all()
            else:
                records = session.query(InquestRecord).filter(
                    and_(filter_list[0], not_(InquestRecord.inquest_end_time is None))) \
                    .order_by(InquestRecord.id.desc()).all()
            session.close()
            if records is not []:
                ret = records
        except Exception as e:
            session.rollback()
            LOG.error("get_all_record_filter %s" % str(e))
            return ret
        return ret

    @staticmethod
    def get_no_attachment_url_filter():
        conn = sqlite3.connect(DB_DATA_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT *  from inquest_record ORDER BY create_time DESC limit 1")
        ret = cursor.fetchone()
        # print(ret)
        if not ret[-7]:
            return False
        else:
            return True




    @staticmethod
    def get_record_by_filter(date_start=None, date_end=None, ask_name=None, be_ask_name=None, be_ask_id_number=None):
        """
        :param date_start: 时间戳 float
        :param date_end: 时间戳 float
        :param ask_name: 问询人姓名
        :param be_ask_name: 被询人姓名
        :param be_ask_id_number: 被询人身份证号
        :return: tuple对象的list
        """
        ret = []
        conn = sqlite3.connect(DB_DATA_PATH)
        cursor = conn.cursor()
        try:
            if date_start is None:
                if ask_name is None:
                    if be_ask_name is None:
                        if be_ask_id_number is None:
                            cursor.execute("SELECT *  from inquest_record WHERE inquest_end_time is NOT ? "
                                           "ORDER BY create_time DESC ", (None,))
                        else:
                            cursor.execute("SELECT *  from inquest_record WHERE inquest_end_time is NOT ? "
                                           "AND be_ask_id_number LIKE ? ORDER BY create_time DESC ",
                                           (None, be_ask_id_number + '%'))
                    else:
                        if be_ask_id_number is None:
                            cursor.execute("SELECT *  from inquest_record WHERE inquest_end_time is NOT ? "
                                           "AND be_ask_name LIKE ? ORDER BY create_time DESC ",
                                           (None, be_ask_name + '%'))
                        else:
                            cursor.execute("SELECT *  from inquest_record WHERE inquest_end_time is NOT ? "
                                           "AND be_ask_name LIKE ? AND be_ask_id_number LIKE ? "
                                           "ORDER BY create_time DESC ",
                                           (None, be_ask_name + '%', be_ask_id_number + '%'))
                else:
                    if be_ask_name is None:
                        if be_ask_id_number is None:
                            cursor.execute("SELECT *  from inquest_record WHERE inquest_end_time is NOT ? "
                                           "AND ask_name LIKE ? ORDER BY create_time DESC ", (None, ask_name + '%'))
                        else:
                            cursor.execute("SELECT *  from inquest_record WHERE inquest_end_time is NOT ? "
                                           "AND ask_name LIKE ? AND be_ask_id_number LIKE ? ORDER BY create_time DESC ",
                                           (None, ask_name + '%', be_ask_id_number + '%'))
                    else:
                        if be_ask_id_number is None:
                            cursor.execute("SELECT *  from inquest_record WHERE inquest_end_time is NOT ? "
                                           "AND ask_name LIKE ? AND be_ask_name LIKE ? ORDER BY create_time DESC ",
                                           (None, ask_name + '%', be_ask_name + '%'))
                        else:
                            cursor.execute("SELECT *  from inquest_record WHERE inquest_end_time is NOT ? "
                                           "AND ask_name LIKE ? AND be_ask_name LIKE ? AND be_ask_id_number LIKE ? "
                                           "ORDER BY create_time DESC ",
                                           (None, ask_name + '%', be_ask_name + '%', be_ask_id_number + '%'))
            else:
                if ask_name is None:
                    if be_ask_name is None:
                        if be_ask_id_number is None:
                            cursor.execute("SELECT *  from inquest_record WHERE create_time >= ? AND create_time < ? "
                                           "AND inquest_end_time is NOT ? ORDER BY create_time DESC",
                                           (date_start, date_end, None))
                        else:
                            cursor.execute("SELECT *  from inquest_record WHERE create_time >= ? AND create_time < ? "
                                           "AND inquest_end_time is NOT ? AND be_ask_id_number LIKE ?"
                                           "ORDER BY create_time DESC",
                                           (date_start, date_end, None, be_ask_id_number + '%'))
                    else:
                        if be_ask_id_number is None:
                            cursor.execute("SELECT *  from inquest_record WHERE create_time >= ? AND create_time < ? "
                                           "AND inquest_end_time is NOT ? AND be_ask_name LIKE ? "
                                           "ORDER BY create_time DESC", (date_start, date_end, None, be_ask_name + '%'))
                        else:
                            cursor.execute("SELECT *  from inquest_record WHERE create_time >= ? AND create_time < ? "
                                           "AND inquest_end_time is NOT ? AND be_ask_name LIKE ? "
                                           "AND be_ask_id_number LIKE ? ORDER BY create_time DESC",
                                           (date_start, date_end, None, be_ask_name + '%', be_ask_id_number + '%'))
                else:
                    if be_ask_name is None:
                        if be_ask_id_number is None:
                            cursor.execute("SELECT *  from inquest_record WHERE create_time >= ? AND create_time < ? "
                                           "AND inquest_end_time is NOT ? AND ask_name LIKE ? "
                                           "ORDER BY create_time DESC", (date_start, date_end, None, ask_name + '%'))
                        else:
                            cursor.execute("SELECT *  from inquest_record WHERE create_time >= ? AND create_time < ? "
                                           "AND inquest_end_time is NOT ? AND ask_name LIKE ? "
                                           "AND be_ask_id_number LIKE ? ORDER BY create_time DESC",
                                           (date_start, date_end, None, ask_name + '%', be_ask_id_number + '%'))
                    else:
                        if be_ask_id_number is None:
                            cursor.execute("SELECT *  from inquest_record WHERE create_time >= ? AND create_time < ? "
                                           "AND inquest_end_time is NOT ? AND ask_name LIKE ? AND be_ask_name LIKE ? "
                                            "ORDER BY create_time DESC",
                                           (date_start, date_end, None, ask_name + '%', be_ask_name + '%'))
                        else:
                            cursor.execute("SELECT *  from inquest_record WHERE create_time >= ? AND create_time < ? "
                                           "AND inquest_end_time is NOT ? AND ask_name LIKE ? AND be_ask_name LIKE ? "
                                           "AND be_ask_id_number LIKE ? ORDER BY create_time DESC",
                                           (date_start, date_end, None, ask_name + '%', be_ask_name + '%',
                                            be_ask_id_number + '%'))
            ret = cursor.fetchall()
        except Exception as e:
            LOG.error("Emotion_Data_get_page_data %s" % str(e))
        cursor.close()
        conn.close()
        return ret

    @staticmethod
    def update_opt(inquest_id, person_id):
        """
        更新审讯结束时间
        is_end: wether or not set the end_time
        """

        ret = None
        session = db_session()
        try:
            update_report_log = session.query(InquestRecord).filter_by(id=inquest_id).first()
            update_report_log.inquest_end_time = time.time()
            update_report_log.inquest_person_id = person_id
            session.commit()
            session.close()
        except Exception as e:
            session.close()
            LOG.error("get_user_opt_all %s" % str(e))
            return ret
        session.close()
        ret = update_report_log
        return ret

    @staticmethod
    def update_opt_bilupath(inquest_id, path):
        """
        is_end: wether or not set the end_time
        """

        ret = None
        session = db_session()
        try:
            update_report_log = session.query(InquestRecord).filter_by(id=inquest_id).first()
            update_report_log.bilu_path = path
            session.commit()
            session.close()
        except Exception as e:
            session.close()
            LOG.error("get_user_opt_all %s" % str(e))
            return ret
        session.close()
        ret = update_report_log
        return ret

    @staticmethod
    def get_user_opt_all(inquest_person_id):
        session = db_session()
        ret = None
        try:
            user_report = session.query(InquestRecord).filter_by(inquest_person_id=inquest_person_id).order_by(
                InquestRecord.id.desc()).all()
        except Exception as e:
            session.rollback()
            session.close()
            LOG.error("get_user_opt_all %s" % str(e))
            return ret
        session.close()
        ret = user_report
        return ret

    @staticmethod
    def get_report_by_person_id(inquest_person_id):
        ret = []
        conn = sqlite3.connect(DB_DATA_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT *  from inquest_record WHERE inquest_end_time is NOT ? "
                           "AND inquest_person_id = ? ORDER BY create_time DESC ",
                           (None, inquest_person_id))
            ret = cursor.fetchall()
        except Exception as e:
            LOG.error("get_report_by_person_id %s" % str(e))
        cursor.close()
        conn.close()
        return ret

    @staticmethod
    def get_opt_all_by_id(inquest_id):
        session = db_session()
        ret = None
        try:
            user_report = session.query(InquestRecord).filter_by(id=inquest_id).first()
        except Exception as e:
            session.rollback()
            session.close()
            LOG.error("get_user_opt_all %s" % str(e))
            return ret
        session.close()
        ret = user_report
        return ret

    @staticmethod
    def update_opt_report_path(inquest_id, report_path):
        """
        更新审讯报告字段
        is_end: wether or not set the end_time
        """

        ret = None
        session = db_session()
        try:
            update_report_log = session.query(InquestRecord).filter_by(id=inquest_id).first()
            update_report_log.report_path = report_path
            session.commit()
            session.close()
        except Exception as e:
            session.close()
            LOG.error("get_user_opt_all %s" % str(e))
            return ret
        session.close()
        return ret

    @staticmethod
    def update_opt_by_inquest_uuid(inquest_uuid, **args):
        ask_name = args.get('ask_name')
        be_ask_name = args.get('be_ask_name')
        be_ask_id_num = args.get('be_ask_id_num')
        report_info = args.get('report_info')
        alarmNum = json.loads(report_info).get('alarmNum', 0)
        ret = None
        session = db_session()
        try:
            update_report_log = session.query(InquestRecord).filter_by(inquest_uuid=inquest_uuid).first()
            alarm_count = session.query(QuestionRecord).filter(
                and_(QuestionRecord.total_status != "配合", QuestionRecord.inquest_uuid == inquest_uuid,
                     QuestionRecord.is_del == False))
            if alarmNum!= alarm_count.count():
                alarmNum = alarm_count.count()
                LOG.warn("报警数量不一致 %s %s"%(alarmNum,len(config.alarm_data_count)))
                config.alarm_data_count.clear()
                for alarm in alarm_count:
                    data = {
                        "uuid": alarm.inquest_uuid,
                        'time_node': alarm.inquest_uuid,
                        'case_type': alarm.case_type,
                        'suspicious_value': alarm.suspicious_value,
                        'body_status': alarm.body_status.replace("、", " "),
                        'emotion_status': alarm.emotion_status,
                        'total_status': alarm.total_status,
                        'inquest_result': alarm.inquest_result,
                        'video_path': alarm.video_path.replace("\\", "/"),
                        'emotion_degree': alarm.emotion_degree,
                        'emotion_degree_count': alarm.emotion_degree,
                        'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(alarm.start_time)),
                        'timeStamp': alarm.timeStamp
                    }
                    config.alarm_data_count.append(data)
            if ask_name is not None:
                update_report_log.ask_name = ask_name
            if be_ask_name is not None:
                update_report_log.be_ask_name = be_ask_name
            if be_ask_id_num is not None:
                update_report_log.be_ask_id_num = be_ask_id_num
            if report_info is not None:
                update_report_log.report_info = report_info
                update_report_log.alarmNum = alarmNum
            session.commit()
            session.close()
        except Exception as e:
            session.close()
            LOG.error("get_user_opt_all %s" % str(e))
            return ret
        session.close()
        ret = update_report_log
        return ret

    @staticmethod
    def delete_record_by_uuid(uuid):
        """
        :param uuid: 审讯记录 uuid
        :return: -1: 删除失败， 0：删除成功
        """
        ret = 0
        conn = sqlite3.connect(DB_DATA_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE from inquest_record WHERE inquest_uuid IS ? ", (uuid,))
            conn.commit()
        except Exception as e:
            LOG.error("delete_record_by_uuid %s" % str(e))
            conn.rollback()
            ret = -1
        cursor.close()
        conn.close()
        return ret

    @staticmethod
    def delete_record_by_id(id):
        """
        :param uuid: 审讯记录 uuid
        :return: -1: 删除失败， 0：删除成功
        """
        ret = 0
        conn = sqlite3.connect(DB_DATA_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE from inquest_record WHERE id is ?", (id,))
            conn.commit()
        except Exception as e:
            LOG.error("delete_record_by_id %s" % str(e))
            conn.rollback()
            ret = -1
        cursor.close()
        conn.close()
        return ret

    @staticmethod
    def get_one_record(uuid):
        """
        :param uuid: 审讯记录 uuid
        """
        ret = []
        conn = sqlite3.connect(DB_DATA_PATH)
        cursor = conn.cursor()
        try:
            if uuid is None:
                cursor.execute("SELECT *  from inquest_record WHERE inquest_uuid IS ? ", (uuid,))
            ret = cursor.fetchone()
        except Exception as e:
            LOG.error("Emotion_Data_get_page_data %s" % str(e))
        cursor.close()
        conn.close()
        return ret


class QuestionRecord(Base):
    # {1: {"question_title": "你的姓名？",
    #      "total_status": "配合",
    #      "body_status": "声强正常、心率正常、体温正常",
    #      "emotion_status": "平和、伤心、害怕",
    #      "emotion": [30, 5, 10, 10, 10, 20, 10, 5],
    #      "emotion_show": "正常",
    #      "voice": [10, 20, 15, 20, 15, 20],
    #      "voice_show": "正常",
    #      "heart_rate": [5, 25, 20, 15, 20, 15],
    #      "heat_show": "正常",
    #      "clinical": [10, 20, 15, 20, 15, 20],
    #      "clinical_show": "正常",
    #      "General_Status": "配合"},

    """
    :parameter:inquest_uuid              => 审讯记录的uuid
    :parameter:question_uuid             => 审讯问题的uuid
    :parameter:question_text             => 审讯问题内容
    :parameter:body_status               => 当前问题所对应的体征状态
    :parameter:emotion_status            => 当前问题所对应的表情状态
    :parameter:total_status              => 嫌疑人状态
    :parameter:judgement_status          => 当前问题所对应的系统分析状态，0：错误 1：正确 2：无法判断
    :parameter:start_time                => 当前问题的起始时间
    :parameter:stop_time                 => 当前问题的终止时间
    :parameter:is_del                    => 当前问题的删除状态
    """
    __tablename__ = 'question_record'
    id = Column(Integer, primary_key=True, autoincrement=True)
    inquest_uuid = Column(String, default='')
    question_uuid = Column(String, default='')
    question_text = Column(String, default='')
    body_status = Column(String, default='')
    emotion_status = Column(String, default='')
    total_status = Column(String, default='')
    judgement_status = Column(Integer, default=1)
    is_del = Column(Boolean, default=False)
    emotion_count = Column(String, default='')
    heart_count = Column(String, default='')
    emotion_show = Column(String, default='')
    heart_show = Column(String, default='')
    # temperature_count = Column(String, default='')
    # voice_count = Column(String, default='')
    start_time = Column(FLOAT)
    stop_time = Column(FLOAT)
    time_node = Column(String, default='')
    case_type = Column(String, default='')
    inquest_result = Column(String, default='')
    suspicious_value = Column(Integer, default=0)
    answer = Column(String, default='')
    video_path = Column(String, default='')
    emotion_degree = Column(String, default='')
    emotion_degree_count = Column(Integer, default=0)
    timeStamp = Column(Integer, default=0)

    @staticmethod
    def add_opt(inquest_uuid, question_uuid, question_text,
                body_status, emotion_status, total_status, emotion_count, heart_count, emotion_show, heart_show,
                start_time, stop_time, time_node, case_type, inquest_result, suspicious_value, answer, video_path,
                emotion_degree, emotion_degree_count, timeStamp):
        ret = []
        session = db_session()
        try:
            add_question = QuestionRecord(inquest_uuid=inquest_uuid,
                                          question_uuid=question_uuid,
                                          question_text=question_text,
                                          body_status=body_status,
                                          emotion_status=emotion_status,
                                          total_status=total_status,
                                          emotion_count=emotion_count,
                                          heart_count=heart_count,
                                          emotion_show=emotion_show,
                                          heart_show=heart_show,
                                          start_time=start_time,
                                          stop_time=stop_time,
                                          time_node=time_node,
                                          case_type=case_type,
                                          inquest_result=inquest_result,
                                          suspicious_value=suspicious_value,
                                          answer=answer,
                                          video_path=video_path,
                                          emotion_degree=emotion_degree,
                                          emotion_degree_count=emotion_degree_count,
                                          timeStamp=timeStamp
                                          )
            session.add(add_question)
            session.commit()
            session.close()
        except Exception as e:
            session.rollback()
            LOG.error("add_opt %s" % str(e))
            return ret
        ret = True
        return ret

    @staticmethod
    def get_objects_by_inquest_uuid(inquest_uuid):
        ret = []
        session = db_session()
        try:
            ret = session.query(QuestionRecord).filter_by(inquest_uuid=inquest_uuid, is_del=False).all()
        except Exception as e:
            session.rollback()
            LOG.error("get_objects_by_inquest_uuid %s" % str(e))
            return ret
        return ret

    @staticmethod
    def get_objects_by_inquest_uuid_start_time(inquest_uuid, pageNum=None, pageSize=None):
        """
        :param inquest_uuid:审讯uuid
        :param pageNum:当前页面
        :param pageSize:页面数量
        :return: result
        """
        ret = []
        count = 0
        session = db_session()
        # 查询数据库数量
        try:
            count = session.query(QuestionRecord).filter(
                and_(QuestionRecord.total_status != "配合", QuestionRecord.inquest_uuid == inquest_uuid,
                     QuestionRecord.is_del == False)).count()
        except Exception as e:
            session.rollback()
            LOG.error("get_objects_by_inquest_uuid %s" % str(e))
            return count,ret

        if pageNum and pageSize:
            try:
                ret = session.query(QuestionRecord).filter(
                    and_(QuestionRecord.total_status != "配合", QuestionRecord.inquest_uuid == inquest_uuid,
                         QuestionRecord.is_del == False)).limit(pageSize).offset((pageNum-1)*pageSize)
            except Exception as e:
                session.rollback()
                LOG.error("get_objects_by_inquest_uuid %s" % str(e))
                return count, ret
        else:
            try:
                ret = session.query(QuestionRecord).filter(
                    and_(QuestionRecord.total_status != "配合", QuestionRecord.inquest_uuid == inquest_uuid,
                         QuestionRecord.is_del == False)).all()
            except Exception as e:
                session.rollback()
                LOG.error("get_objects_by_inquest_uuid %s" % str(e))
                return count, ret
        return count, ret


    @staticmethod
    def del_opt_by_id(id):
        session = db_session()
        ret = False
        try:
            per = session.query(QuestionRecord).filter_by(id=id).first()
            per.is_del = True
            session.commit()
            session.close()
        except Exception as e:
            session.close()
            LOG.error("del_opt_by_id %s" % str(e))
            return ret
        ret = True
        return ret

    @staticmethod
    def update_opt_by_id(id, judgement_status):
        session = db_session()
        ret = False
        try:
            per = session.query(QuestionRecord).filter_by(id=id, is_del=False).first()
            per.judgement_status = judgement_status
            session.commit()
            session.close()
        except Exception as e:
            session.close()
            LOG.error("update_opt_by_id %s" % str(e))
            return ret
        ret = True
        return ret


if __name__ == "__main__":
    import os

    os.chdir("../../")
    print(os.getcwd())
    init_data_database()
    # try:
    #     emotion_data = EmotionData.get_data_by_time(123456, 1234567)
    #     heart_rate_data = HeartRateData.get_data_by_time(123456, 1234567)
    #     print("type(emotion_data)={}, type(heart_rate_data)={}, len(emotion_data)={}, len(heart_rate_data)={}".
    #           format(type(emotion_data), type(heart_rate_data), len(emotion_data), len(heart_rate_data)))
    #     if isinstance(emotion_data, list) and len(emotion_data) > 0:
    #         print("emotion_data[0]={}, heart_rate_data[0]={}".format(emotion_data[0], heart_rate_data[0]))
    # except Exception as e:
    #     print(e)
