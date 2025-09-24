from collections import OrderedDict
from datetime import datetime
import sqlite3
import random

import util
from util.log import timezone


def ordereddict_factory(cursor, row):
  fields = [column[0] for column in cursor.description]
  return OrderedDict(zip(fields, row))


class Cum:
  inited = False

  @classmethod
  def init(cls):
    if cls.inited:
      return
    cls.conn = sqlite3.connect(util.getDataFile('cum.db'))
    cls.conn.row_factory = ordereddict_factory

    cls.conn.execute(
      """CREATE TABLE if not exists users(
  id INTEGER PRIMARY KEY AUTOINCREMENT, 
  uid INTEGER UNIQUE NOT NULL, 
  cum_min INTEGER NOT NULL DEFAULT 200,
  cum_max INTEGER NOT NULL DEFAULT 400,
  behelp_get INTEGER NOT NULL DEFAULT 250,
  help_get INTEGER NOT NULL DEFAULT 250,
  dick_length INTEGER NOT NULL DEFAULT 100,
  dick_thickness INTEGER NOT NULL DEFAULT 200,
  create_time INTEGER NOT NULL 
)"""
    )
    cls.conn.execute('CREATE UNIQUE INDEX if not exists users_id ON users (id)')
    cls.conn.execute('CREATE UNIQUE INDEX if not exists users_uid ON users (uid)')
    r = cls.conn.execute(
      "select count(name) from sqlite_master where type='table' and name='users' and sql like '%dick_length%'"
    )
    if not (res := r.fetchone()) or res['count(name)'] == 0:
      cls.conn.execute(
        'ALTER TABLE users ADD COLUMN dick_length INTEGER NOT NULL DEFAULT 100'
      )
      cls.conn.execute(
        'ALTER TABLE users ADD COLUMN dick_thickness INTEGER NOT NULL DEFAULT 200'
      )

    cls.conn.execute(
      """CREATE TABLE if not exists cum_history(
  id INTEGER PRIMARY KEY AUTOINCREMENT, 
  uid INTEGER NOT NULL, 
  semen INTEGER NOT NULL,
  create_time INTEGER NOT NULL 
)"""
    )
    cls.conn.execute(
      'CREATE UNIQUE INDEX if not exists cum_history_id ON cum_history (id)'
    )
    cls.conn.execute('CREATE INDEX if not exists cum_history_uid ON cum_history (uid)')

    cls.conn.execute(
      """CREATE TABLE if not exists help_history(
  id INTEGER PRIMARY KEY AUTOINCREMENT, 
  uid INTEGER NOT NULL, 
  semen INTEGER NOT NULL,
  from_uid INTEGER NOT NULL,
  semen_to_from INTEGER NOT NULL,
  create_time INTEGER NOT NULL 
)"""
    )
    cls.conn.execute(
      'CREATE UNIQUE INDEX if not exists help_history_id ON help_history (id)'
    )
    cls.conn.execute(
      'CREATE INDEX if not exists help_history_uid ON help_history (uid)'
    )

    cls.conn.execute(
      """CREATE TABLE if not exists use_history(
  id INTEGER PRIMARY KEY AUTOINCREMENT, 
  uid INTEGER NOT NULL, 
  item INTEGER NOT NULL,
  num INTEGER NOT NULL,
  create_time INTEGER NOT NULL 
)"""
    )
    cls.conn.execute(
      'CREATE UNIQUE INDEX if not exists use_history_id ON use_history (id)'
    )
    cls.conn.execute('CREATE INDEX if not exists use_history_uid ON use_history (uid)')

    cls.conn.execute(
      """CREATE TABLE if not exists items(
  id INTEGER PRIMARY KEY AUTOINCREMENT, 
  name NVARCHAR(255) NOT NULL,
  details NTEXT NOT NULL
)"""
    )
    cls.conn.execute('CREATE UNIQUE INDEX if not exists items_id ON items (id)')

    cls.conn.commit()
    cls.inited = True

  @classmethod
  def get_user(cls, uid):
    cls.init()
    r = cls.conn.execute('SELECT * FROM users WHERE uid=?', (uid,))
    if res := r.fetchone():
      return res

    create_time = int(datetime.now().timestamp())
    cursor = cls.conn.cursor()
    cursor.execute(
      'INSERT INTO users(uid, create_time) values(?,?)',
      (uid, create_time),
    )
    cls.conn.commit()

    r = cls.conn.execute('SELECT * FROM users WHERE uid=?', (uid,))
    res = r.fetchone()
    return res

  @classmethod
  def cum(cls, uid):
    cls.init()
    user = Cum.get_user(uid)

    today_midnight = int(
      datetime.now(timezone)
      .replace(hour=0, minute=0, second=0, microsecond=0)
      .timestamp()
    )
    r = cls.conn.execute(
      'SELECT semen, create_time FROM cum_history WHERE uid=? ORDER BY create_time DESC LIMIT 1',
      (uid,),
    )
    if (res := r.fetchone()) and res['create_time'] >= today_midnight:
      return False, res['semen']

    semen = random.randint(user['cum_min'], user['cum_max'])
    create_time = int(datetime.now().timestamp())
    cursor = cls.conn.cursor()
    cursor.execute(
      'INSERT INTO cum_history(uid, semen, create_time) values(?,?,?)',
      (
        uid,
        semen,
        create_time,
      ),
    )
    cls.conn.commit()
    return True, semen

  @classmethod
  def get_semen(cls, uid):
    cls.init()
    Cum.get_user(uid)
    semen = 0
    # 射精得到的
    r = cls.conn.execute('SELECT sum(semen) FROM cum_history WHERE uid=?', (uid,))
    if res := r.fetchone():
      semen += res['sum(semen)'] or 0

    # 被助力得到的
    r = cls.conn.execute('SELECT sum(semen) FROM help_history WHERE uid=?', (uid,))
    if res := r.fetchone():
      semen += res['sum(semen)'] or 0

    # 助力别人得到的
    r = cls.conn.execute(
      'SELECT sum(semen_to_from) FROM help_history WHERE from_uid=?', (uid,)
    )
    if res := r.fetchone():
      semen += res['sum(semen_to_from)'] or 0

    # 减去用掉的
    r = cls.conn.execute(
      'SELECT sum(num) FROM use_history WHERE item=0 AND uid=?', (uid,)
    )
    if res := r.fetchone():
      semen -= res['sum(semen)'] or 0

    return semen

  @classmethod
  def last_cum_time(cls, uid):
    cls.init()
    r = cls.conn.execute(
      'SELECT create_time FROM cum_history WHERE uid=? ORDER BY create_time DESC LIMIT 1',
      (uid,),
    )
    if not (res := r.fetchone()):
      return 0
    return res['create_time']

  @classmethod
  def help(cls, uid, from_uid):
    cls.init()
    user = Cum.get_user(uid)
    from_user = Cum.get_user(from_uid)

    today_midnight = int(
      datetime.now(timezone)
      .replace(hour=0, minute=0, second=0, microsecond=0)
      .timestamp()
    )
    r = cls.conn.execute(
      'SELECT create_time FROM help_history WHERE uid=? AND from_uid=? ORDER BY create_time DESC LIMIT 1',
      (uid, from_uid),
    )
    if (res := r.fetchone()) and res['create_time'] >= today_midnight:
      return False

    create_time = int(datetime.now().timestamp())
    cursor = cls.conn.cursor()
    cursor.execute(
      'INSERT INTO help_history(uid, semen, from_uid, semen_to_from, create_time) values(?,?,?,?,?)',
      (
        uid,
        user['behelp_get'],
        from_uid,
        from_user['help_get'],
        create_time,
      ),
    )
    cls.conn.commit()
    return from_user['help_get']
