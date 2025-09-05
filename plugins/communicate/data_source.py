from util import logger
from util.data import MessageData
import config


echo_chat_id = int(x) if (x := config.env.get('echo_chat_id', '')) else 0
if echo_chat_id == 0:
  logger.warn('communicate 插件并未生效: 配置项 echo_chat_id 未设置或设置错误')


def to_bytes(i):
  return i.to_bytes(4, 'big')


def from_bytes(b):
  return int.from_bytes(b, 'big')


class EchoedMessage(MessageData):
  inited = False

  @classmethod
  def init(cls):
    MessageData.init()
    if EchoedMessage.inited:
      return
    cls._conn.execute(
      'CREATE TABLE if not exists echoed_messages(id INTEGER PRIMARY KEY AUTOINCREMENT, mid int NOT NULL, echo_mid int NOT NULL)'
    )
    cls._conn.execute(
      'CREATE UNIQUE INDEX if not exists id_index ON echoed_messages (id)'
    )
    cls._conn.commit()
    EchoedMessage.inited = True

  @classmethod
  def add_echo(cls, chat_id, message_id, echo_chat_id, echo_message_id):
    cls.init()
    m = cls.get_message(chat_id, message_id)
    echo_m = cls.get_message(echo_chat_id, echo_message_id)
    logger.debug(f'add_echo mid: {m.id} echo_mid: {echo_m.id}')

    cursor = cls._conn.cursor()
    cursor.execute(
      'insert into echoed_messages(mid, echo_mid) values(?,?)', (m.id, echo_m.id)
    )
    cls._conn.commit()
    return cursor.lastrowid

  @classmethod
  def get_echo(cls, chat_id, message_id=None):
    cls.init()
    m = cls.get_message(chat_id, message_id)
    r = cls._conn.execute('SELECT echo_mid FROM echoed_messages WHERE mid=?', (m.id,))
    if res := r.fetchone():
      return cls.get_message_by_rid(res[0])
    return None

  @classmethod
  def get_origin(cls, chat_id, message_id=None):
    cls.init()
    m = cls.get_message(chat_id, message_id)
    r = cls._conn.execute('SELECT mid FROM echoed_messages WHERE echo_mid=?', (m.id,))
    if res := r.fetchone():
      return cls.get_message_by_rid(res[0])
    return None
