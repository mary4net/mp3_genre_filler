"""
GUI tool to batch-fill the Genre tag on MP3 files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import PySimpleGUI as sg
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError


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


def _apply_genre(file_path: Path, genre: str) -> None:
    """Write the genre tag to an MP3 file."""
    try:
        audio = EasyID3(file_path)
    except ID3NoHeaderError:
        audio = mutagen.File(file_path, easy=True)
        if audio is None:
            raise ValueError("Unsupported file; could not read tags")
        audio.add_tags()
        audio = EasyID3(file_path)
    audio["genre"] = [genre]
    audio.save()


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

    layout = [
        [sg.Text("Genre to apply"), sg.Input(key="-GENRE-", size=(30, 1))],
        [
            sg.Button("Choose MP3 Files", key="-CHOOSE-FILES-"),
            sg.Button("Choose Folder", key="-CHOOSE-FOLDER-"),
            sg.Button("Clear List", key="-CLEAR-"),
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
                entries = chosen.split(";")
                selected.extend(_normalize_entries(entries))
        elif event == "-CHOOSE-FOLDER-":
            folder = sg.popup_get_folder("Select a folder")
            if folder:
                selected.append(Path(folder))
        elif event == "-CLEAR-":
            selected = []
            _log_line(window, "Cleared selection.")
        elif event == "-DROP-":
            dropped = _parse_drop_value(values["-DROP-"])
            if dropped:
                selected.extend(_normalize_entries(dropped))
                window["-DROP-"].update("")
        elif event == "-RUN-":
            genre = values.get("-GENRE-", "").strip()
            if not genre:
                sg.popup_error("Enter a genre before running.")
                continue
            mp3s, errors = _collect_mp3s(selected)
            for err in errors:
                _log_line(window, err)
            if not mp3s:
                sg.popup_error("No MP3 files found in the selection.")
                continue

            successes = 0
            for mp3 in mp3s:
                try:
                    _apply_genre(mp3, genre)
                except Exception as exc:  # noqa: BLE001
                    _log_line(window, f"Failed: {mp3} ({exc})")
                else:
                    successes += 1
                    _log_line(window, f"Updated: {mp3}")
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
