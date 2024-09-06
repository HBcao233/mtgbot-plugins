def gen_matrix(row: int) -> list[int]:
  return [
    sum(
      [
        (
          1
          if j in [i - row, i - 1, i, i + 1, i + row, row * row]
          and (i % row != 0 or j != i - 1)
          and (i % row != row - 1 or j != i + 1 or j == row * row)
          else 0
        )
        * 2**j
        for j in range(row * row + 1)
      ]
    )
    for i in range(row * row)
  ]


def format_vector(vector: int, row: int):
  return '\n'.join(
    str([(vector >> i * row + j) & 1 for j in range(row)]) for i in range(row)
  )


def format_mat(mat):
  return '\n\n'.join(format_vector(i) for i in mat)


def gauss_elimination(matrix):
  row = len(matrix)
  for i in range(row):
    cur = i
    while cur < row and not matrix[cur] >> i & 1:
      cur += 1
    if cur == row:
      # 多解时返回一个解
      if not matrix[i] >> row:
        return sum((matrix[i] >> row) * 2**i for i in range(row))
      return []
    if cur != i:
      matrix[cur], matrix[i] = matrix[i], matrix[cur]
    for j in range(row):
      if i != j and (matrix[j] >> i) & 1:
        matrix[j] ^= matrix[i]
  return sum((matrix[i] >> row) * 2**i for i in range(row))


if __name__ == '__main__':
  import sys

  row = int(sys.argv[1])
  mat = gen_matrix(row)
  res = gauss_elimination(mat)
  print(format_vector(res, row))
