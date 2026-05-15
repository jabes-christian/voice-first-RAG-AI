import numpy as np
from scipy.signal import resample_poly
from math import gcd


def convert_to_pcm16k(raw_bytes: bytes, source_rate: int) -> bytes:

    if source_rate == 16000:
        return raw_bytes

    audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)

    divisor = gcd(source_rate, 16000)
    up = 16000 // divisor
    down = source_rate // divisor

    resampled = resample_poly(audio, up, down)

    resampled = np.clip(resampled, -32768, 32767).astype(np.int16)

    return resampled.tobytes()


def chunk_audio(data: bytes, chunk_size: int = 3200) -> list[bytes]:

    return [
        data[i: i + chunk_size]
        for i in range(0, len(data), chunk_size)
    ]