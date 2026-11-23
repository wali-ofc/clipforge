"""Pluggable Urdu-to-Roman Urdu transliteration.

The default transliterator is a lightweight, local, rule-based converter aimed at
readable Pakistani Roman Urdu. It preserves existing Latin text (English words,
numbers, punctuation) so mixed Urdu-English speech is not translated.

This is a display-text layer. It must never overwrite original transcript text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

_LATIN_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9'./:-]*")
_URDU_CHAR = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
_WHITESPACE = re.compile(r"\s+")
_EDGE_PUNCTUATION = ".,!?;:()[]{}\"'“”‘’۔؟،؛"
_PUNCTUATION_MAP = {"۔": ".", "؟": "?", "،": ",", "؛": ";"}


class Romanizer(Protocol):
    def romanize(self, text: str) -> str:
        """Return a Romanized display string for *text*."""


# Common Urdu words/phrases mapped to natural Pakistani Roman Urdu.
_WORD_MAP: dict[str, str] = {
    "آپ": "Aap",
    "آپ کا": "Aap ka",
    "کا": "ka",
    "کی": "ki",
    "کے": "ke",
    "کو": "ko",
    "میں": "mein",
    "ہے": "hai",
    "ہیں": "hain",
    "تھا": "tha",
    "تھی": "thi",
    "تھے": "thay",
    "ہوں": "hun",
    "ہو": "ho",
    "گا": "ga",
    "گی": "gi",
    "گے": "ge",
    "پر": "par",
    "سے": "se",
    "نے": "ne",
    "یہ": "ye",
    "وہ": "wo",
    "اور": "aur",
    "یا": "ya",
    "کہ": "ke",
    "جو": "jo",
    "کیا": "kya",
    "کیوں": "kyun",
    "کیسے": "kaise",
    "کہاں": "kahan",
    "کب": "kab",
    "کون": "kaun",
    "کتنا": "kitna",
    "کتنی": "kitni",
    "کتنے": "kitne",
    "بہت": "bohat",
    "زیادہ": "zyada",
    "کم": "kam",
    "نہیں": "nahi",
    "نہ": "na",
    "ہاں": "haan",
    "جی": "ji",
    "تو": "to",
    "بھی": "bhi",
    "ہی": "hi",
    "اب": "ab",
    "جب": "jab",
    "تب": "tab",
    "اگر": "agar",
    "مگر": "magar",
    "لیکن": "lekin",
    "کیونکہ": "kyunke",
    "اس": "is",
    "اسے": "ise",
    "اسی": "isi",
    "ان": "in",
    "انہیں": "unhein",
    "ہم": "hum",
    "ہمیں": "humein",
    "میرا": "mera",
    "میری": "meri",
    "میرے": "mere",
    "تم": "tum",
    "تمہیں": "tumhein",
    "تمہارا": "tumhara",
    "تمہاری": "tumhari",
    "تمہارے": "tumhare",
    "کر": "kar",
    "کرتے": "karte",
    "کرتا": "karta",
    "کرتی": "karti",
    "کریں": "karen",
    "کرنا": "karna",
    "رہے": "rahe",
    "رہا": "raha",
    "رہی": "rahi",
    "گیا": "gaya",
    "گئی": "gayi",
    "گئے": "gaye",
    "دیا": "diya",
    "دی": "di",
    "لیا": "liya",
    "لی": "li",
    "جائے": "jaye",
    "جانا": "jana",
    "آنا": "aana",
    "آئے": "aaye",
    "بات": "baat",
    "لوگ": "log",
    "وقت": "waqt",
    "دن": "din",
    "رات": "raat",
    "آج": "aaj",
    "کل": "kal",
    "صبح": "subah",
    "شام": "shaam",
    "ابھی": "abhi",
    "پھر": "phir",
    "بعد": "baad",
    "پہلے": "pehle",
    "ساتھ": "saath",
    "بغیر": "baghair",
    "لیے": "liye",
    "والا": "wala",
    "والی": "wali",
    "والے": "wale",
    "کوئی": "koi",
    "کچھ": "kuch",
    "سب": "sab",
    "ہر": "har",
    "ایک": "ek",
    "دو": "do",
    "تین": "teen",
    "چار": "chaar",
    "پانچ": "paanch",
    "مجھے": "Mujhe",
    "سمجھ": "samajh",
    "آئی": "aayi",
    "بالکل": "bilkul",
    "صحیح": "sahi",
    "کہا": "kaha",
    "خیال": "khayal",
    "حاصل": "hasil",
    "صرف": "sirf",
    "اپنی": "apni",
    "نیند": "neend",
    "تھکان": "thakan",
    "بدل": "badal",
    "بجے": "baje",
    "اٹھ": "uth",
}

_CHAR_MAP: dict[str, str] = {
    "ا": "a", "آ": "aa", "أ": "a", "إ": "i", "ب": "b", "پ": "p", "ت": "t",
    "ٹ": "t", "ث": "s", "ج": "j", "چ": "ch", "ح": "h", "خ": "kh", "د": "d",
    "ڈ": "d", "ذ": "z", "ر": "r", "ڑ": "r", "ز": "z", "ژ": "zh", "س": "s",
    "ش": "sh", "ص": "s", "ض": "z", "ط": "t", "ظ": "z", "ع": "a", "غ": "gh",
    "ف": "f", "ق": "q", "ک": "k", "گ": "g", "ل": "l", "م": "m", "ن": "n",
    "ں": "n", "و": "o", "ؤ": "o", "ہ": "h", "ۂ": "h", "ھ": "h", "ء": "",
    "ی": "i", "ئ": "i", "ے": "e", "ۃ": "h",
    "ً": "", "ٌ": "", "ٍ": "", "َ": "a", "ُ": "u", "ِ": "i", "ّ": "", "ْ": "", "ٔ": "", "ٕ": "",
    "۔": ".", "،": ",", "؟": "?", "؛": ";", "٪": "%",
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4", "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
    "\u200c": " ", "\u200d": "",
}


def has_urdu_script(text: str) -> bool:
    return bool(_URDU_CHAR.search(text or ""))


def _normalize_urdu(text: str) -> str:
    return (text or "").replace("\u0640", "").strip()


@dataclass(eq=False)
class RuleBasedUrduRomanizer:
    """Simple local romanizer with word overrides and char fallback."""

    word_map: dict[str, str] | None = None
    char_map: dict[str, str] | None = None

    def __post_init__(self) -> None:
        self._word_map = {_normalize_urdu(k): v for k, v in (self.word_map or _WORD_MAP).items()}
        self._char_map = dict(self.char_map or _CHAR_MAP)
        # Cached per instance so swapping the global romanizer cannot serve stale
        # results from another implementation.
        self._romanize_cached = lru_cache(maxsize=4096)(self._romanize_uncached)

    def romanize(self, text: str) -> str:
        raw = str(text or "")
        if not raw.strip():
            return ""
        if not has_urdu_script(raw):
            return _WHITESPACE.sub(" ", raw).strip()
        return self._romanize_cached(raw)

    def _romanize_uncached(self, text: str) -> str:
        raw = str(text or "")
        if not raw.strip():
            return ""
        if not has_urdu_script(raw):
            return _WHITESPACE.sub(" ", raw).strip()

        tokens = re.findall(r"\s+|[^\s]+", raw)
        out: list[str] = []
        for token in tokens:
            if token.isspace():
                out.append(" ")
                continue
            out.append(self._romanize_token(token))

        roman = "".join(out)
        roman = re.sub(r"\s+([,.;!?])", r"\1", roman)
        roman = _WHITESPACE.sub(" ", roman).strip()
        return roman

    def _romanize_token(self, token: str) -> str:
        parts = re.split(r"([A-Za-z0-9][A-Za-z0-9'./:-]*)", token)
        rendered: list[str] = []
        for part in parts:
            if not part:
                continue
            if _LATIN_TOKEN.fullmatch(part):
                rendered.append(part)
                continue
            rendered.append(self._romanize_urdu_run(part))
        return "".join(rendered)

    def _romanize_urdu_run(self, run: str) -> str:
        normalized = _normalize_urdu(run)
        if not normalized:
            return ""
        if normalized in self._word_map:
            return self._word_map[normalized]

        lead = ""
        trail = ""
        core = normalized
        while core and core[0] in _EDGE_PUNCTUATION:
            lead += _PUNCTUATION_MAP.get(core[0], core[0])
            core = core[1:]
        while core and core[-1] in _EDGE_PUNCTUATION:
            trail = _PUNCTUATION_MAP.get(core[-1], core[-1]) + trail
            core = core[:-1]
        if core in self._word_map:
            return lead + self._word_map[core] + trail

        buf: list[str] = []
        prev_space = True
        for ch in core:
            mapped = self._char_map.get(ch)
            if mapped is None:
                if ch.isascii():
                    buf.append(ch)
                    prev_space = ch.isspace()
                continue
            if mapped == "":
                continue
            if mapped == " ":
                if not prev_space:
                    buf.append(" ")
                    prev_space = True
                continue
            buf.append(mapped)
            prev_space = False

        word = "".join(buf)
        word = re.sub(r"([aeiou])\1{2,}", r"\1\1", word)
        word = _WHITESPACE.sub(" ", word).strip()
        if not word:
            return lead + trail
        return lead + word + trail


_DEFAULT_ROMANIZER: Romanizer = RuleBasedUrduRomanizer()


def get_romanizer() -> Romanizer:
    return _DEFAULT_ROMANIZER


def set_romanizer(romanizer: Romanizer) -> None:
    global _DEFAULT_ROMANIZER
    _DEFAULT_ROMANIZER = romanizer


def romanize_text(text: str, *, language: str | None = None) -> str:
    """Romanize text for display.

    Urdu-script text is converted by the configured romanizer. Existing Latin
    tokens are preserved. Non-Urdu Latin text is returned with normalized spacing.
    """
    raw = str(text or "")
    if not raw.strip():
        return ""
    if has_urdu_script(raw) or (language or "").lower() in {"ur", "urd", "urdu"}:
        if has_urdu_script(raw):
            return get_romanizer().romanize(raw)
    return _WHITESPACE.sub(" ", raw).strip()
