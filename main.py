# coding: utf-8
import logging
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from logging.handlers import TimedRotatingFileHandler

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

app = Flask(__name__)


# 此程序只能运行单线程

class Config(object):
    """配置参数"""
    config_env = os.environ.get('SPIDER_WEB_ENV', 'dev').lower()
    # 设置连接数据库的URL
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://%s:%s@%s:31306/%s' % (
        'officialwebsite', 'Kf8EfwMFxEbDmeL6', '47.241.211.163', 'officialwebsite')

    # 设置sqlalchemy自动更跟踪数据库
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    # 查询时会显示原始SQL语句
    app.config['SQLALCHEMY_ECHO'] = False
    # 禁止自动提交数据处理
    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = False


def add_logger(_app):
    logging_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)s - %(message)s'
    )
    handler = TimedRotatingFileHandler(
        "logs/app/log.log",
        when="D",
        interval=1,
        backupCount=15,
        encoding="UTF-8",
        delay=False,
        utc=True
    )
    handler.setFormatter(logging_format)
    handler.setLevel(logging.DEBUG)
    _app.logger.setLevel(logging.DEBUG)
    _app.logger.addHandler(handler)


# 读取配置
app.config.from_object(Config)

# 创建数据库sqlalchemy工具对象
db = SQLAlchemy(app)
add_logger(app)

loop = asyncio.get_event_loop()
thread_pool = ThreadPoolExecutor(10)

from views import *

if __name__ == '__main__':
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(8800, address='0.0.0.0')  # flask默认的端口
    IOLoop.current().start()
