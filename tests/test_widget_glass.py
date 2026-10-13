from PIL import Image, ImageDraw, ImageStat

from codex_reset_widget import render_glass


def test_glass_keeps_background_visible_and_softens_detail():
    source = Image.new("RGB", (80, 60))
    for x in range(80):
        for y in range(60):
            source.putpixel((x, y), (20, 70, 120) if x < 40 else (90, 150, 220))

    glass = render_glass(source, (80, 60), blur=8)

    assert glass.size == source.size
    assert glass.getpixel((20, 30)) != glass.getpixel((60, 30))
    assert abs(ImageStat.Stat(glass.crop((12, 20, 28, 40))).stddev[0]) < 8
    assert glass.getpixel((40, 2))[0] > glass.getpixel((40, 30))[0]


def test_glass_adapts_to_dark_desktop_without_going_opaque():
    dark = Image.new("RGB", (60, 40), (18, 25, 40))
    glass = render_glass(dark, dark.size, blur=5)

    center = glass.getpixel((30, 20))
    assert 70 < sum(center) / 3 < 220
    assert center[2] > center[0]


def test_bright_wallpaper_pattern_stays_visible_through_glass():
    wallpaper = Image.new("RGB", (320, 200), (60, 160, 220))
    ImageDraw.Draw(wallpaper).rectangle((160, 0, 319, 199), fill=(130, 200, 240))

    glass = render_glass(wallpaper, wallpaper.size, blur=12)
    left = glass.getpixel((60, 100))
    right = glass.getpixel((260, 100))

    assert left[0] <= 112  # the glass must not wash out the blue sky
    assert right[0] - left[0] >= 50  # the wallpaper shape remains visible
