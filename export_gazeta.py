import argparse
from itertools import islice
from pathlib import Path


DATASET = "IlyaGusev/gazeta"
SPLITS = ("train", "validation", "test")
LIMIT = 300


def shorten_reference(text):
    text = " ".join(text.split())
    if len(text) <= LIMIT:
        return text

    cutoff = LIMIT - 1
    prefix = text[:cutoff]
    if not text[cutoff].isspace():
        prefix = prefix.rsplit(" ", 1)[0]
    return prefix.rstrip(" ,;:—–-") + "…"


def export_split(rows, directory, split):
    input_dir, gold_dir = directory / "input", directory / "gold"
    input_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)

    count = shortened = empty = 0
    for count, row in enumerate(rows, start=1):
        article = row["text"] or ""
        reference = row["summary"] or ""
        gold = shorten_reference(reference)
        shortened += len(" ".join(reference.split())) > LIMIT
        empty += not gold

        filename = f"gazeta_{split}_{count:06d}.txt"
        (input_dir / filename).write_text(article, encoding="utf-8", newline="\n")
        (gold_dir / filename).write_text(gold, encoding="utf-8", newline="\n")

        if count % 5000 == 0:
            print(f"{split} — выгружено {count} пар", flush=True)

    print(f"{split} — {count} пар, сокращено эталонов: {shortened}, пустых эталонов: {empty}")
    return count


def main():
    parser = argparse.ArgumentParser(description="Выгрузка Gazeta в пары input и gold.")
    parser.add_argument("--output", type=Path, default=Path("gazeta"), help="Папка выгрузки")
    parser.add_argument("--split", choices=SPLITS, help="Выгрузить только выбранную часть датасета")
    parser.add_argument("--limit", type=int, help="Максимум пар на одну часть датасета")
    parser.add_argument("--flat", action="store_true", help="Создать input и gold прямо в --output")
    args = parser.parse_args()

    if args.flat and not args.split:
        parser.error("--flat используется вместе с --split.")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit должен быть положительным.")

    try:
        from datasets import load_dataset
    except ModuleNotFoundError as error:
        if error.name != "datasets":
            raise
        parser.exit(1, "Установите зависимость: python -m pip install datasets\n")

    for split in (args.split,) if args.split else SPLITS:
        print(f"Загружаю {DATASET}, часть {split}…", flush=True)
        rows = load_dataset(DATASET, split=split, streaming=True)
        if args.limit is not None:
            rows = islice(rows, args.limit)
        directory = args.output if args.flat else args.output / split
        if export_split(rows, directory, split) == 0:
            parser.exit(1, f"В части {split} нет записей.\n")


if __name__ == "__main__":
    main()
