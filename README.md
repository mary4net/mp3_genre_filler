# Genre Filler

Fill in the **Genre** metadata field on MP3 files via a small desktop window. You can pick files, choose a folder in the app, then apply a genre string to every MP3 found.

## Quick start

1. Activate your conda environment that has `python`, `PySimpleGUI`, and `mutagen` (e.g. `conda activate genre-filler`).
2. Run the GUI:
   ```bash
   python genre_filler.py
   ```
3. Type the genre you want (and optionally singer names), select files or a folder (or drop them in), and press **Fill Genre**. The log will show what was updated.

Notes:
- Only `.mp3` files are modified. Non-MP3 files in the selection are skipped.
- Enter multiple singers with comma or semicolon separators (e.g. `Artist One, Artist Two`). They are stored as individual artist entries so players can still find each artist.
- If you leave singers blank, existing artist tags are kept; values like `aaa/bbb` in old files are auto-split into separate artists for better searchability.
- The last two chosen folders are remembered in `.recent_dirs.json`; pick them quickly from the **Recent folders** dropdown.
- Checkbox: “Join artists into one display string (compatibility)” writes `Artist1 / Artist2` as a single artist tag for players that ignore multiple artists. The individual list is also stored in a custom `TXXX:ARTISTS-LIST` frame for future edits.
