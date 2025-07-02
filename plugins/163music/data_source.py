import ujson as json
import base64
import codecs
import random
import asyncio

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
  mid = res['id']
  name = res['name']
  alia = ''
  if len(res['alia']) > 0:
    alia = f' ({res["alia"][0]})'
  url = f'https://music.163.com/#/song?id={mid}'
  singers = '、'.join(
    [
      f'<a href="https://music.163.com/#/artist?id={i["id"]}">{i["name"]}</a>'
      for i in res['ar']
    ]
  )
  msg = (
    f'<a href="{url}">{name}</a>{alia} - {singers} #163music\nvia @%s' % bot.me.username
  )
  return msg


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
    return False
  res = res['data'][0]
  return res['url'], res['type']


async def get_try_url(mid):
  # TODO:
  return


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
