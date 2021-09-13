# -*- coding: utf-8 -*-
# @Time    : 2021/8/26 8:43
# @Author  : 10867
# @FileName: views.py
# @Software: PyCharm
import re
import time
import asyncio
from datetime import datetime
from functools import wraps

import requests
from flask import request, current_app, g
from sqlalchemy import desc
from sqlalchemy.sql.expression import func
from telethon.tl.types import InputUser
from telethon.tl.functions.contacts import DeleteContactsRequest, GetContactsRequest
from telethon import functions

from main import app, db, loop, thread_pool
from model import *
import client

client_count = {}
client_map = {}


# @app.before_request
# def app_before_request():
#     token = request.headers.get('X-Token')
#     g.user_id = int(token)


@app.route('/test', methods=['POST', 'GET'])
def test_view():
    print(current_app.config.get('CRAWL_USER_MAXCOUNT'))

    a = request.args.get('kw')
    client_map[a] = a

    # db.session.query(Collectionfriend).filter(
    #     Collectionfriend.create_id == int(1)
    # ).order_by(
    #     func.rand()
    # ).limit(10).all()
    #
    # user_list = [u.username for u in user_list]
    # app_log.info('记录日志views测试')
    # 同步
    # loop.run_until_complete(client.io_test(a))

    # 异步
    # result = thread_pool.submit(client.io_test, *(a, 1,))

    result = asyncio.run(asyncio.gather(client.io_func1()))
    print('result', result)

    return 'views'


@app.route('/')
def index():
    return 'Index Page'


def identity_auth(_func):
    """
    装饰器，检查用户身份是否有效
    :param _func:
    :return:
    """

    @wraps(_func)
    def _wraps(*args, **kwargs):
        if request.method == 'get' or request.method == 'GET':
            phone = request.args.get('phone', '')
        else:
            phone = request.json.get('phone', '')

        _client = client_map.get(phone)
        if _client:
            status = loop.run_until_complete(_client.is_user_authorized())
            if not status:
                return {
                    'code': 403,
                    'msg': '%s 设备未认证' % phone,
                    'data': None
                }
        else:
            return {
                'code': 200,
                'msg': '%s 设备未登陆' % phone,
                'data': None
            }

        return _func(*args, **kwargs)

    return _wraps


@app.route('/login', methods=['POST'])
def login():
    username = request.json.get("username")
    password = request.json.get("password")

    user = db.session.query(TMember).filter(
        TMember.username == username,
        TMember.pwd == password
    ).first()

    if not user:
        return {'code': 200, 'msg': '请检查用户名和密码是否正确', 'data': None}

    current_count = client_count.get(user.id, 0)

    user_info = db.session.query(TMemberInfo).filter(
        TMemberInfo.id == user.id
    ).first()

    if not user_info:
        return {'code': 201, 'msg': '账号未找到或未激活', 'data': None}

    result_data = {
        'user_name': user.username,
        'user_id': user.id,
        'token': str(user.id),
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


@app.route('/user/info', methods=['GET'])
def user_info():
    user_id = request.args.get("user_id")
    if not user_id:
        return {'code': 200, 'msg': 'user_id不能为空', 'data': {}}

    user = db.session.query(TMember).filter(
        TMember.id == int(user_id)
    ).first()

    if not user:
        return {'code': 200, 'msg': '没找到用户信息', 'data': {}}
    else:
        result = {
            "introduction": "",
            "avatar": "",
            "name": user.username,
        }
        user_info = db.session.query(TMemberInfo).filter(
            TMemberInfo.member_id == int(user_id)
        ).first()
        if user_info:
            result['package_device_num'] = user_info.package_device_num
            result['sign_device_num'] = client_count.get(int(user_id), 0)
            print(client_count)

        return {'code': 200, 'msg': 'success', 'data': result}


@app.route('/sign_in', methods=['POST'])
def sign_in():
    """添加用户"""
    _member_id = request.json.get("member_id")
    _phone = request.json.get("phone")
    _api_id = request.json.get("api_key")
    _api_hash = request.json.get("api_hash")

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
                'msg': '%s 以到最大可登陆设备数' % _phone,
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
        return {'code': 200, 'msg': '%s 设备已登陆' % _phone, 'data': None}

    try:
        _client, status = loop.run_until_complete(client.sign_in(_phone, _api_id, _api_hash))
    except Exception as e:
        return {
            'code': 200,
            'msg': str(e),
            'data': {}
        }

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
    else:
        return {
            'code': 200,
            'msg': 'success',
            'data': {'error': str(status)}
        }

    return {
        'code': 200,
        'msg': 'success',
        'data': {'status': status, 'sign_device_num': client_count[_member_id]}
    }


@app.route('/sendCode', methods=["POST"])
def send_code():
    """发送验证码认证"""
    phone = request.json.get("phone")
    code = request.json.get("code")

    _client = client_map.get(phone)
    if _client is not None:
        loop.run_until_complete(client.send_code(_client, code))

        return {'code': 200, 'msg': 'success', 'data': {}}
    else:
        return {'code': 200, 'msg': 'success', 'data': {}}


@app.route("/getMe", methods=['GET'])
@identity_auth
def get_me():
    """获取自己信息"""
    _phone = request.args.get("phone")
    _client = client_map[_phone]

    me = loop.run_until_complete(client.get_me(_client))
    print(me.stringify())

    return {'code': 200, 'msg': 'success', 'data': {'username': me.username, 'phone': me.phone}}


@app.route("/getDialogs", methods=['GET'])
@identity_auth
def get_dialogs():
    """获取对话框"""
    _phone = request.args.get("phone")
    _client = client_map[_phone]

    dialogs_list = loop.run_until_complete(client.get_dialogs(_client))

    for dia in dialogs_list:
        print(dia)

    return {'code': 200, 'msg': 'success', 'data': {}}


@app.route("/crawl/channel/username", methods=['GET', 'POST'])
@identity_auth
def spider_group_user():
    """采集群友"""
    # _phone = request.args.get("phone")
    # _url = request.args.get("url")
    # _user_id = request.args.get("user_id")

    _phone = request.json.get("phone")
    _url = request.json.get("url")
    _user_id = request.json.get("user_id")

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

    for u in crawl_user_list:

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

        return_rsult.append({'name': i.username})

    return {'code': 200, 'msg': 'success', 'data': return_rsult}


@app.route("/user/list", methods=['GET'])
def get_user():
    """获取群友列表"""
    user_id = request.args.get("user_id")
    page = request.args.get("page")
    page_size = request.args.get("page_size")

    result = db.session.query(Collectionfriend).filter(
        Collectionfriend.create_id == int(user_id)
    ).limit(int(page_size)).offset((int(page) - 1) * int(page_size)).all()

    return_rsult = []
    for i in result:
        item = {
            'username': i.username,
            'groupmemberid': i.groupmember_id,
        }
        return_rsult.append(item)

    return {'code': 200, 'msg': 'success', 'data': return_rsult}


@app.route("/crawl/channel/url", methods=['GET'])
@identity_auth
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

    sum_count = 0
    del_count = 0
    for msg in msg_list:
        content: str = msg.message
        content_list = content.split('\n\n')

        if len(content_list) != 3:
            continue

        title_list = re.findall('\d. (.*?)-', content_list[1])

        entities: list = msg.entities

        # 判断群组链接
        for i, t in enumerate(title_list):
            if '👥' in t:
                sum_count += 1
                entity = entities[i + 1]
                url = entity.url
                if url in group_url_list:
                    del_count += 1
                    continue

                result.append({'name': t, 'vaule': url})

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
        item.group_url = r['vaule']
        item.createtime = datetime.now()
        item.create_id = int(_user_id)
        db.session.add(item)

    db.session.commit()

    TLog(
        message_type='crawl_channel_url',
        message_content='采集群组 %s 条, 去重 %s 条' % (sum_count, del_count),
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
    ).limit(int(page_size)).offset((int(page) - 1) * int(page_size)).all()

    return_rsult = []
    for i in result:
        item = {
            'group_name': i.group_name,
            'group_url': i.group_url,
        }
        return_rsult.append(item)

    return {'code': 200, 'msg': 'success', 'data': return_rsult}


@app.route("/buli/channel/addusers", methods=['POST'])
@identity_auth
def buli_channel_add_user():
    """批量加群"""
    _phone = request.json.get("phone")
    _channel_count = request.json.get("channel_count")
    _user_count = request.json.get("user_count")
    _user_id = request.json.get("user_id")
    _client = client_map[_phone]

    channel_list = db.session.query(Collectiongroup).filter(
        Collectiongroup.create_id == int(_user_id)
    ).order_by(
        func.rand()
    ).limit(int(_channel_count)).all()

    for channel in channel_list:
        # user_list = db.session.query(Collectionfriend).filter(
        #     Collectionfriend.create_id == int(_user_id)
        # ).order_by(
        #     func.rand()
        # ).limit(int(_user_count)).all()
        #
        # thread_pool.submit(
        #     client.channel_add_user,
        #     _client,
        #     # channel.group_url,
        #     channel_url,
        #     user_list,
        #     _phone,
        #     _user_id,
        # )

        # 获取要加入群组的联系人
        user_list = db.session.query(Collectionfriend).filter(
            Collectionfriend.create_id == int(_user_id)
        ).order_by(
            func.rand()
        ).limit(int(_user_count)).all()

        # 同步阻塞
        print('添加联系人')
        add_user_tasks = []
        for u in user_list:
            # loop.run_until_complete(
            #     client.add_user(
            #         _client,
            #         u.username,
            #         u.first_name,
            #         u.last_name
            #     )
            # )

            add_user_tasks.append(
                client.add_user(
                    _client,
                    u.username,
                    u.first_name,
                    u.last_name
                )
            )

        # 添加联系人
        add_user_list = loop.run_until_complete(
            asyncio.gather(*add_user_tasks, loop=loop)
        )
        username_list = [u.username for u in user_list]
        TLog(
            message_type='buli_channel_addusers',
            message_content=str(list(username_list)),
            client_phone=_phone,
            create_time=datetime.now(),
            create_id=_user_id,
        ).save()
        # 获取群组对象
        tg_channel = loop.run_until_complete(_client.get_entity(channel.group_url))
        user_obj_list = [InputUser(int(u.groupmember_id), int(u.access_hash)) for u in user_list]
        # 添加用户到群组
        try:
            print('添加用户到群组')
            loop.run_until_complete(_client(functions.channels.InviteToChannelRequest(
                channel=tg_channel,
                users=user_obj_list
            )))
        except Exception as e:
            TLog(
                message_type='buli_channel_addusers',
                message_content='添加用户到群组%s失败，异常：%s' % (channel.group_url, str(e)),
                client_phone=_phone,
                create_time=datetime.now(),
                create_id=_user_id,
            ).save()
        # 删除联系人
        try:
            print('删除联系人')
            loop.run_until_complete(_client(DeleteContactsRequest(
                id=user_obj_list,
            )))
        except Exception as e:
            TLog(
                message_type='buli_channel_addusers',
                message_content='删除联系人失败，异常%s' % str(e),
                client_phone=_phone,
                create_time=datetime.now(),
                create_id=_user_id,
            ).save()

    return {'code': 200, 'msg': '后台正在处理，请查看日志', 'data': {}}


@app.route("/channel/addusers", methods=['POST'])
@identity_auth
def channel_add_user():
    """指定拉群：将群组添加随机用户"""
    phone = request.json.get("phone")
    channel_url = request.json.get("channel_url")
    user_count = request.json.get("user_count")
    user_id = request.json.get("user_id")
    _client = client_map[phone]

    # 获取随机用户
    user_list = db.session.query(Collectionfriend).filter(
        Collectionfriend.create_id == int(user_id)
    ).order_by(
        func.rand()
    ).limit(int(user_count)).all()

    # 异步，加入群组
    # thread_pool.submit(
    #     client.channel_add_user,
    #     _client,
    #     channel_url,
    #     user_list,
    #     phone,
    #     user_id,
    # )

    # 同步阻塞
    add_user_tasks = []
    for u in user_list:
        add_user_tasks.append(client.add_user(
            _client,
            u.username,
            u.first_name,
            u.last_name
        ))
    add_user_list = loop.run_until_complete(asyncio.gather(*add_user_tasks))

    channel = loop.run_until_complete(_client.get_entity(channel_url))

    user_obj_list = [InputUser(int(u.groupmember_id), int(u.access_hash)) for u in user_list]
    # 4 添加用户到群组
    try:
        loop.run_until_complete(_client(functions.channels.InviteToChannelRequest(
            channel=channel,
            users=user_obj_list
        )))
    except Exception as e:
        TLog(
            message_type='channel_addusers',
            message_content='添加用户到群组%s失败，异常：%s' % (channel.group_url, str(e)),
            client_phone=phone,
            create_time=datetime.now(),
            create_id=user_id,
        ).save()

        return {'code': 200, 'msg': '用户到群组失败', 'data': {'error': str(e)}}

    try:
        loop.run_until_complete(_client(DeleteContactsRequest(
            id=user_obj_list,
        )))
    except Exception as e:
        TLog(
            message_type='channel_addusers',
            message_content='删除联系人失败，异常%s' % str(e),
            client_phone=phone,
            create_time=datetime.now(),
            create_id=user_id,
        ).save()
        return {'code': 200, 'msg': '删除联系人失败', 'data': {'error': str(e)}}

    return {'code': 200, 'msg': 'success', 'data': {}}


@app.route("/send/users", methods=['POST'])
@identity_auth
def buli_send_to_user():
    user_count = request.json.get('user_count')
    user_id = request.json.get('user_id')
    file_name = request.json.get('file_name')
    message = request.json.get('message')
    phone = request.json.get("phone")

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

    return {'code': 200, 'msg': '消息正在发送,请不要重复发送,请查看日志', 'data': {}}


@app.route("/send/channel", methods=['POST'])
@identity_auth
def buli_send_to_channel():
    channel_count = request.json.get('channel_count')
    user_id = request.json.get('user_id')
    file_name = request.json.get('file_name')
    message = request.json.get('message')
    phone = request.json.get("phone")
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

    return {'code': 200, 'msg': '消息正在发送,请不要重复发送,请查看日志', 'data': {}}


@app.route("/logs", methods=['GET'])
def get_logs():
    message_type = request.args.get('message_type')
    user_id = request.args.get('user_id')
    page = request.args.get('page', 1)

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


@app.route("/add/user", methods=['GET'])
@identity_auth
def add_random_user():
    """添加用户"""
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

    result = loop.run_until_complete(asyncio.gather(tasks))

    return {'code': 200, 'msg': 'success', 'data': result}


@app.route("/user/logout", methods=['POST'])
def logout():
    _member_id = request.json.get("member_id")
    phone = request.json.get('phone')

    if not client_map.get(phone):
        return {'code': 200, 'msg': '账号未登陆', 'data': {}}

    _client = client_map[phone]

    c = client_count.get(_member_id, 0)
    if c > 0:
        client_count[_member_id] = c - 1

    # 退出登录
    try:
        loop.run_until_complete(_client.log_out())
    except Exception as e:
        return {'code': 200, 'msg': '退出失败', 'data': {'error': str(e)}}

    client_map.pop(phone)
    return {'code': 200, 'msg': '退出成功', 'data': {}}


@app.route('/get/contacts', methods=['GET'])
@identity_auth
def get_contacts():
    """获取联系人"""
    phone = request.args.get('phone')
    _client = client_map[phone]

    result = loop.run_until_complete(_client(GetContactsRequest(hash=0)))
    print(result)

    return {'code': 200, 'msg': '退出成功', 'data': {}}


def sign_up():
    """注册Telegram账号"""
    _phone = request.json.get('phone')
    first_name = request.json.get('first_name')
    last_name = request.json.get('last_name')
    _client = client_map[_phone]

    sdm_api_name = current_app.config.get('SDM_API_NAME')
    sdm_pass_word = current_app.config.get('SDM_PASS_WORD')
    sdm_login_url = 'http://sudim.cn:88/yhapi.ashx?act=login&ApiName={}&PassWord={}'.format(sdm_api_name, sdm_pass_word)
    # 1 登陆速递码获取token
    response1 = requests.get(sdm_login_url)
    login_text = response1.text.split('|')
    token = login_text[1] if len(login_text) == 2 else ''
    if not token:
        return {'code': 200, 'msg': 'sdm token fail', 'data': {}}
    # 2 获取手机号
    # 1|141616740851026|2021-09-04T18:35:29|COM3|16740851026|联通|河北沧州
    get_phone_url = 'http://sudim.cn:88/yhapi.ashx?' \
                    'act=getPhone&token={}&iid=1416&did=&operator=&provi=&city=&seq=&mobile='.format(token)

    response2 = requests.get(get_phone_url)
    phone_text = response2.text.split('|')
    if len(phone_text) != 7:
        return {'code': 200, 'msg': 'sdm get phone fail', 'data': {}}

    phone_pid = phone_text[1]
    phone = phone_text[4]

    # 3 发送telegram验证码  client.send_code_request(phone)
    loop.run_until_complete(_client.send_code_request('+86' + phone))

    # 4 根据（2）返回的pid获取验证码
    get_code_url = 'http://sudim.cn:88/yhapi.ashx?' \
                   'act=getPhoneCode&token={}&pid={}'.format(token, phone_pid)

    code = None
    for n in range(30):
        time.sleep(1)
        response3 = requests.get(get_code_url)
        if response3.text:
            break

    if not code:
        return {'code': 200, 'msg': '获取验证码超时', 'data': {}}

    # 5 注册telegram账号 client.sign_up(code, first_name='Anna', last_name='Banana')
    sign_up_result = loop.run_until_complete(
        _client.sign_up(code, first_name=first_name, last_name=last_name)
    )

    return {'code': 200, 'msg': '注册成功', 'data': {'phone': phone, 'first_name': first_name, 'last_name': last_name}}
