import json
from urllib.parse import unquote


def ET7M(hu3x):
  if hu3x < -128:
    return ET7M(128 - (-128 - hu3x))
  elif -128 <= hu3x <= 127:
    return hu3x
  elif hu3x > 127:
    return ET7M(-129 + hu3x - 127)
  else:
    raise ValueError('1001')


def ctx9o(hu3x, bo2x):
  return ET7M(hu3x + bo2x)


def ctv8n(bcq3x, bmu5z):
  if bcq3x is None:
    return None
  if bmu5z is None:
    return bcq3x
  sy5D = []
  cts8k = len(bmu5z)
  for i in range(len(bcq3x)):
    sy5D.append(ctx9o(bcq3x[i], bmu5z[i % cts8k]))
  return sy5D


def cto8g(bbZ3x):
  if bbZ3x is None:
    return bbZ3x
  sy5D = []
  for num in bbZ3x:
    sy5D.append(ET7M(0 - num))
  return sy5D


def ctj8b(bmC5H, Qv1x):
  bmC5H = ET7M(bmC5H)
  Qv1x = ET7M(Qv1x)
  return ET7M(bmC5H ^ Qv1x)


def bTz6t(Qu1x, bmT5Y):
  if Qu1x is None or bmT5Y is None or len(Qu1x) != len(bmT5Y):
    return Qu1x
  sy5D = []
  for i in range(len(Qu1x)):
    sy5D.append(ctj8b(Qu1x[i], bmT5Y[i]))
  return sy5D


def ctf8X(dq2x):
  # fmt: off
  bTy6s = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f"]
  # fmt: on
  return bTy6s[(dq2x >> 4) & 15] + bTy6s[dq2x & 15]


def bTw6q(wM6G):
  if wM6G is None or len(wM6G) < 0:
    return ''
  OI1x = []
  for num in wM6G:
    OI1x.append(ctf8X(num))
  return ''.join(OI1x)


def bTv6p(bbs3x):
  if bbs3x is None or len(bbs3x) == 0:
    return bbs3x
  sy5D = []
  for i in range(0, len(bbs3x), 2):
    pP5U = int(bbs3x[i], 16) << 4
    pO5T = int(bbs3x[i + 1], 16)
    sy5D.append(ET7M(pP5U + pO5T))
  return sy5D


def bTs6m(cQ2x):
  if cQ2x is None or cQ2x is None:
    return cQ2x
  Qh1x = cQ2x.encode('utf-8').hex()
  wM6G = []
  for i in range(0, len(Qh1x), 2):
    if Qh1x[i : i + 2] == '%':
      if i + 4 <= len(Qh1x):
        wM6G.append(int(Qh1x[i + 2 : i + 4], 16))
      else:
        raise ValueError('1009')
    else:
      wM6G.append(int(Qh1x[i : i + 2], 16))
  return wM6G


def csN8F(zg6a):
  Y2x = 0
  Y2x += (zg6a[0] & 255) << 24
  Y2x += (zg6a[1] & 255) << 16
  Y2x += (zg6a[2] & 255) << 8
  Y2x += zg6a[3] & 255
  return Y2x


def cMS0x(Y2x):
  zg6a = []
  zg6a.append((Y2x >> 24) & 255)
  zg6a.append((Y2x >> 16) & 255)
  zg6a.append((Y2x >> 8) & 255)
  zg6a.append(Y2x & 255)
  return zg6a


def csL8D(db2x, bnv5A, bu2x):
  if db2x is None or len(db2x) == 0:
    return []
  if len(db2x) < bu2x:
    raise ValueError('1003')
  return db2x[bnv5A : bnv5A + bu2x]


def bnx5C(db2x, bnv5A, tB5G, csI8A, bu2x):
  if db2x is None or len(db2x) == 0:
    return tB5G
  if tB5G is None:
    raise ValueError('1004')
  if len(db2x) < bu2x:
    raise ValueError('1003')
  for i in range(bu2x):
    tB5G[csI8A + i] = db2x[bnv5A + i]
  return tB5G


def csH8z(bu2x):
  return [0] * bu2x


def csA8s(rV5a):
  if rV5a is None or len(rV5a) == 0:
    return csH8z(64)
  if len(rV5a) >= 64:
    return csL8D(rV5a, 0, 64)
  else:
    bTl6f = []
    for i in range(64):
      bTl6f.append(rV5a[i % len(rV5a)])
    return bTl6f


def csy8q(bbf3x):
  if bbf3x is None or len(bbf3x) % 64 != 0:
    raise ValueError('1005')
  boc6W = []
  for i in range(0, len(bbf3x), 64):
    boc6W.append(bbf3x[i : i + 64])
  return boc6W


def cst8l(bTk6e):
  pP5U = (bTk6e >> 4) & 15
  pO5T = bTk6e & 15
  bo2x = pP5U * 16 + pO5T
  # fmt: off
  csG8y = [82, 9, 106, -43, 48, 54, -91, 56, -65, 64, -93, -98, -127, -13, -41, -5, 124, -29, 57, -126, -101, 47, -1, -121, 52, -114, 67, 68, -60, -34, -23, -53, 84, 123, -108, 50, -90, -62, 35, 61, -18, 76, -107, 11, 66, -6, -61, 78, 8, 46, -95, 102, 40, -39, 36, -78, 118, 91, -94, 73, 109, -117, -47, 37, 114, -8, -10, 100, -122, 104, -104, 22, -44, -92, 92, -52, 93, 101, -74, -110, 108, 112, 72, 80, -3, -19, -71, -38, 94, 21, 70, 87, -89, -115, -99, -124, -112, -40, -85, 0, -116, -68, -45, 10, -9, -28, 88, 5, -72, -77, 69, 6, -48, 44, 30, -113, -54, 63, 15, 2, -63, -81, -67, 3, 1, 19, -118, 107, 58, -111, 17, 65, 79, 103, -36, -22, -105, -14, -49, -50, -16, -76, -26, 115, -106, -84, 116, 34, -25, -83, 53, -123, -30, -7, 55, -24, 28, 117, -33, 110, 71, -15, 26, 113, 29, 41, -59, -119, 111, -73, 98, 14, -86, 24, -66, 27, -4, 86, 62, 75, -58, -46, 121, 32, -102, -37, -64, -2, 120, -51, 90, -12, 31, -35, -88, 51, -120, 7, -57, 49, -79, 18, 16, 89, 39, -128, -20, 95, 96, 81, 127, -87, 25, -75, 74, 13, 45, -27, 122, -97, -109, -55, -100, -17, -96, -32, 59, 77, -82, 42, -11, -80, -56, -21, -69, 60, -125, 83, -103, 97, 23, 43, 4, 126, -70, 119, -42, 38, -31, 105, 20, 99, 85, 33, 12, 125]
  # fmt: on
  return csG8y[bo2x]


def bTj6d(bol6f):
  if bol6f is None:
    return None
  bTi6c = []
  for num in bol6f:
    bTi6c.append(cst8l(num))
  return bTi6c


def bTh6b(Pb1x, rV5a):
  if Pb1x is None:
    return None
  if len(Pb1x) == 0:
    return []
  if len(Pb1x) % 64 != 0:
    raise ValueError('1005')
  rV5a = csA8s(rV5a)
  bot6n = rV5a
  bou6o = csy8q(Pb1x)
  PY1x = []
  for i in range(len(bou6o)):
    box6r = bTj6d(bou6o[i])
    box6r = bTj6d(box6r)
    boz6t = bTz6t(box6r, bot6n)
    csn8f = ctv8n(boz6t, cto8g(bot6n))
    boz6t = bTz6t(csn8f, rV5a)
    PY1x.extend(boz6t)
    bot6n = bou6o[i]
  bTd6X = PY1x[len(PY1x) - 4 :]
  bu2x = csN8F(bTd6X)
  if bu2x > len(PY1x):
    raise ValueError('1006')
  sy5D = PY1x[:bu2x]
  return sy5D


def csc8U(baG3x, J2x):
  if baG3x is None:
    return None
  bTb6V = str(baG3x)
  if len(bTb6V) == 0:
    return []
  Pb1x = bTv6p(bTb6V)
  if J2x is None:
    raise ValueError('1007')
  rV5a = bTs6m(J2x)
  return bTh6b(Pb1x, rV5a)


def crZ8R(baG3x, J2x):
  boM6G = csc8U(baG3x, J2x)
  FF8x = bTw6q(boM6G)
  Bo7h = []
  for i in range(0, len(FF8x), 2):
    Bo7h.append('%')
    Bo7h.append(FF8x[i])
    Bo7h.append(FF8x[i + 1])
  return ''.join(Bo7h)


def settmusic(baG3x):
  return json.loads(unquote(crZ8R(baG3x, 'fuck~#$%^&*(458')))
