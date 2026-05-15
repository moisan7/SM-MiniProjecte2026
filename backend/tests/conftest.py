import io
import struct
import cv2
import numpy as np
import pytest


@pytest.fixture
def sample_image_bytes() -> bytes:
    """100×100 white image with a black rectangle — valid JPEG."""
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    cv2.rectangle(img, (10, 10), (90, 90), (0, 0, 0), 2)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


@pytest.fixture
def sample_audio_bytes() -> bytes:
    """Minimal valid WAV file (16-bit PCM, 16 kHz, 1 ch, ~0.1 s silence)."""
    sample_rate = 16000
    num_samples = 1600
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align

    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, num_channels, sample_rate,
                          byte_rate, block_align, bits_per_sample))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(b"\x00" * data_size)
    return buf.getvalue()
