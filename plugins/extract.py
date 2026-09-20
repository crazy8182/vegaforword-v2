import asyncio
import logging
import os
import tempfile
import uuid

import aiofiles
from pymediainfo import MediaInfo

logger = logging.getLogger(__name__)

def format_track(lang: str | None, title: str | None) -> str:
    lang = (lang or "").strip()
    title = (title or "").strip()
    if lang and lang.lower() != "und":
        return lang
    if title:
        return title
    return "und"

async def get_track_languages(client, media_message) -> tuple[str, str]:
    """DreamXBotz-style MediaInfo extraction for audio/subtitle languages.

    Only a small initial portion of the Telegram media is downloaded, matching
    the original DreamX approach. pymediainfo 7.0.1 supplies a bundled native
    MediaInfo library on supported Linux wheels, so Build & Run does not need
    Docker/apt-installed MediaInfo.
    """
    temp_path = os.path.join(
        tempfile.gettempdir(),
        f"caption_tracks_{getattr(media_message, 'id', uuid.uuid4().hex)}_{uuid.uuid4().hex}.tmp"
    )
    try:
        media = getattr(media_message, media_message.media.value) if media_message.media else None
        if not media:
            return "N/A", "N/A"

        file_size = getattr(media, "file_size", 0) or 0
        chunk_limit = 5 if file_size > 200 * 1024 * 1024 else 4

        async with aiofiles.open(temp_path, "wb") as f:
            async for chunk in client.stream_media(media_message, limit=chunk_limit):
                await f.write(chunk)

        media_info = await asyncio.wait_for(
            asyncio.to_thread(MediaInfo.parse, temp_path),
            timeout=10
        )

        audio = []
        subtitles = []
        seen_audio = set()
        seen_subs = set()

        for track in media_info.tracks:
            track_type = (getattr(track, "track_type", "") or "").lower()
            if track_type not in ("audio", "text", "subtitle"):
                continue

            other_language = getattr(track, "other_language", None)
            lang = (
                other_language[0]
                if other_language
                else getattr(track, "language", None) or "und"
            )
            title = getattr(track, "title", None) or ""
            value = format_track(lang, title)
            key = (str(lang).lower(), str(title).lower(), value.lower())

            if track_type == "audio":
                if key not in seen_audio:
                    seen_audio.add(key)
                    audio.append(value)
            else:
                if key not in seen_subs:
                    seen_subs.add(key)
                    subtitles.append(value)

        return (
            ", ".join(audio) if audio else "N/A",
            ", ".join(subtitles) if subtitles else "N/A",
        )
    except Exception:
        logger.exception("Failed to extract embedded audio/subtitle tracks")
        return "N/A", "N/A"
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
