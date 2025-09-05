from datetime import datetime
from asyncio.subprocess import PIPE
import re
import asyncio
import os
import httpx
import time

import util
import config
from util.log import logger
from util.log import timezone
from plugin import import_plugin


try:
  hosting = import_plugin('hosting')
except ModuleNotFoundError:
  hosting = None


PHPSESSID = config.env.get('pixiv_PHPSESSID', '')
gheaders = {'cookie': f'PHPSESSID={PHPSESSID};'}
max_comment_length = 600


class PixivClient(util.curl.Client):
  def __init__(
    self,
    pid,
    *,
    proxy=None,
    headers=None,
    follow_redirects=True,
    timeout=None,
    **kwargs,
  ):
    self.pid = pid
    if headers is None:
      headers = {}
    _headers = httpx.Headers(gheaders)
    _headers.update({'referer': f'https://www.pixiv.net/artworks/{pid}'})
    _headers.update(headers)
    super().__init__(
      proxy=proxy,
      headers=_headers,
      follow_redirects=follow_redirects,
      timeout=timeout,
    )

  async def get_pixiv(self):
    try:
      url = f'https://www.pixiv.net/ajax/illust/{self.pid}'
      logger.info(f'GET {url}')
      r = await self.get(url)
    except Exception:
      return '连接超时'
    res = r.json()
    if 'error' in res and res['error']:
      logger.error(r.text)
      if res['message'] == '':
        res['message'] = '尚无此页'
      return '错误: ' + res['message']
    return res['body']

  async def get_anime(self):
    name = f'{self.pid}_ugoira'
    r = await self.get(f'https://www.pixiv.net/ajax/illust/{self.pid}/ugoira_meta')
    res = r.json()['body']
    frames = res['frames']
    _dir = util.getCache(name + '/')
    if not os.path.isdir(_dir):
      zi = await self.getImg(
        res['src'],
        saveas=name,
        ext=True,
      )
      _, _ext = os.path.splitext(zi)
      os.mkdir(_dir)
      if _ext == '.zip':
        proc = await asyncio.create_subprocess_exec(
          'unzip',
          '-d',
          _dir,
          zi,
          stdout=PIPE,
          stdin=PIPE,
          stderr=PIPE,
        )
      else:
        proc = await asyncio.create_subprocess_exec(
          'tar',
          'xf',
          zi,
          '-C',
          _dir,
          stdout=PIPE,
          stdin=PIPE,
          stderr=PIPE,
        )
      await proc.wait()

    s = []
    for i in frames:
      file = os.path.join(_dir, i['file'])
      delay = i['delay'] / 1000
      s.append(f"file '{file}'")
      s.append(f"duration {delay:.3f}")
    s = '\n'.join(s)
    frames_txt = util.getCache(f'{self.pid}_frames.txt')
    with open(frames_txt, 'w') as f:
      f.write(s)
    
    img = util.getCache(f'{self.pid}_ugoira.mp4')
    
    # fmt: off
    command = [
      'ffmpeg', 
      '-f', 'concat', 
      '-safe', '0', 
      '-i', frames_txt, 
      '-c:v', 'h264', 
      '-pix_fmt', 'yuv420p', 
      '-vf', "pad=ceil(iw/2)*2:ceil(ih/2)*2", 
      '-movflags',
      '+faststart',
      '-y', img
    ]
    # fmt: on
    proc = await asyncio.create_subprocess_exec(
      *command, stdout=PIPE, stdin=PIPE, stderr=PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0 and stderr:
      logger.warning(stderr.decode('utf8'))
      return False

    for i in os.listdir(_dir):
      os.remove(os.path.join(_dir, i))
    os.rmdir(_dir)

    logger.info(f'生成动图成功: {img}')
    return img


def parse_msg(res, hide=False):
  pid = res['illustId']

  tags = []
  for i in res['tags']['tags']:
    tags.append(('#' + i['tag']).replace('#R-', '#R').replace(' ', '_'))
    if 'translation' in i.keys():
      tags.append(('#' + i['translation']['en']).replace('#R-', '#R').replace(' ', '_'))

  props = []
  if res['aiType'] == 2:
    props.append('#AI生成')
    tags.insert(0, '#AI生成')
  if any((tag := t) in tags for t in ['#R18', '#R17.9']):
    props.append(tag)
  if '#R18G' in tags:
    props.append('#R18G')
  if any((tag := t) in tags for t in ['#R18', '#R17.9', '#R18G']):
    props.append('#NSFW')
  if res['illustType'] == 2:
    props.append('#动图')
  prop = ' '.join(props)
  if prop != '':
    prop += '\n'

  title = res['illustTitle']
  uid = res['userId']
  username = res['userName']
  if not hide:
    comment = res['illustComment']
    comment = (
      comment.replace('<br />', '\n')
      .replace('<br/>', '\n')
      .replace('<br>', '\n')
      .replace(' target="_blank"', '')
    )
    comment = re.sub(r'<span[^>]*>(((?!</span>).)*)</span>', r'\1', comment)
    if len(comment) > max_comment_length:
      comment = re.sub(r'<[^/]+[^<]*(<[^>]*)?$', '', comment[:max_comment_length])
      comment = re.sub(r'\n$', '', comment)
      comment = comment + '\n......'
    if comment != '':
      comment = ':\n<blockquote expandable>' + comment + '</blockquote>'
  
  createDate = datetime.strptime(res['createDate'], r'%Y-%m-%dT%H:%M:%S%z')
  createDate.astimezone(timezone)
  createDate = createDate.strftime('%Y年%m月%d日 %H:%M:%S')
  
  msg = (
    f'{prop}<a href="https://www.pixiv.net/artworks/{pid}/">{title}</a>'
    f' | <a href="https://www.pixiv.net/users/{uid}/">{username}</a> #pixiv [<code>{pid}</code>]'
  )
  if not hide:
    msg += f'{comment}\n<blockquote expandable>{" ".join(i for i in tags if i not in ["#R18", "#R18G"])}</blockquote>\n{createDate}'
  return msg, tags


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


async def get_url(imgUrl, pid, i, client, bar):
  data = util.Data('urls')
  img_url = imgUrl.replace('p0', f'p{i}')
  name = f'{pid}_p{i}_regular'
  if url := data.get(name):
    await bar.add(1)
    return Res(url)
  
  async def get_img_retry():
    for j in range(4):
      try:
        logger.info(f'GET {util.curl.logless(img_url)}')
        return await client.getImg(
          img_url,
          saveas=name,
          ext=True,
          timeout=30,
        )
      except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadTimeout):
        time.sleep(1)
        logger.info(f'p{i} 重试 第{j+1}次')
        if j >= 3:
          return Res(None, f'p{i}获取失败')
  img = await get_img_retry()
  if isinstance(img, Res):
    return img
  url = await hosting.get_url(img)
  with data:
    data[name] = url
  await bar.add(1)
  return Res(url)


async def get_telegraph(res, tags, client, mid, nocache):
  data = util.Data('urls')
  now = datetime.now()
  pid = res['illustId']
  key = f'{pid}-{now:%m-%d}'
  count = res['pageCount']
  if not (url := data.get(key)) or nocache:
    bar = util.progress.Progress(
      mid,
      total=count,
      prefix='下载中...',
    )
    imgUrl = res['urls']['regular']
    async with PixivClient(pid) as client:
      tasks = [get_url(imgUrl, pid, i, client, bar) for i in range(count)]
      gather_task = asyncio.gather(*tasks)
      result = await gather_task
    num = sum(1 if getattr(i, 'url') else 0 for i in result)
    result.append(
      Res(None, f'原链接: https://www.pixiv.net/artworks/{pid}'),
    )
    result.append(Res(None, f'获取数量: {num} / {count}'))
    content = [i.parse() for i in result]
    url = await util.telegraph.createPage(
      f'[pixiv] {pid} {res["illustTitle"]}', content,
    )
    with data:
      data[key] = url

  msg = (
    f'标题: {res["illustTitle"]}\n'
    f'标签: {" ".join(tags)}\n'
    f'<a href="{url}">预览</a> | <a href="https://www.pixiv.net/artworks/{pid}">原链接</a>\n'
    f'作者: <a href="https://www.pixiv.net/users/{res["userId"]}/">{res["userName"]}</a>\n'
    f'数量: {res["pageCount"]}'
  )
  return url, msg
