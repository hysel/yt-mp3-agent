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
python youtube_mp3_agent.py https://www.youtube.com/@mkbhd C:\Music

# YouTube Music channel
python youtube_mp3_agent.py https://music.youtube.com/channel/UCxxxx C:\Music

# 20 most recent videos, 320 kbps, 5 parallel threads
python youtube_mp3_agent.py https://www.youtube.com/@lexfridman C:\Music -n 20 -q 320 -w 5

# Skip videos longer than 10 minutes
python youtube_mp3_agent.py https://www.youtube.com/@mkbhd C:\Music --max-duration 10

# Multiple channels from a file
python youtube_mp3_agent.py --url-file channels.txt C:\Music
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

## License

MIT
