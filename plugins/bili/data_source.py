import asyncio
from functools import partial

import util
from util.log import logger
from .auth import gheaders, getMixinKey, wbi

# qn=80: 1080P
# qn=64: 720P
qn = 80


async def get_bili(bvid, aid):
  r = await util.get(
    'https://api.bilibili.com/x/web-interface/view',
    params={'aid': aid, 'bvid': bvid},
    headers=gheaders,
  )
  res = r.json()
  if res['code'] in [-404, 62002, 62004]:
    logger.info(r.text)
    return '视频不存在'
  elif res['code'] != 0:
    logger.info(r.text)
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

  dynamic = res.get('dynamic', '')
  if dynamic:
    dynamic = f'\n<blockquote expandable>{dynamic}</blockquote>'
  msg = (
    f'<a href="https://www.bilibili.com/video/{bvid}{p_url}">{title}{p_tip}</a> | '
    f'<a href="https://space.bilibili.com/{uid}">{nickname}</a> #Bilibili{dynamic}'
  )
  return bvid, aid, cid, title, msg


async def get_video(bvid, aid, cid, bar=None):
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
        progress_callback=bar.update if bar else None,
      )

    # 先按照id降序排序，再按照codecid升序排序
    videos = list(sorted(videos, key=lambda x: (-x['id'], x['codecid'])))
    logger.info(f'video qn: {videos[0]["id"]}, codecid: {videos[0]["codecid"]}')
    video_url = videos[0]['base_url']
    audios = list(sorted(audios, key=lambda x: -x['id']))
    audio_url = audios[0]['base_url']
    logger.info(f'audio qn: {audios[0]["id"]}')

    base = 'base_url'

    async def download_video():
      nonlocal video_url, base
      try:
        return await client.getImg(
          video_url,
          headers={'referer': f'https://www.bilibili.com/video/{bvid}'},
          progress_callback=partial(bar.update, line=1) if bar else None,
        )
      except Exception:
        if base != 'base_url':
          raise
        logger.warning(
          f'尝试获取视频 (id={videos[0]["id"]}, codecid={videos[0]["codecid"]}) {base} 失败',
          exc_info=1,
        )
        video_url = videos[0]['backup_url'][0]
        base = 'backup_url[0]'
        return await download_video()

    result = await asyncio.gather(
      download_video(),
      client.getImg(
        audio_url,
        headers={'referer': f'https://www.bilibili.com/video/{bvid}'},
        progress_callback=partial(bar.update, line=2) if bar else None,
      ),
    )

  path = util.getCache(f'{bvid}_{cid}.mp4')
  command = ['ffmpeg', '-i', result[0]]
  if result[1] != '':
    command.extend(['-i', result[1]])
  command.extend(['-c:v', 'copy', '-c:a', 'copy', '-y', path])
  logger.info(f'{command = }')

  returncode, stdout = await util.media.ffmpeg(command, progress_callback=bar.update)
  if returncode != 0:
    logger.error(stdout)
    return None
  return path


async def _get_video(bvid, cid, client=None):
  url = 'https://api.bilibili.com/x/player/wbi/playurl'
  mixin_key = await getMixinKey(client)
  params = {
    'bvid': bvid,
    'cid': cid,
    'qn': qn,
    'fnver': 0,
    'fnval': 4048,
    'fourk': 1,
    'try_look': 1,
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
