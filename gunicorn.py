# coding: utf-8
import multiprocessing
import os

if not os.path.exists('gunicorn_logs'):
    os.mkdir('gunicorn_logs')

debug = True
preload_app = True
loglevel = 'info'
bind = '0.0.0.0:8000'
pidfile = 'gunicorn_logs/gunicorn.pid'
logfile = 'gunicorn_logs/debug.log'
errorlog = 'gunicorn_logs/error.log'
accesslog = 'gunicorn_logs/access.log'
timeout = 600

# 启动的进程数
# workers = multiprocessing.cpu_count() * 2 + 1
workers = 1
# worker_class = 'eventlet'

x_forwarded_for_header = 'X-FORWARDED-FOR'
