# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
''' .env.example
# superadmin 的 id, 多个请用逗号隔开
superadmin = 1234567, 123456789
'''

from telethon import events
import re
import random
import config
import util
from util.log import logger
from plugin import handler, Scope


@handler('add', 
  info='添加关键词', 
  scope=Scope.superadmin()
)
async def _add(event, text):
  if event.sender_id not in config.superadmin:
    return
  if not (reply_message := await event.message.get_reply_message()):
    return await event.reply('请用命令回复一条消息')
  if text == '':
    return await event.reply('请输入关键词')
    
  with util.Data('keywords') as data:
    if data[text] is None:
      data[text] = []
    data[text].append([event.chat_id, reply_message.id])
  await event.reply(f'添加关键词 "{text}" 成功')
  
  
@handler('del', 
  info='删除关键词', 
  scope=Scope.superadmin()
)
async def _(event, text):
  if event.sender_id not in config.superadmin:
    return
  
  if text == '':
    return await event.reply('请输入需要删除的关键词')
  
  with util.Data('keywords') as data:
    if text not in data:
      return await event.reply(f'关键词 "{text}" 不存在')
    del data[text] 
  await event.reply(f'删除关键词 "{text}" 成功')
  
  
@handler('list', 
  info='查看关键词列表', 
  scope=Scope.superadmin()
)
async def _list(event, text):
  if event.sender_id not in config.superadmin:
    return
  
  data = util.Data('keywords') 
  if len(data) == 0:
    return await event.reply('未添加任何关键词')
  msg = []
  for i in data.keys():
    msg += [f'· <code>{i}</code>']
  await event.reply(
    '关键词列表: \n' + "\n".join(msg), 
    parse_mode='HTML',
  )


@bot.on(events.NewMessage)
async def _(event, text):
  if not text or event.message.message.startswith('/'):
    return
  data = util.Data('keywords')
  ms = []
  for i in data.keys():
    if re.search(i, text):
      ms.extend(data[i])
  
  if len(ms) > 0:
    chat_id, message_id = random.choice(ms)
    await bot.send_message(
      event.peer_id,
      await bot.get_messages(chat_id, ids=message_id),
      reply_to=event.message,
    )
