# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Info    : AI chat
""".env.example"""

from telethon import errors, utils
import os

import util
import filters
from plugin import Command
from .chat import Chat
from .data_source import MEMORY_DIR


deepseek_texts = {}


@Command(
  'chat2',
  info='与小派魔聊天',
  filter=filters.ONLYTEXT,
)
async def _chat(event):
  c = Chat(event)
  await c.main()


@Command('clear2', info='清除上下文记忆')
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
