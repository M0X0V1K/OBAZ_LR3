import argparse
from collections import Counter
from pathlib import Path
import re
from statistics import mean
import sys

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from main import ALGORITHMS, ROOT
from preprocessing import preprocess
from summary import LIMIT


WORD = re.compile(r"[^\W_]+")
METRICS = (1, 2)
COLUMNS = ("Precision", "Recall", "F1")


def words(text):
    return WORD.findall(text.casefold().replace("ё", "е"))


def ngrams(tokens, n):
    return Counter(zip(*(tokens[offset:] for offset in range(n))))


def rouge(summary_words, reference_words, n):
    candidate = ngrams(summary_words, n)
    reference = ngrams(reference_words, n)
    overlap = sum((candidate & reference).values())
    candidate_count = sum(candidate.values())
    reference_count = sum(reference.values())

    precision = overlap / candidate_count if candidate_count else 0.0
    recall = overlap / reference_count if reference_count else 0.0
    total = precision + recall
    f1 = 2 * precision * recall / total if total else 0.0
    return precision, recall, f1


def evaluate(summary, reference_words):
    summary_words = words(summary[:LIMIT])
    return {n: rouge(summary_words, reference_words, n) for n in METRICS}


def score_row(label, n, scores):
    values = " | ".join(f"{score:.4f}" for score in scores)
    return f"| {label} | ROUGE-{n} | {values} |"


def table_header(label):
    return [f"| {label} | Метрика | {' | '.join(COLUMNS)} |", "| --- | --- | ---: | ---: | ---: |"]


def save_report(path, results, averages, problems):
    count = len(next(iter(results.values())))
    overview = ["## Средние метрики", "", f"Документов в оценке — {count}.", "", *table_header("Алгоритм")]
    for name, scores in averages.items():
        overview.extend(score_row(name, n, scores[n]) for n in METRICS)

    lines = ["# Сравнение рефератов", "", *overview]
    for name, documents in results.items():
        lines.extend(("", f"## {name}", "", *table_header("Файл")))
        for filename, scores in documents.items():
            label = filename.replace("|", r"\|")
            lines.extend(score_row(label, n, scores[n]) for n in METRICS)

    if problems:
        lines.extend(("", "## Пропущенные файлы", ""))
        lines.extend(f"- {problem}" for problem in problems)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(overview))


def save_chart(path, n, averages, count):
    figure = Figure(figsize=(8, 4.8), layout="constrained")
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    positions = range(len(COLUMNS))
    width = 0.8 / len(averages)
    for index, (name, scores) in enumerate(averages.items()):
        offset = (index - (len(averages) - 1) / 2) * width
        bars = axis.bar(
            [position + offset for position in positions], scores[n], width=width, label=name
        )
        axis.bar_label(bars, fmt="%.4f", padding=3)
    axis.set_xticks(positions, COLUMNS)
    axis.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1])
    axis.set_ylim(0, 1.08)
    axis.set_ylabel("Средняя оценка")
    figure.suptitle(f"ROUGE-{n} · документов в оценке — {count}")
    axis.legend(loc="lower center", bbox_to_anchor=(0.5, 1), ncol=min(len(averages), 4))
    axis.yaxis.grid(alpha=0.25)
    axis.set_axisbelow(True)
    figure.savefig(path, dpi=160)


def main():
    parser = argparse.ArgumentParser(description="Сравнение алгоритмов по эталонам из gold.")
    parser.add_argument("source", nargs="?", default="all", help="Имя .txt-файла или all")
    args = parser.parse_args()
    input_dir, gold_dir = ROOT / "input", ROOT / "gold"
    for directory in (input_dir, gold_dir):
        if not directory.is_dir():
            parser.error(f"Нужна папка {directory.name} рядом с test.py.")

    inputs = {
        path.name: path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() == ".txt"
    }
    references = {
        path.name: path for path in gold_dir.iterdir() if path.is_file() and path.suffix.lower() == ".txt"
    }
    problems = []
    if args.source == "all":
        filenames = sorted(inputs.keys() & references.keys())
        problems.extend(
            f"{name}: нет эталона в gold." for name in sorted(inputs.keys() - references.keys())
        )
        problems.extend(
            f"{name}: нет исходного текста в input." for name in sorted(references.keys() - inputs.keys())
        )
    else:
        filenames = [args.source] if args.source in inputs and args.source in references else []
    if not filenames:
        parser.error("Для оценки нужны одноимённые .txt-файлы в input и gold.")

    results = {name: {} for name in ALGORITHMS}
    errors = []
    for filename in filenames:
        try:
            source = inputs[filename].read_text(encoding="utf-8-sig")
            reference = words(references[filename].read_text(encoding="utf-8-sig"))
            if not reference:
                raise ValueError("В эталоне нет слов.")
        except (OSError, ValueError) as error:
            errors.append(f"{filename}: {error}")
            continue
        sentences = preprocess(source)
        for name, summarize in ALGORITHMS.items():
            results[name][filename] = evaluate(summarize(sentences), reference)

    for problem in problems + errors:
        print(problem, file=sys.stderr)
    count = len(filenames) - len(errors)
    if not count:
        parser.error("Не удалось оценить ни одной пары файлов.")
    averages = {
        name: {
            n: tuple(mean(column) for column in zip(*(scores[n] for scores in documents.values())))
            for n in METRICS
        }
        for name, documents in results.items()
    }
    destination = ROOT / "output" / "evaluation"
    destination.mkdir(parents=True, exist_ok=True)
    for n in METRICS:
        save_chart(destination / f"rouge-{n}.png", n, averages, count)
    save_report(destination / "report.md", results, averages, problems + errors)
    print(f"\nОтчёт и диаграммы: {destination}")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
