# 大部分代码来自 https://github.com/Evil0ctal/Douyin_TikTok_Download_API/
from pydantic import BaseModel

import util
from .abogus import ABogus


headers = {
  'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
  'Referer': 'https://www.douyin.com/',
  'cookie': '__ac_nonce=067d687ac00d70af16eab; __ac_signature=_02B4Z6wo00f018O6kmgAAIDAR1H8JrcivBPDi5bAAJdBcf; ttwid=1%7C46sVJ6G5zO0ZRKBqbFef2B13U3CqP9gLwQEH8IV2y6A%7C1742112685%7Cae649397cca7dde21884d5f8e3e3d53eb2361aa64af04cd6889fa71d7f23344b; UIFID_TEMP=986fab8dfc2c74111fac2b883dbdee67777473ded35e2c4bebbf68cc8b91739da61f6b365ad9795b0aa3a8bddce6cc3e39c5d4fd4bad667aaefd3d3ec08baac66fe3b215343f12d8aae84e0a24048f44; douyin.com; device_web_cpu_core=16; device_web_memory_size=-1; architecture=amd64; hevc_supported=true; IsDouyinActive=true; home_can_add_dy_2_desktop=%220%22; dy_swidth=1835; dy_sheight=1147; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1835%2C%5C%22screen_height%5C%22%3A1147%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A16%2C%5C%22device_memory%5C%22%3A0%2C%5C%22downlink%5C%22%3A%5C%22%5C%22%2C%5C%22effective_type%5C%22%3A%5C%22%5C%22%2C%5C%22round_trip_time%5C%22%3A0%7D%22; strategyABtestKey=%221742112685.842%22; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Afalse%2C%22volume%22%3A0.5%7D; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A0%2C%5C%22is_mute%5C%22%3A0%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A1%7D%22; xgplayer_user_id=835787001711; fpk1=U2FsdGVkX19Ke0llbjXpGOOr1Jeel/2GnaSJz41VO3mAFs271jC0hG7gdWlk+2pYLM4GF8TVGtwClCJIXsTKUw==; fpk2=2333b8d335abc6e14aef1caed0ae26fc; s_v_web_id=verify_m8bcww86_XfwSCnmj_5i3F_4Joq_8edO_9gRH9JENh07f; csrf_session_id=6f34e666e71445c9d39d8d06a347a13f; FORCE_LOGIN=%7B%22videoConsumedRemainSeconds%22%3A180%7D; biz_trace_id=c34e5eaf; passport_csrf_token=ab84b3e39ad78e719b236035a27379c0; passport_csrf_token_default=ab84b3e39ad78e719b236035a27379c0; __security_mc_1_s_sdk_crypt_sdk=ac2d56c3-44cd-a161; __security_mc_1_s_sdk_cert_key=ccf2bd2d-4718-b8de; __security_mc_1_s_sdk_sign_data_key_web_protect=9995d368-4e45-b17f; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCUHR2ZDlUeGU4UlhPaWdIczFqaStJWityQlF4UWZMKytiL2drbXlYUmNrelNua1lQUjJTRVZHVlo4MWFCU0EvSW4xSnBmbzN3TFlvSnhIZTZTV29DTmc9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; bd_ticket_guard_client_web_domain=2; xg_device_score=8.208487995540095; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e5827292771273f27303035353c3337343437313234272927676c715a75776a716a666a69273f2763646976602778; bit_env=LVdHnIescW9BCGpo5gGuqIlwNfgj757SBdMhdZXBSWjPWbxp9Nv_B2vUt_LtEvr-ioRv0E9b8N8HWiOHe20JqcUhO4YmpIM6gB83hjgqZfmAhYEbzJR7z2bRViJaPg4xeoyGhwdjwK_Bzogp6uoUs4ov-P4JYzMh78i7jaY5Pzd6h3CaVO-eUKnTiFfUlJo_jmhSfHXGdwkurXwR4lO_UnU4Loqa0YlmDiyi0fPxURFIN5t4Ny6Ua8LLSYcUrBXHlXoQ5G4bQN4XqwuWwT9YauexXbkotU1Jv8pMJUiAhlFIMjbvfTutTSnOXJLoH_JsR_doifURl0wf8CIa_OcYw-A2VglrpbaFU6HDVTKbSRKovzIMY9bUwl_4EAiLBf87g2BU0Uz1MHd_lGNdH3ImEWpLtdRvUsW_KD7q87rPsEGVTceyQ5U3ZlETqoEOwOiggNGu5lL_1O8lt8_7eydeGA%3D%3D; gulu_source_res=eyJwX2luIjoiM2Y3NGJhZDgxMzc3OThkNmVkN2U5ZjM3NDMzNGJkYjMwNzRhYjI0ZWJhMDZkMzdmYWNiNjgzNTY2ZjY0OGUyNCJ9; passport_auth_mix_state=c534f2qcgpohqv4juisp74wq28e90snz',
}


class BaseRequestModel(BaseModel):
  device_platform: str = 'webapp'
  aid: str = '6383'
  channel: str = 'channel_pc_web'
  pc_client_type: int = 1
  version_code: str = '290100'
  version_name: str = '29.1.0'
  cookie_enabled: str = 'true'
  screen_width: int = 1920
  screen_height: int = 1080
  browser_language: str = 'zh-CN'
  browser_platform: str = 'Win32'
  browser_name: str = 'Chrome'
  browser_version: str = '130.0.0.0'
  browser_online: str = 'true'
  engine_name: str = 'Blink'
  engine_version: str = '130.0.0.0'
  os_name: str = 'Windows'
  os_version: str = '10'
  cpu_core_num: int = 12
  device_memory: int = 8
  platform: str = 'PC'
  downlink: str = '10'
  effective_type: str = '4g'
  from_user_page: str = '1'
  locate_query: str = 'false'
  need_time_list: str = '1'
  pc_libra_divert: str = 'Windows'
  publish_video_strategy_type: str = '2'
  round_trip_time: str = '0'
  show_live_replay_strategy: str = '1'
  time_list_query: str = '0'
  whale_cut_token: str = ''
  update_version_code: str = '170400'


class PostDetail(BaseRequestModel):
  aweme_id: str


async def get_aweme_detail(aid: str):
  params = PostDetail(aweme_id=aid).dict()
  a_bogus = ABogus().get_value(params)
  params.update({
    'a_bogus': a_bogus,
  })
  r = await util.get(
    'https://www.douyin.com/aweme/v1/web/aweme/detail/',
    params=params,
    headers=headers,
  )
  if r.status_code != 200:
    return 
  res = r.json()
  if res['status_code'] != 0:
    return 
  res = res['aweme_detail']
  res = {
    k: v
    for k, v in res.items()
    if k in ['author', 'aweme_id', 'video', 'desc', 'region', 'preview_title']
  }
  return res


def parse_aweme_detail(res):
  aid = res['aweme_id']
  title = res['preview_title']
  url = f'https://www.douyin.com/video/{aid}'
  uid = res['author']['uid']
  username = res['author']['unique_id']
  nickname = res['author']['nickname']
  sec_uid = res['author']['sec_uid']
  author_url = f'https://www.douyin.com/user/{sec_uid}'
  msg = f'<a href="{url}">{title}</a> - <a href="{author_url}">{nickname}</a> #douyin\nvia @{bot.me.username}' 
  return msg
