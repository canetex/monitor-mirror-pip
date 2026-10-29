"""Testes da lógica de enquadramento (letterbox)."""

from mirror import scale_to_fit


def test_scale_down_keeps_aspect() -> None:
    w, h = scale_to_fit(3840, 2160, 1920, 1080)
    assert (w, h) == (1920, 1080)


def test_scale_up_keeps_aspect() -> None:
    w, h = scale_to_fit(800, 600, 1920, 1080)
    assert (w, h) == (1440, 1080)


def test_narrow_target_letterbox() -> None:
    w, h = scale_to_fit(1920, 1080, 1000, 1080)
    assert (w, h) == (1000, 562)


def test_zero_source_returns_one_pixel() -> None:
    assert scale_to_fit(0, 0, 100, 100) == (1, 1)
