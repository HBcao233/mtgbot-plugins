def allbit_xor(n: int) -> int:
  """
  每一位异或, 返回 0 或 1
  """
  if n < 0:
    raise ValueError("n can't be a negative")
  res = 0
  while n != 0:
    res ^= n & 1
    n >>= 1
  return res


def count_of_1(n: int):
  """
  计算二进制中 1 的数量
  """
  count = 0
  while n & 0xFFFFFFFF != 0:
    count += 1
    n = n & (n - 1)
  return count


def gen_matrix(row: int, init: int = 0) -> list[int]:
  """
  生成大小为 row * row 的求解矩阵
  矩阵的第i行为 第i个单元格所能影响的上下左右的单元格
  """
  return [
    sum(
      (
        1
        if j in [i - row, i - 1, i, i + 1, i + row, row * row]
        and (i % row != 0 or j != i - 1)
        and (i % row != row - 1 or j != i + 1 or j == row * row)
        and (j != row * row or not init >> i & 1)
        else 0
      )
      * 2**j
      for j in range(row * row + 1)
    )
    for i in range(row * row)
  ]


def format_vector(vector: int, row: int):
  """
  格式化二进制向量, 需指定大小 row (向量长度为 row * row)
  """
  return '\n'.join(
    str([(vector >> i * row + j) & 1 for j in range(row)]) for i in range(row)
  )


def format_matrix(matrix: list[int], row: int):
  """
  格式化求解矩阵
  """
  return (
    '\n'.join(
      ' '.join(str((vector >> i) & 1) for i in range(row))
      + ' | '
      + str(vector >> (row) & 1)
      for vector in matrix
    )
    + '\n'
  )


def gauss_elimination(matrix: list[int], all_solves=False) -> int:
  """
  输入矩阵, 二进制高斯消元求解, 返回一个二进制向量
  """

  def to_result(matrix: list[int]) -> int:
    """
    返回结果. 遍历高斯矩阵每一行的最后一列即为结果, 将其转换为十进制
    """
    return sum((matrix[i] >> row) * 2**i for i in range(row))

  def find_optimal_solution(result: int, var_rule: list[int], all_solves=False) -> int:
    """
    寻找最优解 (点灯步骤最少的解)

    Args:
        result: 特解向量
        var_rule: 非自由变量与自由变量之间的关系

    Returns:
        最优解向量
    """
    nonlocal row
    freevar_num = row - len(var_rule)
    # 遍历生成所有解
    l = (
      sum(
        (allbit_xor(var_rule[j] & i) ^ (result >> j & 1)) * 2**j
        for j in range(len(var_rule))
      )
      + (i << len(var_rule))
      for i in range(2**freevar_num)
    )
    if all_solves:
      return list(l)
    return min(
      l,
      key=lambda s: count_of_1(s),
    )

  row = len(matrix)  # 此处 高斯矩阵的row 是原矩阵的 row*row
  for i in range(row):
    cur = i
    while cur < row and not matrix[cur] >> i & 1:
      cur += 1
    if cur == row:
      # print(format_matrix(mat, row))
      # 多解时返回一个解
      if not matrix[i] >> row:
        freevar_num = row - i
        # print('解数量:', 2**freevar_num)
        result = to_result(matrix)
        var_rule = [
          sum((matrix[j] >> (row - k - 1) & 1) * 2**k for k in range(freevar_num))
          for j in range(i)
        ]
        # 解数量较少时尝试寻找最优解, 否则直接返回特解
        return (
          (result if not all_solves else [result])
          if freevar_num > 10
          else find_optimal_solution(result, var_rule, all_solves)
        )
      return False
    if cur != i:
      matrix[cur], matrix[i] = matrix[i], matrix[cur]
    for j in range(row):
      if i != j and (matrix[j] >> i) & 1:
        matrix[j] ^= matrix[i]
  result = to_result(matrix)
  return result if not all_solves else [result]


def find_all_3x3_init():
  l = []

  row = 3
  for i in range(2**9):
    mat = gen_matrix(row, i)
    r = gauss_elimination(mat)
    l.append(count_of_1(r))

  print(l)


def init_3x3_to_index():
  l = [
    5,
    4,
    3,
    2,
    4,
    5,
    2,
    7,
    3,
    2,
    5,
    4,
    6,
    3,
    4,
    5,
    8,
    3,
    6,
    5,
    3,
    4,
    5,
    6,
    6,
    5,
    4,
    7,
    5,
    6,
    3,
    4,
    3,
    6,
    5,
    4,
    2,
    3,
    4,
    5,
    3,
    6,
    5,
    4,
    6,
    3,
    4,
    1,
    6,
    5,
    4,
    3,
    5,
    6,
    7,
    4,
    2,
    5,
    4,
    7,
    5,
    6,
    7,
    4,
    4,
    5,
    6,
    3,
    7,
    6,
    5,
    4,
    2,
    7,
    4,
    5,
    5,
    4,
    7,
    6,
    3,
    4,
    5,
    6,
    2,
    5,
    4,
    3,
    5,
    6,
    3,
    4,
    4,
    3,
    6,
    1,
    6,
    3,
    8,
    5,
    5,
    4,
    3,
    6,
    6,
    7,
    4,
    5,
    5,
    4,
    3,
    6,
    5,
    2,
    3,
    4,
    4,
    7,
    2,
    5,
    5,
    2,
    3,
    4,
    4,
    3,
    6,
    5,
    3,
    6,
    3,
    6,
    6,
    3,
    6,
    7,
    5,
    4,
    5,
    4,
    8,
    5,
    4,
    5,
    6,
    5,
    2,
    5,
    5,
    2,
    5,
    2,
    4,
    3,
    4,
    7,
    3,
    4,
    3,
    4,
    5,
    8,
    5,
    4,
    4,
    5,
    4,
    5,
    5,
    4,
    9,
    4,
    4,
    5,
    4,
    5,
    4,
    3,
    4,
    3,
    3,
    4,
    7,
    4,
    4,
    3,
    4,
    3,
    3,
    8,
    3,
    4,
    2,
    3,
    6,
    3,
    5,
    4,
    5,
    4,
    4,
    5,
    4,
    1,
    3,
    6,
    3,
    6,
    5,
    6,
    5,
    6,
    4,
    7,
    4,
    3,
    7,
    4,
    7,
    4,
    2,
    5,
    6,
    5,
    4,
    5,
    4,
    5,
    7,
    2,
    3,
    2,
    4,
    5,
    4,
    5,
    3,
    2,
    3,
    6,
    3,
    4,
    3,
    8,
    6,
    5,
    6,
    5,
    7,
    4,
    3,
    4,
    6,
    5,
    6,
    5,
    4,
    7,
    6,
    5,
    5,
    6,
    3,
    4,
    6,
    5,
    8,
    3,
    3,
    4,
    5,
    6,
    3,
    2,
    5,
    4,
    4,
    5,
    6,
    3,
    5,
    4,
    3,
    2,
    2,
    7,
    4,
    5,
    2,
    5,
    4,
    7,
    7,
    4,
    5,
    6,
    6,
    5,
    4,
    3,
    7,
    4,
    5,
    6,
    5,
    4,
    3,
    6,
    6,
    3,
    4,
    1,
    5,
    4,
    3,
    6,
    2,
    3,
    4,
    5,
    5,
    6,
    3,
    4,
    6,
    1,
    4,
    3,
    3,
    4,
    5,
    6,
    4,
    3,
    2,
    5,
    4,
    5,
    2,
    7,
    5,
    4,
    7,
    6,
    6,
    3,
    4,
    5,
    7,
    6,
    5,
    4,
    3,
    4,
    5,
    2,
    4,
    3,
    6,
    5,
    3,
    4,
    5,
    2,
    4,
    7,
    2,
    5,
    6,
    7,
    4,
    5,
    3,
    6,
    5,
    4,
    6,
    3,
    8,
    5,
    3,
    6,
    5,
    4,
    2,
    5,
    6,
    5,
    3,
    4,
    3,
    4,
    4,
    7,
    4,
    3,
    5,
    2,
    5,
    2,
    5,
    4,
    5,
    4,
    6,
    7,
    6,
    3,
    3,
    6,
    3,
    6,
    4,
    5,
    8,
    5,
    4,
    3,
    4,
    3,
    5,
    6,
    1,
    6,
    4,
    3,
    4,
    3,
    5,
    2,
    5,
    6,
    7,
    2,
    7,
    6,
    4,
    5,
    4,
    5,
    7,
    6,
    3,
    6,
    4,
    5,
    4,
    5,
    7,
    4,
    7,
    4,
    4,
    3,
    4,
    7,
    5,
    6,
    5,
    6,
    6,
    5,
    2,
    5,
    6,
    3,
    2,
    3,
    3,
    6,
    3,
    6,
    4,
    1,
    4,
    5,
    5,
    4,
    5,
    4,
    5,
    6,
    5,
    2,
    6,
    5,
    6,
    5,
    1,
    6,
    5,
    6,
    6,
    5,
    6,
    5,
    4,
    5,
    4,
    5,
    1,
    4,
    5,
    4,
    4,
    5,
    4,
    5,
    5,
    4,
    5,
    0,
  ]
  res = [[], [], [], [], [], [], [], [], [], []]
  for i, ai in enumerate(l):
    res[ai].append(i)
  print(res)

  """
  res = [
    [511], 
    [47, 95, 203, 311, 325, 422, 473, 488, 500], 
    [3, 6, 9, 36, 56, 72, 84, 113, 118, 121, 146, 149, 151, 192, 220, 229, 231, 237, 273, 283, 284, 288, 316, 334, 338, 355, 363, 366, 384, 397, 399, 429, 433, 462, 466, 483], 
    [2, 8, 13, 17, 20, 30, 32, 37, 40, 45, 51, 67, 80, 87, 90, 93, 97, 102, 110, 114, 122, 125, 128, 130, 133, 153, 156, 158, 177, 179, 180, 185, 187, 188, 190, 193, 195, 204, 206, 215, 230, 236, 238, 240, 242, 250, 262, 267, 268, 272, 279, 282, 299, 306, 309, 314, 317, 322, 327, 328, 333, 345, 352, 357, 360, 372, 377, 380, 388, 390, 395, 407, 408, 410, 417, 419, 425, 427, 442, 453, 465, 467, 468, 470], 
    [1, 4, 11, 14, 21, 26, 31, 35, 38, 43, 46, 50, 55, 58, 63, 64, 71, 74, 77, 81, 86, 91, 92, 101, 106, 109, 115, 116, 123, 124, 137, 139, 142, 152, 154, 157, 159, 163, 164, 166, 169, 171, 172, 174, 176, 178, 181, 183, 184, 186, 191, 197, 199, 200, 202, 212, 214, 217, 219, 224, 226, 232, 234, 241, 249, 251, 256, 263, 269, 275, 276, 281, 286, 290, 293, 298, 301, 305, 310, 313, 318, 323, 326, 329, 332, 336, 341, 346, 351, 353, 356, 361, 364, 370, 375, 383, 389, 391, 392, 394, 401, 403, 412, 416, 418, 424, 426, 436, 438, 444, 446, 449, 451, 452, 454, 472, 474, 477, 479, 496, 498, 501, 503, 504, 506, 509], 
    [0, 5, 10, 15, 19, 22, 25, 28, 34, 39, 42, 49, 52, 57, 60, 65, 70, 75, 76, 82, 85, 88, 99, 100, 107, 108, 112, 119, 120, 127, 136, 138, 141, 143, 145, 147, 148, 150, 160, 162, 165, 167, 168, 173, 175, 196, 198, 201, 208, 210, 221, 223, 225, 227, 233, 235, 245, 247, 253, 255, 259, 260, 265, 270, 274, 277, 280, 287, 289, 294, 297, 302, 304, 312, 319, 320, 330, 335, 337, 340, 347, 350, 354, 359, 362, 367, 371, 374, 379, 382, 385, 387, 396, 398, 400, 402, 413, 415, 420, 428, 430, 437, 439, 445, 447, 456, 458, 461, 463, 475, 476, 478, 480, 482, 485, 487, 490, 493, 495, 497, 499, 502, 505, 507, 508, 510], 
    [12, 18, 23, 24, 29, 33, 41, 44, 48, 53, 61, 66, 69, 79, 83, 89, 94, 96, 103, 104, 111, 126, 129, 131, 132, 134, 144, 194, 205, 207, 209, 211, 222, 239, 244, 246, 252, 254, 258, 261, 264, 271, 278, 295, 296, 303, 307, 308, 315, 321, 324, 331, 343, 344, 349, 358, 368, 373, 376, 381, 386, 404, 406, 409, 411, 421, 423, 431, 435, 441, 443, 457, 459, 460, 464, 469, 471, 481, 484, 486, 489, 491, 492, 494], 
    [7, 27, 54, 59, 62, 68, 73, 78, 105, 117, 135, 155, 182, 213, 216, 218, 228, 248, 257, 285, 291, 292, 300, 339, 342, 348, 365, 369, 393, 405, 432, 434, 440, 448, 450, 455], 
    [16, 98, 140, 161, 189, 243, 266, 378, 414], 
    [170]
  ]
  """


if __name__ == '__main__':
  import sys

  # '''
  row = 3
  # row = int(sys.argv[1])
  print(0b010101111)
  mat = gen_matrix(row, 0b010101111)
  # print(format_matrix(mat, row * row))
  r = gauss_elimination(mat)
  print(format_vector(r, row))
  # print(r)
  # '''

  # init_3x3_to_index()
  # print(format_vector(95, 3))
