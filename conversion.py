from PIL import Image

# ASCII character set ordered by brightness
ASCII_CHARS = "@#S%?*+;:,. "

def frame_to_ascii(image, width=60):
    # Resize maintaining aspect ratio (ASCII characters are taller than wide, so height is halved)
    aspect_ratio = image.height / image.width
    height = int(width * aspect_ratio * 0.55)
    img = image.resize((width, height)).convert("L")
    
    pixels = img.getdata()
    ascii_str = ""
    for i, pixel in enumerate(pixels):
        ascii_str += ASCII_CHARS[pixel // 25]
        if (i + 1) % width == 0:
            ascii_str += "\n"
    return ascii_str, width, height

def generate_animated_svg(gif_path, output_path="minion-ascii.svg", columns=240):
    """Create grayscale text art with fixed columns and discrete animated frames."""
    from html import escape
    from pathlib import Path
    from PIL import ImageOps, ImageSequence

    cell_width, cell_height, padding = 6, 10, 24
    frames = []
    # Light pixels need dense glyphs on a dark background.
    ramp = " .,:;irsXA253hMHGS#9B&@"
    with Image.open(gif_path) as gif:
        rows = max(1, round(columns * gif.height / gif.width * cell_width / cell_height))
        for frame in ImageSequence.Iterator(gif):
            rgb = frame.convert("RGB")
            luminances = list(rgb.resize((columns, rows), Image.Resampling.LANCZOS)
                              .convert("L").getdata())
            gray = ImageOps.autocontrast(rgb.convert("L"))
            gray = gray.resize((columns, rows), Image.Resampling.LANCZOS)
            data = list(gray.getdata())
            lines = [
                "".join(ramp[value * (len(ramp) - 1) // 255]
                        for value in data[y * columns:(y + 1) * columns])
                for y in range(rows)
            ]
            frames.append((lines, luminances))
    width, height = columns * cell_width + padding * 2, rows * cell_height + padding * 2
    count = len(frames)
    # Preserve every ASCII space, including spaces inside grayscale spans.
    # xml:space alone does not prevent whitespace collapsing in modern browsers.
    css = ["text,tspan{white-space:pre}",
           ".frame{visibility:hidden}.frame:first-of-type{visibility:visible}"]
    for i in range(count):
        start, end = i * 100 / count, (i + 1) * 100 / count
        rules = "0%{visibility:hidden}" if i else ""
        rules += f"{start:g}%{{visibility:visible}}{end:g}%{{visibility:hidden}}"
        if end < 100:
            rules += "100%{visibility:hidden}"
        css.append(f"@keyframes f{i}{{{rules}}}.frame:nth-of-type({i + 1})"
                   f"{{animation:f{i} 3s step-end infinite}}")
    css.append("@media(prefers-reduced-motion:reduce){.frame:nth-of-type(n)"
               "{animation:none;visibility:hidden}.frame:nth-of-type(1){visibility:visible}}")
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
             '<title id="title">Animated ASCII Minion</title>',
             f'<desc id="desc">{count} animated frames, each containing {columns} columns '
             f'and {rows} rows of grayscale text art.</desc>',
             '<style>' + ''.join(css) + '</style>',
             f'<rect width="{width}" height="{height}" rx="16" fill="#111111"/>',
             '<g font-family="Courier New,monospace" '
             'font-size="10" xml:space="preserve">']
    # Explicit column positions keep the grid aligned across shade boundaries.
    column_positions = " ".join(str(padding + x * cell_width) for x in range(columns))
    for lines, luminances in frames:
        parts.append('<text class="frame">')
        for y, line in enumerate(lines):
            glyphs = []
            for x, char in enumerate(line):
                shade = luminances[y * columns + x]
                glyphs.append(f'<tspan fill="#{shade:02x}{shade:02x}{shade:02x}">'
                              f'{escape(char)}</tspan>')
            parts.append(f'<tspan class="row" x="{column_positions}" '
                         f'y="{padding + 8 + y * cell_height}">'
                         + ''.join(glyphs) + '</tspan>')
        parts.append('</text>')
    parts.append('</g></svg>')
    Path(output_path).write_text("\n".join(parts), encoding="utf-8")
    print(f"Generated {output_path}: {columns} x {rows} characters, {count} frames, {width} x {height} canvas")


if __name__ == "__main__":
    generate_animated_svg("minion.gif", columns=80)
