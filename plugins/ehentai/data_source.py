from bs4 import BeautifulSoup
import asyncio
import re
import os
import ujson as json
import httpx

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


env = config.env
ipb_member_id = env.get('ex_ipb_member_id', '')
ipb_pass_hash = env.get('ex_ipb_pass_hash', '')
igneous = env.get('ex_igneous', '')
eheaders = {
  'cookie': f'ipb_member_id={ipb_member_id}; ipb_pass_hash={ipb_pass_hash}; igneous={igneous}; nw=1',
}
api_url = 'https://s.exhentai.org/api.php'
if any(i == '' for i in (ipb_member_id, ipb_pass_hash, igneous)):
  logger.warn(
    "env 'ex_ipb_member_id', 'ipb_pass_hash', 'igneous' 配置错误, exhentai 解析将不可用"
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


async def parseEidGMsg(eid, soup):
  title = soup.select('#gd2 #gj')[0].string
  num = soup.select('#gdd tr')[5].select('.gdt2')[0].text.replace(' pages', '')
  if not title:
    title = soup.select('#gd2 #gn')[0].string

  url = soup.select('#gd5 p')[2].a.attrs['onclick'].split("'")[1]
  r = await util.get(url, headers=eheaders)
  html = r.text
  soup2 = BeautifulSoup(html, 'html.parser')

  magnets = []
  for i in soup2.select('table a'):
    torrent = i.attrs['href']
    if torrent:
      match = re.search(r'(?<=/)([0-9a-f]{40})(?=.torrent)', torrent)
      if match:
        magnet = 'magnet:?xt=urn:btih:' + str(match.group())
        magnets.append(magnet)

  return title, num, magnets


async def gallery_info(gid, token):
  data = json.dumps({'method': 'gdata', 'gidlist': [[gid, token]], 'namespace': 1})
  r = await util.post(api_url, data=data, headers=eheaders)
  if 'IP address has been' in r.text:
    raise PluginException('请求过于频繁, IP被禁\n' + r.text)
  if 'Not Found' in r.text:
    raise PluginException('页面不存在')
  try:
    res = r.json()
    if 'error' in res:
      raise PluginException('解析错误')
    res = res['gmetadata'][0]
  except Exception:
    logger.error(f'解析错误: {r.text}', exc_info=1)
    raise PluginException('解析错误')

  if res['title_jpn']:
    title = res['title_jpn']
  else:
    title = res['title']
  num = res['filecount']
  _magnets = []
  for i in res['torrents']:
    _magnets.append(f'· <code>magnet:?xt=urn:btih:{i["hash"]}</code>')
  magnets = ''
  if _magnets:
    magnets = '磁力链：\n' + '\n'.join(_magnets) + '\n'

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
      tag = tags_cn.get(v, None)
      if isinstance(tag, dict):
        tag = tag.get(k, None)
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
  return title, num, magnets, tags + '\n'


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
  def __init__(self, arr, title, num, nocache, mid):
    self.eh = arr[0]
    self.gid = arr[2]
    self.gtoken = arr[3]
    self.eurl = f'https://{self.eh}hentai.org/g/{self.gid}/{self.gtoken}'
    self.num = int(num)
    self.total = min(self.num, 100)
    self.mid = mid
    self.bar = util.progress.Progress(mid, 100, '获取图片列表', False)

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
      logger.info(self.urls)
      try:
        result = await self.download_imgs(client)
      except PluginException as e:
        return str(e)
    return result

  async def get_urls(self, client):
    url = self.eurl
    logger.info(f'GET {logless(url)}')
    r = await client.get(url, params={'p': 0})
    if r.text == '':
      return '请求失败'
    if 'IP address has been' in r.text:
      return 'IP被禁\n' + r.text
    if 'Not Found' in r.text:
      return '页面不存在'

    soup = BeautifulSoup(r.text, 'html.parser')

    self.urls = []
    for i in soup.select('#gdt a'):
      self.urls.append(i.attrs['href'])
    await self.bar.update(len(self.urls), self.total)

    p = 1
    while len(self.urls) < self.total:
      try:
        logger.info(f'GET {logless(url)}?p={p}')
        r = await client.get(self.eurl, params={'p': p})
        if r.text == '':
          break
        soup = BeautifulSoup(r.text, 'html.parser')
        for i in soup.select('#gdt a'):
          self.urls.append(i.attrs['href'])
        await self.bar.update(len(self.urls), self.total)
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
      r'^(?:https?://)?(?:e[x-])hentai\.org/s/([0-9a-z]+)/([0-9a-z-]+)'
    ).match
    self.imgkeys = [_pattern(i).group(1) for i in self.urls]
    r = await client.get(self.urls[0])
    self.showkey = re.search(r'var showkey ?= ?"(.*?)";', r.text).group(1)
    soup = BeautifulSoup(r.text, 'html.parser')
    self.first_url = soup.select('#i3 img')[0].attrs['src']

    with util.Data('urls') as data:
      tasks = [self.download(i, client, data) for i in range(len(self.urls))]
      return await asyncio.gather(*tasks)

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
      img = await client.getImg(
        url,
        saveas=key,
        ext=True,
      )
      try:
        url = await hosting.get_url(img)
      except Exception:
        logger.warning('hosting.get_url 调用失败', exc_info=1)
        raise PluginException('上传失败')
    except Exception:
      logger.warning(f'p{i + 1} 上传失败', exc_info=1)
      return Res(url)
    else:
      data[key] = url
    return Res(url)

  async def get_imgurl(self, i, client):
    if i == 0:
      return Res(self.first_url)

    data = json.dumps(
      {
        'method': 'showpage',
        'gid': self.gid,
        'page': i + 1,
        'imgkey': self.imgkeys[i],
        'showkey': self.showkey,
      }
    )
    try:
      # logger.info(f'GET {logless(api_url)}')
      r = await client.post(api_url, data=data)
    except (httpx.ConnectError, httpx.ConnectTimeout):
      logger.warning(f'p{i + 1} 获取第一次尝试失败，正在重试')
      try:
        logger.info(f'retry GET {logless(api_url)}')
        r = await client.post(api_url, data=data)
      except httpx.ConnectError:
        w = f'p{i + 1} 获取失败'
        logger.warning(w)
        return Res(None, w)
    match = re.search(
      r'''<a.*?load_image\((\d*),.*?'(.*?)'\).*?<img.*?src="(.*?)"''', r.json()['i3']
    )
    # next_i, next_imgkey = match.group(1), match.group(2)
    return Res(match.group(3))


async def get_telegraph(arr, title, num, nocache, mid):
  if not nocache:
    for i in await getPageList():
      if i['title'] == title:
        return i['url']

  gt = GT(arr, title, num, nocache, mid)
  eurl = gt.eurl
  result = await gt.main()
  if isinstance(result, str):
    return {'code': 1, 'message': result}

  success_num = len(result)
  result.extend(
    [
      Res(None, f'获取数量: {success_num} {f" / {num}" if num != success_num else ""}'),
      Res(None, f'原链接: {eurl}'),
    ]
  )
  content = [res.parse() for res in result]
  page = await createPage(title, content)
  logger.info(f'生成telegraph: {page}')
  return page
