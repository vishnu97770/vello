"""
Text preprocessing pipeline — cleans and normalizes text before TTS.

Why this exists: TTS engines produce unnatural output when they receive
raw text containing markdown symbols, abbreviations, currency, large numbers,
or dense punctuation. This layer fixes all of that before audio is generated.
"""
import re


# ── Abbreviation expansion ─────────────────────────────────────────────────────
# Order matters: longer expansions first so "Dr." isn't matched before "Dr. Smith"
_ABBREVS = [
    (r'\bDr\.', 'Doctor'),
    (r'\bMr\.', 'Mister'),
    (r'\bMrs\.', 'Missus'),
    (r'\bMs\.', 'Miss'),
    (r'\bProf\.', 'Professor'),
    (r'\bSt\.', 'Saint'),
    (r'\betc\.', 'etcetera'),
    (r'\be\.g\.', 'for example'),
    (r'\bi\.e\.', 'that is'),
    (r'\bvs\.', 'versus'),
    (r'\bapprox\.', 'approximately'),
    (r'\bmax\.', 'maximum'),
    (r'\bmin\.', 'minimum'),
    (r'\bno\.', 'number'),
    (r'\bvol\.', 'volume'),
    (r'\bft\.', 'feet'),
    (r'\bin\.', 'inches'),
    (r'\blbs\.', 'pounds'),
    (r'\bkgs?\.', 'kilograms'),
    (r'\bsec\.', 'seconds'),
    (r'\bms\.', 'milliseconds'),
    (r'\bkm\.', 'kilometers'),
    (r'\bGB\b', 'gigabytes'),
    (r'\bMB\b', 'megabytes'),
    (r'\bTB\b', 'terabytes'),
    (r'\bKB\b', 'kilobytes'),
    (r'\bCPU\b', 'C P U'),
    (r'\bRAM\b', 'RAM'),
    (r'\bSSH\b', 'S S H'),
    (r'\bURL\b', 'U R L'),
    (r'\bAPI\b', 'A P I'),
    (r'\bOS\b', 'O S'),
    (r'\bOK\b', 'okay'),
    (r'\bOk\b', 'okay'),
    (r'\bA\.I\.', 'A I'),
    (r'\bAI\b', 'A I'),
]

# ── Large number suffix expansion ─────────────────────────────────────────────
_NUMBER_SUFFIXES = [
    (r'(\d+(?:\.\d+)?)\s*[Tt]rillion', lambda m: f"{m.group(1)} trillion"),
    (r'(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion"),
    (r'(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million"),
    (r'(\d+(?:\.\d+)?)\s*[Kk]', lambda m: f"{m.group(1)} thousand"),
]

# ── Currency symbols ───────────────────────────────────────────────────────────
_CURRENCIES = [
    (r'\$(\d+(?:\.\d+)?)', lambda m: f"{m.group(1)} dollars"),
    (r'£(\d+(?:\.\d+)?)', lambda m: f"{m.group(1)} pounds"),
    (r'€(\d+(?:\.\d+)?)', lambda m: f"{m.group(1)} euros"),
    (r'¥(\d+(?:\.\d+)?)', lambda m: f"{m.group(1)} yen"),
]

# ── Markdown stripping ────────────────────────────────────────────────────────
_MARKDOWN_PATTERNS = [
    (r'\*\*(.+?)\*\*', r'\1'),       # **bold**
    (r'\*(.+?)\*', r'\1'),           # *italic*
    (r'__(.+?)__', r'\1'),           # __bold__
    (r'_(.+?)_', r'\1'),             # _italic_
    (r'`(.+?)`', r'\1'),             # `code`
    (r'```[\s\S]*?```', ''),         # ```code blocks```
    (r'#{1,6}\s*', ''),              # # headings
    (r'\[(.+?)\]\(.+?\)', r'\1'),    # [link](url)
    (r'!\[.+?\]\(.+?\)', ''),        # ![image](url)
    (r'^[-*+]\s+', '', ),            # bullet points (line start)
    (r'^\d+\.\s+', ''),              # numbered lists
    (r'>{1,}\s*', ''),               # > blockquote
    (r'\|[^|\n]+', ''),              # table cells
    (r'-{2,}', '—'),                 # --- horizontal rule → em dash
    (r'={2,}', ''),                  # ===
]

# ── Clause-boundary split regex ────────────────────────────────────────────────
# Splits at sentence endings and natural pause points (commas in long clauses,
# semicolons, em dashes) — NOT at every comma (that creates choppy output).
_CLAUSE_SPLIT = re.compile(
    r'(?<=[.!?])\s+'                      # sentence boundary
    r'|(?<=;)\s+'                          # semicolon
    r'|(?<=—)\s*'                          # em dash
    r'|(?<=:)\s+(?=[A-Z])'               # colon followed by capital
)


def expand_abbreviations(text: str) -> str:
    for pattern, replacement in _ABBREVS:
        if callable(replacement):
            text = re.sub(pattern, replacement, text)
        else:
            text = re.sub(pattern, replacement, text)
    return text


def normalize_numbers(text: str) -> str:
    """Convert currency symbols and number+suffix combos to speakable form."""
    for pattern, replacement in _CURRENCIES:
        text = re.sub(pattern, replacement, text)
    for pattern, replacement in _NUMBER_SUFFIXES:
        text = re.sub(pattern, replacement, text)

    # Expand plain large numbers (>999) using num2words if available
    try:
        from num2words import num2words

        def _replace_number(m):
            try:
                n = int(m.group(0).replace(',', ''))
                if 1000 <= n <= 10_000_000:
                    return num2words(n)
                return m.group(0)
            except (ValueError, OverflowError):
                return m.group(0)

        text = re.sub(r'\b\d{4,}(?:,\d{3})*\b', _replace_number, text)
    except ImportError:
        pass

    return text


def strip_markdown(text: str) -> str:
    for pattern, replacement in _MARKDOWN_PATTERNS:
        flags = re.MULTILINE if '^' in pattern else 0
        text = re.sub(pattern, replacement, text, flags=flags)
    # Collapse multiple spaces / newlines
    text = re.sub(r'\n{2,}', '. ', text)
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def clean_for_tts(text: str) -> str:
    """Full preprocessing pipeline — apply in this order."""
    text = strip_markdown(text)
    text = expand_abbreviations(text)
    text = normalize_numbers(text)
    # Remove leftover symbols TTS engines stumble on
    text = re.sub(r'[*_#~^]', '', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def split_into_chunks(text: str, max_chars: int = 200) -> list[str]:
    """
    Split text into speakable chunks at natural clause boundaries.
    Chunks stay under max_chars so TTS latency stays predictable.

    Why clause boundaries instead of sentence endings only:
    Splitting only at '.' creates very long chunks for list-style responses.
    Splitting at every comma creates choppy robotic delivery.
    Clause boundaries (semicolons, em dashes, sentence ends) hit the sweet spot.
    """
    if len(text) <= max_chars:
        return [text] if text.strip() else []

    parts = _CLAUSE_SPLIT.split(text)
    chunks: list[str] = []
    current = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(current) + len(part) + 1 <= max_chars:
            current = (current + " " + part).strip()
        else:
            if current:
                chunks.append(current)
            # If the part itself exceeds max_chars, split at comma
            if len(part) > max_chars:
                sub_parts = re.split(r',\s+', part)
                sub_current = ""
                for sp in sub_parts:
                    if len(sub_current) + len(sp) + 2 <= max_chars:
                        sub_current = (sub_current + ", " + sp).lstrip(", ")
                    else:
                        if sub_current:
                            chunks.append(sub_current)
                        sub_current = sp
                current = sub_current
            else:
                current = part

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]
