# -*- coding: utf-8 -*-
# @Author  : Nyan2024
# @Info    : AI chat
""".env.example
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
import random
import base64
import binascii
import re
import asyncio

import util
import filters
from plugin import Command, InlineCommand, Scope
from util.log import logger
from .chat import Chat
from .data_source import Sessions, format_content, length


deepseek_texts = {}


@Command(
  'chat',
  info='与小派魔聊天 (Deepseek)',
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


@Command(
  'chat_list',
  info='查看对话记录',
  filter=filters.ONLYTEXT & filters.PRIVATE,
  scope=Scope.private(),
)
async def chat_list(event, p=0):
  logger.info(f'p: {p}')
  user_id = event.sender_id
  chat = await bot.get_entity(event.sender_id)
  name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
  if t := getattr(chat, 'last_name', None):
    name += ' ' + t

  sender_id = utils.get_peer_id(event.sender_id)
  url = f'tg://user?id={sender_id}'
  name = f'<a href="{url}">{util.string.html_escape(name)}</a>'

  sessions = Sessions(user_id)
  if len(sessions.sessions) < p * 10 + 1:
    return await event.respond(f'对话列表没有第 {p + 1} 页喵')

  res = []
  session_list = [session for session in sessions.sessions if session['delete_time'] == 0]
  for index, session in enumerate(session_list[p * 10 : p * 10 + 10]):
    session_id = index + p * 10
    encode_session_id = base64.urlsafe_b64encode(
      session_id.to_bytes(1, signed=False),
    ).decode()
    tip = ''
    if sessions.current_session_index == session_id:
      tip = ' ⬅️'
    res.append(
      f'\n◆ <a href="https://t.me/{bot.me.username}?start=chat_{encode_session_id}">{session["name"]}</a> ({session_id + 1}){tip}'
    )
    if len(session['historys']) == 0:
      res.append('  ● 暂无聊天记录')
      continue
    for i in session['historys'][:4]:
      content = format_content(i['content'])
      if len(content) > 20:
        content = content[:20] + '...'
      if i['role'] == 'user':
        res.append(f'  ● 你: {content}')
      else:
        res.append(f'  ● 小派魔: {content}')
    if len(session['historys']) > 4:
      res.append('  ...')

  res = '\n'.join(res)
  buttons = None
  if len(sessions.sessions) > 10:
    page_num = len(sessions.sessions) // 10 + 1
    buttons = []
    for i in range(min(page_num, 5)):
      buttons.append(
        Button.inline(f'* {i + 1}', b'chat_empty')
        if p == i
        else Button.inline(f'{i + 1}', b'chat_list_' + str(i).encode())
      )
    if page_num > 5:
      buttons = [buttons, []]
      for i in range(5, page_num):
        buttons[1].append(
          Button.inline(f'* {i + 1}', b'chat_empty')
          if p == i
          else Button.inline(f'{i + 1}', b'chat_list_' + str(i).encode())
        )

  page = ''
  if len(sessions.sessions) > 10:
    page = f' (第{p + 1}页)'
  await event.respond(
    f'{name} 您的对话列表{page}:\n{res}', parse_mode='html', buttons=buttons
  )


@bot.on(events.CallbackQuery(pattern=rb'^chat_empty$'))
async def empty_button(event):
  await event.answer()


list_session_pattern = re.compile(rb'chat_list_([0-9])').match


@bot.on(events.CallbackQuery(pattern=list_session_pattern))
async def list_session(event):
  """
  对话列表换页
  """
  match = event.pattern_match
  p = match.group(1)
  await chat_list(event, int(p))


@Command(
  'chat_clear',
  info='清空小派魔对话历史记录',
  filter=filters.ONLYTEXT,
)
async def _(event):
  user_id = event.sender_id
  chat = await bot.get_entity(event.sender_id)
  name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
  if t := getattr(chat, 'last_name', None):
    name += ' ' + t

  sender_id = utils.get_peer_id(event.sender_id)
  url = f'tg://user?id={sender_id}'
  name = f'[{util.string.markdown_escape(name)}]({url})'

  sessions = Sessions(user_id)
  historys = sessions.current_historys
  if len(historys) == 0:
    m = await event.respond(f'ℹ️ {name} 当前对话上下文为空，无需清除。')
  else:
    with sessions:
      sessions.delete_session()
      if len(sessions.sessions) == 0 or len(sessions.sessions[len(sessions.sessions) - 1]['historys']) != 0:
        sessions.add_session()
      sessions.switch_session(len(sessions) - 1)
    m = await event.respond(f'✅ {name} 已清除当前对话上下文记忆。')
  if not event.is_private:
    try:
      await bot.delete_messages(event.peer_id, event.message.id)
    except errors.MessageDeleteForbiddenError:
      pass
    bot.schedule_delete_messages(10, event.peer_id, m.id)


@Command('start', pattern=r'/start chat_([0-9a-zA-Z_\-=]{4,4})')
async def _(event):
  await event.message.delete()
  match = event.pattern_match
  encode_session_id = match.group(1)
  try:
    session_id = int.from_bytes(base64.urlsafe_b64decode(encode_session_id))
  except binascii.Error:
    return await event.respond('对话不存在')

  user_id = event.sender_id
  sessions = Sessions(user_id)
  if len(sessions.sessions) <= session_id:
    return await event.respond('对话不存在')

  session = sessions.sessions[session_id]
  res = [f'◆ {session["name"]} ({session_id})']
  if len(session['historys']) == 0:
    res.append('  ● 暂无聊天记录')
  else:
    historys = session['historys']
    if len(historys) > 10:
      historys = historys[0:1] + historys[-9:]
    for i in historys:
      content = format_content(i['content'])
      if len(content) > 50:
        content = content[:50] + '...'
      if i['role'] == 'user':
        res.append(f'\n  ● 你: {content}')
      else:
        res.append(f'  ● 小派魔: {content}')
    if len(session['historys']) > 10:
      res.insert(2, '  ...')

  res = '\n'.join(res)
  buttons = [
    [Button.inline('ℹ️ 重命名对话', b'chat_rename_' + encode_session_id.encode())],
    [Button.inline('✅ 切换对话', b'chat_switch_' + encode_session_id.encode())],
    [Button.inline('❎️ 删除对话', b'chat_delete_' + encode_session_id.encode())],
  ]
  await event.respond(res, parse_mode='html', buttons=buttons)


rename_session_pattern = re.compile(rb'chat_rename_([0-9a-zA-Z_\-=]{4,4})').match


@bot.on(events.CallbackQuery(pattern=rename_session_pattern))
async def rename_session(event):
  match = event.pattern_match
  encode_session_id = match.group(1)
  try:
    session_id = int.from_bytes(base64.urlsafe_b64decode(encode_session_id))
  except binascii.Error:
    return await event.answer('对话不存在', alert=True)

  user_id = event.sender_id
  sessions = Sessions(user_id)
  if len(sessions.sessions) <= session_id:
    return await event.answer('对话不存在', alert=True)

  await event.answer()
  session = sessions.sessions[session_id]
  peer = event.query.peer
  try:
    async with bot.conversation(peer) as conv:
      mid = await conv.send_message(
        f'正在重命名对话 "{session["name"]}"\n请在 60 秒内发送您想要设置的名称  (不大于20个字)'
      )
      while True:
        try:
          message = await conv.get_response()
        except asyncio.TimeoutError:
          await mid.delete()
          break
        if message.message.startswith('/'):
          continue
        if message.message == '取消':
          await message.delete()
          await mid.delete()
          break
        if length(message.message) <= 20:
          with sessions:
            sessions.rename_session(session_id, message.message)
          await bot.send_message(peer, '重命名成功')
          break
        await conv.send_message(
          f'名称不能大于20个字 (当前: {length(message.message)}), 请在60秒内重新输入',
        )
  except errors.AlreadyInConversationError:
    return


switch_session_pattern = re.compile(rb'chat_switch_([0-9a-zA-Z_\-=]{4,4})').match


@bot.on(events.CallbackQuery(pattern=switch_session_pattern))
async def switch_session(event):
  match = event.pattern_match
  encode_session_id = match.group(1)
  try:
    session_id = int.from_bytes(base64.urlsafe_b64decode(encode_session_id))
  except binascii.Error:
    return await event.answer('对话不存在', alert=True)

  user_id = event.sender_id
  sessions = Sessions(user_id)
  if len(sessions.sessions) <= session_id:
    return await event.answer('对话不存在', alert=True)

  if sessions.current_session_index == session_id:
    return await event.answer('ℹ️ 已经是当前对话了', alert=True)

  with sessions:
    sessions.switch_session(session_id)
  session = sessions.sessions[session_id]
  await event.respond(
    f'✅ 已切换到对话 "{session["name"]}".',
  )
  await event.answer()


delete_session_pattern = re.compile(rb'chat_delete_([0-9a-zA-Z_\-=]{4,4})').match


@bot.on(events.CallbackQuery(pattern=delete_session_pattern))
async def delete_session(event):
  match = event.pattern_match
  encode_session_id = match.group(1)
  try:
    session_id = int.from_bytes(base64.urlsafe_b64decode(encode_session_id))
  except binascii.Error:
    return await event.answer('对话不存在', alert=True)

  user_id = event.sender_id
  sessions = Sessions(user_id)
  if len(sessions.sessions) <= session_id:
    return await event.answer('对话不存在喵', alert=True)

  if len(sessions.sessions) == 1:
    return await event.answer('最后一个对话不能删喵', alert=True)

  with sessions:
    sessions.delete_session(session_id)
    sessions.switch_session(0)
  session = sessions.sessions[session_id]
  await event.respond(
    f'删除对话 "{session["name"]}" 成功.',
  )
  await event.answer()


@Command(
  'chat_new',
  info='新建对话',
  filter=filters.ONLYTEXT,
)
async def _(event):
  user_id = event.sender_id
  sessions = Sessions(user_id)
  if len(sessions.sessions) >= 100:
    return await event.respond('这么多受不了了喵，最多只能创建100个对话喵！')
  with sessions:
    sessions.add_session()
  session_id = len(sessions.sessions) - 1
  encode_session_id = base64.urlsafe_b64encode(
    session_id.to_bytes(1, signed=False),
  ).decode()
  await event.respond(
    f'新建对话 "[新对话](https://t.me/{bot.me.username}?start=chat_{encode_session_id})"({session_id}) 成功喵！',
    buttons=[
      [Button.inline('ℹ️ 重命名对话', b'chat_rename_' + encode_session_id.encode())],
      [Button.inline('✅ 切换对话', b'chat_switch_' + encode_session_id.encode())],
    ],
  )
