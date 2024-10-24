import re
import asyncio
import os.path
from datetime import datetime
import httpx
from asyncio.subprocess import PIPE

import util
import config
from util.log import logger


PHPSESSID = config.env.get('pixiv_PHPSESSID', '')
gheaders = {'cookie': f'PHPSESSID={PHPSESSID};'}
max_comment_length = 600


class PixivClient(util.curl.Client):
  def __init__(
    self,
    pid,
    *,
    proxy=True,
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
      proxy=proxy, headers=_headers, follow_redirects=follow_redirects, timeout=timeout
    )

  async def get_pixiv(self):
    try:
      r = await self.get(f'https://www.pixiv.net/ajax/illust/{self.pid}')
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
    if not os.path.isdir(util.getCache(name + '/')):
      zi = await self.getImg(
        res['src'],
        saveas=name,
        ext='zip',
      )
      proc = await asyncio.create_subprocess_exec(
        'unzip',
        '-o',
        '-d',
        util.getCache(name + '/'),
        zi,
        stdout=PIPE,
        stdin=PIPE,
        stderr=PIPE,
      )
      await proc.wait()

    f = frames[0]['file']
    f, ext = os.path.splitext(f)
    rate = str(round(1000 / frames[0]['delay'], 2))
    img = util.getCache(f'{self.pid}.mp4')
    # fmt: off
    command = [
      'ffmpeg', 
      '-framerate', rate, 
      '-loop', '0', 
      '-f', 'image2',
      '-i', util.getCache(name + f'/%{len(f)}d{ext}'), 
      '-r', rate, 
      '-c:v', 'h264', 
      '-pix_fmt', 'yuv420p', 
      '-vf', "pad=ceil(iw/2)*2:ceil(ih/2)*2", 
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
  if any((tag := t) in tags for t in ['#R18', '#R17.9']):
    props.append('#NSFW')
    props.append(tag)
  if '#R18G' in tags:
    props.append('#R18G')
    props.append('#NSFW')
  if res['illustType'] == 2:
    props.append('#动图')
  if res['aiType'] == 2:
    props.append('#AI生成')
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

  msg = (
    f'{prop}[<code>{pid}</code>] <a href="https://www.pixiv.net/artworks/{pid}/">{title}</a>'
    f' | <a href="https://www.pixiv.net/users/{uid}/">{username}</a> #pixiv'
    + (
      ''
      if hide
      else f"{comment}\n<blockquote expandable>{' '.join(i for i in tags if i not in ['#R18', '#R18G'])}</blockquote>"
    )
  )
  return msg, tags


async def get_telegraph(res, tags, client, mid):
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
    nonlocal data, client
    _key = f'pximg{pid}-{i}'
    if url := data.get(_key, None):
      return Res(url)
    try:
      r = await client.get(imgUrl.replace('_p0', f'_p{i}'))
      r.raise_for_status()
      return Res(await util.curl.postimg_upload(r.content, client))
    except Exception:
      return Res(None, f'p{i+1} 获取失败')
    else:
      with data:
        data[_key] = url

  async def parse(i):
    res = await _parse(i)
    await bar.add(1)
    return res

  data = util.Data('urls')
  now = datetime.now()
  pid = res['illustId']
  key = f'{pid}-{now:%m-%d}'
  count = res['pageCount']
  bar = util.progress.Progress(mid, count, '上传中...', False)
  if not (url := data[key]):
    imgUrl = res['urls']['regular']
    tasks = (parse(i) for i in range(count))
    result = await asyncio.gather(*tasks)
    result.append(
      Res(None, f'原链接: https://www.pixiv.net/artworks/{pid}'),
    )
    content = [i.parse() for i in result]
    url = await util.telegraph.createPage(
      f"[pixiv] {pid} {res['illustTitle']}", content
    )
    with data:
      data[key] = url

  msg = (
    f"标题: {res['illustTitle']}\n"
    f"标签: {' '.join(tags)}\n"
    f"作者: <a href=\"https://www.pixiv.net/users/{res['userId']}/\">{res['userName']}</a>\n"
    f"数量: {res['pageCount']}\n"
    f"<a href=\"{url}\">预览</a> | <a href=\"https://www.pixiv.net/artworks/{pid}\">原链接</a>"
  )
  return url, msg
