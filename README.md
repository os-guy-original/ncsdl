# ncsdl - NCS YouTube Downloader

Download NoCopyrightSounds music from YouTube with automatic title style detection, genre classification, duplicate checking, and metadata embedding.

## Features

- **Title Style Detection**: Automatically parses NCS YouTube titles in all known formats:
  - Modern (Oct 2023+): `Artist - Song | Genre | NCS - Copyright Free Music`
  - Old (Pre-Oct 2023): `Artist - Song [NCS Release]`
  - Legacy: `Artist - Song`
- **Genre Classification**: Supports 60+ NCS genres including Trap, House, Dubstep, Drum & Bass, Future Bass, and more
- **Duplicate Checking**: Automatically skips already downloaded songs
- **Metadata Embedding**: Embeds artist, title, genre, and album tags into downloaded files
- **Clean CLI**: Unix-style command-line interface with clear tabular output

## Installation

### Prerequisites

- Python 3.9+
- ffmpeg (for audio conversion and metadata embedding)

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

### Download Songs

Download by genre, or the entire library:

```bash
# Download Trap songs
python -m ncsdl download --genre Trap

# Download all NCS songs
python -m ncsdl download --genre all

# Download to specific directory
python -m ncsdl download --genre House --output ~/music/ncs

# List found videos without downloading
python -m ncsdl download --genre Trap --list-only

# Download with metadata embedding
python -m ncsdl download --genre Dubstep --embed-metadata
```

### Embed Metadata

Add ID3 tags to existing audio files:

```bash
python -m ncsdl metadata song1.mp3 song2.mp3
python -m ncsdl metadata ~/music/ncs/*.mp3
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
| `download`, `dl` | Download NCS songs |
| `metadata`, `meta` | Embed metadata into audio files |
| `check-dupes` | Check for duplicate songs in a directory |

## Title Styles Detected

The tool recognizes three main title formats:

| Style | Example | Era |
|---|---|---|
| modern | `Lost Sky - Lost pt. II | Trap | NCS - Copyright Free Music` | Oct 2023+ |
| old | `Elektronomia - Sky high [NCS Release]` | Pre-Oct 2023 |
| bare | `Cartoon - On & On` | Early uploads |

## Supported Genres

60+ genres including: Trap, House, Dubstep, Drum & Bass, Future Bass, Electro, Progressive House, Chill, Lofi Hip-Hop, Pop, Techno, Trance, Wave, Phonk, and more.

## License

MIT
