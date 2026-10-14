"""P2: 将 P1 占位 regions/armies 中的晚明/女真语境改为北宋熙宁口径。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "content" / "scenarios" / "song_xining_v2"

TEXT_REPLACEMENTS = [
    ("努尔哈赤", "李元昊系党项诸部"),
    ("建州女真诸部", "西夏边军"),
    ("建州女真", "西夏"),
    ("建州 / 赫图阿拉", "西夏 / 兴庆"),
    ("建州诸部", "党项诸部"),
    ("女真渐强", "西夏近扰"),
    ("女真诸部", "党项诸部"),
    ("女真索伦诸部", "东北诸部"),
    ("野人女真", "黑龙江诸部"),
    ("俺答汗", "辽道宗"),
    ("俺答余部", "契丹诸部"),
    ("俺答封顺义王", "辽宋和战"),
    ("俺答", "契丹"),
    ("土默特骑兵", "契丹骑兵"),
    ("土默特 / 河套", "辽境 / 幽云以北"),
    ("土默特", "契丹"),
    ("辽饷", "岁币边饷"),
    ("边将累破女真", "边将备西夏"),
    ("防蒙古俺答余部叩边", "防契丹诸部叩边"),
    ("累破女真", "备西夏"),
    ("owner_power\": \"jurchen\"", "owner_power\": \"xixia\""),
    ("owner_power\": \"mongol\"", "owner_power\": \"liao\""),
    ("owner_power\": \"korea\"", "owner_power\": \"korea\""),
    ("\"jurchen_host\"", "\"xixia_host\""),
    ("\"mongol_tumed_host\"", "\"liao_cavalry_host\""),
    ("controller\": \"建州女真\"", "controller\": \"西夏\""),
    ("controller\": \"土默特\"", "controller\": \"辽\""),
    ("controlled_by\": \"jurchen\"", "controlled_by\": \"xixia\""),
    ("controlled_by\": \"mongol\"", "controlled_by\": \"liao\""),
    ("controlled_by\": \"houjin\"", "controlled_by\": \"liao\""),
    ("建州势力渐渗", "党项势力渐强"),
    ("奴儿干都司羁縻旧制", "东北羁縻旧制"),
    ("复奴儿干都司羁縻旧制", "复东北羁縻旧制"),
    ("辽东边将时代，建州女真渐强", "西北边警未息，岁币边饷并见"),
    ("7亿亩·1.5亿口", "约3亿亩·8000万口（北宋口径占位）"),
]

META_NOTE = (
    "熙宁变法（1068）盘面：岁币边饷并见，西北西夏、北境辽国为要；"
    "数值为占位，P2 未做平衡。"
)


def main() -> None:
    for name in ("regions.json", "armies.json"):
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        for old, new in TEXT_REPLACEMENTS:
            text = text.replace(old, new)
        if name == "regions.json":
            text = text.replace(
                "熙宁变法（1068）盘面：岁币边饷并见，西北边警未息，岁币边饷并见。",
                META_NOTE,
            )
            if META_NOTE not in text:
                import re

                text = re.sub(
                    r'"note": "[^"]*"',
                    f'"note": "{META_NOTE}"',
                    text,
                    count=1,
                )
        path.write_text(text, encoding="utf-8")
        print(f"sanitized {name}")


if __name__ == "__main__":
    main()
