import httpx
import json
import re
from datetime import datetime

import util
import config
from util.log import logger
from util.log import timezone


token = config.env.get('misskey_token', '')
dvd_token = config.env.get('dvd_token', '')
if not token:
  logger.warning('misskey_token 未配置, misskey 获取将不可用.')


async def get_note(noteId):
  try:
    r = await util.post(
      'https://misskey.io/api/notes/show',
      data=f'{{"i":"{token}","noteId":"{noteId}"}}',
      headers={
        'content-type': 'application/json',
        'referer': f'https://misskey.io/notes/{noteId}',
        'Authorization': f'Bearer {token}',
      },
    )
    res = r.json()
    if 'error' in res:
      if res['error']['code'] == 'NO_SUCH_NOTE':
        return '未找到这篇笔记'
      return res['error']['message']
    if 'renote' in res:
      res = res['renote']

    if dvd_token:
      try:
        noteId = res['id']
        r1 = await util.post(
          'https://dvd.chat/api/ap/show',
          data=f'{{"uri":"https://misskey.io/notes/{noteId}"}}',
          headers={
            'content-type': 'application/json',
            'referer': 'https://dvd.chat/',
            'Authorization': f'Bearer {dvd_token}',
          },
        )
        res1 = r1.json()
        res['dvdId'] = res1['object']['id']
      except Exception:
        logger.warn('获取dvdId错误', exc_info=1)

    return res
  except httpx.ConnectError:
    return '连接超时'
  except json.JSONDecodeError:
    logger.info(r.text)
    return '未找到这篇笔记'
  except Exception:
    logger.info(r.text)
    return '未知错误'


def parse_msg(res):
  noteId = res['id']
  username = res['user']['username']
  nickname = res['user']['name']
  
  # createdAt = res['createdAt'].replace('.000Z', '').replace('T', '')
  createdAt = datetime.strptime(res['createdAt'].split('.')[0], r'%Y-%m-%dT%H:%M:%S')
  createdAt.astimezone(timezone)
  createdAt = createdAt.strftime('%Y年%m月%d日 %H:%M:%S')
  text = res['text']
  text = re.sub(r'\?\[([\s\S]*?)\]\(([\s\S]*?)\)', r'<a href="\2">\1</a>', text)
  if text:
    text = f'\n<blockquote expandable>{text}\n{createdAt}</blockquote>'
  else:
    text = f'\n{createdAt}'
  
  dvdInfo = ''
  if dvdId := res.get('dvdId', ''):
    dvdInfo = f'\n<a href="https://dvd.chat/notes/{dvdId}">在 DVD Chat 上访问</a>'

  msg = (
    f'<a href="https://misskey.io/notes/{noteId}">{noteId}</a> | '
    f'<a href="https://misskey.io/@{username}">{nickname}</a> #Misskey'
    f'{dvdInfo}{text}'
    f'\nvia @{bot.me.username}'
  )
  return msg


def parse_medias(res):
  """
  {
    "id": "9zykcjhy4rzo002b",
    "createdAt": "2024-10-29T22:08:06.070Z",
    "name": "20241012-1.png.webp",
    "type": "image/webp",
    "md5": "ee06cefe548baca379938d6c009f436f",
    "size": 952924,
    "isSensitive": true,
    "blurhash": "eMLEH69$0M~qDk1Q%OoPoZD+059dx^ti%2E8MzX7W9s*o~%0s,R6jX",
    "properties": {
      "width": 2048,
      "height": 2048
    },
    "url": "https://media.misskeyusercontent.jp/io/c81ad3bb-ec4e-4022-a8df-2d48996300fd.webp?sensitive=true",
    "thumbnailUrl": "https://media.misskeyusercontent.jp/io/thumbnail-3ff07ebe-5218-4a76-b87f-65ae59bc5a9e.webp",
    "comment": null,
    "folderId": null,
    "folder": null,
    "userId": "9dyc6niimd",
    "user": null
  }
  """
  return [
    {
      'type': 'photo' if i['type'].startswith('image') else 'video',
      'md5': i['md5'],
      'url': i['url'],
      'content-type': i['type'],
      'ext': (
        ('gif' if i['type'] == 'image/gif' else 'jpg')
        if i['type'].startswith('image')
        else i['name'].split('.')[-1]
      ),
    }
    for i in res['files']
    if i['type'].startswith('image') or i['type'].startswith('video')
  ]
