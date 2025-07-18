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
    res = (
      sum(
        (allbit_xor(var_rule[j] & i) ^ (result >> j & 1)) * 2**j
        for j in range(len(var_rule))
      )
      + (int(bin(i)[2:].zfill(4)[::-1], 2) << len(var_rule))
      for i in range(2**freevar_num)
    )
    if all_solves:
      return list(res)
    return min(
      res,
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


if __name__ == '__main__':
  # '''
  row = 4
  # row = int(sys.argv[1])
  mat = gen_matrix(row)
  # print(format_matrix(mat, row * row))
  r = gauss_elimination(mat)
  print(format_vector(r, row))
  # print(r)
  # '''

  # init_3x3_to_index()
  # print(format_vector(95, 3))
