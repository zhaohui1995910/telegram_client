# -*- coding: utf-8 -*-
# @Time    : 2021/8/26 8:43
# @Author  : 10867
# @FileName: views.py
# @Software: PyCharm
import re
import time
import asyncio
from datetime import datetime

from flask import request, current_app
from sqlalchemy import desc
from sqlalchemy.sql.expression import func

from main import app, db, loop, thread_pool
from model import *
import client

client_count = {}
client_map = {}


@app.route('/test')
def test_func():
    print(current_app.config.get('CRAWL_USER_MAXCOUNT'))

    a = request.args.get('kw')
    client_map[a] = a

    db.session.query(Collectionfriend).filter(
        Collectionfriend.create_id == int(1)
    ).order_by(
        func.rand()
    ).limit(10).all()
    #
    # user_list = [u.username for u in user_list]
    # app_log.info('记录日志views测试')
    # 同步
    # loop.run_until_complete(client.io_test(a))

    # 异步
    result = thread_pool.submit(client.io_test, *(a, 1,))
    print(result)

    return 'views'


@app.route('/')
def index():
    return 'Index Page'


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    user = db.session.query(TMember).filter(
        TMember.username == username
    ).first()

    if not user:
        return {'code': 200, 'msg': '没有找到用户', 'data': None}

    current_count = client_count.get(user.id, 0)

    user_info = db.session.query(TMemberInfo).filter(
        TMemberInfo.id == user.id
    ).first()

    if not user_info:
        return {'code': 200, 'msg': '没有找到用户信息', 'data': None}

    result_data = {
        'package_device_num': user_info.package_device_num,
        'current_count': current_count
    }

    if user:
        if user.pwd == password:
            return {'code': 200, 'msg': 'success', 'data': result_data}
        else:
            return {'code': 200, 'msg': '密码验证失败', 'data': result_data}
    else:
        return {'code': 200, 'msg': '没有找到该用户', 'data': result_data}


@app.route('/sign_in')
def sign_in():
    """添加用户"""
    _member_id = request.args.get("member_id")
    _phone = request.args.get("phone")
    _api_id = request.args.get("api_key")
    _api_hash = request.args.get("api_hash")

    item = db.session.query(TMemberInfo).filter(
        TMemberInfo.member_id == _member_id
    ).first()

    if item:
        if client_count.get(_member_id, 0) >= item.package_device_num:
            TLog(
                message_type='sign_in',
                message_content='以到最大可登陆设备数',
                client_phone=_phone,
                create_time=datetime.now(),
                create_id=_member_id,
            ).save()
            return {
                'code': 200,
                'msg': '以到最大可登陆设备数' % _phone,
                'data': None
            }

    # 需要判断客户端是否已经存在
    if _phone in client_map:
        TLog(
            message_type='sign_in',
            message_content='设备已登陆',
            client_phone=_phone,
            create_time=datetime.now(),
            create_id=_member_id,
        ).save()
        return {'code': 200, 'msg': '%s 设别已登陆' % _phone, 'data': None}

    _client, status = loop.run_until_complete(client.sign_in(_phone, _api_id, _api_hash))

    if _client:
        client_map[_phone] = _client
        client_count[_member_id] = client_count.get(_member_id, 0) + 1

        TLog(
            message_type='sign_in',
            message_content='添加设备',
            client_phone=_phone,
            create_time=datetime.now(),
            create_id=_member_id,
        ).save()

    return {
        'code': 200,
        'msg': 'success',
        'data': {'status': status}
    }


@app.route('/sendCode')
def send_code():
    """发送验证码认证"""
    _phone = request.args.get("phone")
    code = request.args.get("code")

    _client = client_map.get(_phone)
    if _client is not None:
        loop.run_until_complete(client.send_code(_client, code))

        return {'code': 200, 'msg': 'success', 'data': None}
    else:
        return {'code': 200, 'msg': 'success', 'data': None}


@app.route("/getMe", methods=['GET'])
def get_me():
    """获取自己信息"""
    _phone = request.args.get("phone")
    _client = client_map[_phone]

    me = loop.run_until_complete(client.get_me(_client))
    print(me.stringify())

    return {'code': 200, 'msg': 'success', 'data': {'username': me.username, 'phone': me.phone}}


@app.route("/getDialogs", methods=['GET'])
def get_dialogs():
    """获取对话框"""
    _phone = request.args.get("phone")
    _client = client_map[_phone]

    dialogs_list = loop.run_until_complete(client.get_dialogs(_client))

    for dia in dialogs_list:
        print(dia)

    return {'code': 200, 'msg': 'success', 'data': None}


@app.route("/crawl/channel/username", methods=['GET'])
def spider_group_user():
    """采集群友"""
    _phone = request.args.get("phone")
    _url = request.args.get("url")
    _user_id = request.args.get("user_id")
    _client = client_map[_phone]

    crawl_user_list = loop.run_until_complete(client.spider_group_user(_client, _url))

    TLog(
        message_type='crawl_channel_username',
        message_content='采集群组用户共 %s 条' % len(crawl_user_list),
        client_phone=_phone,
        create_time=datetime.now(),
        create_id=_user_id
    ).save()

    user_list = db.session.query(Collectionfriend).filter(
        Collectionfriend.create_id == int(_user_id)
    ).all()

    user_id_list = [u.groupmember_id for u in user_list]

    crawl_user_maxcount = current_app.config.get('CRAWL_USER_MAXCOUNT')

    # 删除username为空的用户
    crawl_user_list = [user for user in crawl_user_list if user.username]

    for u in crawl_user_list[:crawl_user_maxcount]:

        if u.id in user_id_list:
            continue

        item = Collectionfriend()
        item.username = u.username
        item.first_name = u.first_name
        item.last_name = u.last_name
        item.access_hash = u.access_hash
        item.groupmember_id = u.id
        item.create_id = int(_user_id)
        item.create_time = datetime.now()

        db.session.add(item)

    db.session.commit()

    return_rsult = []
    for i in crawl_user_list[:crawl_user_maxcount]:
        if not i.username:
            continue

        return_rsult.append(i.username)

    return {'code': 200, 'msg': 'success', 'data': return_rsult}


@app.route("/user/list", methods=['GET'])
def get_user():
    """获取群友列表"""
    user_id = request.args.get("user_id")
    page = request.args.get("page")
    page_size = request.args.get("page_size")

    result = db.session.query(Collectionfriend).filter(
        Collectionfriend.create_id == int(user_id)
    ).limit(int(page_size)).offset((page - 1) * int(page_size)).all()

    return_rsult = []
    for i in result:
        item = {
            'username': i.username,
            'groupmemberid': i.groupmember_id,
        }
        return_rsult.append(item)

    return {'code': 200, 'msg': 'success', 'data': return_rsult}


@app.route("/crawl/channel/url", methods=['GET'])
def spider_group_url():
    """收集群组"""
    _user_id = request.args.get("user_id")
    _phone = request.args.get("phone")
    _client = client_map[_phone]

    msg_list = loop.run_until_complete(client.spider_group_url(_client))
    result = []

    group_list = db.session.query(Collectiongroup).filter(
        Collectiongroup.create_id == int(_user_id)
    ).all()

    group_url_list = [g.group_url for g in group_list]

    for msg in msg_list:
        content: str = msg.message
        content_list = content.split('\n\n')

        if len(content_list) != 3:
            continue

        title_list = re.findall('\d. (.*?)-', content_list[1])

        entities: list = msg.entities

        for i, t in enumerate(title_list):
            if '👥' in t:
                entity = entities[i + 1]
                url = entity.url
                if url in group_url_list:
                    continue

                result.append((t, url))

                item = Collectiongroup()
                # item.group_name = t.replace('👥', '')  # 因 '👥' 编码问题无法写入数据库
                item.group_url = url
                item.createtime = datetime.now()
                item.create_id = int(_user_id)
                db.session.add(item)

    crawl_channel_maxcount = current_app.config.get('CRAWL_CHANNEL_MAXCOUNT')
    for r in result[:crawl_channel_maxcount]:
        item = Collectiongroup()
        # item.group_name = t.replace('👥', '')  # 因 '👥' 编码问题无法写入数据库
        item.group_url = r[1]
        item.createtime = datetime.now()
        item.create_id = int(_user_id)
        db.session.add(item)

    db.session.commit()

    TLog(
        message_type='crawl_channel_url',
        message_content='采集群组 %s 条, 去重 %s 条' % (len(msg_list), (len(msg_list) - len(result[:crawl_channel_maxcount]))),
        client_phone=_phone,
        create_time=datetime.now(),
        create_id=_user_id
    ).save()

    return {'code': 200, 'msg': 'success', 'data': result}


@app.route("/channel/list", methods=['GET'])
def get_group():
    """获取群组列表"""
    user_id = request.args.get("user_id")
    page = request.args.get("page")
    page_size = request.args.get("page_size")

    result = db.session.query(Collectiongroup).filter(
        Collectiongroup.create_id == int(user_id)
    ).limit(int(page_size)).offset((page - 1) * int(page_size)).all()

    return_rsult = []
    for i in result:
        item = {
            'group_name': i.group_name,
            'group_url': i.group_url,
        }
        return_rsult.append(item)

    return {'code': 200, 'msg': 'success', 'data': return_rsult}


@app.route("/buli/channel/addusers", methods=['POST'])
def buli_channel_add_user():
    """批量加群"""
    _phone = request.form.get("phone")
    _channel_count = request.form.get("channel_count")
    _user_count = request.form.get("user_count")
    _user_id = request.form.get("user_id")
    _client = client_map[_phone]

    channel_list = db.session.query(Collectiongroup).filter(
        Collectiongroup.create_id == int(_user_id)
    ).order_by(
        func.rand()
    ).limit(int(_channel_count)).all()

    for channel in channel_list:
        user_list = db.session.query(Collectionfriend).filter(
            Collectionfriend.create_id == int(_user_id)
        ).order_by(
            func.rand()
        ).limit(int(_user_count)).all()

        thread_pool.submit(
            client.channel_add_user,
            _client,
            channel.group_url,
            user_list,
            _phone,
            _user_id,
        )

    return {'code': 200, 'msg': 'success', 'data': '后台正在处理，请查看日志'}


@app.route("/channel/addusers", methods=['POST'])
def channel_add_user():
    """指定拉群：将群组添加随机用户"""
    _phone = request.args.get("phone")
    channel_url = request.form.get("channel_url")
    _user_count = request.form.get("user_count")
    _user_id = request.form.get("user_id")
    _client = client_map[_phone]

    # 获取随机用户
    user_list = db.session.query(Collectionfriend).filter(
        Collectionfriend.create_id == int(_user_id)
    ).order_by(
        func.rand()
    ).limit(int(_user_count)).all()

    print('user_list_len', len(user_list))

    # 加入群组
    thread_pool.submit(
        client.channel_add_user,
        _client,
        channel_url,
        user_list,
        _phone,
        _user_id,
    )

    return {'code': 200, 'msg': 'success', 'data': '后台正在处理，请查看日志'}


@app.route("/send/users", methods=['POST'])
def buli_send_to_user():
    user_count = request.form.get('user_count')
    user_id = request.form.get('user_id')
    file_name = request.form.get('file_name')
    message = request.form.get('message')
    phone = request.args.get("phone")

    user_count = int(user_count)
    if user_count > current_app.config.get('SEDN_USER_LIMIT'):
        user_count = current_app.config.get('SEDN_USER_LIMIT')

    # 随机获取用户数
    user_list = db.session.query(Collectionfriend).filter(
        Collectionfriend.create_id == int(user_id)
    ).order_by(
        func.rand()
    ).limit(user_count).all()

    _client = client_map[phone]

    # filepath
    if file_name:
        f = request.files['file']
        filename = str(int(time.time() * 1000)) + file_name
        f.save(filename)
    else:
        filename = None

    username_list = [u.username for u in user_list]

    if filename:
        file_path = 'files/' + filename
    else:
        file_path = None

    # 异步阻塞
    # result = loop.run_until_complete(
    #     client.send_user_message_gather(
    #         _client,
    #         file_path,
    #         message,
    #         username_list,
    #         user_id,
    #         phone
    #     )
    # )

    # 异步费阻塞
    func_args = (_client, file_path, message, username_list, user_id, phone)
    thread_pool.submit(
        client.async_send_user_msg,
        *func_args
    )

    # 同步
    # loop.run_until_complete(
    #     client.send_user_message(
    #         _client,
    #         'files/' + filename,
    #         message,
    #         username_list
    #     )
    # )

    return {'code': 200, 'msg': 'success', 'data': '消息正在发送,请不要重复发送,请查看日志'}


@app.route("/send/channel", methods=['POST'])
def buli_send_to_channel():
    channel_count = request.form.get('channel_count')
    user_id = request.form.get('user_id')
    file_name = request.form.get('file_name')
    message = request.form.get('message')
    phone = request.args.get("phone")
    _client = client_map[phone]

    channel_count = int(channel_count)
    if channel_count > current_app.config.get('SEDN_CHANNEL_LIMIT'):
        channel_count = current_app.config.get('SEDN_CHANNEL_LIMIT')

    _client = client_map[phone]

    channel_list = db.session.query(Collectiongroup).filter(
        Collectiongroup.create_id == int(user_id)
    ).order_by(
        func.rand()
    ).limit(channel_count).all()

    channel_url_list = [c.group_url for c in channel_list]

    if file_name:
        f = request.files['file']
        filename = str(int(time.time() * 1000)) + file_name
        f.save(filename)
    else:
        filename = None

    if filename:
        file_path = 'files/' + filename
    else:
        file_path = None

    # 并发
    # tasks = [client.send_channel_msg(
    #     _client, file_path, message, channel_url
    # ) for channel_url in channel_url_list]

    # 异步非阻塞
    func_args = (_client, file_path, message, channel_url_list, user_id, phone)
    thread_pool.submit(
        client.async_send_channel_msg,
        *func_args
    )
    # 异步阻塞
    # result = loop.run_until_complete(
    #     client.send_channel_message_gather(*func_args)
    # )

    # 同步
    # loop.run_until_complete(
    #     client.send_channel_message(
    #         _client,
    #         'files/' + filename,
    #         message,
    #         channel_url_list
    #     )
    # )

    return {'code': 200, 'msg': 'success', 'data': '消息正在发送,请不要重复发送,请查看日志'}


@app.route("/logs", methods=['GET'])
def get_logs():
    message_type = request.args.get('message_type')
    user_id = request.args.get('user_id')
    page = request.args.get('page')

    filter_dict = {}
    if message_type:
        filter_dict['message_type'] = message_type

    if user_id:
        filter_dict['create_id'] = user_id

    item_list = db.session.query(TLog).filter_by(**filter_dict).order_by(desc('create_time')).limit(20).offset(
        int(page) - 1).all()

    result = [{
        'create_id': r.create_id,
        'client_phone': r.client_phone,
        'message_type': r.message_type,
        'message_content': r.message_content,
        'create_time': r.create_time,
    } for r in item_list]

    return {'code': 200, 'msg': 'success', 'data': result}


def add_random_user():
    _phone = request.args.get("phone")
    _user_count = request.form.get("user_count")
    _user_id = request.form.get("user_id")
    _client = client_map[_phone]

    user_list = db.session.query(Collectionfriend).filter(
        Collectionfriend.create_id == int(_user_id)
    ).order_by(
        func.rand()
    ).limit(int(_user_count)).all()

    tasks = [
        client.add_user(_client, u.username, u.first_name, u.last_name)
        for u in user_list
    ]

    result = asyncio.gather(tasks)
    print(result)

    return {'code': 200, 'msg': 'success', 'data': '添加成功'}
