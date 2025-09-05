# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Info    : 网易云音乐解析
"""requirement
pycryptodome
pyexecjs
"""

""".env.example
# cookie 中的 __csrf
163music_csrf_token =
163music_u = ""
"""

from telethon import types, Button
import re
import asyncio

import filters
import util
from plugin import Command, Scope
from util.log import logger
from util.progress import Progress
from .data_source import (
  get_song_detail,
  parse_song_detail,
  get_url,
  general_search,
  parse_search,
  getImg,
  add_metadata,
  get_program_info,
  parse_program_info,
)


_p = r'(?:^/163music |(?:/163music )?(?:(?:https?://)?(?:y\.)?music\.163\.com/(?:[#m|]/)?song\?.*?id=))([0-9]{3,12})|(?:163cn\.tv/([0-9a-zA-Z]{7,7}))|(?:y\.)?music\.163\.com/(?:[#m]/)?program\?.*?id=([0-9]{3,12})|^/163music(?![^ ])'
_pattern = re.compile(_p).search


@Command(
  '163music',
  pattern=_pattern,
  info='网易云音乐链接解析',
  filter=filters.ONLYTEXT & filters.PRIVATE,
  scope=Scope.private(),
)
async def _song(event, sid=''):
  program = False
  pid = None
  if not sid:
    match = event.pattern_match
    if (
      (sid := match.group(1)) is None
      and match.group(2) is None
      and match.group(3) is None
    ):
      return await event.reply(
        '用法: /163music <url/id>',
      )

    if match.group(2):
      r = await util.get('http://163cn.tv/' + match.group(2))
      # logger.info(r.url)
      text = str(r.url)
      match = _pattern(text)
      sid = match.group(1)
      await event.reply(
        f'https://music.163.com/#/song?id={sid}',
      )
    elif pid := match.group(3):
      program = True  # 播客

  options = util.string.Options(event.message.message, nocache=())
  logger.info(f'sid: {sid}, program: {program}, pid: {pid}, options: {options}')
  mid = await event.reply('请等待...')
  if not program:
    info = await get_song_detail(sid)
  else:
    info = await get_program_info(pid)
    sid = info['program']['mainTrackId']

  if isinstance(info, str):
    return await event.reply(info)

  if not program:
    msg, metainfo = parse_song_detail(info)
  else:
    msg, metainfo = parse_program_info(info)

  key = f'163music_{sid}'
  title = metainfo['title']
  bar = Progress(mid)
  async with bot.action(event.peer_id, 'audio'):
    if not (img := (util.data.Audios()[key] or util.data.Audios()[key + '_try'])) or options.nocache:
      
      await mid.edit('下载中...')
      bar.set_prefix('下载中...')
      res = await get_url(sid)
      if res is None:
        return await event.reply(
          '\n'.join(msg),
          parse_mode='html',
        )
      url, ext, time = res
      if not url:
        return await mid.edit('\n'.join(msg), parse_mode='html',)
      logger.info(f'url: {url}')
      if time < metainfo['duration']:
        key += '_try'
        title = '(试听) ' + title
        
      img = await getImg(
        url,
        saveas=key,
        ext=ext,
        progress_callback=bar.update,
      )
      msg.insert(1, f'Type: {ext}')
      img = await add_metadata(img, ext, metainfo)
      await mid.edit('上传中...')
      bar.set_prefix('上传中...')
      
      cover = await getImg(
        metainfo['coverUrl'],
        saveas=f'163music_{sid}_cover',
        ext='jpg',
      )
      thumb = util.media.img2bytes(util.media.getPhotoThumbnail(cover), 'jpg')
      img = await util.media.file_to_media(
        img,
        thumb=thumb,
        attributes=[
          types.DocumentAttributeAudio(
            voice=False,
            duration=time,
            title=title,
            performer=metainfo['singers'],
            waveform=None,
          ),
          types.DocumentAttributeFilename(
            f'{metainfo["title"]} - {metainfo["singers"]}.mp3'
          ),
        ],
        progress_callback=bar.update,
      )

    m = await bot.send_file(
      event.peer_id,
      file=img,
      caption='\n'.join(msg),
      parse_mode='html',
    )
    await mid.delete()
  with util.data.Audios() as data:
    data[key] = m


@Command(
  '163music_search',
  info='网易云音乐搜索',
  filter=filters.ONLYTEXT & filters.PRIVATE,
  scope=Scope.private(),
)
async def _search(event):
  keyword = ''
  arr = event.raw_text.split(' ')
  if len(arr) > 1:
    keyword = arr[1]

  if not keyword:
    async with bot.conversation(event.chat_id) as conv:
      mid = await conv.send_message(
        '请在 60 秒内发送您想要搜索的关键词',
        buttons=[
          Button.text('取消', single_use=True),
          Button.text('占位', single_use=False),
        ],
      )

      while True:
        try:
          message = await conv.get_response()
        except asyncio.TimeoutError:
          pass
        if message.message != '占位':
          break

      if message.message == '取消':
        return await mid.respond('操作取消', buttons=Button.clear())
      if (
        not message.message
        or message.message.startswith('/')
        or len(message.message) > 64
      ):
        return await mid.respond('输入有误', buttons=Button.clear())
      keyword = message.message.strip()

  mid = await event.respond('请稍后...', buttons=Button.clear())
  res = await general_search(keyword)
  if not res:
    return await event.respond('搜索获取失败, 请检查配置')
  msg, buttons = parse_search(res)
  await mid.delete()
  await event.reply(
    msg,
    parse_mode='html',
    buttons=buttons,
  )


@Command('start', pattern=r'/start 163music_([0-9]{3,12})')
async def _(event):
  match = event.pattern_match
  mid = match.group(1)
  await _song(event, mid)
