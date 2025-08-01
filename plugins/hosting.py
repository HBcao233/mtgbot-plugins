from urllib.parse import urlparse
import os
import re
import time
import random
import config
import util


hosting_host = config.env.get('hosting_host', '')
hosting_root = os.path.join(config.botRoot, 'hosting')
if hosting_host:
  u = urlparse(hosting_host)
  if u.scheme == '' and u.netloc == '':
    hosting_host = 'http://' + u.path.split('/')[0]
  else:
    hosting_host = u.netloc
    if u.scheme:
      hosting_host = f'{u.scheme}://{u.netloc}'
# logger.info(hosting_host)


async def get_url(path: str, rename: str = None) -> str:
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
  r = await util.post(
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
  async with util.curl.Client() as client:
    r = await client.get(url)
  match = re.search(r'<input id="code_direct".*?value="(.*?)"', r.text)
  return match and match.group(1)
