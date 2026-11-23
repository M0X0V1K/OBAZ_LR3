from collections import Counter

from preprocessing import STOP_WORDS
from summary import select_sentences


def sentence_score(lemmas, significant):
    best = 0.0
    first = last = -1
    count = 0
    for index, word in enumerate(lemmas):
        if word not in significant:
            continue
        if last < 0 or index - last > 5:
            if count:
                best = max(best, count ** 2 / (last - first + 1))
            first = index
            count = 0
        last = index
        count += 1
    if count:
        best = max(best, count ** 2 / (last - first + 1))
    return best


def summarize(sentences):
    frequencies = Counter(
        word for sentence in sentences for word in sentence.lemmas if word not in STOP_WORDS
    )
    significant = {word for word, count in frequencies.items() if count >= 2} or set(frequencies)
    scores = [sentence_score(sentence.lemmas, significant) for sentence in sentences]
    return select_sentences(sentences, scores)
