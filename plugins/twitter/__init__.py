# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
""".env.example
# X cookie 中的 ct0
twitter_csrf_token =
# X cookie 中的 auth_token
twitter_auth_token =
"""

from telethon import events, errors, Button
import re
import ujson as json

import util
import filters
from util.log import logger
from util.progress import Progress
from plugin import Command, Scope
from .data_source import gheaders, get_twitter, parse_msg, parseMedias


cmd_header_pattern = re.compile(r'/?tid')
_p = r'(?:^/?tid |(?:https?://)?[a-z]*?(?:twitter|x)\.com/[a-zA-Z0-9_]+/status/)(\d{13,20})(?:[^0-9].*)?$|^/tid(?![^ ])'
_pattern = re.compile(_p).search


@Command(
  'tid',
  pattern=_pattern,
  info='获取推文 /tid <url/tid> [hide] [mask]',
  filter=filters.ONLYTEXT & filters.PRIVATE,
  scope=Scope.private(),
)
async def _tid(event, text):
  text = cmd_header_pattern.sub('', text).strip()
  match = _pattern(text)
  if match is None or not (tid := match.group(1)):
    return await event.reply(
      '用法: /tid <url/tid> [options]:\n'
      '获取推文\n'
      '- <url/tid>: 推文链接或 status id\n'
      '- [hide/简略]: 获取简略推文\n'
      '- [mask/遮罩]: 添加遮罩'
    )

  options = util.string.Options(text, hide=('简略', '省略'), mask=('spoiler', '遮罩'))
  logger.info(f'{tid = }, {options = }')
  mid = await event.reply('请等待...')

  res = await get_twitter(tid)
  if isinstance(res, str):
    return await event.reply(res)
  if 'tombstone' in res.keys():
    logger.info('tombstone: %s', json.dumps(res))
    return await event.reply(res['tombstone']['text']['text'].replace('了解更多', ''))

  msg, full_text, time = parse_msg(res)
  msg = msg if not options.hide else 'https://x.com/i/status/' + tid
  tweet = res['legacy']
  medias_info = parseMedias(tweet)
  if len(medias_info) == 0:
    return await event.reply(msg, parse_mode='HTML')

  medias = []
  photos = util.Photos()
  videos = util.Videos()
  bar = Progress(mid, prefix='下载中...')
  async with bot.action(event.chat_id, medias_info[0]['type']):
    for index, i in enumerate(medias_info):
      url = i['url']
      md5 = i['md5']
      t = photos if i['type'] == 'photo' else videos
      ext = 'jpg' if i['type'] == 'photo' else 'mp4'
      if file_id := t[md5]:
        media = util.media.file_id_to_media(file_id, options.mask)
      else:
        file = await util.getImg(
          url,
          headers=gheaders,
          saveas=f'{tid}_{index}',
          ext=ext,
          progress_callback=bar.update,
        )
        if i['type'] == 'video':
          file = await util.media.video2mp4(file)
        bar.set_prefix('上传中...')
        media = await util.media.file_to_media(
          file,
          options.mask,
          progress_callback=bar.update,
        )
      medias.append(media)

    res = await bot.send_file(
      event.chat_id,
      medias,
      reply_to=event.message,
      caption=msg,
      parse_mode='HTML',
    )
    await mid.delete()

  with photos:
    with videos:
      for i, ai in enumerate(res):
        t = photos if ai.photo else videos
        t[medias_info[i]['md5']] = ai

  message_id_bytes = res[0].id.to_bytes(4, 'big')
  sender_bytes = b'~' + event.sender_id.to_bytes(6, 'big', signed=True)
  tid_bytes = int(tid).to_bytes(8, 'big')
  await event.reply(
    '获取完成',
    buttons=[
      [
        Button.inline(
          '移除遮罩' if options.mask else '添加遮罩',
          b'mask_' + message_id_bytes + sender_bytes,
        ),
        Button.inline(
          '详细描述' if options.hide else '简略描述',
          b'tid_' + message_id_bytes + b'_' + tid_bytes + sender_bytes,
        ),
      ],
      # [Button.inline('关闭面板', b'delete' + sender_bytes)],
    ],
  )
  raise events.StopPropagation


_button_pattern = re.compile(
  rb'tid_([\x00-\xff]{4,4})_([\x00-\xff]{8,8})(?:~([\x00-\xff]{6,6}))?$'
).match


@bot.on(events.CallbackQuery(pattern=_button_pattern))
async def _event(event):
  """
  简略描述/详细描述 按钮回调
  """
  peer = event.query.peer
  match = event.pattern_match
  message_id = int.from_bytes(match.group(1), 'big')
  tid = int.from_bytes(match.group(2), 'big')
  sender_id = None
  if t := match.group(3):
    sender_id = int.from_bytes(t, 'big')
  # logger.info(f'{message_id=}, {tid=}, {sender_id=}, {event.sender_id=}')

  if sender_id and event.sender_id and sender_id != event.sender_id:
    participant = await bot.get_permissions(peer, event.sender_id)
    if not participant.delete_messages:
      return await event.answer('只有消息发送者可以修改', alert=True)

  message = await bot.get_messages(peer, ids=message_id)
  if message is None:
    return await event.answer('消息被删除', alert=True)

  hide = '年' in message.message
  msg = f'https://x.com/i/status/{tid}'
  if not hide:
    res = await get_twitter(tid)
    if isinstance(res, str) or 'tombstone' in res:
      if isinstance(res, str):
        res = res['tombstone']['text']['text'].replace('了解更多', '')
      return await event.answer(res, alert=True)
    msg, _, _ = parse_msg(res)
  try:
    await message.edit(msg, parse_mode='html')
  except errors.MessageNotModifiedError:
    logger.warning('MessageNotModifiedError')

  message = await event.get_message()
  buttons = message.buttons[0]
  text = '详细描述' if hide else '简略描述'
  index = 0
  for i, ai in enumerate(buttons):
    if _button_pattern(ai.data):
      index = i
      data = ai.data
      break
  buttons[index] = Button.inline(text, data)

  try:
    await event.edit(buttons=buttons)
  except errors.MessageNotModifiedError:
    logger.warning('MessageNotModifiedError')
  await event.answer()
