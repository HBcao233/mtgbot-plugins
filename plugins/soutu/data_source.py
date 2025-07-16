from functools import cmp_to_key
from urllib.parse import urlparse
from bs4 import BeautifulSoup, element
import os
import ujson as json
import httpx

import util
import config
from util.log import logger

env = config.env
saucenao_api_key = env.get('saucenao_api_key', '')
if saucenao_api_key == '':
  logger.warn('saucenao_api_key 未配置, saucenao 搜索将不可用')

ipb_member_id = env.get('ex_ipb_member_id', '')
ipb_pass_hash = env.get('ex_ipb_pass_hash', '')
igneous = env.get('ex_igneous', '')
eheaders = {
  'cookie': f'ipb_member_id={ipb_member_id}; ipb_pass_hash={ipb_pass_hash}; igneous={igneous}',
}
if any(i == '' for i in (ipb_member_id, ipb_pass_hash, igneous)):
  logger.warn("env 'ex_ipb_member_id', 'ipb_pass_hash', 'igneous' 配置错误, exsearch 可能不可用")


async def to_img(path, ext='jpg'):
  _name = os.path.basename(path)
  name = os.path.splitext(_name)[0]
  img = util.getCache(f'{name}_img.{ext}')
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
      # TODO:
      logger.info(i)
      service_name = 'seiga'
      member_id = i['data']['member_id']
      seiga_id = i['data']['seiga_id']

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
      # 倒闭了
      drawr_id = i['data']['drawr_id']
      title = i['data']['title']
      url = f'https://drawr.net/show.php?id={drawr_id}'
      member_id = i['data']['member_id']
      member_name = i['data']['member_name']
      msgs.append(
        f'项目: Drawr\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'链接: <a href="{url}">{title}</a>\n'
        f'作者: {member_id} - {member_name}'
      )

    elif index_id == 11:
      nijie_id = i['data']['nijie_id']
      title = i['data']['title']
      url = f'https://nijie.info/view.php?id={nijie_id}'
      member_id = i['data']['member_id']
      member_name = i['data']['member_name']
      member_url = f'https://sp.nijie.info/members.php?id={member_id}'
      msgs.append(
        f'项目: Nijie\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'链接: <a href="{url}">{title}</a>\n'
        f'作者: <a href="{member_url}">{member_name}</a>'
      )

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
      # 半次元 已停运
      bcy_type = i['data']['bcy_type']
      bcy_id = i['data']['bcy_id']
      title = i['data']['title']
      member_link_id = i['data']['member_link_id']
      member_url = f'https://bcy.net/coser/detail/{member_link_id}'
      member_name = i['data']['member_name']
      msgs.append(
        f'项目: bcy.net\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'类型: {bcy_type}\n'
        f'id及标题: {bcy_id} - {title}\n'
        f'作者: <a href="{member_url}">{member_name}</a>'
      )

    elif index_id == 32:
      logger.info(i)
      

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

    elif index_id == 36:
      _type = i['data']['type']
      mu_id = i['data']['mu_id']
      url = f'https://www.mangaupdates.com/series.html?id={mu_id}'
      source = i['data']['source']
      part = i['data']['part']
      msgs.append(
        f'项目: Madokami ({_type})\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'part: <a href="{url}">{part}</a>\n'
        f'source: {source}'
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

    elif index_id == 38:
      jp_name = i['data']['jp_name']
      eng_name = i['data']['eng_name']
      source = i['data']['source']
      creator = ', '.join(i['data']['creator'])
      msgs.append(
        '项目: H-Misc (E-Hentai)\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'日文标题: <code>{jp_name}</code>\n'
        f'英文标题: <code>{eng_name}</code>\n'
        f'来源: {source}\n'
        f'画师: {creator}'
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
    elif index_id == 42:
      # Furry Network
      fn_type = i['data']['fn_type']
      fn_id = i['data']['fn_id']
      title = i['data']['title']
      url = f'https://furrynetwork.com/artwork/{fn_id}'
      author_url = i['data']['author_url']
      author_name = i['data']['author_name']
      msgs.append(
        f'项目: Furry Network\n'
        f'<a href="{thumbnail}">预览图</a>\n'
        f'相似度: {similarity}%\n'
        f'类型: {fn_type}\n'
        f'链接: <a href="{url}">{title}</a>\n'
        f'作者: <a href="{author_url}">{author_name}</a>'
      )

    else:
      # TODO:
      logger.info(i)

  if not res['header'].get('cache'):
    msgs.append(
      f'3s内剩余搜索次数: {short_remaining}\n24h内剩余搜索次数: {long_remaining}\n'
    )
  return msgs

  
async def esearch(path):
  eh = 'ex'
  if any(i == '' for i in (ipb_member_id, ipb_pass_hash, igneous)):
    logger.warn("env 'ex_ipb_member_id', 'ipb_pass_hash', 'igneous' 配置错误, exsearch 将使用 e-hentai.org 站点")
    eh = 'e-'
  r = httpx.post(
    f'https://upld.{eh}hentai.org/upld/image_lookup.php',
    headers=eheaders,
    files={
      'sfile': open(path, 'rb')
    },
    data={
      'fs_similar': 'on',
      'fs_covers': '',
    }
  )
  if r.status_code != 302:
    logger.info(f'{path} {r.status_code} {r.text}')
    if 'Please wait a bit longer between each file search.' in r.text:
      return '请求过快'
    return '请求失败'
  url = r.headers['location'] + '&fs_similar=on'
  r = await util.get(url, headers=eheaders)
  if 'No hits found' in r.text:
    return '无结果'
    
  res = []
  soup = BeautifulSoup(text, 'html.parser')
  arr = soup.select('.glte')[0].children
  for i in arr:
    if not isinstance(i, element.Tag):
      continue
    a = i.find('td').find('a')
    url = a.attrs['href']
    img = a.find('img')
    title = img.attrs['title']
    image = img.attrs['src']
    res.append({
      'url': url,
      'title': title,
      'image': image,
    })
    
  res = [
    f'结果{i + 1}: <a href="{i["url"]}">预览图</a>'
    f'链接: <a href="{i["url"]}">{i["title"]}</a>'
    for i, ai in enumerate(res)
  ]
  return res
