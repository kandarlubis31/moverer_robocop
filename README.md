# Storage Optimizer Pro — Batch

A Windows desktop tool for a nearly full system drive: move heavy folders to an external USB
disk, then leave a directory symlink where they used to be. Applications keep working from
the original path while the bytes live somewhere else.

## Why a symlink

Plain copying frees nothing until you delete the source, and deleting breaks every project
that references it. A junction (`mklink /D`) keeps the original path valid while the data is
physically on USB.

## How it works

1. You queue one or more source folders and pick a target drive.
2. Each folder is moved off the system drive, either by **plain robocopy** or through an
   **optional 7-Zip compression pass** first (much faster when the target is a slow USB 2.0
   stick).
3. A directory symlink is created at the original path, pointing at the new location.
4. The source is removed and the queue item turns green (or red, with the reason).

Progress is estimated from a `robocopy /L` file count so the bar moves during the copy, and
from 7-Zip's own `-bsp1` percentage stream during compression.

## Modes

| Mode | What happens |
| --- | --- |
| **Robocopy** | `robocopy /E /MOVE /MT:32` straight to the target, then symlink |
| **Compress (7-Zip)** | `7z a -mx=1 -mmt=on` → move archive → `7z x` on the target → delete archive → symlink |

The compression mode trades time and peak disk usage for a much faster transfer over USB —
useful for source folders with thousands of small files.

## Requirements

- Windows (robocopy, `mklink` and UAC elevation are all required)
- Administrator rights — the app relaunches itself elevated on start
- 7-Zip, only if you want compression mode. It is looked up in this order:
  bundled `7z.exe` next to the executable → `C:\Program Files\7-Zip` →
  `C:\Program Files (x86)\7-Zip` → `PATH`

## Run

```bash
python storage_optimizer.py
```

## Build a standalone executable

```bat
build.bat
```

That runs PyInstaller with `--noconsole --onefile --uac-admin --name "StorageOptimizer"`.
Drop `7z.exe` beside the resulting executable to make compression mode self-contained.

## Warnings the app gives you

- **`node_modules` detected** — those folders are flagged in the queue and the app asks for
  confirmation before compressing, because binary content barely shrinks and the round trip
  wastes time.
- **Source equals target** — refuses to process a folder into itself.

## Caveats

- A symlink is not a backup. If the USB drive is unplugged, every linked project breaks until
  it is reconnected.
- Moving a folder an application is currently using can fail mid-copy. Close what you are
  working on first.
- The target must be NTFS or exFAT for junctions to behave; FAT32 has no symlink support.

---

## Bahasa Indonesia

**Storage Optimizer Pro — Batch** adalah aplikasi desktop Windows untuk drive sistem yang hampir penuh: folder besar dipindahkan ke disk USB eksternal, lalu ditinggalkan symbolic link di lokasi aslinya sehingga aplikasi tetap berjalan dari path yang sama.

Mode batch memproses beberapa folder sekaligus, dengan peringatan sebelum pemindahan dan catatan prasyarat yang jelas.

---

## License

MIT
