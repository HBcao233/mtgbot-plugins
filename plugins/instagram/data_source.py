import json
import os 
import httpx 
from datetime import datetime

import util
import config
from util.log import logger
from util.log import timezone


csrftoken = config.env.get('instagram_csrftoken', '')
sessionid = config.env.get('instagram_sessionid', '')
gheaders = {
  'cookie': f'sessionid={sessionid}',
  'X-Csrftoken': csrftoken,
}
if csrftoken == '' or sessionid == '':
  logger.warning('instagram_csrftoken或instagram_sessionid配置错误, instagram解析将不可用')

ig_proxy = config.env.get('ig_proxy', None)
logger.info(f'ig_proxy: {ig_proxy}')


async def media_info(shortcode):
  try:
    r = await util.post(
      'https://www.instagram.com/graphql/query',
      headers=gheaders,
      data={
        'query_hash': '477b65a610463740ccdb83135b2014db',
        'variables': f'{{"shortcode":"{shortcode}"}}',
      },
      proxy=ig_proxy,
    )
  except httpx.ConnectError:
    return '请求失败'
  if r.status_code != 200:
    logger.info(r.text)
    return '请求失败'
  try:
    res = r.json()['data']['shortcode_media']
  except (json.JSONDecodeError, KeyError):
    logger.info(r.text)
    return '解析失败'
  return res


def parse_info(info):
  shortcode = info['shortcode']
  url = f'https://www.instagram.com/p/{shortcode}/'
  fullname = info['owner']['full_name']
  username = info['owner']['username']
  author_url = f'https://www.instagram.com/{username}/'
  
  taken_at_timestamp = info['taken_at_timestamp']
  taken_datetime = datetime.fromtimestamp(taken_at_timestamp, timezone)
  taken_time = taken_datetime.strftime('%Y年%m月%d日 %H:%M:%S')
  
  captions = info['edge_media_to_caption']['edges']
  caption = ''
  if len(captions) > 0:
    caption = '\n'.join([i['node']['text'] for i in captions])
  if caption != '':
    caption = f'\n<blockquote expandable>{caption}\n{taken_time}</blockquote>'
  else:
    caption = f'\n{taken_time}'
  msg = (
    f'<a href="{url}">{shortcode}</a> - <a href="{author_url}">{fullname}</a> #instagram{caption}'
    f'\nvia @{bot.me.username}' 
  )
  return msg 


def parse_medias(info):
  # logger.info(info)
  medias = []
  m = [info]
  if 'edge_sidecar_to_children' in info:
    m = [i['node'] for i in info['edge_sidecar_to_children']['edges']]
  for ai in m:
    _type = 'photo'
    if ai['__typename'] == 'GraphImage':
      _type = 'photo'
      url = ai['display_url']
    elif info['__typename'] == 'GraphVideo':
      _type = 'video'
      url = ai['video_url']
    else:
      logger.info(ai['__typename'])
    
    ext = os.path.splitext(url.split('?')[0])[-1]
    
    medias.append({
      'type': _type,
      'key': f'ig_{ai["__typename"]}_{ai["id"]}',
      'url': url,
      'ext': ext,
      'is_video': ai['is_video'],
    })
  return medias