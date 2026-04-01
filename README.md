# yt-mp3-agent

A Python command-line tool that downloads entire YouTube or YouTube Music channels as MP3 files — with embedded album art, artist tags, parallel downloads, and smart duplicate skipping.

> 🤖 Built entirely through a conversation with [Claude.ai](https://claude.ai) by Anthropic — no code was written manually.

---

## Features

- 🎵 Downloads full YouTube and YouTube Music channels as MP3
- 🖼️ Embeds video thumbnail as album art
- 🏷️ Sets channel name as the artist ID3 tag
- ⚡ Parallel multi-threaded downloads
- ⏭️ Skips already-downloaded videos via an archive file
- 🔁 Prompts to overwrite or skip files that already exist on disk
- ⏱️ Optional duration filter — skip videos longer than X minutes
- 📋 Supports a text file with multiple channel URLs
- 📦 Auto-downloads `ffmpeg` on Windows if not installed
- 📊 Progress bars per file and overall

---

## Requirements

**Install Python dependencies:**

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install -U "yt-dlp[default]" requests tqdm mutagen pillow
```

**ffmpeg:**
- Windows: auto-downloaded on first run
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`

**JavaScript runtime** (required by yt-dlp for YouTube):
- Recommended: [Deno](https://deno.com) — enabled by default
- Alternative: [Node.js 20+](https://nodejs.org)

---

## Usage

```bash
# Single channel
python youtube_mp3_agent.py <channel_url> <destination> [options]

# Multiple channels from a file
python youtube_mp3_agent.py --url-file channels.txt <destination> [options]
```

---

## Examples

```bash
# Download an entire channel
python yt-mp3-agent.py https://www.youtube.com/@mkbhd C:\Music

# YouTube Music channel
python yt-mp3-agent.py https://music.youtube.com/channel/UCxxxx C:\Music

# 20 most recent videos, 320 kbps, 5 parallel threads
python yt-mp3-agent.py https://www.youtube.com/@lexfridman C:\Music -n 20 -q 320 -w 5

# Skip videos longer than 10 minutes
python yt-mp3-agent.py https://www.youtube.com/@mkbhd C:\Music --max-duration 10

# Multiple channels from a file
python yt-mp3-agent.py --url-file channels.txt C:\Music
```

**`channels.txt` format:**
```
# Lines starting with # are ignored
https://www.youtube.com/@mkbhd
https://www.youtube.com/@lexfridman
https://music.youtube.com/channel/UCxxxx
```

---

## Output Structure

```
<destination>/
└── <Channel Name>/
    ├── Video Title.mp3
    ├── Another Video.mp3
    └── .archive.txt        ← tracks downloaded IDs, hidden file
```

---

## Options

| Flag | Short | Description | Default |
|---|---|---|---|
| `--url-file FILE` | `-f` | Text file with one channel URL per line | — |
| `--workers N` | `-w` | Parallel download threads | `3` |
| `--limit N` | `-n` | Max videos to download | all |
| `--quality KBPS` | `-q` | MP3 bitrate: 128 / 192 / 256 / 320 | `192` |
| `--max-duration MIN` | `-d` | Skip videos longer than N minutes | — |

### Metadata Options

All metadata flags are optional and additive. The only automatic tags are **artist** (channel name) and **cover art** (thumbnail).

| Flag | Description | Default |
|---|---|---|
| `--genre GENRE` | Set the genre ID3 tag | not set |
| `--album ALBUM` | Set the album ID3 tag | not set |
| `--year` | Embed the upload year as the year tag | off |
| `--comment-url` | Embed the YouTube video URL as the comment tag | off |
| `--track-numbers` | Number tracks by position in the download queue | off |
| `--strip-title` | Clean YouTube noise from title tags: `(Official Video)`, `[HD]`, etc. | off |
| `--no-art` | Skip thumbnail embedding | off |
| `--no-artist` | Don't override the artist tag with the channel name | off |
| `--description-as-comment` | Embed the video description as the comment tag (one extra API call per video) | off |

---

## Archive File

`.archive.txt` records the YouTube video ID of every completed download. On the next run, any ID already in this file is skipped automatically — even if you've renamed or moved the MP3.

- Delete a line → re-download that video next run
- Delete the file → treat everything as new (overwrite prompt will catch existing files on disk)

---

## How It Was Built

This script was built entirely through a conversation with **[Claude.ai](https://claude.ai)** by [Anthropic](https://www.anthropic.com) — no code was written by hand. The full feature set was developed iteratively by describing requirements, reporting errors, and requesting improvements in plain language.

It's a practical example of using an AI assistant to build a real, production-ready command-line tool from scratch.

---

## Regenerating This Script with Claude

You can recreate this script from scratch by pasting the following prompt into [Claude.ai](https://claude.ai):

---

> Create a Python command-line script that downloads an entire YouTube or YouTube Music channel as MP3 files using yt-dlp.
>
> Requirements:
> - Accept a channel URL and a destination folder as positional arguments
> - Support a `--url-file` flag to pass a text file with multiple channel URLs (one per line, `#` lines ignored)
> - Skip already-downloaded videos using yt-dlp's built-in download archive file (`.archive.txt`)
> - Before downloading, detect MP3 files that already exist on disk and prompt the user to overwrite or skip — with options to apply the choice to all remaining conflicts
> - Download audio only (no video), convert to MP3 using ffmpeg, and embed the video thumbnail as album art
> - Set the channel name as the artist ID3 tag
> - Support parallel downloads via a `--workers` flag (default: 3)
> - Show a tqdm progress bar per file (bytes + speed) and an overall progress bar (videos completed)
> - Pre-fetch the video list before downloading so the total count, already-downloaded count, and to-download count are printed upfront
> - Print the video title when each download starts and when it completes
> - Support `--limit N` to download only the N most recent videos
> - Support `--quality` with choices 128 / 192 / 256 / 320 kbps (default: 192)
> - Support `--max-duration MINUTES` to skip videos longer than a given duration
> - Support YouTube Music URLs (music.youtube.com) by resolving them to their canonical youtube.com channel URL before processing
> - On Windows, auto-download a static ffmpeg build if ffmpeg is not found on PATH
> - Auto-detect Node.js and inject it into PATH so yt-dlp can use it as a JS runtime
> - Save MP3s to `<destination>/<channel name>/` using the real channel display name (not the URL handle)
> - File names should be the video title only, with no video ID suffix
> - Optional metadata flags (all off by default):
>   - `--genre` — set the genre ID3 tag
>   - `--album` — set the album ID3 tag
>   - `--year` — embed the video upload year as the year tag
>   - `--comment-url` — embed the YouTube video URL as the comment tag
>   - `--track-numbers` — number tracks by position in the download queue
>   - `--strip-title` — clean common YouTube noise from title tags (e.g. "(Official Video)", "[HD]")
>   - `--no-art` — skip thumbnail embedding
>   - `--no-artist` — don't override the artist tag
>   - `--description-as-comment` — fetch and embed the video description as the comment tag
> - Include a detailed `-h` / `--help` output with descriptions for every argument
> - Windows-compatible: sanitize folder and file names, use `windowsfilenames: True` in yt-dlp
> - Dependencies: `yt-dlp[default]`, `requests`, `tqdm`, `mutagen`, `pillow`

---

## License

MIT
