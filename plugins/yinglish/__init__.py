# -*- coding: utf-8 -*-
# @Author  : HBcao233
# @Info    : 淫语翻译器
""".env.example
# 填写API地址
yinglish_api_url = 
chat_api_url =

# 输入你的API的密钥（Token），获取方法见上方文档
yinglish_api_key = 
chat_api_key = 

# 模型名称
yinglish_model = 'deepseek-ai/deepseek-v3.1'

# 根据模型文档填写
yinglish_max_tokens = 8192
"""

from telethon import events, types, errors, Button
import random

import filters
from plugin import Command, InlineCommand
from util.log import logger
from .data_source import get_yinglish


texts = {}


@Command(
  'yinglish',
  info='淫语翻译器',
  filter=filters.ONLYTEXT,
)
async def _chat(event):
  text = ''
  parts = event.raw_text.split(maxsplit=1)
  if len(parts) > 1:
    text = parts[1].strip()
  
  logger.info(f'text: {text}')
  reply_to = None
  if event.message:
    reply_to = event.message.id
    reply = await event.message.get_reply_message()
    if reply:
      reply_to = reply.id
      
  if not text:
    return await event.respond(
      '用法: /yinglish 文本',
      reply_to=reply_to,
    )
  
  inline_mode = event.message is None
  nickname = await get_nickname(event)
  res = await get_yinglish(text)
  logger.info(f'淫语翻译器结果: {res}')
  result = f"{text} :\n淫语翻译失败: {res['message']}"
  if res['code'] == 0:
    data = res['data'] 
    text_tip = data['original']
    if '[' not in text_tip:
      text_tip += f'  [{data['role']}/{data['target']}]'
    result = f"{text_tip}:\n淫语翻译器结果: {data['dirty_talk']}\n\n<blockquote expandable>{data['explanation']}</blockquote>"

  msg = f'$ {nickname} {result}'
  logger.info(f'淫语翻译器回复: {msg}')
  if inline_mode:
    return await event.edit(msg, parse_mode='html')
  return await event.respond(
    msg,
    reply_to=reply_to,
    parse_mode='html',
  )


@InlineCommand(r'^ *[^ ].{2,}')
async def _(event):
  builder = event.builder
  did = random.randrange(4_294_967_296)
  texts[did] = event.text
  did_bytes = int(did).to_bytes(4, 'big')
  return [
    builder.article(
      title='淫语翻译器',
      description=event.text,
      text=event.text,
      buttons=Button.inline('开始翻译', b'yinglish_' + did_bytes),
    ),
  ]


@bot.on(events.CallbackQuery(pattern=b'yinglish_([\x00-\xff]{4,4})$'))
async def _(event):
  await event.answer()
  match = event.pattern_match
  did = int.from_bytes(match.group(1), 'big')
  text = texts[did]
  del texts[did]
  event.raw_text = f'$ {text}'
  try:
    await event.edit(f'$ {text}\n请等待...', buttons=[])
  except errors.MessageNotModifiedError:
    pass
  event.message = None
  event.peer_id = event.query.user_id
  await _chat(event)


async def get_nickname(event):
  if not event.is_private:
    user_id = event.sender_id
    chat = await bot.get_entity(user_id)
    name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
    if t := getattr(chat, 'last_name', None):
      name += ' ' + t
    return f'<a href="tg://user?id={user_id}">{name}</a> '
  return ''
