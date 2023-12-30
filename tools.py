from sqlalchemy import create_engine, Column, Integer, String, DateTime, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.mysql import LONGTEXT
from datetime import datetime
from threading import local
from sqlalchemy.orm import Session, sessionmaker
import time, hashlib, random, json, requests

# 创建数据库连接
engine = create_engine('mysql+pymysql://root:password@IP/database')

# 创建映射模型
Base = declarative_base()

# 创建线程本地存储对象
local_data = local()


class User(Base):
    """用户表"""
    __tablename__ = "user"
    # 用户id
    id = Column(Integer(), unique=True, primary_key=True, autoincrement=True)
    # 用户名
    name = Column(String(128))
    # 邀请码
    invite_lj = Column(String(128))
    # 余额
    balance = Column(Integer())
    # 状态
    status = Column(String(96))
    # 第一名字
    firstname = Column(String(96))
    # 注册时间
    time = Column(DateTime(), default=datetime.now())
    # tg的id
    t_id = Column(String(96))
    # 会员标识
    vip = Column(String(96))
    # 拉新人数
    low = Column(Integer(), default=0)

    # 将映射与数据库引擎绑定
    __table_args__ = {'mysql_engine': 'InnoDB'}


class Recharge(Base):
    """充值表"""
    __tablename__ = "recharge"
    # id
    id = Column(Integer(), unique=True, primary_key=True, autoincrement=True)
    # 充值金额
    money = Column(String(256))
    # 状态 0失败，1成功，2待支付，3已超时，4已取消
    status = Column(Integer())
    # 转账钱包
    from_address = Column(String(256))
    # 创建时间
    create_time = Column(DateTime(), default=datetime.now())
    # tg的id
    t_id = Column(String(96))
    # 用户id
    user_id = Column(Integer())
    # 第一名字
    firstname = Column(String(96))
    # 是否已告知用户 0未告知，1已告知
    is_send = Column(Integer(), default=0)

    # 将映射与数据库引擎绑定
    __table_args__ = {'mysql_engine': 'InnoDB'}


class Record(Base):
    """需求审核表"""
    __tablename__ = "record"
    # id
    id = Column(Integer(), unique=True, primary_key=True, autoincrement=True)
    # 需求内容
    values = Column(LONGTEXT)
    # 创建时间
    create_time = Column(DateTime(), default=datetime.now())
    # 状态 0失败，1成功，2待审核
    status = Column(Integer())
    # tg的id
    t_id = Column(String(96))
    # 用户id
    user_id = Column(Integer())
    # 第一名字
    firstname = Column(String(96))

    # 将映射与数据库引擎绑定
    __table_args__ = {'mysql_engine': 'InnoDB'}


class Wallet(Base):
    """钱包记录表"""
    __tablename__ = 'wallet'
    # 订单id
    id = Column(String(256), unique=True, primary_key=True)
    # 订单金额
    money = Column(String(256))
    # 创建时间
    create_time = Column(DateTime())
    # 发起人
    sender = Column(String(256))
    # 接收人
    recipient = Column(String(256))
    # 类型
    typestr = Column(String(48), default="USDT")
    # 插入时间
    insert_time = Column(DateTime(), default=datetime.now())

    # 将映射与数据库引擎绑定
    __table_args__ = {'mysql_engine': 'InnoDB'}


def get_session():
    if not hasattr(local_data, 'session') or not local_data.session.is_active:
        local_data.session = Session()
    return local_data.session


def timestr_to_time(timestr):
    """时间戳转换为时间字符串"""
    try:
        timestr = int(timestr)
    except Exception as e:
        print(e)
        return 0
    try:
        # 获取年份
        res = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestr))
    except Exception as e:
        return 0
    return res


def md5(target):  # md5加密
    hash_object = hashlib.md5("%$^ASGJZAAss&*(z".encode("utf-8"))
    hash_object.update(target.encode("utf-8"))
    return hash_object.hexdigest()


def get_code():
    now = str(time.time())
    result = now.replace(".", "")
    for i in range(30):
        random_str = random.choice('0123456789abcdefghijklmnopqrstuvwxyzQWERTYUIOPASDFGHJKLZXCVBNM!@#$%^&*()_+')
        result += random_str
    result = result[:30]
    result = md5(result)[:10]
    return result


def register(update):
    user_id = update.message.from_user["id"]
    username = update.message.from_user["username"]
    first_name = update.message.from_user["first_name"]
    session = get_session()
    try:
        user = session.query(User).filter_by(t_id=user_id).first()
    except Exception as e:
        print(e)
        print("这里查询出错了！！")
        user = None
    if user:
        return user
    # 生成一个自己的邀请码
    code = get_code()
    try:
        new_user = User(name=username, invite_lj=code, t_id=user_id, firstname=first_name, status=1, balance=0)
        session.add(new_user)
        session.commit()
    except Exception as e:
        session.rollback()
        print(e)
        print("注册失败")
        return None
    return user


def get_order_id():
    now = str(time.time())
    result = now.replace(".", "")
    for i in range(30):
        random_str = random.choice('0123456789abcdefghijklmnopqrstuvwxyzQWERTYUIOPASDFGHJKLZXCVBNM!@#$%^&*()_+')
        result += random_str
    result = result[:30]
    result = md5(result)
    return result


# 创建表
Base.metadata.create_all(engine)
# 在映射配置类的最后将数据库引擎与 Base 类绑定
Base.metadata.bind = engine
# 创建会话工厂
Session = sessionmaker(bind=engine)
