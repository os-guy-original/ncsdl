# ncsdl - NCS YouTube Downloader

Download NoCopyrightSounds music from YouTube with automatic title style detection, genre classification, duplicate checking, thumbnail embedding, and metadata tags.

## Features

- **Title Style Detection**: Automatically parses NCS YouTube titles in all known formats:
  - Modern (Oct 2023+): `Artist - Song | Genre | NCS - Copyright Free Music`
  - Old (Pre-Oct 2023): `Artist - Song [NCS Release]`
  - Legacy: `Artist - Song`
- **Genre Classification**: Supports 60+ NCS genres including Trap, House, Dubstep, Drum & Bass, Future Bass, and more
- **M4A Audio Format**: Downloads best available audio and converts to M4A with AAC codec
- **Cookie Authentication**: Download age-restricted or private-listed videos using browser cookies
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
- Node.js (required by yt-dlp for YouTube signature decryption)
- ffmpeg (for audio conversion)

### Install

```bash
# Install Python dependencies
pip install yt-dlp mutagen

# Install Node.js (required for yt-dlp YouTube challenge solving)
sudo apt install nodejs    # Ubuntu/Debian
sudo dnf install nodejs    # Fedora
brew install node          # macOS

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

Search results show video IDs that can be used with `ncsdl download <ID>`.

### List Genres

View all supported NCS genres:

```bash
python -m ncsdl list-genres
python -m ncsdl list-genres --verbose        # with search counts
python -m ncsdl list-genres --verbose --show-empty
```

### Download Songs

Download by video ID, by genre, or the entire library:

```bash
# Download a specific song by video ID
python -m ncsdl download cj-HnSUqx3w

# Download with output directory
python -m ncsdl download cj-HnSUqx3w --output ~/music/ncs

# Download by genre (Trap songs with thumbnails, default)
python -m ncsdl download --genre Trap

# Download entire NCS library
python -m ncsdl download --genre all

# Download to specific directory
python -m ncsdl download --genre House --output ~/music/ncs

# Download without thumbnails
python -m ncsdl download --genre Dubstep --no-thumbnail

# Download with browser cookies (for age-restricted videos)
python -m ncsdl download --genre all --cookies-from-browser firefox

# List found videos without downloading
python -m ncsdl download --genre Trap --list-only

# With 0 retries (fail fast)
python -m ncsdl download --genre Trap --retries 0
```

### Resume Interrupted Downloads

If a download was interrupted, resume where you left off:

```bash
python -m ncsdl resume
python -m ncsdl resume --output ~/music/ncs
```

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
| `detect-genres` | Detect genres from NCS YouTube channel |
| `search` | Search for specific NCS songs by pattern |
| `list-genres` | List all supported NCS genres |
| `stats` | Show download statistics for a directory |
| `download` (`dl`) | Download NCS songs |
| `resume` | Resume an interrupted download |
| `metadata` (`meta`) | Embed metadata into audio files |
| `check-dupes` | Check for duplicate songs in a directory |

## Title Styles Detected

The tool recognizes five title formats used across the NCS YouTube channel:

| Style | Pattern | Example |
|---|---|---|
| modern | `Artist - Song \| Genre \| NCS [x Partner] - Copyright Free Music` | `Janji - Heroes Tonight (feat. Johnning) \| Progressive House \| NCS - Copyright Free Music` |
| mashup | `Song A x Song B Mashup [NCS - Copyright Free Music]` | `Razihel x Tria x Kisma - Touch Me Mashup NCS - Copyright Free Music` |
| collab | `Artist - Song [Genre] NCS - Copyright Free Music` | `Almost Weekend & Max Vermeulen - Island (ft. Michael Shynes) NCS - Copyright Free Music` |
| old | `Artist - Song [NCS Release]` | `Elektronomia - Sky High [NCS Release]` |
| bare | `Artist - Song` | `Cartoon - On & On` |

### Format Notes

- **modern**: Pipe-separated format with genre field. The `NCS` suffix may include digits (e.g. `NCS10`, `NCS13`) and an optional partner name (e.g. `NCS x Launch13`). Genre is extracted from the pipe-separated field.
- **mashup**: Detected by `x` separator and `Mashup` keyword in the title. Both artists are combined into the artist tag.
- **collab**: No genre separator pipes — just the NCS suffix at the end. Genre is heuristically extracted from the end of the title when it matches a known genre name (e.g. `Trap`, `Melodic Dubstep`).
- **old**: Pre-October 2023 uploads with `[NCS Release]` tag. No genre information is available in the title.
- **bare**: Early uploads with no NCS branding. No genre information is available.

Suffixes like `(VIP)`, `(Remix)`, `(Sped Up)`, `(Hindi)`, `(YYYY Edit)`, and `pt. II` are automatically detected and preserved in the song title. Featuring artists in parentheses (e.g. `(feat. Johnning)`) are extracted into a separate tag field.

## License

MIT
