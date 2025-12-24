from bs4 import BeautifulSoup
import re
import os
import json
import httpx
import asyncio

import util
import config
from util.log import logger
from util.curl import logless
from util.telegraph import createPage, getPageList
from plugin import import_plugin

try:
  hosting = import_plugin('hosting')
except ModuleNotFoundError:
  hosting = None


# 最大获取画廊图片数量
MAX_FETCH_NUM = 200
# 并行下载数量
ASYNC_DOWNLOAD_CAPACITY = 3

env = config.env
ipb_member_id = env.get('ex_ipb_member_id', '')
ipb_pass_hash = env.get('ex_ipb_pass_hash', '')
igneous = env.get('ex_igneous', '')
eheaders = {
  'cookie': f'ipb_member_id={ipb_member_id}; ipb_pass_hash={ipb_pass_hash}; igneous={igneous}; nw=1',
}
api_url = 'https://s.exhentai.org/api.php'
has_cookie = all(i != '' for i in (ipb_member_id, ipb_pass_hash, igneous))
site_host = 'ex.fangliding.eu.org'
if not has_cookie:
  api_url = 'https://ex.fangliding.eu.org/domain/s/api.php'
  eheaders = {
    'cookie': 'nw=1',
  }
  logger.warn(
    "env 'ex_ipb_member_id', 'ipb_pass_hash', 'igneous' 配置错误, exhentai 解析将使用 fangliding"
  )


class PluginException(Exception):
  pass


async def get(url, params=None, headers=None, *args, **kwargs):
  if headers is None:
    headers = {}
  r = await util.get(
    url, params=params, headers={**eheaders, **headers}, *args, **kwargs
  )
  if 'IP address has been' in r.text:
    raise PluginException('IP被禁\n' + r.text)
  if 'Not Found' in r.text:
    raise PluginException('页面不存在')
  return r


async def getImg(url, *args, **kwargs):
  return await util.getImg(url, headers=eheaders, *args, **kwargs)


async def api_call(args):
  try:
    r = await util.post(
      api_url, 
      headers=eheaders,
      json=args,
    )
  except (httpx.ConnectError, httpx.ConnectTimeout):
    raise PluginException('连接失败')
  if 'IP address has been' in r.text:
    raise PluginException('请求过于频繁, IP被禁\n' + r.text)
  if 'Not Found' in r.text:
    raise PluginException('页面不存在')
  try:
    res = r.json()
    if 'error' in res:
      logger.error(f'解析错误: {res}')
      raise PluginException(f'解析错误: {res}')
  except Exception:
    logger.exception(f'解析错误: {r.text}')
    raise PluginException('解析错误')
  return res


async def api_gdata(gid, token):
  res = await api_call({
    'method': 'gdata', 
    'gidlist': [[gid, token]], 
    'namespace': 1,
  })
  res = res['gmetadata'][0]
  if 'error' in res:
    raise PluginException(f'请求错误: {res["error"]}')
  return res


async def api_showpage(gid, page, imgkey, showkey):
  res = await api_call({
    'method': 'showpage',
    'gid': gid,
    'page': page,
    'imgkey': imgkey,
    'showkey': showkey,
  })
  return res


def page_info(eid, _html):
  soup = BeautifulSoup(_html, 'html.parser')
  name = soup.select('#i1 h1')[0].string
  url = soup.select('#i3 img')[0].attrs['src']
  sn = soup.select('#i2 .sn div')[0].text

  prev = soup.select('#i2 #prev')[0].attrs['href']
  next = soup.select('#i2 #next')[0].attrs['href']
  source = soup.select('#i6 a')[2].attrs['href']
  parent = soup.select('#i5 a')[0].attrs['href']
  return (
    f'<code>{name}</code>\n'
    f'{sn}\n'
    f'此页: {eid}\n'
    f'前页：{prev}\n'
    f'后页：{next}\n'
    f'原图：{source}\n'
    f'画廊：{parent}'
  ), url

async def gallery_info(gid, token):
  res = await api_gdata(gid, token)
  info = {
    'title_jpn': res['title_jpn'],
    'title': res['title'],
    'num': res['filecount'],
  }
  _magnets = []
  for i in res['torrents']:
    _magnets.append(f'· <code>magnet:?xt=urn:btih:{i["hash"]}</code>')
  magnets = ''
  if _magnets:
    magnets = '磁力链：\n' + '\n'.join(_magnets) + '\n'
  info['magnets'] = magnets

  _tags: dict[str, list[str]] = {
    'language': [],
    'female': [],
    'male': [],
    'mixed': [],
    'other': [],
  }
  filepath = os.path.join(os.path.dirname(__file__), 'ehtags-cn.json')
  with open(filepath, 'r') as f:
    r = f.read()
    r = re.sub(r"""(?<=[}\]"'\d,])[,\s]+(?!\s*[{["'\d])""", '', r)
  tags_cn = json.loads(r)
  for i in res['tags']:
    k, v = i.split(':')
    if k in _tags:
      tag = tags_cn.get(v, v.replace(' ', '_'))
      if isinstance(tag, dict):
        tag = tag.get(k, v)
      if tag:
        _tags[k].append('#' + tag)

  _tags['other'] = _tags['mixed'] + _tags['other']
  categories = {
    'Doujinshi': '#同人志',
    'Manga': '#漫画',
    'Artist CG': '#画师CG',
    'Game CG': '#游戏CG',
    'Western': '#西方',
    'Non-H': '#无H',
    'Image Set': '#图集',
    'Cosplay': '#Cosplay',
    'Asian Porn': '#亚洲色情',
    'Misc': '#其他',
    'Private': '#私有',
  }
  if res['category'] in categories:
    _tags['category'] = [categories[res['category']]]
  else:
    logger.warning(f'未知画廊分类: {res["category"]}')

  ns = {
    'category': '分类',
    'language': '语言',
    'female': '女性',
    'male': '男性',
    'other': '其他',
  }
  # 命名空间名: #标签1 #标签2
  tags = '\n'.join(ns[k] + ': ' + ' '.join(_tags[k]) for k in ns if _tags[k])
  info['tags'] = tags + '\n'
  return info


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


class GT:
  def __init__(self, arr, title, start, num, nocache, mid):
    self.eh = arr[0]
    self.gid = arr[2]
    self.gtoken = arr[3]
    site = f'{self.eh}hentai.org' if has_cookie else site_host
    self.eurl = f'https://{site}/g/{self.gid}/{self.gtoken}'
    self.start = start
    self.num = int(num)
    self.end = min(start + 200, num)
    self.total = self.end - self.start + 1
    self.mid = mid
    self.start_p = (self.start - 1) // 20
    self.pages = (self.total - 1) // 20 + 1
    self.bar = util.progress.Progress(mid, self.pages, '获取图片列表中...', False)

  async def main(self):
    async with util.curl.Client(
      headers={
        **eheaders,
        'referer': self.eurl,
      },
      timeout=20,
    ) as client:
      res = await self.get_urls(client)
      if isinstance(res, str):
        return res
      # logger.info(self.urls)
      try:
        result = await self.download_imgs(client)
      except PluginException as e:
        return str(e)
    return result

  async def get_urls(self, client):
    await self.mid.edit('获取图片列表中...')
    
    url = self.eurl
    logger.info(f'GET {logless(url)}')
    try: 
      r = await client.get(url, params={'p': self.start_p})
    except httpx.ReadTimeout:
      return '请求超时'
    
    if r.text == '':
      return '请求失败'
    if 'IP address has been' in r.text:
      return 'IP被禁\n' + r.text
    if 'Not Found' in r.text:
      return '页面不存在'

    soup = BeautifulSoup(r.text, 'html.parser')

    self.urls = {}
    for i, tag in enumerate(soup.select('#gdt a')):
      self.urls[f'p{self.start_p * 20 + i}'] = tag.attrs['href']
    await self.bar.add(1)

    p = self.start_p + 1
    while len(self.urls) < self.total:
      try:
        logger.info(f'GET {logless(url)}?p={p}')
        r = await client.get(self.eurl, params={'p': p})
        if r.text == '':
          break
        soup = BeautifulSoup(r.text, 'html.parser')
        for i, tag in enumerate(soup.select('#gdt a')):
          self.urls[f'p{p * 20 + i}'] = tag.attrs['href']
        await self.bar.add(1)
      except Exception:
        logger.warning('未能成功获取所有p', exc_info=1)
        break
      p += 1

  async def download_imgs(self, client):
    await self.mid.edit('下载中...')
    self.bar.set_prefix('下载中...')
    self.bar.set_total(len(self.urls))
    # bar.percent = True
    self.bar.p = 0

    _pattern = re.compile(
      r'^(?:https?://)?(?:e[x-])(?:hentai|\.fangliding\.eu)\.org/s/([0-9a-z]+)/([0-9a-z-]+)'
    ).match
    self.imgkeys = {k: _pattern(v).group(1) for k, v in self.urls.items()}
    r = await client.get(self.urls[f'p{self.start - 1}'])
    self.showkey = re.search(r'var showkey ?= ?"(.*?)";', r.text).group(1)
    soup = BeautifulSoup(r.text, 'html.parser')
    self.first_url = soup.select('#i3 img')[0].attrs['src']

    # 并行数 
    semaphore = asyncio.Semaphore(ASYNC_DOWNLOAD_CAPACITY)
    
    async def limited_download(index, client, data):
      async with semaphore:
        return await self.download(index, client, data)
    
    with util.Data('urls') as data:
      tasks = [
        limited_download(i, client, data) 
        for i in range(self.start - 1, self.end)
      ]
      result = await asyncio.gather(*tasks)
    return result

  async def download(self, i, client, data):
    res = await self._download(i, client, data)
    await self.bar.add(1)
    return res

  async def _download(self, i, client, data):
    key = f'es{self.gid}_{i}'
    if url := data.get(key):
      return Res(url)

    res = await self.get_imgurl(i, client)
    if res.url is None:
      return res
    url = res.url
    try:
      logger.info(f'GET {logless(url)}')
      try:
        img = await client.getImg(
          url,
          saveas=key,
          ext=True,
        )
      except (httpx.ConnectTimeout, httpx.RemoteProtocolError):
        # 重试
        img = await client.getImg(
          url,
          saveas=key,
          ext=True,
        )
      img = await util.media.to_img(img)
      try:
        url = await hosting.get_url(img)
      except Exception:
        logger.warning('hosting.get_url 调用失败', exc_info=1)
        raise PluginException('上传失败')
    except Exception:
      logger.warning(f'p{i + 1} 上传失败', exc_info=1)
      return Res(f'p{i + 1} 获取失败')
    else:
      if url:
        data[key] = url
    return Res(url)

  async def get_imgurl(self, i, client):
    if i == 0:
      return Res(self.first_url)

    print(i, self.imgkeys[f'p{i}'])
    try:
      res = await api_showpage(
        self.gid, 
        i + 1, 
        self.imgkeys[f'p{i}'], 
        self.showkey,
      )
    except PluginException as e:
      logger.exception(f'page{i+1} 获取失败')
      return Res(None, f'page{i+1} 获取失败: {e}')
    match = re.search(
      r'''<a.*?load_image\((\d*),.*?'(.*?)'\).*?<img.*?src="(.*?)"''',
      res['i3'],
    )
    # next_i, next_imgkey = match.group(1), match.group(2)
    return Res(match.group(3))


async def get_telegraph(arr, title, start, num, nocache, mid):
  """
  if not nocache:
    for i in await getPageList():
      if i['title'] == title:
        return i['url']
  """
  
  gt = GT(arr, title, start, num, nocache, mid)
  eurl = gt.eurl
  result = await gt.main()
  if isinstance(result, str):
    return {'code': 1, 'message': result}

  success_num = len(result)

  num_tip = ''
  p_tip = ''
  if num != success_num:
    num_tip = f' / {num}'
  if start > 1:
    p_tip = f' (p{start}~{gt.end})'
  result.extend(
    [
      Res(
        None,
        f'获取数量: {success_num} {num_tip}{p_tip}',
      ),
      Res(None, f'原链接: {eurl}'),
    ]
  )
  content = [res.parse() for res in result]
  page = await createPage(title, content)
  logger.info(f'生成telegraph: {page}')
  return page
