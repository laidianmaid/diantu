import re
from typing import AsyncGenerator

COLOR_MAP = {
    "红": "red", "绿": "green", "黄": "yellow", "蓝": "blue",
    "紫": "purple", "橙": "orange", "粉": "pink", "黑": "black",
    "白": "white", "灰": "gray",
}


def parse_markdown_table(content: str) -> list[dict]:
    lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
    rows = []
    for line in lines:
        if not line.startswith("|"):
            continue
        if re.match(r"^\|[-| ]+\|$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 3 and cells[0] not in ("店名", "name"):
            name = cells[0].strip()
            color_zh = cells[1].strip()
            address = cells[2].strip()
            color = COLOR_MAP.get(color_zh, color_zh.lower())
            rows.append({"name": name, "color": color, "address": address})
    return rows
