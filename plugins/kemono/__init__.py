from telethon import types, Button
import re
import os
import asyncio

import util
from util.log import logger
from util.progress import Progress
from plugin import Command, Scope
import filters
from .data_source import parse_page, get_info, gif2mp4


_pattern = re.compile(
  r'^(?:/kid)? ?(?:(?:https://)?kemono\.(?:party|su)/)?([a-z]+)(?:(?:/user)?/(\d+))?(?:/post)?/(\d+)|^/kid(?![^ ])'
).match


@Command(
  'kid',
  pattern=_pattern,
  info='kemono爬取 /kid <url>',
  filter=filters.ONLYTEXT & filters.PRIVATE,
  scope=Scope.private(),
)
async def _kid(event, text):
  match = event.pattern_match
  if not (pid := match.group(3)):
    return await event.reply('用法: /kid <kemono_url>')
  options = util.string.Options(text, nocache=(), mask=('遮罩', 'spoiler'))
  source = match.group(1)
  uid = match.group(2)
  kid = f'https://kemono.su/{source}'
  if uid:
    kid += f'/user/{uid}'
  kid += f'/post/{pid}'
  mid = await event.reply('请等待...')

  info = await get_info(source, uid, pid)
  if not info:
    return await mid.edit('请求失败')
  # logger.info(info)
  # uid = user_url.split('/')[-1]
  # if source == 'fanbox' and len(files) > 1:
  #  files = files[1:]
  title = info['post']['title']
  user_name = info['author']['name']
  user_url = f'https://www.pixiv.net/fanbox/creator/{uid}'
  _files = {
    i['name']: {
      'name': i['name'],
      'thumbnail': i['server'] + '/data' + i['path'],
    }
    for i in info['previews']
  }
  for i in info['post']['attachments']:
    if 'name' not in i:
      u = i['path']
      if 'http' not in u:
        u = 'https://kemono.su' + u
      n = os.path.basename(u)
      n = os.path.splitext(n)[0]
      _files[n] = {
        'name': n,
        'url': u,
      }
    elif i['name'] in _files:
      _files[i['name']]['url'] = 'https://kemono.su/data' + i['path']
  files = [i for i in _files.values()]
  _attachments = [
    {
      'name': i['name'],
      'url': i['server'] + '/data' + i['path'],
    }
    for i in info['attachments']
  ]
  attachments = '\n'.join(
    [f'<code>{i["name"]}</code>: {i["url"]}' for i in _attachments]
  )

  if len(files) > 10:
    key = f'kemono_{source}_{pid}'
    with util.Data('urls') as data:
      if not (url := data[key]) or options.nocache:
        url = await parse_page(title, files, options.nocache)

    msg = (
      f'标题: {title}\n'
      f'作者: <a href="{user_url}">{user_name}</a>\n'
      f'预览: {url}\n'
      f'原链接: {kid}'
    )
    if attachments:
      msg += '\n\n' + attachments
    await bot.send_file(
      event.peer_id,
      caption=msg,
      parse_mode='HTML',
      file=types.InputMediaWebPage(
        url=url,
        force_large_media=True,
        optional=True,
      ),
      reply_to=event.message,
    )
    return await mid.delete()

  bar = Progress(mid, total=len(files), prefix='图片下载中...')
  msg = f'<a href="{kid}">{title}</a> - <a href="{user_url}">{user_name}</a> #kemono'
  if attachments:
    msg += '\n\n' + attachments

  data = util.Photos()

  async def get_media(i):
    nonlocal files, data, options
    key = f'kemono_{source}_{pid}_p{i}'
    if file_id := data[key]:
      return util.media.file_id_to_media(file_id, options.mask)
    if 'thumbnail' in files[i]:
      url = files[i]['thumbnail']
    elif 'url' in files[i]:
      url = files[i]['url']
    else:
      return None
    ext = os.path.splitext(url)[-1]
    if ext == '.gif':
      if 'url' not in files[i]:
        return None
      url = files[i]['url']
    img = await util.getImg(url, saveas=key, ext=True)
    if ext == '.gif':
      img = await gif2mp4(img)
      if not img:
        return None
    await bar.add(1)
    return await util.media.file_to_media(img, options.mask)

  bar.set_prefix('发送中...')
  tasks = [get_media(i) for i in range(len(files))]
  medias = await asyncio.gather(*tasks)
  medias = [i for i in medias if i is not None]
  logger.info(medias)
  async with bot.action(event.peer_id, 'photo'):
    res = await bot.send_file(
      event.peer_id,
      medias,
      caption=msg,
      parse_mode='html',
      reply_to=event.message,
      progress_callback=bar.update,
    )
  await mid.delete()
  with data:
    for i, ai in enumerate(res):
      key = f'kemono_{source}_{pid}_p{i}'
      data[key] = ai

  message_id_bytes = res[0].id.to_bytes(4, 'big')
  sender_bytes = b'~' + event.sender_id.to_bytes(6, 'big', signed=True)
  await event.reply(
    '获取完成',
    buttons=[
      Button.inline(
        '移除遮罩' if options.mask else '添加遮罩',
        b'mask_' + message_id_bytes + sender_bytes,
      ),
    ],
  )
