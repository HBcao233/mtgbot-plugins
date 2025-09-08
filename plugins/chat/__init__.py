# -*- coding: utf-8 -*-
# @Author  : Nyan2024
# @Info    : AI chat
""".env.example
# ==============一些必须填写的变量=================================================================================：
# API可以去薅Modelscope魔塔社区的免费一天2000次Inference，其它平台通用OpenAI格式的API也可以。
# 英伟达的deepseek是免费的, 而且 deepseek-ai/deepseek-r1-0528 模型对涩涩限制不大
# 参阅 https://www.modelscope.cn/docs/model-service/API-Inference/intro

# 填写API地址，不要忘记后面有个/v1
chat_api_url =
# 输入你的API的密钥（Token），获取方法见上方文档
chat_api_key =
# 模型名称，比如想用的模型链接是https://www.modelscope.cn/models/deepseek-ai/DeepSeek-R1。填写deepseek-ai/DeepSeek-R1即可
chat_model =
# 根据模型文档填写
chat_max_tokens =
"""

from telethon import events, types, errors, utils, Button
import os
import random

import util
import filters
from plugin import Command, InlineCommand
from .chat import Chat
from .data_source import MEMORY_DIR


deepseek_texts = {}


@Command(
  'chat',
  info='与小派魔聊天',
  filter=filters.ONLYTEXT,
)
async def _chat(event):
  c = Chat(event)
  await c.main()


@InlineCommand(r'^ *[^ ].{2,}')
async def _(event):
  builder = event.builder
  msg = f'$ {event.text}'
  did = random.randrange(4_294_967_296)
  deepseek_texts[did] = msg
  did_bytes = int(did).to_bytes(4, 'big')
  return [
    builder.document(
      title='问问小派魔',
      description=msg,
      text=msg,
      buttons=Button.inline('点击召唤Deepseek', b'deepseek_' + did_bytes),
      file=b'<html></html>',
      attributes=[types.DocumentAttributeFilename('output.html')],
    ),
  ]


@bot.on(events.CallbackQuery(pattern=b'deepseek_([\x00-\xff]{4,4})$'))
async def _(event):
  try:
    await event.edit(buttons=[])
  except errors.MessageNotModifiedError:
    pass
  await event.answer()
  match = event.pattern_match
  did = int.from_bytes(match.group(1), 'big')
  event.raw_text = deepseek_texts[did]
  del deepseek_texts[did]
  event.message = None
  event.peer_id = event.query.user_id
  await _chat(event)


@Command('clear', info='清除上下文记忆')
async def _(event):
  # 清除指定用户的上下文记忆
  user_id = event.sender_id
  path = os.path.join(MEMORY_DIR, f'{user_id}.json')

  chat = await bot.get_entity(event.sender_id)
  name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
  if t := getattr(chat, 'last_name', None):
    name += ' ' + t

  sender_id = utils.get_peer_id(event.sender_id)
  url = f'tg://user?id={sender_id}'
  name = f'[{util.string.markdown_escape(name)}]({url})'

  if os.path.isfile(path):
    os.remove(path)
    m = await event.respond(f'✅ {name} 已清除你的对话上下文记忆。')
  else:
    m = await event.respond(f'ℹ️ {name} 你的对话上下文为空，无需清除。')
  if not event.is_private:
    try:
      await bot.delete_messages(event.peer_id, event.message.id)
    except errors.MessageDeleteForbiddenError:
      pass
    bot.schedule_delete_messages(10, event.peer_id, m.id)
