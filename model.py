# coding: utf-8
from sqlalchemy import BigInteger, Column, DateTime, Integer, String, text, Text
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.ext.declarative import declarative_base

from main import db

Base = declarative_base()
metadata = Base.metadata


class Collectionfriend(Base):
    __tablename__ = 'collectionfriend'

    id = Column(Integer, primary_key=True)
    username = Column(String(255))
    groupmember_id = Column(Integer)
    create_id = Column(Integer)
    create_time = Column(DateTime)
    first_name = Column(String(255))
    last_name = Column(String(255))
    access_hash = Column(String(255))


class Collectiongroup(Base):
    __tablename__ = 'collectiongroup'

    id = Column(Integer, primary_key=True)
    group_name = Column(VARCHAR(255))
    group_url = Column(VARCHAR(255))
    group_id = Column(Integer)
    create_id = Column(Integer)
    create_time = Column(DateTime)


class TLog(Base):
    __tablename__ = 't_logs'

    id = Column(Integer, primary_key=True)
    message_type = Column(VARCHAR(255), nullable=False)
    message_content = Column(Text)
    client_phone = Column(VARCHAR(255))
    create_time = Column(DateTime, nullable=False)
    create_id = Column(Integer, nullable=False)

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            print(e)
            db.session.rallback()


class TMember(Base):
    __tablename__ = 't_member'

    id = Column(BigInteger, primary_key=True, comment='Id')
    username = Column(VARCHAR(200), comment='账号')
    pwd = Column(VARCHAR(200), comment='密码')
    create_time = Column(DateTime, comment='创建时间')
    status = Column(Integer, server_default=text("'0'"), comment='状态(0:正常;1:禁用)')
    is_deleted = Column(Integer, server_default=text("'0'"), comment='是否删除(0:否;1:是)')
    is_activation = Column(Integer, server_default=text("'0'"), comment='是否激活(0:未激活;1:已激活)')


class TMemberInfo(Base):
    __tablename__ = 't_member_info'

    id = Column(BigInteger, primary_key=True, comment='id')
    member_id = Column(BigInteger, comment='会员ID')
    package_id = Column(BigInteger, comment='套餐ID')
    package_device_num = Column(BigInteger, comment='设备数')
    create_time = Column(DateTime, comment='创建时间')
    expiration_time = Column(DateTime, comment='过期时间')
    status = Column(Integer, server_default=text("'0'"), comment='状态(0:有效;1:无效)')


__all__ = [
    'Collectionfriend',
    'Collectiongroup',
    'TLog',
    'TMember',
    'TMemberInfo',
]
