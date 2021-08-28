# coding: utf-8
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

app = Flask(__name__)


# 此程序只能运行单线程

class Config:
    """配置参数"""
    config_env = os.environ.get('SPIDER_WEB_ENV', 'dev').lower()
    # 设置连接数据库的URL
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://%s:%s@%s:31306/%s?charset=utf8mb4' % (
    #     'officialwebsite', 'Kf8EfwMFxEbDmeL6', '127.0.0.1', 'officialwebsite')

    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://%s:%s@%s:3306/%s?charset=utf8mb4' % (
        'root', '123456', '192.168.1.100', 'test')

    # 设置sqlalchemy自动更跟踪数据库
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    # 查询时会显示原始SQL语句
    app.config['SQLALCHEMY_ECHO'] = False
    # 禁止自动提交数据处理
    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = False

    # 体验版
    CRAWL_CHANNEL_MAXCOUNT = 11  # 采集群组数量
    CRAWL_USER_MAXCOUNT = 6  # 采集群友数量
    SEDN_CHANNEL_LIMIT = 6  # 发送群组数
    SEDN_USER_LIMIT = 6  # 发送群友数


# 读取配置
app.config.from_object(Config)

# 创建数据库sqlalchemy工具对象
db = SQLAlchemy(app)

loop = asyncio.get_event_loop()
thread_pool = ThreadPoolExecutor(10)

from views import *

if __name__ == '__main__':
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(8000, address='0.0.0.0')  # flask默认的端口
    IOLoop.current().start()
