from pathlib import Path

from mutagen.easyid3 import EasyID3

mp3 = Path("./AMEE; Hoàng Dũng - nàng thơ… trời giấu trời mang đi.mp3")
tags = EasyID3(mp3)
artists = tags.get("artist", [])
print("Raw artist list from ID3:", artists)
