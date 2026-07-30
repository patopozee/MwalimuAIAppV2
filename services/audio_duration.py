from io import BytesIO
from mutagen.mp3 import MP3


def get_audio_duration(audio_bytes: bytes) -> float:
    """
    Returns the exact duration of an MP3 in seconds.
    """
    audio = MP3(BytesIO(audio_bytes))
    return float(audio.info.length)