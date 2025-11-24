"""
GUI tool to batch-fill the Genre tag on MP3 files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Sequence, Tuple
import json

import PySimpleGUI as sg
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError, TXXX


RECENT_PATH = Path(__file__).with_name(".recent_dirs.json")


def _log_line(window: sg.Window, message: str) -> None:
    """Append a line to the log output."""
    log: sg.Multiline = window["-LOG-"]
    log.print(message)


def _normalize_entries(entries: Sequence[str]) -> List[Path]:
    """Convert user-provided paths into Path objects, skipping empties."""
    cleaned: List[Path] = []
    for raw in entries:
        if not raw:
            continue
        cleaned.append(Path(raw).expanduser())
    return cleaned


def _collect_mp3s(items: Iterable[Path]) -> Tuple[List[Path], List[str]]:
    """Return MP3 files discovered under the given paths plus any errors."""
    mp3s: List[Path] = []
    errors: List[str] = []
    seen = set()
    for item in items:
        if not item.exists():
            errors.append(f"Missing path skipped: {item}")
            continue
        if item.is_file():
            if item.suffix.lower() == ".mp3":
                if item not in seen:
                    mp3s.append(item)
                    seen.add(item)
            else:
                errors.append(f"Not an MP3 file skipped: {item}")
            continue
        # Directory walk
        for mp3 in item.rglob("*.mp3"):
            if mp3 not in seen:
                mp3s.append(mp3)
                seen.add(mp3)
    return mp3s, errors


def _ensure_easy_tags(file_path: Path) -> EasyID3:
    """Return an EasyID3 instance, creating a tag header if missing."""
    try:
        audio = EasyID3(file_path)
    except ID3NoHeaderError:
        audio = mutagen.File(file_path, easy=True)
        if audio is None:
            raise ValueError("Unsupported file; could not read tags")
        audio.add_tags()
        audio = EasyID3(file_path)
    return audio


def _normalize_artist_entries(raw_artists: Iterable[str]) -> List[str]:
    """Split artist strings on common separators and trim whitespace."""
    normalized: List[str] = []
    for raw in raw_artists:
        if not raw:
            continue
        # ID3 often stores multiple artists as separate entries, but some tools
        # join with "/" or ",". Split on common separators to restore the list.
        for piece in str(raw).replace(";", ",").replace("/", ",").split(","):
            name = piece.strip()
            if name:
                normalized.append(name)
    return normalized


def _load_recent_dirs() -> List[Path]:
    """Load up to 2 recent directories from disk."""
    try:
        data = json.loads(RECENT_PATH.read_text())
        return [Path(p) for p in data if p]
    except Exception:
        return []


def _save_recent_dirs(recent: List[Path]) -> None:
    """Persist recent directories."""
    try:
        RECENT_PATH.write_text(json.dumps([str(p) for p in recent]))
    except Exception:
        pass  # Swallow persistence errors; not critical.


def _remember_dir(current: List[Path], new_dir: Path) -> List[Path]:
    """Insert a directory at the front of the MRU list, keeping max 2."""
    resolved = new_dir.resolve()
    updated = [resolved] + [p for p in current if p != resolved]
    return updated[:2]


def _parse_drop_value(value: str) -> List[str]:
    """
    PySimpleGUI may send dropped file paths separated by newline or semicolon.
    Return a list of raw string paths.
    """
    if not value:
        return []
    parts: List[str] = []
    for chunk in value.replace(";", "\n").splitlines():
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return parts


def main() -> None:
    sg.theme("SystemDefault")

    recent_dirs = _load_recent_dirs()

    layout = [
        [sg.Text("Genre to apply"), sg.Input(key="-GENRE-", size=(30, 1))],
        [
            sg.Text("Singer(s) to apply"),
            sg.Input(
                key="-ARTIST-",
                size=(30, 1),
                tooltip="Use comma or semicolon to separate multiple singers",
            ),
        ],
        [
            sg.Button("Choose MP3 Files", key="-CHOOSE-FILES-"),
            sg.Button("Choose Folder", key="-CHOOSE-FOLDER-"),
            sg.Button("Clear List", key="-CLEAR-"),
        ],
        [
            sg.Text("Recent folders"),
            sg.Combo(
                values=[str(p) for p in recent_dirs],
                key="-RECENT-",
                size=(50, 1),
                readonly=True,
            ),
            sg.Button("Add Recent", key="-USE-RECENT-"),
        ],
        [
            sg.Listbox(
                values=[],
                size=(70, 8),
                key="-TARGETS-",
                enable_events=False,
            )
        ],
        [
            sg.Text("Drop files or folders below"),
        ],
        [
            sg.Input(
                key="-DROP-",
                enable_events=True,
                tooltip="Drag MP3 files or folders here",
                size=(70, 1),
            )
        ],
        [
            sg.Checkbox(
                "Join artists into one display string (compatibility)",
                key="-JOIN-ARTISTS-",
                default=True,
                tooltip="Unchecked = save artists as separate entries; some players only show the first entry.",
            )
        ],
        [
            sg.Button("Fill Genre", key="-RUN-", button_color=("white", "#4a7a44")),
            sg.Button("Exit"),
        ],
        [sg.Frame("Log", [[sg.Multiline(key="-LOG-", size=(70, 12), autoscroll=True, disabled=True, reroute_stdout=False, reroute_stderr=False)]])],
    ]

    window = sg.Window(
        "Genre Filler",
        layout,
        finalize=True,
    )

    selected: List[Path] = []

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Exit"):
            break

        if event == "-CHOOSE-FILES-":
            chosen = sg.popup_get_file(
                "Select MP3 files",
                multiple_files=True,
                file_types=(("MP3 Files", "*.mp3"),),
                no_window=True,
            )
            if chosen:
                if isinstance(chosen, (tuple, list)):
                    entries = list(chosen)
                else:
                    entries = str(chosen).split(";")
                selected.extend(_normalize_entries(entries))
        elif event == "-CHOOSE-FOLDER-":
            folder = sg.popup_get_folder("Select a folder")
            if folder:
                selected.append(Path(folder))
                recent_dirs = _remember_dir(recent_dirs, Path(folder))
                _save_recent_dirs(recent_dirs)
                window["-RECENT-"].update(values=[str(p) for p in recent_dirs], value=str(recent_dirs[0]))
        elif event == "-USE-RECENT-":
            recent_choice = values.get("-RECENT-")
            if recent_choice:
                path_choice = Path(recent_choice)
                selected.append(path_choice)
                recent_dirs = _remember_dir(recent_dirs, path_choice)
                _save_recent_dirs(recent_dirs)
                window["-RECENT-"].update(values=[str(p) for p in recent_dirs], value=str(recent_dirs[0]))
        elif event == "-CLEAR-":
            selected = []
            _log_line(window, "Cleared selection.")
        elif event == "-DROP-":
            dropped = _parse_drop_value(values["-DROP-"])
            if dropped:
                dropped_paths = _normalize_entries(dropped)
                selected.extend(dropped_paths)
                for p in dropped_paths:
                    if p.is_dir():
                        recent_dirs = _remember_dir(recent_dirs, p)
                _save_recent_dirs(recent_dirs)
                if recent_dirs:
                    window["-RECENT-"].update(values=[str(d) for d in recent_dirs], value=str(recent_dirs[0]))
                window["-DROP-"].update("")
        elif event == "-RUN-":
            genre = values.get("-GENRE-", "").strip()
            artists_raw = values.get("-ARTIST-", "").strip()
            artists: List[str] = []
            if artists_raw:
                # Split on comma/semicolon into individual artist strings
                artists = _normalize_artist_entries([artists_raw])

            mp3s, errors = _collect_mp3s(selected)
            for err in errors:
                _log_line(window, err)
            if not mp3s:
                sg.popup_error("No MP3 files found in the selection.")
                continue

            successes = 0
            for mp3 in mp3s:
                try:
                    audio = _ensure_easy_tags(mp3)
                    if genre:
                        audio["genre"] = [genre]

                    # Choose artists to write: user-specified list, or normalized
                    # existing tags if none provided (helps split "aaa/bbb" into entries).
                    artists_to_write = artists
                    if not artists_to_write:
                        existing = audio.get("artist", [])
                        artists_to_write = _normalize_artist_entries(existing)

                    if artists_to_write:
                        join_artists = values.get("-JOIN-ARTISTS-", True)
                        if join_artists:
                            audio["artist"] = [" / ".join(artists_to_write)]
                        else:
                            audio["artist"] = artists_to_write

                        # Also store canonical list for future processing.
                        try:
                            id3 = audio.tags
                            # Remove old copy first to avoid duplicates.
                            if "TXXX:ARTISTS-LIST" in id3:
                                del id3["TXXX:ARTISTS-LIST"]
                            id3.add(TXXX(encoding=3, desc="ARTISTS-LIST", text=artists_to_write))
                        except Exception:
                            pass
                    audio.save()
                except Exception as exc:  # noqa: BLE001
                    _log_line(window, f"Failed: {mp3} ({exc})")
                else:
                    successes += 1
                    _log_line(
                        window,
                        f"Updated: {mp3} "
                        f"{'(genre)' if genre else ''}"
                        f"{' (artist)' if artists else ''}",
                    )
            sg.popup_ok(f"Finished. Updated {successes} file(s).")

        # Refresh listbox display with unique, readable paths
        deduped = []
        seen = set()
        for item in selected:
            if item not in seen:
                deduped.append(item)
                seen.add(item)
        selected = deduped
        window["-TARGETS-"].update(values=[str(p) for p in selected])

    window.close()


if __name__ == "__main__":
    main()
