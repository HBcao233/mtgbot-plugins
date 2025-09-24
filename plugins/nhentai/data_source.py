import asyncio
import os
import re
import json

import util
from util import logger
from util.telegraph import createPage, getPageList
from plugin import import_plugin

try:
  hosting = import_plugin('hosting')
except ModuleNotFoundError:
  hosting = None


class PluginException(Exception):
  pass


async def gallery_info(gid):
  url = f'https://nhentai.net/api/gallery/{gid}'
  headers = {'referer': f'https://nhentai.net/g/{gid}'}
  r = await util.get(url, headers=headers)
  try:
    res = r.json()
  except json.JSONDecodeError:
    raise PluginException('解析失败')

  logger.debug(f'nhentai: {res}')
  if 'error' in res:
    e = res['error']
    _dict = {'does not exist': '页面不存在'}
    raise PluginException(_dict.get(e, e))
  media_id = res['media_id']
  if res['title']['japanese']:
    title = res['title']['japanese']
  else:
    title = res['title']['english']
  try:
    num = res['num_pages']
    ext_dict = {
      'j': 'jpg',
      'p': 'png',
      'g': 'gif',
      'w': 'webp',
    }
    exts = [ext_dict[i['t']] for i in res['images']['pages']]
    _tags = [i['name'] for i in res['tags']]
  except Exception as e:
    logger.exception('解析失败')
    raise PluginException(f'解析失败 {type(e).__name__}: {e}')

  filepath = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'ehentai', 'ehtags-cn.json'
  )
  if not os.path.isfile(filepath):
    tags = _tags
  else:
    tags = []
    with open(filepath, 'r') as f:
      r = f.read()
      r = re.sub(r"""(?<=[}\]"'\d,])[,\s]+(?!\s*[{["'\d])""", '', r)
    tags_cn = json.loads(r)
    for i in _tags:
      tag = tags_cn.get(i, None)
      if isinstance(tag, dict):
        tag = tag.values()[0]
      if tag:
        tags.append('#' + tag)

  if tags:
    tags = '标签: ' + ' '.join(tags) + '\n'
  else:
    tags = ''
  return title, num, media_id, exts, tags


async def get_telegraph(gid, title, media_id, exts, nocache, mid):
  if not nocache:
    for i in await getPageList():
      if i['title'] == title:
        return i['url']
  num = len(exts)
  bar = util.progress.Progress(mid, total=num, prefix='下载中', percent=False)

  class Res:
    def __init__(self, url=None, text=None):
      self.url = url
      self.text = text

    def parse(self):
      if self.url:
        return {
          'tag': 'img',
          'attrs': {'src': self.url},
        }
      return {
        'tag': 'p',
        'children': [self.text],
      }

  async def _parse(i):
    nonlocal client
    key = f'nhentais{gid}-{i}'
    if url := data.get(key):
      return Res(url)

    url = f'https://i.nhentai.net/galleries/{media_id}/{i + 1}.{exts[i]}'

    try:
      logger.info(f'GET {util.curl.logless(url)}')
      img = await client.getImg(
        url,
        saveas=f'nhentaig{gid}_p{i + 1}',
        ext=exts[i], 
        headers={'referer': f'https://nhentai.net/g/{gid}'}
      )
      img = await util.media.to_img(img)
      url = await hosting.get_url(img)
    except Exception:
      w = f'p{i + 1} 获取失败'
      logger.warning(w, exc_info=1)
      return Res(None, w)
    else:
      with data:
        data[key] = url

    return Res(url)

  async def parse(i):
    res = await _parse(i)
    await bar.add(1)
    return res

  async with util.curl.Client(
    headers={'referer': f'https://nhentai.net/g/{gid}'}
  ) as client:
    data = util.Data('urls')
    tasks = [parse(i) for i in range(num)]
    result = await asyncio.gather(*tasks)

  success_num = len(result)
  result.extend(
    [
      Res(
        None,
        f'获取数量: {success_num} {f" / {num}" if num != success_num else ""}',
      ),
      Res(None, f'原链接: https://nhentai.net/g/{gid}'),
    ]
  )
  content = [i.parse() for i in result]
  data.save()

  page = await createPage(title, content)
  return page
