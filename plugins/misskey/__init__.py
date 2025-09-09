# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Info    : misskey 爬取
""".env.example
# misskey cookie 中的 token
misskey_token =
# (可选) dvd.chat cookie 中的 token
dvd_token =
"""

from telethon import Button
import re
import asyncio


import util
from util.log import logger
from plugin import Command, Scope
import filters
from .data_source import get_note, parse_msg, parse_medias


_p = r'(?:^/misskey |(?:/misskey )?(?:https?://)?(?:misskey\.io/notes/))([a-z0-9A-Z]{16})(?:[^a-zA-Z0-9\n].*)?$|^/misskey(?![^ ])'
_pattern = re.compile(_p).search


@Command(
  'misskey',
  pattern=_pattern,
  info='获取misskey笔记 /misskey <url/noteId> [hide] [mask]',
  filter=filters.PRIVATE & filters.ONLYTEXT,
  scope=Scope.private(),
)
async def _misskey(event, text=''):
  match = event.pattern_match
  if not (noteId := match.group(1)):
    return await event.reply(
      '用法: /misskey <url/noteId> [hide] [mask]\n'
      '获取misskey笔记\n'
      '- <url/noteId>: 链接或noteId\n'
      '- [hide/省略]: 省略图片说明\n'
      '- [mask/遮罩]: 给图片添加遮罩'
    )

  options = util.string.Options(
    text, hide=('简略', '省略'), mask=('spoiler', '遮罩')
  )
  logger.info(f'noteId: {noteId}, options: {options}')

  res = await get_note(noteId)
  if isinstance(res, str):
    return await event.reply(res)
  msg = parse_msg(res)
  medias = parse_medias(res)
  photos = util.Photos()
  videos = util.Videos()
  documents = util.Documents()
  force_document = False
  async with bot.action(event.chat_id, medias[0]['type']):

    async def get_file(i):
      nonlocal force_document
      key = f'{noteId}_{i}'
      data = (
        (photos if medias[i]['type'] == 'photo' else videos)
        if medias[i]['ext'] != 'gif'
        else documents
      )
      if file_id := data[key]:
        return util.media.file_id_to_media(file_id, options.mask)

      file = await util.getImg(
        medias[i]['url'],
        headers={'referer': f'https://misskey.io/notes/{noteId}'},
        saveas=key,
        ext=medias[i]['ext'],
      )
      if medias[i]['ext'] == 'gif':
        force_document = True
        return file
      if medias[i]['type'] == 'video':
        file = await util.media.video2mp4(file)
      return await util.media.file_to_media(file, options.mask)

    tasks = [get_file(i) for i in range(len(medias))]
    files = await asyncio.gather(*tasks)
    m = await bot.send_file(
      event.chat_id,
      files,
      reply_to=event.message,
      caption=msg,
      parse_mode='HTML',
      force_document=force_document,
    )

  with photos, documents, videos:
    for i, ai in enumerate(m):
      data = (
        (photos if medias[i]['type'] == 'photo' else videos)
        if not force_document
        else documents
      )
      key = f'{noteId}_{i}'
      data[key] = ai

  message_id_bytes = m[0].id.to_bytes(4, 'big')
  sender_bytes = b'~' + event.sender_id.to_bytes(6, 'big', signed=True)
  await event.reply(
    '获取完成',
    buttons=[
      [
        Button.inline(
          '移除遮罩' if options.mask else '添加遮罩',
          b'mask_' + message_id_bytes + sender_bytes,
        ),
      ],
      # [Button.inline('关闭面板', b'delete' + sender_bytes)],
    ],
  )
