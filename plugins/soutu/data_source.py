from functools import cmp_to_key
from urllib.parse import urlparse
import os
import ujson as json

import util
import config
from util.log import logger


saucenao_api_key = config.env.get('saucenao_api_key', '')
if saucenao_api_key == '':
  logger.warn('saucenao_api_key 未配置, saucenao 搜索将不可用')


async def to_img(path):
  _name = os.path.basename(path)
  name = os.path.splitext(_name)[0]
  img = util.getCache(f'{name}_img.jpg')
  command = [
    'ffmpeg',
    '-i',
    path,
    '-frames:v',
    '1',
    img,
    '-y',
  ]
  returncode, stdout = await util.media.ffmpeg(command)
  if returncode != 0:
    logger.error(stdout)
    return False
  return img


async def saucenao_search(path):
  data = util.Data('saucenao_result')
  if res := data.get(path):
    res['header']['cache'] = True
    return parse_saucenao(res)

  r = await util.post(
    f'https://saucenao.com/search.php',
    params={
      'db': 999,
      'output_type': 2,
      'numres': 16,
      'api_key': saucenao_api_key,
    },
    files={'file': open(path, 'rb')},
  )
  res = r.json()
  with data:
    data[path] = res
  return parse_saucenao(res)


def parse_saucenao(res):
  if res['header']['status'] == -1:
    msg = res['header']['message']
    if msg == 'The anonymous account type does not permit API usage.':
      msg = 'api_key 未配置'
    return msg
  if res['header']['results_returned'] <= 0:
    return '无结果'
  short_remaining = res['header']['short_remaining']
  long_remaining = res['header']['long_remaining']
  minimum_similarity = float(res['header']['minimum_similarity'])
  if float(res['results'][0]['header']['similarity']) <= minimum_similarity:
    logger.info(res)
    return '结果相似度过低'

  results = [
    i for i in res['results'] if float(i['header']['similarity']) > minimum_similarity
  ]

  def cmp(x, y):
    i = x['header']['index_id']
    j = y['header']['index_id']
    if i == 5 and j != 5:
      return -1
    if i == j == 5:
      return 0
    if i != 5 and j == 5:
      return 1
    if i == 27 and j != 27:
      return -1
    if i == j == 27:
      return 0
    if i != 27 and j == 27:
      return 1
    return i - j

  results = sorted(results, key=cmp_to_key(cmp))

  msgs = []
  for i in results:
    index_id = i['header']['index_id']
    thumbnail = i['header']['thumbnail']
    similarity = i['header']['similarity']
    if index_id == 5 or index_id == 6:
      # 5->pixiv 6->pixiv historical
      illust_id = i['data']['pixiv_id']
      title = i['data']['title']
      member_id = i['data']['member_id']
      member_name = i['data']['member_name']
      msgs.append(
        f'项目: pixiv\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'链接: <a href="https://www.pixiv.net/artworks/{illust_id}">{title}</a>\n'
        f'画师: <a href="https://www.pixiv.net/users/{member_id}">{member_name}</a>'
      )
    elif index_id == 8:
      service_name = 'seiga'
      member_id = results['results'][0]['data']['member_id']
      illust_id = results['results'][0]['data']['seiga_id']

    elif index_id == 9 or index_id == 12:
      creator = i['data']['creator']
      source = i['data']['source']
      if 'i.pximg.net' in source:
        pid = source.split('/')[-1]
        if (f := pid.find('_')) != -1:
          pid = pid[:f]
        source = f'https://www.pixiv.net/artworks/{pid}'
      u = urlparse(source)
      host = u.netloc.replace('www.', '')
      m = (
        f'项目: Danbooru/Yande/Gelbooru\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'作者: {creator}\n'
        f'来源: <a href="{source}">{host}</a>'
      )
      if t := i['data'].get('danbooru_id'):
        m += f'\nDanbooru: <a href="https://danbooru.donmai.us/post/show/{t}">danbooru_{t}</a>'
      if t := i['data'].get('yandere_id'):
        m += f'\nYande: <a href="https://yande.re/post/show/{t}">yande_{t}</a>'
      if t := i['data'].get('gelbooru_id'):
        m += f'\nGelbooru: <a href="https://gelbooru.com/index.php?page=post&s=view&id={t}">gelbooru_{t}</a>'
      msgs.append(m)

    elif index_id == 10:
      service_name = 'drawr'
      member_id = results['results'][0]['data']['member_id']
      illust_id = results['results'][0]['data']['drawr_id']
    elif index_id == 11:
      service_name = 'nijie'
      member_id = results['results'][0]['data']['member_id']
      illust_id = results['results'][0]['data']['nijie_id']

    elif index_id == 18:
      jp_name = i['data']['jp_name']
      eng_name = i['data']['eng_name']
      msgs.append(
        '项目: NHentai\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'日文标题: <code>{jp_name}</code>\n'
        f'英文标题: <code>{eng_name}</code>'
      )

    elif index_id == 27:
      creator = i['data']['creator']
      sankaku_id = i['data']['sankaku_id']
      msgs.append(
        '项目: Sankaku\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'链接: <a href="https://chan.sankakucomplex.com/post/show/{sankaku_id}">sankaku_{sankaku_id}</a>\n'
        f'作者: {creator}'
      )
    elif index_id == 20:
      url = i['data']['url']
      title = i['data']['title']
      member_name = i['data']['member_name']
      member_id = i['data']['member_id']
      member_url = f'https://medibang.com/author/{member_id}'
      msgs.append(
        '项目: MediBang\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'链接: <a href="{url}">{title}</a>\n'
        f'作者: <a href="{member_url}">{member_name}</a>'
      )
    elif index_id == 31:
      bcy_id = i['data']['bcy_id']
      url = f'https://bcy.net/illust/detail/{bcy_id}'
      title = i['data']['title']
      author_name = i['data']['author_name']
      author_url = i['data']['author_url']
      msgs.append(
        '项目: deviantArt2\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'链接: <a href="{url}">{title}</a>\n'
        f'作者: <a href="{author_url}">{author_name}</a>'
      )
    elif index_id == 34:
      da_id = i['data']['da_id']
      url = f'https://deviantart.com/view/{da_id}'
      title = i['data']['title']
      author_name = i['data']['author_name']
      author_url = i['data']['author_url']
      msgs.append(
        '项目: deviantArt2\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'链接: <a href="{url}">{title}</a>\n'
        f'作者: <a href="{author_url}">{author_name}</a>'
      )
    elif index_id == 39:
      as_project = i['data']['as_project']
      url = f'https://www.artstation.com/artwork/{as_project}'
      title = i['data']['title']
      author_name = i['data']['author_name']
      author_url = i['data']['author_url']
      msgs.append(
        '项目: Artstation\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'链接: <a href="{url}">{title}</a>\n'
        f'作者: <a href="{author_url}">{author_name}</a>'
      )
    elif index_id == 37 or index_id == 371:
      md_id = i['data']['md_id']
      url = f'https://mangadex.org/chapter/{md_id}/'
      source = i['data']['source']
      part = i['data']['part']
      author = i['data']['author']
      artist = i['data']['artist']
      msg = (
        '项目: MangaDex2\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'链接: <a href="{url}">{source} {part}</a>\n'
        f'作者: {author}\n'
        f'艺术家: {artist}'
      )
      if t := i['data'].get('mu_id'):
        msg += f'\nhttps://www.mangaupdates.com/series.html?id={t}'
      if t := i['data'].get('mal_id'):
        msg += f'\nhttps://myanimelist.net/manga/{t}/'
      msgs.append(msg)
  if not res['header'].get('cache'):
    msgs.append(
      f'3s内剩余搜索次数: {short_remaining}\n24h内剩余搜索次数: {long_remaining}\n'
    )
  return msgs
