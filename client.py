# coding: utf-8
import base64
import asyncio
import time
from datetime import datetime

import nest_asyncio

nest_asyncio.apply()

from telethon import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import PeerChannel, InputPhoneContact
from telethon import functions
from telethon.errors.rpcerrorlist import UserNotMutualContactError, ChatWriteForbiddenError
from telethon import utils

from main import loop
from model import TLog


def thread_async(func):
    def make_decorater(*args):
        """
        注意：asyncio在新的os线程中运行，需要当前os线程中有事件循环loop或在asyncio运行命令中指定loop
            (1) asyncio.set_event_loop （可以使用全局的loop）
            (2) 在当前os线程中创建新的loop，之后请async函数的运行使用这个loop
                _loop.run_until_complete(func(_loop, *args))
        """

        # 方案一
        asyncio.set_event_loop(loop)
        result = asyncio.run(func(args))

        # 方案二
        # _loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(_loop)
        # func_rsult = _loop.run_until_complete(func(_loop, *args))  # 需要在func函数loop参数，接收新的loop
        # _loop.close()

        return result

    return make_decorater


@thread_async
async def io_test(a):
    result = await asyncio.gather(io_func(), io_func(), io_func())
    print(result, a)
    TLog(
        message_type='send_channel',
        message_content='测试一下client模块写入日志',
        client_phone=115456,
        create_time=datetime.now(),
        create_id=1,
    ).save()

    return result


async def io_func():
    print('io_func 1')
    time.sleep(5)
    print('io_func 2')
    return 'ok'


async def get_dialogs(client):
    """获取对话框列表"""

    dialog_list = []
    async with client:
        async for dialog in client.iter_dialogs():
            dialog_list.append(dialog)

    return dialog_list


async def get_entity(client, _id):
    channel = await client.get_entity(PeerChannel(_id))
    responses = client.iter_participants(channel, aggressive=True)
    print(responses)
    async for response in responses:
        if response.first_name is not None:
            first_name = bytes.decode(base64.b64encode(response.first_name.encode('utf-8')))
        else:
            first_name = None
        if response.last_name is not None:
            last_name = bytes.decode(base64.b64encode(response.last_name.encode('utf-8')))
        else:
            last_name = None

        print(first_name, last_name)
        print('username', response.username)


async def resolve_id(_id):
    real_id, peer_type = utils.resolve_id(_id)

    print(real_id)  # 456
    print(peer_type)  # <class 'telethon.tl.types.PeerChannel'>

    peer = peer_type(real_id)
    print(peer)  # PeerChannel(channel_id=456)


async def add_user(phone, _id, _hash):
    _client = TelegramClient('session/' + phone, int(_id), _hash)

    await _client.connect()

    status = await _client.is_user_authorized()

    if not status:
        await _client.sign_in(phone)

    status_str = '正在发送验证码' if status else '已在登录状态'
    return _client, status_str


async def send_code(client, code):
    """发送验证码"""
    await client.sign_in(code=code)

    await client.start()


async def get_me(client):
    """获取自己信息"""

    async with client:
        me = await client.get_me()
        return me


async def spider_group_user(client, url):
    """
    采集群友
    :param client: 用户客户端
    :param url: 群地址
    :return: 群友username列表
    """
    channel = await client.get_entity(url)

    result = []
    # 采集所有群友
    responses = client.iter_participants(channel, aggressive=True)
    async for response in responses:
        result.append(response)

    return result


async def spider_group_url(client):
    """搜群神器，获取群链接"""
    # 1348832038 搜群神器id
    soqun = await client.get_entity('https://t.me/soqun')

    result = []
    async for msg in client.iter_messages(soqun, limit=5):
        result.append(msg)

    return result


async def channel_add_user(client, channel_url, user_list):
    """
    批量将用户加入群组
    :param client:
    :param channel_url: 群组的URL地址
    :param user_list: 用户名（username）列表
    :return:
    """
    print('---client---', client)

    # 1 获取user对象
    users = []
    for username in user_list:
        user = await client.get_entity(username)
        users.append(user)

    # 2 获取群对象
    channel = await client.get_entity(channel_url)
    print('---channel---', channel)

    try:
        result = await client(functions.channels.InviteToChannelRequest(
            channel=channel,
            users=users
        ))
    except UserNotMutualContactError:
        print('此用户不是好友')
        pass

    except ChatWriteForbiddenError:
        print('此用不不能添加到群组')
        pass

    except Exception as e:
        print(e)
        pass

    else:
        return result


async def input_contacts_request(client, username_list):
    """添加联系人"""
    print(username_list)
    contact = InputPhoneContact(
        client_id=0,
        phone="+12345678",
        first_name="ABC",
        last_name="abc"
    )

    result = await client.invoke(ImportContactsRequest([contact]))
    print(result)


async def send_user_message(client, filename, message, username_list):
    """群友群发"""
    for username in username_list:
        try:
            await client.send_message(username, message, file=filename)
        except Exception as e:
            print(e)
            print(username, '发送失败')


async def send_user_message_gather(client, filename, message, username_list, user_id, phone):
    """群友群发"""
    tasks = []
    for username in username_list:
        tasks.append(send_user_msg(client, filename, message, username))

    result = await asyncio.gather(*tasks, loop=loop)

    TLog(
        message_type='send_channel',
        message_content=str(list(zip(username_list, result))),
        client_phone=phone,
        create_time=datetime.now(),
        create_id=user_id,
    ).save()

    return result


async def send_user_msg(client, filename, message, username):
    """群友群发"""
    try:
        await client.send_message(username, message, file=filename)
        return '发送成功'
    except Exception as e:
        print(e)
        print(username, '发送失败')
        return '发送失败'


async def send_channel_message(client, filename, message, channel_url_list):
    """群组群发"""
    for channel_url in channel_url_list:
        channel = await client.get_entity(channel_url)
        try:
            await client.send_message(channel.id, message, file=filename)
            return True
        except Exception as e:
            print(e)
            return False


async def send_channel_message_gather(client, filename, message, channel_url_list, user_id, phone):
    """群组群发"""
    tasks = []
    for channel_url in channel_url_list:
        tasks.append(send_channel_msg(client, filename, message, channel_url))

    result = await asyncio.gather(*tasks, loop=loop)

    TLog(
        message_type='send_channel',
        message_content=str(list(zip(channel_url_list, result))),
        client_phone=phone,
        create_time=datetime.now(),
        create_id=user_id,
    ).save()

    return result


async def send_channel_msg(client, filename, message, channel_url):
    """群组群发"""
    try:
        channel = await client.get_entity(channel_url)
    except Exception as e:
        print(e)
        return '未找到'
    try:
        await client.send_message(channel.id, message, file=filename)
        return '发送成功'
    except Exception as e:
        print(e)
        return '发送失败'


@thread_async
async def async_send_user_msg(client, filename, message, username_list, user_id, phone):
    result = await send_user_message_gather(
        client,
        filename,
        message,
        username_list,
        user_id,
        phone
    )

    return result


@thread_async
async def async_send_channel_msg(client, filename, message, channel_url_list, user_id, phone):
    result = await send_channel_message_gather(
        client,
        filename,
        message,
        channel_url_list,
        user_id,
        phone
    )

    return result
