import httpx
import json
import util
from util.log import logger
import config


token = config.env.get('misskey_token', '')


async def get_note(noteId):
  try:
    r = await util.post(
      'https://misskey.io/api/notes/show',
      data=f'{{"i":"{token}","noteId":"{noteId}"}}',
      headers={
        'content-type': 'application/json',
        'referer': f'https://misskey.io/notes/{noteId}',
      },
    )
    res = r.json()
    if 'error' in res:
      if res['error']['code'] == 'NO_SUCH_NOTE':
        return '未找到这篇笔记'
      return res['error']['message']
    if 'renote' in res:
      return res['renote']
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
  msg = (
    f'<a href="https://misskey.io/notes/{noteId}">{noteId}</a> | '
    f'<a href="https://misskey.io/@{username}">{nickname}</a> #Misskey'
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
      'type': 'photo',
      'md5': i['md5'],
      'url': i['url'],
      'content-type': i['type'],
    }
    for i in res['files']
    if i['type'].startswith('image')
  ]
