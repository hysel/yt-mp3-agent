#!/usr/bin/env python3
"""
YouTube / YouTube Music Channel MP3 Downloader
===============================================
Downloads all videos from a YouTube or YouTube Music channel as MP3 files,
with embedded album art (video thumbnail) and artist tag (channel name).

FEATURES
--------
  • YouTube and YouTube Music channel support
  • Parallel downloads (multi-threaded)
  • Skips already-downloaded videos via an archive file
  • Prompts to overwrite or skip files that exist on disk
  • Filters out videos longer than a specified duration
  • Auto-downloads ffmpeg on Windows if not installed
  • Progress bars per file and overall
  • Supports a text file with multiple channel URLs

REQUIREMENTS
------------
  pip install -U "yt-dlp[default]" requests tqdm mutagen pillow

  JS runtime (pick one — required by yt-dlp for YouTube):
    Deno (recommended, enabled by default):  https://deno.com
    Node.js 20+:                             https://nodejs.org

  ffmpeg:
    Windows  : auto-downloaded on first run
    macOS    : brew install ffmpeg
    Ubuntu   : sudo apt install ffmpeg

OUTPUT STRUCTURE
----------------
  <destination>/
  └── <Channel Name>/
      ├── Video Title.mp3        ← audio + embedded art + artist tag
      ├── Another Video.mp3
      └── .archive.txt           ← tracks downloaded IDs (hidden file)

ARCHIVE FILE
------------
  .archive.txt records the YouTube video ID of every completed download.
  On the next run, any ID already in this file is skipped automatically.
  Delete a line to re-download that video. Delete the file to start fresh.

USAGE
-----
  Single channel:
    python youtube_mp3_agent.py <channel_url> <destination> [options]

  Multiple channels from a file:
    python youtube_mp3_agent.py --url-file channels.txt <destination> [options]

EXAMPLES
--------
  # Download entire channel
  python youtube_mp3_agent.py https://www.youtube.com/@mkbhd C:/Music

  # YouTube Music channel
  python youtube_mp3_agent.py https://music.youtube.com/channel/UCxxxx C:/Music

  # Only the 20 most recent videos, at 320 kbps, using 5 threads
  python youtube_mp3_agent.py https://www.youtube.com/@lexfridman C:/Music -n 20 -q 320 -w 5

  # Skip anything longer than 10 minutes (e.g. exclude podcasts / livestreams)
  python youtube_mp3_agent.py https://www.youtube.com/@mkbhd C:/Music --max-duration 10

  # Multiple channels from a file
  python youtube_mp3_agent.py --url-file channels.txt C:/Music

  channels.txt format:
    # Lines starting with # are comments and are ignored
    https://www.youtube.com/@mkbhd
    https://www.youtube.com/@lexfridman
    https://music.youtube.com/channel/UCxxxx
"""

import argparse
import os
import platform
import re
import shutil
import sys
import zipfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Dependency / environment setup
# ---------------------------------------------------------------------------

def check_dependencies():
    missing = []
    for pkg in ("yt_dlp", "tqdm", "requests"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg.replace("_", "-"))
    if missing:
        print("❌  Missing packages:", ", ".join(missing))
        print('    Run:  pip install -U "yt-dlp[default]" requests tqdm')
        sys.exit(1)


def find_or_install_ffmpeg() -> str:
    """Return directory containing ffmpeg. Auto-downloads a Windows static build if missing."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return os.path.dirname(ffmpeg)

    if platform.system() != "Windows":
        print("⚠️  ffmpeg not found.")
        print("    macOS:   brew install ffmpeg")
        print("    Ubuntu:  sudo apt install ffmpeg")
        sys.exit(1)

    ffmpeg_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ffmpeg-yt-dlp"
    ffmpeg_exe = ffmpeg_dir / "ffmpeg.exe"

    if ffmpeg_exe.exists():
        return str(ffmpeg_dir)

    print("\n📦  ffmpeg not found — downloading a static Windows build...")
    import requests
    from tqdm import tqdm

    url = (
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
        "ffmpeg-master-latest-win64-gpl.zip"
    )
    zip_path = ffmpeg_dir / "ffmpeg.zip"
    ffmpeg_dir.mkdir(parents=True, exist_ok=True)

    r = requests.get(url, stream=True, timeout=180)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))

    with open(zip_path, "wb") as f, tqdm(
        total=total, unit="B", unit_scale=True, unit_divisor=1024,
        desc="  Downloading ffmpeg", colour="cyan"
    ) as bar:
        for chunk in r.iter_content(chunk_size=256 * 1024):
            f.write(chunk)
            bar.update(len(chunk))

    print("    Extracting...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            if member.endswith("bin/ffmpeg.exe"):
                zf.extract(member, ffmpeg_dir)
                (ffmpeg_dir / member).rename(ffmpeg_exe)
                break
    zip_path.unlink(missing_ok=True)

    if not ffmpeg_exe.exists():
        print("❌  Extraction failed. Install ffmpeg manually: https://ffmpeg.org")
        sys.exit(1)

    print(f"✅  ffmpeg ready: {ffmpeg_exe}\n")
    return str(ffmpeg_dir)


def find_nodejs() -> str | None:
    node = shutil.which("node")
    if node:
        return os.path.dirname(node)
    if platform.system() != "Windows":
        return None
    for p in [
        Path(os.environ.get("ProgramFiles",      "C:/Program Files"))       / "nodejs",
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "nodejs",
    ]:
        if (p / "node.exe").exists():
            return str(p)
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_youtube_music(url: str) -> bool:
    """Return True if the URL is from music.youtube.com."""
    return "music.youtube.com" in url


def channel_name_from_url(url: str) -> str:
    """
    Derive a safe folder name from the channel URL without making any network
    requests.

    Examples:
      https://www.youtube.com/@mkbhd               -> mkbhd
      https://www.youtube.com/channel/UCxxxx       -> UCxxxx
      https://music.youtube.com/channel/UCxxxx     -> UCxxxx
      https://music.youtube.com/browse/MPADxxxx    -> MPADxxxx
    """
    url = url.rstrip("/")
    for pattern in (
        r"/@([^/?&]+)",
        r"/c/([^/?&]+)",
        r"/channel/([^/?&]+)",
        r"/user/([^/?&]+)",
        r"/browse/([^/?&]+)",
    ):
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return url.split("/")[-1] or "channel"


def sanitize_folder(name: str) -> str:
    return "".join(c if c not in r'\/:*?"<>|' else "_" for c in name).strip()


def load_archive(archive_path: Path) -> set[str]:
    ids: set[str] = set()
    if archive_path.exists():
        for line in archive_path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split()
            if len(parts) == 2:
                ids.add(parts[1])
    return ids


# ---------------------------------------------------------------------------
# Progress hook
# ---------------------------------------------------------------------------

class DownloadProgress:
    """Feeds yt-dlp's progress hook into a tqdm bar (one bar per file)."""

    def __init__(self):
        self._bar  = None
        self._last = 0

    def __call__(self, d: dict):
        from tqdm import tqdm

        status = d.get("status")

        if status == "downloading":
            total      = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            speed      = d.get("speed") or 0
            filename   = Path(d.get("filename", "")).stem[:55]

            if self._bar is None:
                self._bar  = tqdm(
                    total=total,
                    unit="B", unit_scale=True, unit_divisor=1024,
                    desc=f"  ⬇  {filename}",
                    colour="green",
                    leave=False,
                )
                self._last = 0

            inc = downloaded - self._last
            if inc > 0:
                self._bar.update(inc)
                self._last = downloaded

            if total and self._bar.total != total:
                self._bar.total = total
                self._bar.refresh()

            if speed:
                self._bar.set_postfix(speed=f"{speed / 1_048_576:.1f} MB/s", refresh=False)

        elif status == "finished":
            if self._bar:
                self._bar.close()
                self._bar = None
            self._last = 0

        elif status == "postprocessing":
            if self._bar:
                self._bar.set_description("  ⚙  Converting to MP3...", refresh=True)

        elif status == "error":
            if self._bar:
                self._bar.close()
                self._bar = None
            self._last = 0


# ---------------------------------------------------------------------------
# Metadata options
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field

@dataclass
class MetadataOptions:
    genre:                  str | None = None   # --genre
    album:                  str | None = None   # --album
    use_upload_year:        bool       = False  # --year
    comment_source_url:     bool       = False  # --comment-url
    track_numbers:          bool       = False  # --track-numbers
    strip_title_patterns:   bool       = False  # --strip-title
    no_art:                 bool       = False  # --no-art
    no_artist:              bool       = False  # --no-artist
    description_as_comment: bool       = False  # --description-as-comment


# Common YouTube title noise to strip when --strip-title is enabled
_STRIP_PATTERNS = [
    r"\s*[\(\[]?\s*official\s*(music\s*)?video\s*[\)\]]?",
    r"\s*[\(\[]?\s*official\s*audio\s*[\)\]]?",
    r"\s*[\(\[]?\s*lyrics?\s*[\)\]]?",
    r"\s*[\(\[]?\s*lyric\s*video\s*[\)\]]?",
    r"\s*[\(\[]?\s*audio\s*[\)\]]?",
    r"\s*[\(\[]?\s*hd\s*[\)\]]?",
    r"\s*[\(\[]?\s*4k\s*[\)\]]?",
    r"\s*[\(\[]\s*explicit\s*[\)\]]",
    r"\s*\|\s*.+$",
]

def clean_title(title: str) -> str:
    """Strip common YouTube noise from a track title."""
    import re as _re
    for pat in _STRIP_PATTERNS:
        title = _re.sub(pat, "", title, flags=_re.IGNORECASE)
    return title.strip(" -–—")


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def run(channel_url: str, output_base: str, limit: int | None, quality: str, workers: int = 3, max_duration: int | None = None, meta: MetadataOptions | None = None):
    check_dependencies()
    if meta is None:
        meta = MetadataOptions()
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import yt_dlp
    from tqdm import tqdm

    ffmpeg_dir = find_or_install_ffmpeg()
    music_mode = is_youtube_music(channel_url)

    if music_mode:
        print("\U0001f3b5  YouTube Music mode enabled")

    node_dir = find_nodejs()
    if node_dir:
        os.environ["PATH"] = node_dir + os.pathsep + os.environ.get("PATH", "")
        print(f"✅  Node.js : {node_dir}")
    else:
        print("ℹ️   Node.js not found — Deno will be used (install from https://deno.com if needed)")

    Path(output_base).mkdir(parents=True, exist_ok=True)
    archive_file = Path(output_base) / ".archive.txt"
    archive_lock = threading.Lock()
    archived_ids = load_archive(archive_file)
    already_done = len(archived_ids)

    # yt-dlp redirects music.youtube.com -> youtube.com/channel/UC.../videos internally.
    # That /videos suffix triggers "unviewable playlist", so we convert the URL
    # to a plain youtube.com channel URL ourselves and drop any /videos suffix.
    if music_mode:
        # Resolve the redirect by doing a quick silent fetch, then use the resolved URL
        resolve_opts = {"quiet": True, "extract_flat": True, "skip_download": True,
                        "ignoreerrors": True, "ffmpeg_location": ffmpeg_dir}
        with yt_dlp.YoutubeDL(resolve_opts) as ydl:
            resolved = ydl.extract_info(channel_url, download=False)
        # The resolved webpage_url gives us the canonical youtube.com URL
        resolved_url = (resolved or {}).get("webpage_url") or channel_url
        # Strip any /videos, /shorts, /streams suffix yt-dlp may have added
        resolved_url = re.sub(r"/(videos|shorts|streams|releases)$", "", resolved_url.rstrip("/"))
        channel_url = resolved_url
        print(f"   ↳  Resolved to: {channel_url}")

    # --- Pre-fetch video list (flat, no download) ---
    print(f"\n🔍  Fetching video list from: {channel_url}")
    flat_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "ignoreerrors": True,
        "ffmpeg_location": ffmpeg_dir,
    }
    with yt_dlp.YoutubeDL(flat_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)

    all_entries = [e for e in (info.get("entries") or []) if e]
    if limit:
        all_entries = all_entries[:limit]

    # Grab the real channel display name from the flat-fetch metadata
    channel_name = (
        info.get("channel")
        or info.get("uploader")
        or info.get("playlist_uploader")
        or (all_entries[0].get("channel") if all_entries else None)
        or channel_name_from_url(channel_url)
    )
    channel_name = sanitize_folder(channel_name)

    # Filter out videos that exceed the max duration
    if max_duration is not None:
        max_secs = max_duration * 60
        before   = len(all_entries)
        all_entries = [
            e for e in all_entries
            if (e.get("duration") or 0) <= max_secs or e.get("duration") is None
        ]
        filtered = before - len(all_entries)
        if filtered:
            print(f"⏱️   Filtered out  : {filtered} video(s) longer than {max_duration} min")

    total       = len(all_entries)
    to_download_entries = [e for e in all_entries if e.get("id") not in archived_ids]
    to_download = len(to_download_entries)
    to_skip     = total - to_download

    # --- Check for files that already exist on disk ---
    # Now that we know channel_name, look directly in the right folder.
    channel_dir = Path(output_base) / channel_name

    def existing_mp3(entry: dict) -> Path | None:
        t = entry.get("title")
        if not t:
            return None
        safe = sanitize_folder(t)
        p = channel_dir / f"{safe}.mp3"
        return p if p.exists() else None

    conflicts = [(e, existing_mp3(e)) for e in to_download_entries]
    conflicts = [(e, p) for e, p in conflicts if p is not None]

    # Map video_id -> True (overwrite) / False (skip)
    overwrite_decisions: dict[str, bool] = {}

    if conflicts:
        print(f"\n⚠️   {len(conflicts)} file(s) already exist on disk:")
        for entry, path in conflicts[:5]:
            print(f"     • {path.name}")
        if len(conflicts) > 5:
            print(f"     ... and {len(conflicts) - 5} more")
        print()
        print("  [O] Overwrite all")
        print("  [S] Skip all")
        print("  [A] Ask for each file")
        while True:
            choice = input("  Your choice (O/S/A): ").strip().upper()
            if choice in ("O", "S", "A"):
                break
            print("  Please type O, S, or A.")

        if choice == "O":
            for entry, _ in conflicts:
                overwrite_decisions[entry.get("id", "")] = True
            print("  → Overwriting all existing files.\n")

        elif choice == "S":
            for entry, _ in conflicts:
                overwrite_decisions[entry.get("id", "")] = False
            print("  → Skipping all existing files.\n")

        else:
            # Ask individually — with "apply to all remaining" escape hatch
            bulk_policy: bool | None = None
            for entry, path in conflicts:
                vid_id = entry.get("id", "")
                if bulk_policy is not None:
                    overwrite_decisions[vid_id] = bulk_policy
                    continue
                print(f"\n  ⚠️  {path.name}")
                print("    [O] Overwrite   [S] Skip   [OA] Overwrite all remaining   [SA] Skip all remaining")
                while True:
                    ans = input("    Your choice: ").strip().upper()
                    if ans in ("O", "S", "OA", "SA"):
                        break
                    print("    Please type O, S, OA, or SA.")
                if ans == "OA":
                    bulk_policy = True
                    overwrite_decisions[vid_id] = True
                    print("  → Overwriting all remaining existing files.")
                elif ans == "SA":
                    bulk_policy = False
                    overwrite_decisions[vid_id] = False
                    print("  → Skipping all remaining existing files.")
                elif ans == "O":
                    overwrite_decisions[vid_id] = True
                else:
                    overwrite_decisions[vid_id] = False

    # Remove skipped entries from the download queue
    to_download_entries = [
        e for e in to_download_entries
        if overwrite_decisions.get(e.get("id", ""), True)  # default True = not a conflict
    ]

    to_download = len(to_download_entries)
    to_skip     = total - to_download

    source_label = "YouTube Music" if music_mode else "YouTube"
    print(f"\n📁  Output      : {Path(output_base).resolve() / channel_name}")
    print(f"▶️   Source      : {source_label}")
    print(f"🎵  Quality     : {quality} kbps")
    print(f"🧵  Threads     : {workers}")
    if max_duration:
        print(f"⏱️   Max duration : {max_duration} min")
    print(f"📼  Total       : {total} video(s)")
    print(f"⬇️   To download : {to_download} video(s)")
    print(f"⏭️   To skip     : {to_skip} already downloaded")
    print("=" * 60)

    if to_download == 0:
        print("✅  Nothing new to download.")
        return

    stats_lock = threading.Lock()
    stats = {"success": 0, "failed": 0}

    # Overall bar sits at position 0; per-thread bars occupy positions 1..workers
    overall = tqdm(
        total=to_download,
        unit=" video",
        desc="📦  Overall",
        colour="blue",
        position=0,
        leave=True,
    )
    overall.set_postfix(done=0, skipped=to_skip, failed=0)

    # Pool of tqdm bar slots for worker threads (position 1, 2, 3, ...)
    bar_slots   = list(range(1, workers + 1))
    slot_lock   = threading.Lock()
    free_slots  = list(bar_slots)

    def acquire_slot() -> int:
        with slot_lock:
            return free_slots.pop(0) if free_slots else bar_slots[0]

    def release_slot(slot: int):
        with slot_lock:
            if slot not in free_slots:
                free_slots.append(slot)

    def write_archive(video_id: str):
        with archive_lock:
            with open(archive_file, "a", encoding="utf-8") as f:
                f.write(f"youtube {video_id}\n")

    def download_one(entry: dict, force_overwrite: bool = False, track_num: int | None = None):
        video_id = entry.get("id")
        title    = entry.get("title") or video_id or "Unknown"
        url      = f"https://www.youtube.com/watch?v={video_id}"
        slot     = acquire_slot()

        # Delete any existing file variants so yt-dlp's own checks don't block it
        if force_overwrite:
            for ext in ("mp3", "m4a", "webm", "opus", "ogg", "jpg", "webp", "png"):
                for f in Path(output_base).glob(f"{channel_name}/{title}.{ext}"):
                    try:
                        f.unlink()
                    except OSError:
                        pass

        printed_start = False
        printed_done  = False

        file_bar: list = [None]
        last_bytes: list[int] = [0]

        def progress_hook(d: dict):
            nonlocal printed_start
            status = d.get("status")
            if status == "downloading":
                # Print the "now downloading" line exactly once
                if not printed_start:
                    overall.write(f"▶  {title}")
                    printed_start = True

                total_b    = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                speed      = d.get("speed") or 0

                if file_bar[0] is None:
                    file_bar[0] = tqdm(
                        total=total_b,
                        unit="B", unit_scale=True, unit_divisor=1024,
                        desc=f"  [{slot}] {title[:40]}",
                        colour="green",
                        position=slot,
                        leave=False,
                    )
                    last_bytes[0] = 0

                inc = downloaded - last_bytes[0]
                if inc > 0:
                    file_bar[0].update(inc)
                    last_bytes[0] = downloaded

                if total_b and file_bar[0].total != total_b:
                    file_bar[0].total = total_b
                    file_bar[0].refresh()

                if speed:
                    file_bar[0].set_postfix(
                        speed=f"{speed / 1_048_576:.1f} MB/s", refresh=False
                    )

            elif status == "finished":
                if file_bar[0]:
                    file_bar[0].close()
                    file_bar[0] = None
                last_bytes[0] = 0

            elif status == "postprocessing":
                if file_bar[0]:
                    file_bar[0].set_description(
                        f"  [{slot}] ⚙ Converting: {title[:35]}", refresh=True
                    )

            elif status == "error":
                if file_bar[0]:
                    file_bar[0].close()
                    file_bar[0] = None

        def postprocessor_hook(d: dict):
            nonlocal printed_done
            # yt-dlp fires postprocessor_hook "finished" once per postprocessor
            # (e.g. once for extraction, once for metadata). Only act on the
            # final MP3 postprocessor to avoid printing the ✅ line multiple times.
            if d["status"] != "finished":
                return
            pp = d.get("postprocessor", "")
            # Only fire on the final postprocessor to avoid multiple prints
            if pp and pp != last_pp:
                return
            if printed_done:
                return
            printed_done = True

            write_archive(video_id)
            with stats_lock:
                stats["success"] += 1
                s = stats["success"]
                f = stats["failed"]
            overall.update(1)
            overall.set_postfix(done=s, skipped=to_skip, failed=f)
            overall.write(f"  ✅  {title[:70]}")

        # After URL resolution music.youtube.com -> youtube.com, no special extractor needed
        ydl_opts_extra = {}

        # --- Build track title (optionally cleaned) ---
        track_title = clean_title(title) if meta.strip_title_patterns else title

        # --- Build ffmpeg metadata args ---
        ffmpeg_meta_args = []
        # Always set the cleaned title
        ffmpeg_meta_args += ["-metadata", f"title={track_title}"]
        # Artist tag: channel name unless --no-artist
        if not meta.no_artist:
            ffmpeg_meta_args += ["-metadata", f"artist={channel_name}"]
        # Genre
        if meta.genre:
            ffmpeg_meta_args += ["-metadata", f"genre={meta.genre}"]
        # Track number
        if meta.track_numbers and track_num is not None:
            ffmpeg_meta_args += ["-metadata", f"track={track_num}"]
        # Album
        if meta.album:
            ffmpeg_meta_args += ["-metadata", f"album={meta.album}"]
        # Upload year as date/year tag
        if meta.use_upload_year:
            ffmpeg_meta_args += ["-metadata", "date=%(upload_date>%Y)s"]
        # Video URL as comment
        if meta.comment_source_url:
            video_url_comment = f"https://www.youtube.com/watch?v={video_id}"
            ffmpeg_meta_args += ["-metadata", f"comment={video_url_comment}"]

        # --- Build postprocessors list ---
        postprocessors = [
            {
                # 1. Extract audio to MP3
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            },
            {
                # 2. Write ID3 tags
                "key": "FFmpegMetadata",
                "add_metadata": True,
                "add_chapters": False,
            },
        ]
        # Description as comment — fetch full info (slight overhead per video)
        if meta.description_as_comment:
            try:
                import yt_dlp as _ydlp
                with _ydlp.YoutubeDL({"quiet": True, "skip_download": True}) as _ydl:
                    _vinfo = _ydl.extract_info(url, download=False)
                _desc = (_vinfo or {}).get("description", "")
                if _desc:
                    # Truncate to 500 chars to keep ID3 tag reasonable
                    ffmpeg_meta_args += ["-metadata", f"comment={_desc[:500]}"]
            except Exception:
                pass
        # Album art — skip if --no-art
        if not meta.no_art:
            postprocessors.append({
                "key": "EmbedThumbnail",
                "already_have_thumbnail": False,
            })

        # The last postprocessor name for the done-hook
        last_pp = "EmbedThumbnail" if not meta.no_art else "FFmpegMetadata"

        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": str(Path(output_base) / channel_name / "%(title)s.%(ext)s"),
            "ffmpeg_location": ffmpeg_dir,
            "windowsfilenames": True,
            "ignoreerrors": True,
            "quiet": True,
            "no_warnings": True,
            "writethumbnail": not meta.no_art,
            "overwrites": force_overwrite,
            **ydl_opts_extra,
            "progress_hooks": [progress_hook],
            "postprocessor_hooks": [postprocessor_hook],
            "postprocessors": postprocessors,
            "postprocessor_args": {
                "ffmpegmetadata": ffmpeg_meta_args,
            },
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            overall.write(f"  ❌  {title[:60]} — {e}")
            with stats_lock:
                stats["failed"] += 1
            overall.update(1)
        finally:
            if file_bar[0]:
                file_bar[0].close()
            release_slot(slot)

    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    download_one,
                    e,
                    overwrite_decisions.get(e.get("id", ""), False),
                    (i + 1) if meta.track_numbers else None,
                ): e
                for i, e in enumerate(to_download_entries)
            }
            for future in as_completed(futures):
                exc = future.exception()
                if exc:
                    entry = futures[future]
                    overall.write(f"  ❌  {entry.get('title', '?')[:60]} — {exc}")
                    with stats_lock:
                        stats["failed"] += 1
    except KeyboardInterrupt:
        overall.write("\n⚠️  Interrupted by user.")
    finally:
        overall.close()

    print("\n" + "=" * 60)
    print(f"🎉  Done!  ✅ Downloaded: {stats['success']}  "
          f"⏭  Skipped: {to_skip}  ❌ Failed: {stats['failed']}")
    print(f"📂  Files saved to: {Path(output_base).resolve() / channel_name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "YouTube / YouTube Music Channel MP3 Downloader\n"
            "Downloads a channel\'s videos as MP3 files with embedded art and artist tag.\n"
            "Run with --help for full documentation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Single URL or a file of URLs
    url_group = parser.add_mutually_exclusive_group(required=True)
    url_group.add_argument(
        "channel_url", nargs="?", default=None,
        metavar="CHANNEL_URL",
        help=(
            "YouTube or YouTube Music channel URL.\n"
            "Accepted formats:\n"
            "  https://www.youtube.com/@handle\n"
            "  https://www.youtube.com/channel/UCxxxx\n"
            "  https://music.youtube.com/channel/UCxxxx"
        ),
    )
    url_group.add_argument(
        "--url-file", "-f", metavar="FILE",
        help=(
            "Path to a text file containing one channel URL per line.\n"
            "Lines starting with # are treated as comments and ignored.\n"
            "Useful for downloading multiple channels in one run."
        ),
    )

    parser.add_argument(
        "destination",
        help=(
            "Root folder where MP3s are saved.\n"
            "A subfolder named after the channel is created automatically.\n"
            "Example: C:\\Music  →  C:\\Music\\MKBHD\\Video.mp3"
        ),
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=3, metavar="N",
        help=(
            "Number of videos to download in parallel (default: 3).\n"
            "Higher values are faster but use more bandwidth and CPU.\n"
            "Recommended range: 2–6."
        ),
    )
    parser.add_argument(
        "--limit", "-n", type=int, default=None, metavar="N",
        help=(
            "Only download the N most recent videos (default: all).\n"
            "Useful for a quick sync or testing."
        ),
    )
    parser.add_argument(
        "--quality", "-q", default="192",
        choices=["128", "192", "256", "320"],
        help=(
            "MP3 bitrate in kbps (default: 192).\n"
            "  128  — small files, acceptable quality\n"
            "  192  — good quality, recommended default\n"
            "  256  — high quality\n"
            "  320  — maximum quality, largest files"
        ),
    )
    parser.add_argument(
        "--max-duration", "-d", type=int, default=None, metavar="MINUTES",
        help=(
            "Skip videos longer than MINUTES minutes (default: no limit).\n"
            "Useful for filtering out livestream recordings, podcasts, or\n"
            "long compilations when you only want regular music videos.\n"
            "Example: --max-duration 10  skips anything over 10 minutes."
        ),
    )

    # --- Metadata options ---
    meta_group = parser.add_argument_group(
        "metadata options",
        "All metadata options are optional. Tags are embedded into each MP3 file.",
    )
    meta_group.add_argument(
        "--genre", metavar="GENRE", default=None,
        help=(
            "Set the genre ID3 tag (default: not set).\n"
            "Example: --genre \'Electronic\'"
        ),
    )
    meta_group.add_argument(
        "--album", metavar="ALBUM", default=None,
        help=(
            "Set the album ID3 tag (default: not set).\n"
            "Example: --album \'Best of MKBHD\'"
        ),
    )
    meta_group.add_argument(
        "--year", action="store_true", default=False,
        help="Embed the video upload year as the year/date ID3 tag.",
    )
    meta_group.add_argument(
        "--comment-url", action="store_true", default=False,
        help="Embed the original YouTube video URL as the comment ID3 tag.",
    )
    meta_group.add_argument(
        "--track-numbers", action="store_true", default=False,
        help=(
            "Embed a track number into each MP3, numbered by position\n"
            "in the download queue (1, 2, 3, ...)."
        ),
    )
    meta_group.add_argument(
        "--strip-title", action="store_true", default=False,
        help=(
            "Auto-clean common YouTube noise from the title tag:\n"
            "e.g. \'(Official Video)\', \'[HD]\', \'| Lyrics\', etc."
        ),
    )
    meta_group.add_argument(
        "--no-art", action="store_true", default=False,
        help="Do not embed the video thumbnail as album art (faster, smaller files).",
    )
    meta_group.add_argument(
        "--no-artist", action="store_true", default=False,
        help="Do not override the artist tag with the channel name.",
    )
    meta_group.add_argument(
        "--description-as-comment", action="store_true", default=False,
        help=(
            "Fetch and embed the video description as the comment ID3 tag\n"
            "(truncated to 500 characters). Adds one extra API call per video."
        ),
    )

    args = parser.parse_args()

    meta = MetadataOptions(
        genre                  = args.genre,
        album                  = args.album,
        use_upload_year        = args.year,
        comment_source_url     = args.comment_url,
        track_numbers          = args.track_numbers,
        strip_title_patterns   = args.strip_title,
        no_art                 = args.no_art,
        no_artist              = args.no_artist,
        description_as_comment = args.description_as_comment,
    )

    # Build list of URLs
    if args.url_file:
        url_file = Path(args.url_file)
        if not url_file.exists():
            print(f"\u274c  URL file not found: {url_file}")
            sys.exit(1)
        urls = [
            line.strip()
            for line in url_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not urls:
            print(f"\u274c  No URLs found in {url_file}")
            sys.exit(1)
        print(f"\U0001f4cb  Loaded {len(urls)} channel(s) from {url_file}\n")
    else:
        urls = [args.channel_url]

    # Process each channel
    for i, url in enumerate(urls, start=1):
        if len(urls) > 1:
            print(f"\n{"=" * 60}")
            print(f"\U0001f4fa  Channel {i}/{len(urls)}: {url}")
            print(f"{"=" * 60}")
        run(url, args.destination, args.limit, args.quality, args.workers, args.max_duration, meta)

    if len(urls) > 1:
        print(f"\n\u2705  All {len(urls)} channels processed.")


if __name__ == "__main__":
    main()
