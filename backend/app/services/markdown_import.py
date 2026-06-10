import re
from dataclasses import dataclass, field

VALID_COLORS = {"sagegreen", "olivedrab", "seagreen", "salmon", "hotpink"}

COLOR_MAP = {
    "纯素": "sagegreen", "半绿半素": "olivedrab", "纯绿": "seagreen",
    "半荤半绿": "salmon", "纯荤": "hotpink",
    "纯萃": "hotpink", "半素半绿": "olivedrab",
}


@dataclass
class ParseWarning:
    row: int
    name: str
    field: str
    value: str
    reason: str

    def __str__(self):
        return f"行{self.row} [{self.name}] {self.field}='{self.value}': {self.reason}"


@dataclass
class ParseResult:
    rows: list[dict] = field(default_factory=list)
    warnings: list[ParseWarning] = field(default_factory=list)


def parse_markdown_table(content: str) -> ParseResult:
    lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
    result = ParseResult()
    data_row = 0

    for line in lines:
        if not line.startswith("|"):
            continue
        if re.match(r"^\|[-| ]+\|$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0] in ("店名", "name"):
            continue

        data_row += 1
        name = cells[0].strip()
        color_raw = cells[1].strip()
        address = cells[2].strip()

        # 跳过明显是标题/统计行的行（名称里含区域信息，颜色为空）
        if not name:
            continue
        if re.search(r"(^\S{1,4}区$|共计\d+家)", name):
            result.warnings.append(ParseWarning(
                row=data_row, name=name, field="name", value=name,
                reason="疑似标题/统计行，已跳过"
            ))
            continue

        # 颜色映射与校验
        color = COLOR_MAP.get(color_raw) or color_raw.lower()
        if not color:
            result.warnings.append(ParseWarning(
                row=data_row, name=name, field="color", value=color_raw,
                reason="颜色为空，将使用默认值 sagegreen"
            ))
            color = "sagegreen"
        elif color not in VALID_COLORS:
            result.warnings.append(ParseWarning(
                row=data_row, name=name, field="color", value=color_raw,
                reason=f"未知颜色值 '{color}'，有效值: {sorted(VALID_COLORS)}"
            ))

        # 地址校验
        if not address:
            result.warnings.append(ParseWarning(
                row=data_row, name=name, field="address", value="",
                reason="地址为空，无法地理编码"
            ))

        result.rows.append({"name": name, "color": color, "address": address})

    return result
