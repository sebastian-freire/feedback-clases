"""Palabras más repetidas en los comentarios (extra de la Fase 6)."""

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable

MIN_WORD_LENGTH = 3

# Palabras vacías del español (artículos, preposiciones, pronombres, verbos auxiliares comunes).
STOPWORDS = frozenset(
    """
    a al algo algun alguna algunas alguno algunos ante antes aqui asi aun aunque bien cada casi
    como con contra cual cuales cuando de del desde donde dos el ella ellas ellos en entre era
    eran es esa esas ese eso esos esta estaba estaban estan estar este esto estos estuvo fue fueron
    ha habia han hasta hay hizo la las le les lo los mas me mi mis mucha muchas mucho muchos muy
    nada ni no nos nosotros o otra otras otro otros para pero poco por porque que quien se sea
    ser si sido sin sobre solo son su sus tal tambien tan tanto te tenia tiene tienen todo todos
    tu tus un una unas uno unos usted ya yo vez veces hace hacer puede pueden fue sea cosa cosas
    clase clases
    """.split()
)

_WORD = re.compile(r"[^\W\d_]+")


def _normalize(word: str) -> str:
    """Sin tildes (la ñ se conserva), para contar "práctica" y "practica" como la misma."""
    word = word.replace("ñ", "\0")
    word = "".join(c for c in unicodedata.normalize("NFD", word) if unicodedata.category(c) != "Mn")
    return word.replace("\0", "ñ")


def top_words(texts: Iterable[str | None], limit: int) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    spellings: dict[str, Counter[str]] = {}
    for text in texts:
        if not text:
            continue
        for word in _WORD.findall(text.lower()):
            key = _normalize(word)
            if len(key) < MIN_WORD_LENGTH or key in STOPWORDS:
                continue
            counter[key] += 1
            spellings.setdefault(key, Counter())[word] += 1
    # Más frecuentes primero y, a igual frecuencia, alfabético. Se muestra la grafía más usada.
    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return [(spellings[key].most_common(1)[0][0], count) for key, count in ranked]
