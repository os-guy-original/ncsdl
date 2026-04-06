# ncsdl - NCS YouTube Downloader

Download NoCopyrightSounds music from YouTube with automatic title style detection, genre classification, duplicate checking, thumbnail embedding, and metadata tags.

## Features

- **Title Style Detection**: Automatically parses NCS YouTube titles in all known formats:
  - Modern (Oct 2023+): `Artist - Song | Genre | NCS - Copyright Free Music`
  - Old (Pre-Oct 2023): `Artist - Song [NCS Release]`
  - Legacy: `Artist - Song`
- **Genre Classification**: Supports 60+ NCS genres including Trap, House, Dubstep, Drum & Bass, Future Bass, and more
- **Modern Audio Formats**: M4A (default), FLAC, Opus, or MP3
- **Thumbnail Embedding**: Album art from YouTube is embedded as cover art
- **Metadata Tags**: Artist, title, genre, album tags embedded during download
- **Duplicate Checking**: Automatically skips already downloaded songs
- **Download Resume**: Interrupted downloads can be resumed without re-downloading
- **Retry Logic**: Configurable retry attempts for failed downloads
- **Search**: Find songs by artist, title, or genre
- **Statistics**: View download stats with genre detection from file metadata
- **Clean CLI**: Unix-style command-line interface with clear tabular output

## Installation

### Prerequisites

- Python 3.9+
- ffmpeg (for audio conversion)

### Install

```bash
# Install Python dependencies
pip install yt-dlp mutagen

# Install ffmpeg (Ubuntu/Debian)
sudo apt install ffmpeg

# Install ffmpeg (Fedora)
sudo dnf install ffmpeg

# Install ffmpeg (macOS)
brew install ffmpeg
```

### Install as Package

```bash
pip install -e .
```

## Usage

### Analyze NCS Title Styles

See genre distribution and title style breakdown across the NCS channel:

```bash
python -m ncsdl analyze
python -m ncsdl analyze --genre Trap
python -m ncsdl analyze --limit 500
```

### Search for Songs

Find specific songs by artist, title, or genre:

```bash
python -m ncsdl search "Alan Walker"
python -m ncsdl search "Heroes Tonight"
python -m ncsdl search "Trap" --limit 20
```

### List Genres

View all supported NCS genres:

```bash
python -m ncsdl list-genres
python -m ncsdl list-genres --verbose        # with search counts
python -m ncsdl list-genres --verbose --show-empty
```

### Download Songs

Download by genre, or the entire library:

```bash
# Download Trap songs (M4A with thumbnails, default)
python -m ncsdl download --genre Trap

# Download entire library in FLAC
python -m ncsdl download --genre all --format flac

# Download to specific directory in Opus
python -m ncsdl download --genre House --output ~/music/ncs --format opus

# Download as MP3 without thumbnails
python -m ncsdl download --genre Dubstep --format mp3 --no-thumbnail

# List found videos without downloading
python -m ncsdl download --genre Trap --list-only

# With 0 retries (fail fast)
python -m ncsdl download --genre Trap --retries 0
```

### Resume Interrupted Downloads

If a download was interrupted, resume where you left off:

```bash
python -m ncsdl resume
python -m ncsdl resume --output ~/music/ncs --format flac
```

### Supported Audio Formats

| Format | Extension | Codec | Quality | Use Case |
|---|---|---|---|---|
| m4a (default) | .m4a | AAC | Lossy | Best balance of quality and size |
| flac | .flac | FLAC | Lossless | Archival, audiophile |
| opus | .opus | Opus | Lossy | Best compression, modern players |
| mp3 | .mp3 | MP3 | Lossy | Maximum compatibility |

### View Download Statistics

Analyze a download directory:

```bash
python -m ncsdl stats ~/music/ncs
```

Shows: file count, total size, average size, genre breakdown (from embedded metadata), format breakdown.

### Embed Metadata

Add tags to existing audio files (without re-encoding):

```bash
python -m ncsdl metadata song1.m4a song2.flac
python -m ncsdl metadata ~/music/ncs/*.m4a
```

### Check for Duplicates

Find existing songs in a directory:

```bash
python -m ncsdl check-dupes ~/music/ncs
python -m ncsdl check-dupes ~/music/ncs --verbose
```

## Commands

| Command | Description |
|---|---|
| `analyze` | Analyze NCS title styles and genre distribution |
| `search` | Search for specific NCS songs by pattern |
| `list-genres` | List all 66 supported NCS genres |
| `stats` | Show download statistics for a directory |
| `download` (`dl`) | Download NCS songs |
| `resume` | Resume an interrupted download |
| `metadata` (`meta`) | Embed metadata into audio files |
| `check-dupes` | Check for duplicate songs in a directory |

## Title Styles Detected

The tool recognizes three main title formats:

| Style | Example | Era |
|---|---|---|
| modern | `Lost Sky - Lost pt. II \| Trap \| NCS - Copyright Free Music` | Oct 2023+ |
| old | `Elektronomia - Sky high [NCS Release]` | Pre-Oct 2023 |
| bare | `Cartoon - On & On` | Early uploads |

## Supported Genres

66 genres including: Trap, House, Dubstep, Drum & Bass, Future Bass, Electro, Progressive House, Chill, Lofi Hip-Hop, Pop, Techno, Trance, Wave, Phonk, and more.

## License

MIT
