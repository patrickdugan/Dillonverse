from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .store import read_jsonl, upsert


def _yt_dlp() -> list[str]:
    executable = shutil.which("yt-dlp")
    if executable:
        return [executable]
    try:
        from importlib.util import find_spec

        if find_spec("yt_dlp") is not None:
            return [sys.executable, "-m", "yt_dlp"]
    except (ImportError, ValueError):
        pass
    raise FileNotFoundError("yt-dlp is not installed; run: python -m pip install -e '.[collector]'")


def discover(root: Path, limit: int | None = None) -> int:
    config = json.loads((root / "config/sources.json").read_text(encoding="utf-8"))
    result = subprocess.run(
        [*_yt_dlp(), "--flat-playlist", "--dump-single-json", "--skip-download", "--no-warnings", config["youtube_channel"]],
        text=True,
        capture_output=True,
        check=False,
        timeout=300,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[-1500:])
    listing = json.loads(result.stdout)
    entries = [item for item in (listing.get("entries") or []) if item and item.get("id")]
    if limit is not None:
        entries = entries[:limit]
    now = datetime.now(timezone.utc).isoformat()
    videos = []
    for item in entries:
        video_id = item["id"]
        videos.append({
            "video_id": video_id,
            "canonical_url": f"https://www.youtube.com/watch?v={video_id}",
            "title": item.get("title"),
            "publication_date": item.get("upload_date"),
            "duration_seconds": item.get("duration"),
            "channel": item.get("channel") or listing.get("channel"),
            "channel_id": item.get("channel_id") or listing.get("channel_id"),
            "discovered_from": config["youtube_channel"],
            "discovered_at": now,
            "caption_status": "not_checked",
            "transcript_path": None,
            "scope_review": "review_required",
        })
    upsert(root / "catalog/videos.jsonl", videos)
    return len(videos)


def _clean_vtt(raw: str) -> tuple[list[dict[str, Any]], str]:
    cues: list[dict[str, Any]] = []
    for block in re.split(r"\n\s*\n", raw.replace("\r\n", "\n").replace("\r", "\n")):
        lines = block.splitlines()
        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue
        timing = lines[timing_index].split("-->", 1)
        start = timing[0].strip().split()[0]
        end = timing[1].strip().split()[0]
        text = html.unescape(re.sub(r"<[^>]*>", "", " ".join(lines[timing_index + 1:]))).strip()
        text = re.sub(r"\s+", " ", text)
        if text and (not cues or text != cues[-1]["text"]):
            cues.append({"start": start, "end": end, "text": text})
    formatted = "\n".join(f"[{cue['start']} --> {cue['end']}] {cue['text']}" for cue in cues)
    return cues, formatted + ("\n" if formatted else "")


def collect_captions(root: Path, limit: int | None = None, video_ids: set[str] | None = None) -> dict[str, int]:
    catalog = root / "catalog/videos.jsonl"
    videos = read_jsonl(catalog)
    if video_ids:
        videos = [video for video in videos if video["video_id"] in video_ids]
    if limit is not None:
        videos = videos[:limit]
    counts = {"checked": 0, "stored": 0, "unavailable": 0, "failed": 0, "skipped": 0}
    for video in videos:
        counts["checked"] += 1
        if video.get("transcript_path") and (root / video["transcript_path"]).is_file():
            counts["skipped"] += 1
            continue
        video_id = video["video_id"]
        private_dir = root / "transcripts/private"
        private_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(private_dir / f"{video_id}.%(ext)s")
        result = subprocess.run(
            [*_yt_dlp(), "--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", "en,en-orig", "--sub-format", "vtt", "--output", output_template, video["canonical_url"]],
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
        vtt_files = sorted(private_dir.glob(f"{video_id}*.vtt"))
        if result.returncode and not vtt_files:
            video["caption_status"] = "failed"
            video["caption_error"] = (result.stderr or result.stdout).strip()[-800:]
            counts["failed"] += 1
        elif not vtt_files:
            video["caption_status"] = "unavailable"
            video["caption_checked_at"] = datetime.now(timezone.utc).isoformat()
            counts["unavailable"] += 1
        else:
            source = vtt_files[0]
            cues, formatted = _clean_vtt(source.read_text(encoding="utf-8-sig"))
            text_path = source.with_suffix(".txt")
            text_path.write_text(formatted, encoding="utf-8")
            video["caption_status"] = "stored_locally"
            video["caption_language"] = source.name.removeprefix(video_id + ".").removesuffix(".vtt")
            video["transcript_path"] = text_path.relative_to(root).as_posix()
            video["caption_source_file"] = source.relative_to(root).as_posix()
            video["caption_kind"] = "YouTube-provided caption; manual or automatic as provided by YouTube"
            video["caption_cue_count"] = len(cues)
            video["caption_checked_at"] = datetime.now(timezone.utc).isoformat()
            counts["stored"] += 1
        upsert(catalog, [video])
        time.sleep(1.0)
    return counts
