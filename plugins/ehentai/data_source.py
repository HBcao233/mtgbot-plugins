from bs4 import BeautifulSoup
import asyncio
import re, os
import ujson as json

import util
import config
from util import logger
from util.telegraph import createPage, getPageList


env = config.env
ipb_member_id = env.get('ex_ipb_member_id', '')
ipb_pass_hash = env.get('ex_ipb_pass_hash', '')
igneous = env.get('ex_igneous', '')
eheaders = {
  'cookie': f'ipb_member_id={ipb_member_id};ipb_pass_hash={ipb_pass_hash};igneous={igneous}',
}
api_url = 'https://s.exhentai.org/api.php'


class PluginException(Exception):
  pass


async def get(url, params=None, headers=None, *args, **kwargs):
  if headers is None:
    headers = {}
  r = await util.get(url, params=params, headers={**eheaders, **headers}, *args, **kwargs)
  if "Your IP address has been" in r.text:
    raise PluginException("IP被禁")
  if "Not Found" in r.text:
    raise PluginException("页面不存在")
  return r


async def getImg(url, *args, **kwargs):
  return await util.getImg(url, headers=eheaders, *args, **kwargs)
  

def page_info(eid, _html):
  soup = BeautifulSoup(_html, "html.parser")
  name = soup.select("#i1 h1")[0].string
  url = soup.select("#i3 img")[0].attrs["src"]
  sn = soup.select("#i2 .sn div")[0].text

  prev = soup.select("#i2 #prev")[0].attrs["href"]
  next = soup.select("#i2 #next")[0].attrs["href"]
  source = soup.select("#i6 a")[2].attrs["href"]
  parent = soup.select("#i5 a")[0].attrs["href"]
  return (
    f"<code>{name}</code>\n"
    f"{sn}\n"
    f"此页: {eid}\n"
    f"前页：{prev}\n"
    f"后页：{next}\n"
    f"原图：{source}\n"
    f"画廊：{parent}"
  ), url


async def parseEidGMsg(eid, soup):
  title = soup.select("#gd2 #gj")[0].string
  num = soup.select("#gdd tr")[5].select(".gdt2")[
      0].text.replace(" pages", "")
  if not title:
    title = soup.select("#gd2 #gn")[0].string

  url = soup.select("#gd5 p")[2].a.attrs["onclick"].split("'")[1]
  r = await util.get(url, headers=eheaders)
  html = r.text
  soup2 = BeautifulSoup(html, "html.parser")

  magnets = []
  for i in soup2.select("table a"):
    torrent = i.attrs["href"]
    if torrent:
      match = re.search(r"(?<=/)([0-9a-f]{40})(?=.torrent)", torrent)
      if match:
        magnet = "magnet:?xt=urn:btih:" + str(match.group())
        magnets.append(magnet)
      
  return title, num, magnets 


async def gallery_info(gid, token):
  data=json.dumps({
    'method': 'gdata',
    'gidlist': [
      [gid, token]
    ],
    'namespace': 1
  })
  r = await util.post(api_url, data=data, headers=eheaders)
  try:
    res = r.json()
    if 'error' in res:
      raise PluginException('解析错误')
    res = res['gmetadata'][0]
  except:
    raise PluginException('解析错误')
  
  if res['title_jpn']:
    title = res['title_jpn']
  else:
    title = res['title']
  num = res['filecount']
  _magnets = []
  for i in res['torrents']:
    _magnets.append(f"· <code>magnet:?xt=urn:btih:{i['hash']}</code>")
  magnets = ''
  if _magnets:
    magnets = "磁力链：\n" + "\n".join(_magnets) + "\n"
    
  _tags = {
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
    
  if _tags['language']:
    _tags['language'] = _tags['language'][:1]
  _tags['other'] = _tags['mixed'] + _tags['other']
  
  ns = {
    'language': '语言',
    'female': '女性',
    'male': '男性',
    'other': '其他',
  }
  tags = []
  for k in ns:
    if _tags[k]:
      tags.append(ns[k] + ': ' + ' '.join(_tags[k]))
  tags = '\n'.join(tags)
  if tags:
    tags += "\n"
  return title, num, magnets, tags

    
async def get_telegraph(arr, title, num, nocache, mid):
  if not nocache:
    for i in await getPageList():
      if i['title'] == title:
        return i['url']
  gid = arr[2]
  eurl = f"https://{arr[0]}hentai.org/g/{gid}/{arr[3]}"
  num = int(num)
  bar = util.progress.Progress(mid, 100, '获取图片列表', False)
  
  class Res:
    def __init__(self, url=None, text=None):
      self.url = url 
      self.text = text
      
    def parse(self):
      if self.url:
        return {
          'tag': 'img',
          'attrs': {
            'src': self.url
          },
        } 
      return {
        'tag': 'p',
        'children': [self.text],
      }
      
  async def get_imgurl(i):
    nonlocal gid, imgkeys, showkey, client
    if i == 0:
      return Res(first_url)
      
    data=json.dumps({
      'method': 'showpage',
      'gid': gid,
      'page': i + 1,
      'imgkey': imgkeys[i],
      'showkey': showkey,
    })
    try:
      r = await client.post(api_url, data=data, headers=eheaders)
    except:
      try:
        r = await client.post(api_url, data=data, headers=eheaders)
      except:
        w = f'p{i+1} 获取失败'
        logger.warning(w, exc_info=1)
        return Res(None, w)
    match = re.search(r'''<a.*?load_image\((\d*),.*?'(.*?)'\).*?<img.*?src="(.*?)"''', r.json()['i3'])
    next_i, next_imgkey = match.group(1), match.group(2) 
    return Res(match.group(3))
      
  async def _parse(i):
    nonlocal gid, bar, urls, data, client
    key = f"es{gid}-{i}"
    if (url := data.get(key)):
      return Res(url)
    
    res = await get_imgurl(i)
    if res.url is None:
      return res
    url = res.url
    try:
      r = await client.post(
        'https://telegra.ph/upload',
        files={
          'file': (await client.get(url)).content
        }
      )
    except:
      logger.warning(f'p{i+1} 上传失败', exc_info=1)
      return Res(url)
    else:
      url = r.json()[0]['src']
      data[key] = url
    return Res(url)
    
  async def parse(i):
    res = await _parse(i)
    await bar.add(1)
    return res
  
  async with util.curl.Client(headers=dict(eheaders, referer=eurl)) as client:
    r = await client.get(eurl, params={'p': 0})
    soup = BeautifulSoup(r.text, "html.parser")
  
    urls = []
    for i in soup.select("#gdt a"):
      urls.append(i.attrs["href"])
    await bar.update(len(urls), min(num, 100))
  
    p = 1
    while len(urls) < min(num, 100):
      try:
        r = await client.get(eurl, params={'p': p})
        arr = BeautifulSoup(r.text, "html.parser").select("#gdt a")
        for i in arr:
          urls.append(i.attrs["href"])
        await bar.update(len(urls), min(num, 100))
      except Exception:
        logger.warning(f'未能成功获取所有p', exc_info=1)
        break
      p += 1
    
    bar.set_prefix('下载中...')
    bar.set_total(len(urls))
    # bar.percent = True
    bar.p = 0
    
    _pattern = re.compile(r'^(?:https?://)?(?:e[x-])hentai\.org/s/([0-9a-z]+)/([0-9a-z-]+)').match
    imgkeys = [_pattern(i).group(1) for i in urls]
    r = await client.get(urls[0], params={'p': p})
    showkey = re.search(r'var showkey ?= ?"(.*?)";', r.text).group(1)
    soup = BeautifulSoup(r.text, "html.parser")
    first_url = soup.select("#i3 img")[0].attrs["src"]
  
    data = util.Data('urls')
    tasks = [parse(i) for i in range(len(urls))]
    result = await asyncio.gather(*tasks)
  
  success_num = len(result)
  result.extend([
    Res(None, f"获取数量: {success_num} {f' / {num}' if num != success_num else ''}"),
    Res(None, f"原链接: {eurl}")
  ])
  content = [res.parse() for res in result]
  data.save()
  page = await createPage(title, content)
  return page
  