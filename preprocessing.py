from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import re

from pymorphy3 import MorphAnalyzer


WORD = re.compile(r"[^\W_]+")
RUSSIAN = re.compile(r"[а-яё]+")
SENTENCE_END = re.compile(r"""[.!?…]+[»”"')\]]*(?=\s|$)""")
ABBREVIATION = re.compile(
    r"(?i:\b(?:г|ул|им|рис|табл|проф|акад|см|стр|т|е)\.)$|\b[А-ЯЁ]\.$"
)
STOP_WORDS = frozenset("""
а без быть в весь вот вы где да даже для до его ее ещё еще если есть же за
и из или им их к как когда который ли либо между мы на над не нет ни но о
об однако он она они от по под после при про с себя свой так такой там тот
тоже только тут ты у уже что чтобы этот я
""".split())


@dataclass(frozen=True)
class Sentence:
    text: str
    lemmas: tuple[str, ...]


@lru_cache(maxsize=1)
def analyzer():
    return MorphAnalyzer()


@lru_cache(maxsize=32768)
def lemma_candidates(word):
    if not RUSSIAN.fullmatch(word):
        return (word,)
    parses = analyzer().parse(word)
    return tuple(dict.fromkeys(parse.normal_form for parse in parses if parse.score == parses[0].score))


def split_sentences(text):
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = " ".join(paragraph.split())
        start = 0
        for match in SENTENCE_END.finditer(paragraph):
            end = match.end()
            sentence = paragraph[start:end].strip()
            if end < len(paragraph) and ABBREVIATION.search(sentence):
                continue
            yield sentence
            start = end
        if start < len(paragraph):
            yield paragraph[start:].strip()


def preprocess(text):
    sentences = list(split_sentences(text))
    candidates = [
        [lemma_candidates(word) for word in WORD.findall(sentence.casefold())]
        for sentence in sentences
    ]
    unambiguous = Counter(options[0] for row in candidates for options in row if len(options) == 1)
    return [
        Sentence(sentence, tuple(max(options, key=unambiguous.__getitem__) for options in row))
        for sentence, row in zip(sentences, candidates)
    ]
