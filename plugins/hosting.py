from urllib.parse import urlparse
import os
import re
import time
import random
import config
import util
from util.log import logger


hosting_host = config.env.get('hosting_host', '')
picgo_api_key = config.env.get('picgo_api_key', '')
picgo_album_id = config.env.get('picgo_album_id', '')
hosting_root = os.path.join(config.botRoot, 'hosting')
if hosting_host:
  u = urlparse(hosting_host)
  if u.scheme == '' and u.netloc == '':
    hosting_host = 'http://' + u.path
  else:
    hosting_host = f'http://{u.netloc}{u.path}'
    if u.scheme:
      hosting_host = f'{u.scheme}://{u.netloc}{u.path}'
# logger.info(hosting_host)


async def get_url(path: str, rename: str = None) -> str:
  if picgo_api_key:
    return await upload_picgo(path, rename)
  if hosting_host:
    return upload_local(path, rename)
  return await upload_postimage(path, rename)


def upload_local(path, rename=None):
  dirname, name = os.path.split(path)
  if rename is not None:
    name = rename
  target_path = os.path.join(hosting_root, name)
  with open(path, 'rb') as f1:
    with open(target_path, 'wb') as f2:
      f2.write(f1.read())

  return f'{hosting_host}/{name}'


async def upload_postimage(path, rename=None):
  file = open(path, 'rb')
  if rename is not None:
    file = (rename, file, '')
  now = str(int((time.time()) * 1000))
  now += '.'
  for i in range(16):
    now += str(random.randint(0, 9))
  async with util.curl.Client(
    follow_redirects=False,
    timeout=30,
  ) as client:
    r = await client.post(
      'https://postimages.org/json/rr',
      headers={
        'origin': 'https://postimages.org',
        'referer': 'https://postimages.org/',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
      },
      data={
        'gallery': '',
        'optsize': 0,
        'expire': 0,
        'numfiles': 1,
        'upload_session': now,
      },
      files={'file': file},
    )
    if r.status_code != 200:
      return {'code': 1, 'message': '请求失败'}
    res = r.json()
    if res['status_code'] != 200:
      return {'code': 1, 'message': '上传失败'}

    url = res['url']
    r = await client.get(url)
  match = re.search(r'<input id="code_direct".*?value="(.*?)"', r.text)
  return match and match.group(1)


async def upload_picgo(path, rename=None):
  if not picgo_api_key:
    return {'code': 1, 'message': 'picgo_api_key 未配置'}
  file = open(path, 'rb')
  if rename is not None:
    file = (rename, file, '')

  r = await util.post(
    'https://www.picgo.net/api/1/upload',
    headers={
      'X-API-Key': picgo_api_key,
    },
    data={
      'album_id': picgo_album_id,
    },
    files={
      'source': file,
    },
  )
  if r.status_code != 200:
    return {'code': 1, 'message': '连接失败'}
  res = r.json()
  logger.debug(f'picgo: {res}')
  if res['status_code'] != 200:
    error = res.get('error', {}).get('message', '')
    return {'code': 1, 'message': f'上传失败: {error}'}
  return res['image']['url']
