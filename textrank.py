from math import log

from preprocessing import STOP_WORDS
from summary import select_sentences


DAMPING = 0.85


def sentence_graph(terms):
    edges = [[] for _ in terms]
    totals = [0.0] * len(terms)
    for left, left_terms in enumerate(terms):
        for right in range(left + 1, len(terms)):
            right_terms = terms[right]
            common = len(left_terms & right_terms)
            if not common:
                continue
            denominator = log(len(left_terms)) + log(len(right_terms))
            weight = common / denominator if denominator else float(common)
            edges[left].append((right, weight))
            edges[right].append((left, weight))
            totals[left] += weight
            totals[right] += weight
    return edges, totals


def pagerank(edges, totals):
    size = len(edges)
    if not size:
        return []
    scores = [1 / size] * size
    for _ in range(100):
        dangling = sum(score for score, total in zip(scores, totals) if total == 0)
        updated = [(1 - DAMPING + DAMPING * dangling) / size] * size
        for source, neighbors in enumerate(edges):
            for target, weight in neighbors:
                updated[target] += DAMPING * scores[source] * weight / totals[source]
        if sum(abs(new - old) for new, old in zip(updated, scores)) < 1e-8:
            return updated
        scores = updated
    return scores


def summarize(sentences):
    terms = [set(sentence.lemmas) - STOP_WORDS for sentence in sentences]
    scores = pagerank(*sentence_graph(terms))
    return select_sentences(sentences, scores)
