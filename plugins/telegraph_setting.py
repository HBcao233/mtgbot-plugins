# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Info    : 提供用户自定义 telegraph作者配置项

from telethon import Button
import asyncio

import util
import config
from plugin import Setting


@Setting('telegraph 作者名')
async def _(event):
  await event.delete()
  key = str(event.chat_id)
  chat = await bot.get_entity(event.chat_id)
  name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
  btns = [
    Button.text(
      name,
      single_use=True,
    )
  ]
  if last_name := getattr(chat, 'last_name', None):
    btns.append(Button.text(name + ' ' + last_name, single_use=True))

  buttons = [
    btns,
    [
      Button.text('留空', single_use=True),
      Button.text('重置为默认值', single_use=True),
      Button.text('取消', single_use=True),
    ],
  ]
  msg = '设置成功'
  async with bot.conversation(event.chat_id) as conv:
    with util.data.Settings() as data:
      if not data.get('telegraph', None):
        data['telegraph'] = {}
      if not data['telegraph'].get('author_name', None):
        data['telegraph']['author_name'] = {}

      mid = await conv.send_message(
        "请在 60 秒内发送您想要设置的 telegraph 作者名 (不大于128个字符)\n"
        f"当前值: {data['telegraph']['author_name'].get(key, config.telegraph_author_name)}\n"
        f"默认值: {config.telegraph_author_name}\n",
        buttons=buttons,
      )
      while True:
        try:
          message = await conv.get_response()
        except asyncio.TimeoutError:
          msg = '设置超时'
          break

        if message.message in ['留空', '重置为默认值', '取消']:
          if message.message == '留空':
            data['telegraph']['author_name'][key] = ''
          if (
            message.message == '重置为默认值'
            and key in data['telegraph']['author_name']
          ):
            del data['telegraph']['author_name'][key]
          if message.message == '取消':
            msg = '设置取消'
          break
        if len(message.message) <= 128:
          data['telegraph']['author_name'][key] = message.message
          break

        await conv.send_message(
          '作者名不能大于128个字符, 请在60秒内重新输入', buttons=buttons
        )

  await event.respond(msg, buttons=Button.clear(), reply_to=mid)


@Setting('telegraph作者链接')
async def _(event):
  await event.delete()
  key = str(event.chat_id)

  chat = await bot.get_entity(event.chat_id)
  username = getattr(chat, 'username', None)
  buttons = []
  if username:
    buttons.append(
      [
        Button.text(
          f'https://t.me/{username}',
          single_use=True,
        )
      ]
    )
  buttons.append(
    [
      Button.text('留空', single_use=True),
      Button.text('重置为默认值', single_use=True),
      Button.text('取消', single_use=True),
    ]
  )

  msg = '设置成功'
  async with bot.conversation(event.chat_id) as conv:
    with util.data.Settings() as data:
      if not data.get('telegraph', None):
        data['telegraph'] = {}
      if not data['telegraph'].get('author_url', None):
        data['telegraph']['author_url'] = {}

      mid = await conv.send_message(
        "请在 60 秒内发送您想要设置的 telegraph 作者链接 (不大于512个字符)\n"
        f"当前值: {data['telegraph']['author_url'].get(key, config.telegraph_author_url)}\n"
        f"默认值: {config.telegraph_author_url}\n",
        buttons=buttons,
      )
      while True:
        try:
          message = await conv.get_response()
        except asyncio.TimeoutError:
          msg = '设置超时'
          break

        if message.message in ['留空', '重置为默认值', '取消']:
          if message.message == '留空':
            data['telegraph']['author_url'][key] = ''
          if (
            message.message == '重置为默认值' and key in data['telegraph']['author_url']
          ):
            del data['telegraph']['author_url'][key]
          if message.message == '取消':
            msg = '设置取消'
          break

        if len(message.message) > 512:
          msg = '作者链接不能大于 512 个字符'
        elif not (
          message.message.startswith('http://')
          or message.message.startswith('https://')
        ):
          msg = '作者链接需以 http:// 或 https:// 开头'
        else:
          data['telegraph']['author_url'][key] = message.message
          break

        await conv.send_message(msg + ', 请在60秒内重新输入', buttons=buttons)

  await event.respond(msg, buttons=Button.clear(), reply_to=mid)
