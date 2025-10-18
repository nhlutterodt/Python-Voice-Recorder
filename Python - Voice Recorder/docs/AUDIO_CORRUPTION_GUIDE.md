# Audio File Corruption Troubleshooting Guide

## Problem: "Failed to load audio file"

When trying to load certain audio files in Voice Recorder Pro, you may encounter this error:

```
Failed to load audio file: 
Decoding failed. ffmpeg returned error code: 3199971767
Output from ffmpeg/avlib:
[wav @ ...] no 'fmt ' or 'XMA2' tag found
Error opening input file: Invalid data found when processing input
```

This means the WAV file is **corrupted or has an invalid structure**.

## Root Causes

1. **Incomplete recording** - File write was interrupted during recording
2. **File transfer error** - Audio file was corrupted during transfer/backup
3. **Incompatible format** - File uses an unsupported audio codec
4. **File system corruption** - Hard drive or storage device error

## Solution Options

### Option 1: Use the Audio Repair Tool (Recommended)

The application includes an audio repair utility that can fix many corrupted files:

```bash
cd "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder"
python tools/audio_repair.py <corrupted_file.wav>
```

This will create a `<file>.repaired.wav` file with standard PCM format (16-bit, 44.1kHz stereo).

**Example:**
```bash
python tools/audio_repair.py recordings/raw/410fec3353e048c588e4e115ed617a93.wav
```

### Option 2: Use FFmpeg Directly

If the audio repair tool doesn't work, try FFmpeg with explicit parameters:

```bash
ffmpeg -i corrupted.wav -acodec pcm_s16le -ar 44100 -ac 2 repaired.wav
```

**Parameters explained:**
- `-acodec pcm_s16le` - Use standard PCM audio codec (16-bit signed)
- `-ar 44100` - Set sample rate to 44.1kHz (universal standard)
- `-ac 2` - Convert to stereo (2 channels)

### Option 3: Try Multiple FFmpeg Strategies

If standard FFmpeg fails, try these alternative approaches:

**Force input format:**
```bash
ffmpeg -f wav -i corrupted.wav -acodec pcm_s16le -ar 44100 output.wav
```

**Copy audio stream with minimal reprocessing:**
```bash
ffmpeg -i corrupted.wav -c:a pcm_s16le -y output.wav
```

**Extract audio with sample rate conversion:**
```bash
ffmpeg -i corrupted.wav -ar 44100 -f wav output.wav
```

### Option 4: Batch Repair All Corrupted Files

To repair all files in the recordings directory at once:

```bash
python tools/audio_repair.py --dir recordings/raw
```

This will scan all `.wav` files and create `.repaired.wav` versions for files that are corrupted.

## Prevention Tips

1. **Allow complete recording** - Don't interrupt recordings or close the app during recording
2. **Proper shutdown** - Always close the application cleanly (use Stop/Exit buttons)
3. **Verify after transfer** - When transferring audio files, verify they're not corrupted before deleting originals
4. **Regular backups** - Back up important recordings to multiple locations
5. **Monitor disk space** - Ensure sufficient disk space during recording (low disk space can cause corruption)

## When Files Are Unrecoverable

If a file is **severely corrupted** (missing essential WAV structure chunks), it may not be recoverable. In this case:

1. **Accept the loss** - Consider it a system/hardware failure and move on
2. **Check hard drive health** - Use Windows `chkdsk` or hard drive diagnostic tools
3. **Review logs** - Check the application logs in the `logs/` directory for any error records

Run disk check:
```bash
chkdsk C: /F /R
```

## Getting Help

If you continue experiencing issues:

1. Check the application logs in `logs/` directory
2. Note the exact error message and file name
3. Report to the development team with:
   - Error message (full text from the dialog)
   - File size
   - Approximate recording date
   - System information (Windows version, Python version)

## Technical Details

Voice Recorder Pro attempts to load audio files in this order:

1. **Direct WAV loading** - Try loading as standard WAV format
2. **Auto-detection** - Let FFmpeg detect the format automatically
3. **Explicit format** - Try loading as WAV with explicit FFmpeg parameters
4. **Python wave module** - Attempt raw PCM data extraction
5. **Manual repair** - Reconstruct minimal WAV header from raw audio data (if available)

If all strategies fail, you'll see the error message with recovery options.
