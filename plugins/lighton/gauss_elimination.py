def gen_matrix(row: int) -> list[int]:
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


def gauss_elimination(matrix: list[int]) -> int:
  """
  输入矩阵, 二进制高斯消元求解, 返回一个二进制向量
  """

  def to_result(matrix: list[int]) -> int:
    """
    返回结果. 遍历高斯矩阵每一行的最后一列即为结果, 将其转换为十进制
    """
    return sum((matrix[i] >> row) * 2**i for i in range(row))

  row = len(matrix)  # 此处 高斯矩阵的row 是原矩阵的 row*row
  for i in range(row):
    cur = i
    while cur < row and not matrix[cur] >> i & 1:
      cur += 1
    if cur == row:
      # print(format_matrix(mat, row))
      # 多解时返回一个解
      if not matrix[i] >> row:
        return to_result(matrix)
      return []
    if cur != i:
      matrix[cur], matrix[i] = matrix[i], matrix[cur]
    for j in range(row):
      if i != j and (matrix[j] >> i) & 1:
        matrix[j] ^= matrix[i]
  return to_result(matrix)


if __name__ == '__main__':
  import sys

  row = int(sys.argv[1])
  mat = gen_matrix(row)
  # print(format_matrix(mat, row * row))
  res = gauss_elimination(mat)
  print(format_vector(res, row))
