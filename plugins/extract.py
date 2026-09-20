import asyncio
import logging
import os
import tempfile
import uuid

import aiofiles
from pymediainfo import MediaInfo
from pyrogram import Client

logger = logging.getLogger(__name__)


def format_track(lang: str | None, title: str | None) -> str:
    lang = (lang or "").strip()
    title = (title or "").strip()

    if lang and lang.lower() != "und":
        return lang
    if title:
        return title
    return "und"


async def get_track_languages(client: Client, media_message) -> tuple[str, str]:
    """Extract embedded audio/subtitle languages using the DreamXBotz MediaInfo method."""
    temp_path = os.path.join(
        tempfile.gettempdir(),
        f"caption_tracks_{getattr(media_message, 'id', uuid.uuid4().hex)}_{uuid.uuid4().hex}.tmp"
    )
    try:
        media = getattr(media_message, media_message.media.value) if media_message.media else None
        file_size = getattr(media, "file_size", 0) or 0
        chunk_limit = 5 if file_size > 200 * 1024 * 1024 else 4

        async with aiofiles.open(temp_path, "wb") as f:
            async for chunk in client.stream_media(media_message, limit=chunk_limit):
                await f.write(chunk)

        lib_path = os.path.abspath("MediaInfo.dll") if os.path.exists("MediaInfo.dll") else None
        media_info = await asyncio.wait_for(
            asyncio.to_thread(MediaInfo.parse, temp_path, library_file=lib_path),
            timeout=8
        )

        audio = []
        subtitles = []
        seen_audio = set()
        seen_subs = set()

        for track in media_info.tracks:
            ttype = (track.track_type or "").lower()
            if ttype not in ("audio", "text", "subtitle"):
                continue

            lang = (
                track.other_language[0]
                if getattr(track, "other_language", None)
                else track.language or "und"
            )
            value = format_track(lang, track.title)
            key = (str(lang).lower(), str(track.title or "").lower(), value.lower())

            if ttype == "audio":
                if key not in seen_audio:
                    seen_audio.add(key)
                    audio.append(value)
            else:
                if key not in seen_subs:
                    seen_subs.add(key)
                    subtitles.append(value)

        return (
            ", ".join(audio) if audio else "N/A",
            ", ".join(subtitles) if subtitles else "N/A"
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
