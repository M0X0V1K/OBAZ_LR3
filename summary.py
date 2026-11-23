LIMIT = 300


def select_sentences(sentences, scores):
    original = "\n".join(sentence.text for sentence in sentences)
    if len(original) <= LIMIT:
        return original

    ranked = sorted(range(len(sentences)), key=lambda index: (-scores[index], index))
    selected = []
    seen = set()
    remaining = LIMIT
    for index in ranked:
        text = sentences[index].text
        key = text.casefold()
        cost = len(text) + bool(selected)
        if key not in seen and cost <= remaining:
            selected.append(index)
            seen.add(key)
            remaining -= cost

    if selected:
        return "\n".join(sentences[index].text for index in sorted(selected))

    text = sentences[ranked[0]].text
    fragment = text[:LIMIT - 1]
    if text[LIMIT - 1] != " ":
        fragment = fragment.rsplit(" ", 1)[0]
    return fragment.rstrip(" ,:—-") + "…"
