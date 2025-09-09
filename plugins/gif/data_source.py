import os
from rlottie_python import LottieAnimation
import cv2

import util
from util.log import logger


async def video2gif(img, mid):
  _path, name = os.path.split(img)
  _name, _ext = os.path.splitext(name)
  output = os.path.join(_path, f'{_name}_gif.gif')
  bar = util.progress.Progress(mid)
  bar.set_prefix('转换中...')

  cv = 'h264'
  if _ext == '.webm':
    cv = 'libvpx-vp9'
  cap = cv2.VideoCapture(img)
  width = cap.get(3)
  w = 360
  if width < 360:
    w = width
  command = [
    'ffmpeg',
    '-c:v',
    cv,
    '-i',
    img,
    '-r',
    '15',
    '-b:v',
    '1000k',
    '-lavfi',
    f'fps=15,scale={w}:-1:flags=lanczos,pad={w}:ih:(ow-iw)/2:(oh-ih)/2:00000000,split[s0][s1];[s0]palettegen=reserve_transparent=on:transparency_color=00000000[p];[s1][p]paletteuse',
    output,
    '-y',
  ]
  returncode, stdout = await util.media.ffmpeg(
    command, progress_callback=bar.update
  )
  if returncode != 0:
    logger.error(stdout)
    return False
  return output


async def tgs2ext(img, ext='gif'):
  _path, name = os.path.split(img)
  _name, _ = os.path.splitext(name)
  output = os.path.join(_path, _name + '.' + ext)
  anim = LottieAnimation.from_tgs(img)
  anim.save_animation(output)
  return output


async def video2ext(img, ext, mid):
  _path, name = os.path.split(img)
  _name, _ = os.path.splitext(name)
  output = os.path.join(_path, f'{_name}_{ext}.{ext}')
  bar = util.progress.Progress(mid)
  bar.set_prefix('转换中...')

  cv = 'h264'
  if ext == 'webm':
    cv = 'libvpx-vp9'
  command = [
    'ffmpeg',
    '-i',
    img,
    '-c:v',
    cv,
    '-pix_fmt',
    'yuv420p',
    '-r',
    '30',
    '-b:v',
    '1500k',
    '-lavfi',
    'scale=2560:-1:flags=lanczos,pad=ceil(iw/2)*2:ceil(ih/2)*2',
    output,
    '-y',
  ]
  returncode, stdout = await util.media.ffmpeg(
    command, progress_callback=bar.update
  )
  if returncode != 0:
    logger.error(stdout)
    return False
  return output
