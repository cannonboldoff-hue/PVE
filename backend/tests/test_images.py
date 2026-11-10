from PIL import Image

from app.clients import video


def test_photo_becomes_five_second_clip(tmp_path):
    src = tmp_path / "p.jpg"
    Image.new("RGB", (301, 401), (200, 60, 60)).save(src)  # small and odd-sized: both break the encoder if not handled
    out = tmp_path / "p.mp4"
    video.image_to_clip(src, out)
    i = video.info(out)
    assert abs(i["duration"] - 5.0) < 0.2 and i["width"] >= 540 and i["height"] >= 720
    assert i["width"] % 2 == 0 and i["height"] % 2 == 0
    assert not list(tmp_path.glob("*.still.*"))  # temp files cleaned up


def test_exif_rotation_is_applied(tmp_path):
    src = tmp_path / "r.jpg"
    im = Image.new("RGB", (800, 600), (10, 120, 200))
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 on display: a landscape file shows as portrait
    im.save(src, exif=exif)
    out = tmp_path / "r.mp4"
    video.image_to_clip(src, out)
    i = video.info(out)
    assert i["height"] > i["width"]
