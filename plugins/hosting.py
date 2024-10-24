import os
import config


root_folder = os.path.join(config.botRoot, 'hosting')


def get_url(path: str, rename=None) -> str:
  dirname, name = os.path.split(path)
  if rename is not None:
    name = rename
  target_path = os.path.join(root_folder, name)
  if not os.path.isfile(target_path):
    with open(path, 'rb') as f1:
      with open(target_path, 'wb') as f2:
        f2.write(f1.read())
  return f'https://i.xxx.xxx/{name}'
