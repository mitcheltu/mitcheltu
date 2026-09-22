"""Render the repository's GIF as a GitHub-ready ASCII animation."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageSequence

from conversion import frame_to_ascii

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
COLUMNS = 96
CELL_WIDTH, CELL_HEIGHT = 8, 12
PADDING = 24
BACKGROUND = "#0d1117"


def main():
    ASSETS.mkdir(exist_ok=True)
    font = ImageFont.load_default()
    rendered = []
    durations = []
    with Image.open(ROOT / "minion.gif") as source:
        for frame in ImageSequence.Iterator(source):
            rgb = frame.convert("RGB")
            ascii_art, columns, rows = frame_to_ascii(rgb, width=COLUMNS)
            colors = rgb.resize((columns, rows))
            canvas = Image.new(
                "RGB", (columns * CELL_WIDTH + PADDING * 2, rows * CELL_HEIGHT + 112),
                BACKGROUND,
            )
            draw = ImageDraw.Draw(canvas)
            draw.text((PADDING, 18), "MINION / CHARACTER STUDY", font=font, fill="#f3cf55")
            draw.text((canvas.width - 179, 18), "ASCII PLAYBACK  [LOOP]", font=font, fill="#8b949e")
            draw.line((PADDING, 42, canvas.width - PADDING, 42), fill="#30363d")
            for y, line in enumerate(ascii_art.splitlines()):
                for x, char in enumerate(line):
                    # A small luminance floor keeps the dark parts legible.
                    color = tuple(max(48, channel) for channel in colors.getpixel((x, y)))
                    draw.text((PADDING + x * CELL_WIDTH, 58 + y * CELL_HEIGHT),
                              char, font=font, fill=color)
            footer_y = canvas.height - 28
            draw.text((PADDING, footer_y), "ONE GIF. THOUSANDS OF CHARACTERS.",
                      font=font, fill="#8b949e")
            draw.text((canvas.width - 145, footer_y), "PYTHON + PILLOW", font=font, fill="#f3cf55")
            rendered.append(canvas)
            durations.append(frame.info.get("duration", 100))
    rendered[0].save(ASSETS / "minion-ascii.gif", save_all=True,
                     append_images=rendered[1:], duration=durations, loop=0,
                     disposal=2, optimize=False)
    rendered[0].save(ASSETS / "minion-ascii-still.png")
    # The strip is generated from the input, so its numbers stay in sync.
    values = [("SOURCE FRAMES", str(len(rendered))), ("TEXT COLUMNS", str(COLUMNS)),
              ("LOOP DURATION", f"{sum(durations) / 1000:g} s"), ("OUTPUT", "GIF + PNG")]
    cells = []
    for i, (label, value) in enumerate(values):
        x = 24 + i * 204
        cells.append(f'<text x="{x}" y="28" fill="#8b949e" font-size="10">{label}</text>'
                     f'<text x="{x}" y="59" fill="#f3cf55" font-size="22">{value}</text>')
    (ASSETS / "specs.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="816" height="84" viewBox="0 0 816 84">'
        '<rect width="816" height="84" rx="8" fill="#0d1117"/>'
        '<g font-family="monospace">' + "".join(cells) + '</g></svg>', encoding="utf-8")
    print(f"Rendered {len(rendered)} ASCII frames to {ASSETS}")


if __name__ == "__main__":
    main()
