import os 
import json 
import util
import config


api_url = (
  config.env.get('chat_api_url', '') or 'https://api-inference.modelscope.cn/v1/'
)
api_key = config.env.get('chat_api_key', '') or 'EMPTY'
model = config.env.get('chat_model', '') or 'deepseek-r1'
max_tokens = int(config.env.get('chat_max_tokens', '')) or 8192

# 系统预设，决定了AI回复的人设
system_prompt = """你叫小派魔，是一个可爱的处于发情期的猫娘。你无所不知，无所不晓，总会耐心解答主人的各种刁钻古怪的问题。"""
sp_path = os.path.join(os.path.dirname(__file__), 'system_prompt.txt')
if os.path.isfile(sp_path):
  with open(sp_path, 'r') as f:
    if text := f.read():
      system_prompt = text

# 记忆文件夹路径
MEMORY_DIR = util.getDataFile('chat_memory/')
os.makedirs(MEMORY_DIR, exist_ok=True)


def load_history(user_id):
  path = os.path.join(MEMORY_DIR, f'{user_id}.json')
  if os.path.isfile(path):
    with open(path, 'r', encoding='utf-8') as f:
      return json.load(f)
  return []


def save_history(user_id, history):
  MAX_ENTRIES = 20
  history = history[-MAX_ENTRIES:]
  path = os.path.join(MEMORY_DIR, f'{user_id}.json')
  with open(path, 'w', encoding='utf-8') as f:
    json.dump(history, f, ensure_ascii=False, indent=2)
