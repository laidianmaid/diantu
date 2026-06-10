import re
from typing import AsyncGenerator

COLOR_MAP = {
    "纯素": "sagegreen", "半绿半素": "olivedrap", "纯绿": "seagreen",
    "半荤半绿": "salmon", "纯荤": "hotpink",
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
