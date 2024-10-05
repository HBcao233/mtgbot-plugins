import asyncio
from functools import cmp_to_key

import util
from util.log import logger
from .auth import gheaders, getMixinKey, wbi

# qn=64 代表 720P
qn = 64


@cmp_to_key
def choose_video(x, y):
  """
  选择不大于 qn 的最大清晰度 (有大于qn选择qn, 没有则选择最大清晰度);
  多个qn则更倾向于选择 codecid=12 (HEVC 编码).
  """
  if x['id'] > qn:
    return 1
  if y['id'] > qn:
    return -1
  if x['id'] == y['id'] == qn:
    if x['codecid'] == 12:
      return -1
    if y['codecid'] == 12:
      return 1
    return 0
  if x['id'] < y['id']:
    return 1
  if x['id'] > y['id']:
    return -1
  return 0


async def get_bili(bvid, aid):
  r = await util.get(
    'https://api.bilibili.com/x/web-interface/view',
    params={'aid': aid, 'bvid': bvid},
    headers=gheaders,
  )
  res = r.json()
  if res['code'] in [-404, 62002, 62004]:
    return '视频不存在'
  elif res['code'] != 0:
    return '请求失败'
  return res['data']


def parse_msg(res, p=1):
  aid = res['aid']
  bvid = res['bvid']
  cid = res['cid']
  p_url = ''
  p_tip = ''
  if p > 1:
    p_url = '?p=' + str(p)
    p_tip = ' P' + str(p)
    for i in res['pages']:
      if i['page'] == p:
        cid = i['cid']
  title = res['title'].replace('&', '&gt;').replace('<', '&lt;').replace('>', '&gt;')
  uid = res['owner']['mid']
  nickname = res['owner']['name']
  msg = (
    f'[<code>{bvid}</code>] <a href="https://www.bilibili.com/video/{bvid}{p_url}">{title}{p_tip}</a> | '
    f'<a href="https://space.bilibili.com/{uid}">{nickname}</a> #Bilibili'
  )
  return bvid, aid, cid, title, msg


async def get_video(bvid, aid, cid, progress_callback=None):
  async with util.curl.Client(headers=gheaders) as client:
    video_url = None
    audio_url = None
    videos, audios = await _get_video(bvid, cid, client)
    if videos is None:
      return None
    if audios is None:
      video_url = videos
      return await client.getImg(
        video_url,
        headers={'referer': f'https://www.bilibili.com/video/{bvid}'},
        saveas=f'{bvid}_{cid}',
        ext='mp4',
      )

    videos = sorted(videos, key=choose_video)
    logger.info(f"qn: {videos[0]['id']}, codecid: {videos[0]['codecid']}")
    video_url = videos[0]['base_url']
    for i in audios:
      if i['id'] == 30216:
        audio_url = i['base_url']
        break

    result = await asyncio.gather(
      client.getImg(
        video_url, headers={'referer': f'https://www.bilibili.com/video/{bvid}'}
      ),
      client.getImg(
        audio_url, headers={'referer': f'https://www.bilibili.com/video/{bvid}'}
      ),
    )

  path = util.getCache(f'{bvid}_{cid}.mp4')
  command = ['ffmpeg', '-i', result[0]]
  if result[1] != '':
    command.extend(['-i', result[1]])
  command.extend(['-c:v', 'copy', '-c:a', 'copy', '-y', path])
  logger.info(f'{command = }')

  returncode, stdout = await util.media.ffmpeg(command, progress_callback)
  if returncode != 0:
    logger.error(stdout)
    return None
  return path


async def _get_video(bvid, cid, client=None):
  url = 'https://api.bilibili.com/x/player/wbi/playurl'
  mixin_key = await getMixinKey(client)
  params = {
    'fnver': 0,
    'fnval': 16,
    'qn': qn,
    'bvid': bvid,
    'cid': cid,
  }
  r = await client.get(
    url,
    params=wbi(mixin_key, params),
    headers={'referer': f'https://www.bilibili.com/video/{bvid}'},
  )
  # logger.info(r.text)
  res = r.json()['data']
  if 'dash' in res:
    return res['dash']['video'], res['dash']['audio']
  if 'durl' not in res:
    return None, None
  return res['durl'][0]['url'], None
