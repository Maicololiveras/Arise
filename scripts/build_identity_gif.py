"""Encode ARISE's existing app frames as a lightweight README identity GIF."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'docs/identity/arise-assistant.gif'
atlas = Image.open(ROOT / 'assets/orb-atlas.png').convert('RGBA')
frame_width = atlas.width // 24
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--font', default='DejaVuSans.ttf', help='TrueType font path (e.g. C:/Windows/Fonts/segoeui.ttf)')
font = ImageFont.truetype(parser.parse_args().font, 38)
background = Image.new('RGB', (720, 264), '#0A1828')
draw = ImageDraw.Draw(background)
draw.rounded_rectangle((1, 1, 718, 262), radius=24, outline='#174058', width=2)
draw.text((276, 91), 'ARISE', font=font, fill='#74F6FF')
draw.text((276, 138), 'Assistant', font=font, fill='#E4F5FC')
frames = []
for index in range(24):
    frame = background.copy()
    orb = atlas.crop((index * frame_width, 0, (index + 1) * frame_width, atlas.height))
    frame.paste(orb, (44, 36), orb)
    frames.append(frame)
# A common palette avoids changes to the fixed wordmark between frames.
palette = frames[0].quantize(colors=192)
frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
frames[0].save(OUTPUT, save_all=True, append_images=frames[1:], duration=100, loop=0, optimize=True, disposal=1)
with Image.open(OUTPUT) as result:
    assert result.n_frames == 24 and result.size == (720, 264)
    assert result.info['loop'] == 0
print(f'{OUTPUT}: {OUTPUT.stat().st_size} bytes, 24 frames, 10 FPS')
