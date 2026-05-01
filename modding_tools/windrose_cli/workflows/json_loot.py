from __future__ import annotations

from collections.abc import Callable


def loot_row_filter_text(item: dict) -> str:
    parts = [str(item.get("LootItem") or ""), str(item.get("LootTable") or "")]
    return " ".join(parts).lower()


def scale_loot_rows(
    data: dict,
    multiplier: float,
    include_keywords: set[str],
    exclude_keywords: set[str],
    scale_value: Callable[[int, float], int],
) -> list[dict]:
    file_edits = []
    for index, item in enumerate(data.get("LootData", [])):
        if not isinstance(item, dict):
            continue
        if "Min" not in item or "Max" not in item:
            continue
        filter_text = loot_row_filter_text(item)
        if include_keywords and not any(keyword in filter_text for keyword in include_keywords):
            continue
        if exclude_keywords and any(keyword in filter_text for keyword in exclude_keywords):
            continue
        old_min = int(item["Min"])
        old_max = int(item["Max"])
        new_min = scale_value(old_min, multiplier)
        new_max = scale_value(old_max, multiplier)
        item["Min"] = new_min
        item["Max"] = new_max
        file_edits.append(
            {
                "row_index": index,
                "loot_item": item.get("LootItem"),
                "loot_table": item.get("LootTable"),
                "old_min": old_min,
                "old_max": old_max,
                "new_min": new_min,
                "new_max": new_max,
            }
        )
    return file_edits
