from datetime import datetime
import math
import base64
import binascii

import filters
from util.log import logger
from plugin import Command
from .tables import Cum
from .data_source import (
  omikuji_levels,
  get_omikuji_details,
  formatTime,
  dick_length_levels,
  dick_thickness_levels,
  dick_cum_levels,
  get_help_details,
)


@Command(
  'cum_self',
  info='自慰射精（签到）',
  filter=filters.ONLYTEXT,
)
async def cum(event):
  user_id = event.sender_id
  chat = await bot.get_entity(user_id)
  name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
  if t := getattr(chat, 'last_name', None):
    name += ' ' + t
  name = f'[{name}](tg://user?id={user_id})'

  user = Cum.get_user(user_id)
  cum_min = user['cum_min']
  cum_max = user['cum_max']
  res, semen = Cum.cum(user_id)
  omikuji = math.floor((semen - cum_min) / ((cum_max - cum_min) / 6))
  level = omikuji_levels[omikuji]
  logger.info(f'res: {res}, semen: {semen}, omikuji: {omikuji}')
  if not res:
    return await event.reply(
      f'{name} 您今天已经射过了喵，再射会坏掉的\n\n今日运势: {level}，今日射精 {semen/ 100} mL'
    )

  details = await get_omikuji_details(omikuji)
  await event.reply(
    f'{name} {details}\n\n今日运势: {level}，您获得了 {semen/100} mL 精液',
  )


@Command(
  'cum_jar',
  info='查看您的糖罐',
  filter=filters.ONLYTEXT,
)
async def cum_jar(event):
  user_id = event.sender_id
  chat = await bot.get_entity(user_id)
  name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
  if t := getattr(chat, 'last_name', None):
    name += ' ' + t
  name = f'[{name}](tg://user?id={user_id})'

  semen = Cum.get_semen(user_id)
  jar_status = f'您的糖罐里还有 {semen / 100} mL 精液'
  if semen == 0:
    jar_status = '您的糖罐一滴不剩了'
  last_cum_time = Cum.last_cum_time(user_id)
  if last_cum_time == 0:
    jar_status = '您的糖罐还是崭新的'
  else:
    now = int(datetime.now().timestamp())
    time_status = formatTime(now - last_cum_time)
    jar_status += f'，上次新鲜精液灌入是在 {time_status} 前'
  await event.reply(
    f'{name} {jar_status}',
  )


@Command(
  'cum_status',
  info='查看您的状态',
  filter=filters.ONLYTEXT,
)
async def cum_status(event):
  user_id = event.sender_id
  chat = await bot.get_entity(user_id)
  name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
  if t := getattr(chat, 'last_name', None):
    name += ' ' + t
  name = f'[{name}](tg://user?id={user_id})'

  user = Cum.get_user(user_id)
  # 长度
  dick_length = round(user['dick_length'] / 100, 2)
  dick_length_level = math.floor((user['dick_length'] - 100) / 300)
  dick_length_level_info = dick_length_levels[-1]
  if dick_length_level < len(dick_length_levels):
    dick_length_level_info = dick_length_levels[dick_length_level]

  # 粗细
  dick_thickness = round(user['dick_thickness'] / 100, 2)
  dick_thickness_level = math.floor((user['dick_thickness'] - 200) / 100)
  dick_thickness_level_info = dick_thickness_levels[-1]
  if dick_thickness_level < len(dick_thickness_levels):
    dick_thickness_level_info = dick_thickness_levels[dick_thickness_level]

  # 射精量
  cum_min = user['cum_min']
  cum_max = user['cum_max']
  cum_average = round((cum_min + cum_max) / 2)
  cum_level = 4
  if cum_average < 600:
    cum_level = 0
  elif cum_average < 1500:
    cum_level = 1
  elif cum_average < 3000:
    cum_level = 2
  elif cum_average < 6000:
    cum_level = 3
  cum_level_info = dick_cum_levels[cum_level]

  await event.reply(
    f"""{name} 您的状态面板:
◆ 肉棒长度: {dick_length}cm ({dick_length_level_info['name']})
  * {dick_length_level_info['details']}

◆ 肉棒粗度: {dick_thickness}cm ({dick_thickness_level_info['name']})
  * {dick_thickness_level_info['details']}

◆ 射精量: {cum_min/100}~{cum_max/100}mL ({cum_level_info['name']})
  * {cum_level_info['details']}""",
  )


@Command(
  'cum_invite',
  info='查看您的邀请链接',
  filter=filters.ONLYTEXT,
)
async def cum_invite(event):
  user_id = event.sender_id
  chat = await bot.get_entity(user_id)
  name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
  if t := getattr(chat, 'last_name', None):
    name += ' ' + t
  name = f'[{name}](tg://user?id={user_id})'

  encode_user_id = base64.urlsafe_b64encode(
    user_id.to_bytes(6, signed=True),
  ).decode()
  url = f'https://t.me/{bot.me.username}?start=cum_invite_{encode_user_id}'
  await event.reply(
    f"""{name} 您的邀请链接: {url}

◆ 古老的符文在地面上闪烁着诱人的光芒，空气中弥漫着奇异的香气。这是一个名为'灵欲交织阵'的魔法阵，传说它并非由凡人所创，而是由沉溺于欲望的古老神祇所留下。
◆ 阵法中央，两道光柱缓缓升起，交织缠绕，如同彼此吸引的灵魂。当另一位玩家接受你的邀请，魔法阵便会感知到回应的渴望，启动连接仪式……
◆ 欲望共鸣：连接两个渴望者的心意，放大彼此的欲望。
◆ 生命馈赠：阵法将根据双方的渴望程度，给予生命精华。
◆ 使用限制：每天与同一名玩家只能进行一次该阵法"""
  )


@Command(
  'start',
  pattern=r'^/start cum_invite_([0-9a-zA-Z_\-=]{8,8})',
)
async def help_other(event):
  await event.message.delete()
  user_id = event.sender_id
  match = event.pattern_match
  encode_uid = match.group(1)
  try:
    uid = int.from_bytes(base64.urlsafe_b64decode(encode_uid), signed=True)
  except binascii.Error:
    return await event.respond('邀请链接不存在')

  if user_id == uid:
    return await event.respond('不能自己和自己使用 “灵欲交织阵”')
  help_get = Cum.help(uid, user_id)
  chat = await bot.get_entity(user_id)
  name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
  if t := getattr(chat, 'last_name', None):
    name += ' ' + t
  name = f'[{name}](tg://user?id={user_id})'
  if not help_get:
    return await event.respond(
      f'你今天已经和 {name} 使用过 “灵欲交织阵”了喵，明天再来吧',
    )

  help_details = await get_help_details()
  await event.respond(
    f'{help_details}\n\n您获得了 {help_get/100} mL 精液',
  )
