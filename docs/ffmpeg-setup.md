# FFmpeg Installation & Configuration (Windows)

MeetMind AI uses **FFmpeg** as an external system dependency to extract audio from video files and normalize audio into mono 16 kHz WAV format for local Faster-Whisper transcription.

## 1. Install FFmpeg on Windows

Choose one of the following methods:

### Option A: Using `winget` (Recommended)
```powershell
winget install --id Gyan.FFmpeg -e
```
After installation, open a **new** PowerShell terminal so your `PATH` updates.

### Option B: Manual Download
1. Download a Windows build from [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/) (e.g., `ffmpeg-release-essentials.zip`).
2. Extract it to a permanent folder such as `C:\ffmpeg`.
3. Add `C:\ffmpeg\bin` to your System or User `PATH` environment variable.

## 2. Verify FFmpeg Installation

```powershell
ffmpeg -version
```

## 3. Configure `backend/.env`

If `ffmpeg` is available on your `PATH`, keep the default:
```env
FFMPEG_PATH=ffmpeg
```

If you prefer not to modify `PATH`, set `FFMPEG_PATH` to the full executable path:
```env
FFMPEG_PATH=C:\ffmpeg\bin\ffmpeg.exe
```

## 4. Faster-Whisper Settings

Default local-first CPU settings in `backend/.env`:
```env
WHISPER_MODEL_SIZE=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_DOWNLOAD_ROOT=
```

- `WHISPER_DOWNLOAD_ROOT` can be left blank to use the default local Hugging Face cache, or set to a local directory path (e.g., `../storage/models`).
