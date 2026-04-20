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
- **Migrate Command**: Move or copy songs between directories with automatic renaming
- **Progress Indicators**: Real-time feedback during migrations with `--progress` flag
- **KIO Protocol Support**: Transfer files to/from MTP devices, SMB shares, SFTP, and more

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

### Optional Dependencies

For MTP/KIO protocol support (transferring to/from mobile devices, network shares):

```bash
# KDE users (kioclient is included with KDE)
# No additional installation needed

# Non-KDE users - install simple-mtpfs for MTP support
sudo pacman -S simple-mtpfs    # Arch/Artix
sudo apt install simple-mtpfs  # Ubuntu/Debian
sudo dnf install simple-mtpfs  # Fedora
```

## MTP Device Usage

ncsdl supports transferring files to/from MTP devices (Android phones, tablets) using KIO protocols. This is particularly useful for copying NCS music libraries to your phone's Music folder.

### Finding Your MTP Device Path

Before using MTP, you need to discover your device's mount point:

```bash
# List all available KIO locations (including MTP devices)
kioclient ls mtp:/

# List the root of your MTP device
kioclient ls mtp:/$(kioclient ls mtp:/ | head -1)

# Or use mtp-detect to see device info (install with: sudo apt install mtp-tools)
mtp-detect
```

The device path will look like `mtp:/<device_name>/` (e.g., `mtp:/Pixel_4/` or `mtp:/Internal%20storage/`). Spaces in device names are URL-encoded as `%20`.

### Using MTP with ncsdl

#### Copy/Migrate to MTP Device

Transfer downloaded NCS songs to your phone's Music folder:

```bash
# Copy from local directory to MTP device
ncsdl migrate --mode copy --progress ~/music/ncs mtp:/Internal\ storage/Music/NCS

# Or with URL-encoded spaces
ncsdl migrate --mode copy --progress ~/music/ncs mtp:/Internal%20storage/Music/NCS

# Move instead of copy (removes source files after successful transfer)
ncsdl migrate --progress ~/music/ncs mtp:/Music/NCS

# Show detailed progress (logs each file as it's processed)
ncsdl migrate --progress --mode copy ~/music/ncs mtp:/Music/NCS
```

#### Copy from MTP Device to Local

Migrate songs from your phone to your computer:

```bash
# Copy from MTP to local directory (use --mode move to delete from phone)
ncsdl migrate --mode copy --progress mtp:/Music/NCS ~/music/ncs_from_phone

# The source can also be a USB drive mounted via MTP
ncsdl migrate --mode copy --progress mtp:/USB\ drive/Secrets/NCS ~/music/ncs
```

#### Direct Download to MTP

You can also download directly to an MTP device:

```bash
# Download a specific video directly to your phone
ncsdl download cj-HnSUqx3w --output mtp:/Music/NCS

# Download an entire genre directly to MTP device
ncsdl download --genre Trap --output mtp:/Music/NCS --progress

# IMPORTANT: Direct MTP downloads show no progress during transfer.
# Use download to local folder first, then migrate to MTP for better progress feedback.
```

### MTP Tips & Troubleshooting

- **Spaces in paths**: Escape spaces with backslash (`\ `) or use URL encoding (`%20`)
- **Case sensitivity**: MTP paths are case-sensitive. Use `kioclient ls mtp:/` to browse and get exact paths
- **Slow transfers**: MTP is slower than local file operations. Use `--progress` to see activity
- **KIO not available**: If `kioclient` commands fail, ensure KDE packages are installed:
  ```bash
  # Ubuntu/Debian
  sudo apt install kio

  # Fedora
  sudo dnf install kio
  ```
- **No MTP devices listed**: Your phone must be connected and set to "File Transfer" / "MTP" mode, not just charging
- **Permission denied**: On some systems, you may need to add your user to the `fuse` group: `sudo usermod -aG fuse $USER`

### Example: Copy NCS Songs from USB to Phone

Assuming your NCS library is on a USB drive at `/run/media/sd-v/76E8-CACF/Secrets/NCS`:

```bash
# 1. First, copy from USB to local (fast)
ncsdl migrate --mode copy --progress /run/media/sd-v/76E8-CACF/Secrets/NCS ~/music/ncs

# 2. Then copy from local to phone MTP
ncsdl migrate --mode copy --progress ~/music/ncs mtp:/Music/NCS

# Alternative: direct USB to phone (slower, but fewer steps)
ncsdl migrate --mode copy --progress /run/media/sd-v/76E8-CACF/Secrets/NCS mtp:/Music/NCS
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
| `migrate` | Move or copy songs between directories (supports MTP) |

### Migrate Command

Transfer songs between directories, with support for local paths and KIO protocols (MTP, SMB, SFTP, etc.). Automatically renames files to match NCS naming standards using embedded metadata.

```bash
ncsdl migrate --mode copy --progress ~/music/ncs mtp:/Music/NCS
ncsdl migrate --mode move /run/media/usb/NCS ~/music/ncs
```

**Options:**
- `--mode`, `-m`: Transfer mode: `move` (delete source after successful transfer) or `copy` (keep source files). Default: `move`
- `--format`, `-f`: Target audio format (default: `m4a`)
- `--progress`: Show detailed progress during transfer (each file processed)
- `--quiet`, `-q`: Suppress all output except final summary

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
