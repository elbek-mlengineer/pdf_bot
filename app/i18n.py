import json
from contextvars import ContextVar
from pathlib import Path

LANGUAGES = {"uz": "O‘zbekcha", "ru": "Русский", "en": "English"}
_catalogs = {
    code: json.loads(
        (Path(__file__).parent / "locales" / f"{code}.json").read_text(encoding="utf8")
    )
    for code in LANGUAGES
}
current_language = ContextVar("current_language", default="en")


def tr(key: str, *values) -> str:
    return _catalogs[current_language.get()][key].format(*values)


def labels(key: str) -> frozenset[str]:
    return frozenset(catalog[key] for catalog in _catalogs.values())


def layout_name(value: str) -> str:
    key = value.lower()
    return tr(key, "") if key in {"portrait", "landscape", "original"} else value


MENU_LABELS = frozenset().union(
    *(labels(k) for k in _catalogs["en"] if k.startswith("menu_")), labels("language")
)
