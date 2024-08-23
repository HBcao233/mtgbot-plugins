import asyncio, os, re
import ujson as json

import util
import config
from util import logger
from util.telegraph import createPage, getPageList


class PluginException(Exception):
  pass


async def get(url, params=None, headers=None, *args, **kwargs):
  if headers is None:
    headers = {}
  return r


async def gallery_info(gid):
  url = f"https://nhentai.net/api/gallery/{gid}"
  headers = { 'referer': f"https://nhentai.net/g/{gid}" }
  r = await util.get(url, headers=headers)
  res = r.json()
  if 'error' in res:
    e = res['error']
    _dict = {
      'does not exist': '页面不存在'
    }
    raise PluginException(_dict.get(e, e))
  media_id = res['media_id']
  if res['title']['japanese']:
    title = res['title']['japanese']
  else:
    title = res['title']['english']
  num = res['num_pages']
  ext_dict = {
    'j': 'jpg',
    'p': 'png',
    'g': 'gif',
  }
  exts = [ext_dict[i['t']] for i in res['images']['pages']]
  _tags = [i['name'] for i in res['tags']]
  
  filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ehentai', 'ehtags-cn.json')
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
    tags = "标签: " + ' '.join(tags) + "\n"
  else:
    tags = ""
  return title, num, media_id, exts, tags


async def get_telegraph(gid, title, media_id, exts, nocache, mid):
  if not nocache:
    for i in await getPageList():
      if i['title'] == title:
        return i['url'], []
  
  bar = util.progress.Progress(mid, total=len(exts))
  warnings = []
  
  async def parse(i):
    nonlocal warnings
    key = f"nhentais{gid}-{i}"
    if not nocache and (url := data.get(key)):
      await bar.add(1)
      return url
    
    url = f"https://i.nhentai.net/galleries/{media_id}/{i+1}.{exts[i]}"
    try:
      headers = { 'referer': f"https://nhentai.net/g/{gid}" }
      r = await util.post(
        'https://telegra.ph/upload',
        files={
          'file': (await util.get(url, headers=headers)).content
        }
      )
      url = r.json()[0]['src']
      data[key] = url
    except:
      warnings.append(f'p{i+1} 获取失败')
      logger.warning(traceback.format_exc())
    
    await bar.add(1)
    return url
  
  data = util.Data('urls')
  tasks = [parse(i) for i in range(len(exts))]
  content = [{
    'tag': 'img',
    'attrs': {
      'src': i,
    },
  } for i in await asyncio.gather(*tasks)] 
  data.save()
  
  page = await createPage(title, content)
  return page, warnings
  