import ujson as json
import base64
import codecs
import random
import asyncio
import execjs
import os

# pip install pycryptodome
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

import util
import config
from util.log import logger
from .settmusic import settmusic


csrf_token = config.env.get('163music_csrf_token', '')
music_u = config.env.get('163music_u', '')
headers = {
  'cookie': f'os=pc; appver=8.9.70; MUSIC_U={music_u}',
}
path = os.path.dirname(__file__)
js_path = os.path.join(path, 'encode.js')
with open(js_path, 'r') as f:
  js_code = f.read()


async def asrsea(data):
  def aes(data, key):
    iv = '0102030405060708'.encode()
    data = pad(data.encode(), AES.block_size, 'pkcs7')
    key = key.encode()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = cipher.encrypt(data)
    res = base64.b64encode(encrypted_data).decode()
    return res

  async def rsa(data):
    data = data[::-1]
    data = data.encode()
    loop = asyncio.get_event_loop()
    d = await loop.run_in_executor(
      None,
      pow,
      int(codecs.encode(data, encoding='hex'), 16),
      int('010001', 16),
      int(
        '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7',
        16,
      ),
    )
    return format(d, 'x').zfill(256)

  data = json.dumps(data, ensure_ascii=False)
  key = '0CoJUm6Qyw8W8jud'
  secKey = ''.join(
    random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    for i in range(16)
  )
  encText = aes(data, key)
  encText = aes(encText, secKey)
  encSecKey = await rsa(secKey)

  return {
    'params': encText,
    'encSecKey': encSecKey,
  }


async def curl(url, params):
  params.update({'csrf_token': csrf_token})
  r = await util.post(
    url, headers=headers, params={'csrf_token': csrf_token}, data=await asrsea(params)
  )
  if r.status_code != 200:
    return False
  res = r.json()
  if res['code'] != 200:
    return False
  return res


async def getImg(*args, headers=None, **kwargs):
  return await util.getImg(*args, headers=headers, **kwargs)


async def get_song_detail(mid):
  res = await curl(
    'https://music.163.com/weapi/v3/song/detail',
    {'id': mid, 'c': json.dumps([{'id': mid}])},
  )
  if not res:
    return '获取失败'
  res = res['songs']
  if len(res) == 0:
    return '获取失败'
  return res[0]


def parse_song_detail(res):
  sid = res['id']
  name = res['name']
  alia = ''
  if len(res['alia']) > 0:
    alia = f' ({", ".join(res["alia"])})'
  url = f'https://music.163.com/#/song?id={sid}'
  singers = '、'.join(
    [
      f'<a href="https://music.163.com/#/artist?id={i["id"]}">{i["name"]}</a>'
      for i in res['ar']
    ]
  )
  msg = [
    f'<a href="{url}">{name}</a>{alia} - {singers} #163music',
    'via @%s' % bot.me.username,
  ]
  metainfo = {
    'sid': sid,
    'coverUrl': res['al']['picUrl'],
    'title': name + alia,
    'singers': '、'.join([i['name'] for i in res['ar']]),
    'album': res['al']['name'],
  }
  return msg, metainfo


async def get_song_url(mid):
  res = await curl(
    'https://music.163.com/weapi/song/enhance/player/url/v1',
    {
      'ids': f'[{mid}]',
      'level': 'exhigh',
      'encodeType': 'mp3',  # aac ; mp3
    },
  )
  if not res:
    return
  res = res['data'][0]
  return res['url'], res['type']


async def get_flac_url(mid):
  r = await util.post(
    'https://api.toubiec.cn/api/get-token.php',
    headers={'referer': 'https://api.toubiec.cn/wyapi.html'},
  )
  if r.status_code != 200:
    return
  res = r.json()
  if 'token' not in res:
    return
  auth = res['token']
  ctx = execjs.compile(js_code)
  token = ctx.call('md5', auth)
  r = await util.post(
    'https://api.toubiec.cn/api/music_v1.php',
    headers={
      'referer': 'https://api.toubiec.cn/wyapi.html',
      'Authorization': f'Bearer {auth}',
    },
    data=f'{{"url":"https://music.163.com/song?id={mid}","level":"lossless","type":"song","token":"{token}"}}',
  )
  res = r.json()
  if res['status'] != 200 or 'url_info' not in res:
    logger.info(res)
    return
  return res['url_info']['url'], res['url_info']['type']


async def get_url(mid):
  '''
  res = await get_flac_url(mid)
  if res is not None:
    return res
  '''
  return await get_song_url(mid)


async def add_metadata(img, ext, metainfo):
  sid = metainfo['sid']
  cover_name = f'163music_{sid}_cover'
  cover_url = metainfo['coverUrl']
  cover = await getImg(
    cover_url,
    saveas=cover_name,
    ext=True,
  )
  resimg_name = f'163music_{sid}_meta.{ext}'
  resimg = util.getCacheFile(resimg_name)
  title = metainfo['title']
  singers = metainfo['singers']
  album = metainfo['album']
  returncode, stdout = await util.media.ffmpeg(
    [
      'ffmpeg',
      '-i',
      cover,
      '-i',
      img,
      # '-c',
      # 'copy',
      '-map',
      '0:v',
      '-map',
      '1:a',
      '-metadata',
      f'title={title}',
      '-metadata',
      f'artist={singers}',
      '-metadata',
      f'album={album}',
      '-metadata:s:v',
      'title=Front cover',
      '-metadata:s:v',
      'comment=Cover (front)',
      '-y',
      resimg,
    ]
  )
  if returncode != 0:
    logger.warning(stdout)
    return img
  return resimg


async def general_search(keyword):
  res = await curl(
    'https://music.163.com/weapi/cloudsearch/get/web',
    {
      'hlpretag': '<span class="s-fc7">',
      'hlposttag': '</span>',
      's': keyword,
      'type': '1',
      'offset': '0',
      'total': 'true',
      'limit': '10',
    },
  )
  if not res:
    return
  result = res['result']
  if res['abroad']:
    result = settmusic(result)
  if not isinstance(result, dict):
    logger.info(result)
    return
  return result['songs']


def parse_search(res):
  from telethon import Button

  icons = [f'{i}\ufe0f\u20e3' for i in range(1, 10)] + ['\U0001f51f']

  arr = [
    f'{icons[i]} <a href="https://t.me/{bot.me.username}?start=163music_{res[i]["id"]}">{res[i]["name"]}</a> - '
    + '、'.join([j['name'] for j in res[i]['ar']])
    for i in range(10)
  ]

  icon = '\U0001f3b5'
  urls = [f'https://t.me/{bot.me.username}?start=163music_{i["id"]}' for i in res]
  btns = [Button.url(f'{i + 1} {icon}', urls[i]) for i in range(10)]
  buttons = [btns[i : i + 5] for i in range(0, 10, 5)]
  return '\n'.join(arr), buttons


async def get_program_info(pid):
  res = await curl(
    'https://interface.music.163.com/weapi/dj/program/detail/static/get', {'id': pid}
  )
  if not res:
    return
  return res['data']


def parse_program_info(res):
  pid = res['program']['id']
  title = res['program']['name']
  url = f'https://music.163.com/m/program?id={pid}'
  description = res['program']['description']
  mainTrackId = res['program']['mainTrackId']
  # song_url = f'https://music.163.com/#/song?id={mainTrackId}'

  userId = res['anchor']['userId']
  nickname = res['anchor']['nickname']
  user_url = f'https://y.music.163.com/m/user?id={userId}'
  album_id = res['radio']['id']
  album = res['radio']['name']
  album_url = f'http://music.163.com/radio?id={album_id}'
  desc = res['radio']['desc']
  descriptions = []
  if description:
    descriptions.append(description)
  if desc:
    descriptions.append(desc)
  descriptions = '\n'.join(descriptions)
  msg = [
    f'<a href="{url}">{title}</a>',
    f'合集: <a href="{album_url}">{album}</a>',
    f'作者: <a href="{user_url}">{nickname}</a>',
    f'<blockquote expandable>{descriptions}</blockquote>',
    '#163music #播客',
    f'via @{bot.me.username}',
  ]
  metainfo = {
    'sid': mainTrackId,
    'coverUrl': res['program']['coverUrl'],
    'title': title,
    'singers': nickname,
    'album': album,
  }
  return msg, metainfo
