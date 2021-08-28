import asyncio
import base64

from telethon.sync import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest

from telethon.tl.functions.messages import CheckChatInviteRequest, AddChatUserRequest
from telethon import utils
from telethon import functions, types
from telethon.tl.types import InputChannel, InputUser, InputPhoneContact
from telethon.tl.functions.contacts import ImportContactsRequest, AddContactRequest, DeleteContactsRequest

# import asyncio

# loop = asyncio.get_event_loop()

# Use your own values from my.telegram.org
api_id = 7053776
api_hash = '2cc9a6b6d6bf191118813fc41fd74f7c'

client = TelegramClient('test', api_id, api_hash)
client.start()


# loop = asyncio.get_event_loop()


async def main():
    # Getting information about yourself
    me = await client.get_me()

    # "me" is a user object. You can pretty-print
    # any Telegram object with the "stringify" method:
    print(me.stringify())

    # When you print something, you see a representation of it.
    # You can access all attributes of Telegram objects with
    # the dot operator. For example, to get the username:
    username = me.username
    print(username)
    print(me.phone)

    # You can print all the dialogs/conversations that you are part of:
    async for dialog in client.iter_dialogs():
        print(type(dialog), dialog, dialog.__hash__())
        # print(dialog.name, 'has ID', dialog.id)
        # print(dialog.hash)


async def _get_entity(_id):
    channel = await client.get_entity('https://t.me/yinyuedareguan')
    responses = client.iter_participants(channel, aggressive=True)
    print(responses)

    i = 0
    async for response in responses:
        i += 1
        if i > 10:
            break
        print(type(response))
        print(response)
        if response.first_name is not None:
            first_name = bytes.decode(base64.b64encode(response.first_name.encode('utf-8')))
        else:
            first_name = None
        if response.last_name is not None:
            last_name = bytes.decode(base64.b64encode(response.last_name.encode('utf-8')))
        else:
            last_name = None

        print('phone', response.phone)

        print('username', response.username)

        print(first_name, last_name)


async def _resolve_id(_id):
    real_id, peer_type = utils.resolve_id(_id)

    print(real_id)  # 456
    print(peer_type)  # <class 'telethon.tl.types.PeerChannel'>

    peer = peer_type(real_id)
    print(peer)  # PeerChannel(channel_id=456)


async def _CheckChatInviteRequest():
    a = client(CheckChatInviteRequest(
        hash='-4781549370774631323'
    ))

    print(a.stringify())


async def getYou():
    u = client.get_entity('@dongyu123')
    print('1111', u)

    contact = InputPhoneContact(client_id=0, phone='', first_name="冻鱼", last_name='')

    result = await client(ImportContactsRequest([contact]))
    return await client.get_me()


async def _get_dialogs():
    # username = await client.get_entity('https://t.me/SuperIndexNews')
    username = await client.get_entity('https://t.me/pppfffs')
    print(type(username), username)
    input_channel = InputChannel(username.id, username.access_hash)
    # username = await client.get_entity('https://t.me/plus_movie_best')
    # username = await client.get_entity('https://t.me/yinyuedareguan')
    # username = await client.get_entity('https://t.me/bcdgjk')

    username1 = await client.get_entity('https://t.me/yinyuedareguan')
    print(type(username1), username1)
    responses = client.iter_participants(username1, aggressive=True, limit=10)
    async for r in responses:
        print(r.id)
        print(r.access_hash)

    users = [InputUser(r.id, r.access_hash) async for r in responses]
    print(users)

    result = functions.channels.InviteToChannelRequest(
        channel=input_channel,
        users=users,
    )

    print(result.stringify())


async def _get_massage(_id):
    a = 0
    username = await client.get_entity('https://t.me/soqun')
    async for i in client.iter_messages(username.id, limit=3):
        # async for i in client.iter_messages(_id):
        a += 1
        print(i)
        if a > 10:
            break


# 1493798959   频道
# 1348832038   群组

async def add_channel():
    result = client(functions.channels.InviteToChannelRequest(
        channel='pppfffs',
        users=['@chengjiahao', 'pingguo75']
    ))
    print(result.stringify())


# with client:

# client.loop.run_until_complete(_get_dialogs())
# client.loop.run_until_complete(_resolve_id(1493798959))
# client.loop.run_until_complete(_get_entity(1493798959))
# client.loop.run_until_complete(_get_massage(1348832038))
# client.loop.run_until_complete(getYou())

# client.send_message(1447449352, 'hello')

# # 邀请人加入频道
# client(InviteToChannelRequest(
#     channel=1182116619,  # 频道id
#     users=['HuingZM'],  # 列表格式的username
# ))
#
# 邀请人加群
# client(AddChatUserRequest(
#     chat_id=-269442445,  # chat_id
#     user_id=585015279,  # 被邀请人id
#     fwd_limit=10  # Allow the user to see the 10 last messages
# ))

# client.loop.run_until_complete(add_channel())

# channel = client.get_entity('https://t.me/yinyuedareguan')
# user = client.get_me()
# print(user.username)
# result = client(functions.channels.InviteToChannelRequest(
#     channel=channel,
#     users=['@chengjiahao']
# ))

# client(JoinChannelRequest(
#     channel=channel
# ))
# print(type(result))

# print(result)

# channel = client.get_entity('https://t.me/pppfffs')
# channel = client.get_entity('https://t.me/paofen55')
# print('---channel---', channel)
# user1 = client.get_entity('@chengjiahao')
# print(user1)
# user2 = client.get_entity('@cjiahao')
# print(user2)

# result = client(functions.channels.InviteToChannelRequest(
#     channel,
#     [user2],
# ))


# result = client(functions.messages.AddChatUserRequest(
#     chat_id=1387198993,
#     user_id=1984561352,
#     fwd_limit=42
# ))
# print(result.stringify())
# print('---result---', result)


# contact = InputPhoneContact(client_id=0, phone="+12345678", first_name="ABC", last_name="abc")
#
# result = client(ImportContactsRequest([contact], replace=True))

# user = client.get_entity('@xiaotong666')
# print(user)


# user = client.get_me()
# print(user)
# #
# channel = client.get_entity('https://t.me/yinyuedareguan')
# channel = client.get_entity('https://t.me/aaaurl')
# print(channel.id)
#
# # client.send_message('me', '花海')
# client.send_message(channel.id, '烟花易冷')
# client.send_message(channel.id, '花海', file='WechatIMG304.jpeg')
# client.send_message('me', '花海', file='1629641282078165.mp4')

# client.send_file()

# u = client.get_entity('zSL2C4p')
# print(u)

result = client(AddContactRequest(
    id='zSL2C4p',
    first_name='🐜',
    last_name='',

    phone='some string here',
    add_phone_privacy_exception=True

))

print(result.stringify())


# result = client(DeleteContactsRequest(
#     id=['zSL2C4p'],
# ))
# #
# print(result.stringify())
