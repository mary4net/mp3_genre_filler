# Genre Filler

Fill in the **Genre** metadata field on MP3 files via a small desktop window. You can pick files, choose a folder in the app, then apply a genre string to every MP3 found.

## Quick start

1. Activate your conda environment that has `python`, `PySimpleGUI`, and `mutagen` (e.g. `conda activate genre-filler`).
2. Run the GUI:
   ```bash
   python genre_filler.py
   ```
3. Type the genre you want, select files or a folder (or drop them in), and press **Fill Genre**. The log will show what was updated.

Notes:
- Only `.mp3` files are modified. Non-MP3 files in the selection are skipped.
