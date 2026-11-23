import argparse
from pathlib import Path
import sys

import luhn
import textrank
from preprocessing import preprocess


ROOT = Path(__file__).resolve().parent
ALGORITHMS = {"luhn": luhn.summarize, "textrank": textrank.summarize}


def process_file(path, output_dir, summarize):
    source = path.read_text(encoding="utf-8-sig")
    summary = summarize(preprocess(source))
    (output_dir / f"{path.name}.summary.txt").write_text(summary, encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description="Реферирование TXT-файлов из папки input.")
    parser.add_argument("algorithm", choices=ALGORITHMS, help="Алгоритм реферирования")
    parser.add_argument("source", help="Имя .txt-файла или all для всех .txt-файлов")
    args = parser.parse_args()
    input_dir = ROOT / "input"
    output_dir = ROOT / "output"
    if not input_dir.is_dir():
        parser.error("Рядом с main.py должна быть папка input.")

    if args.source == "all":
        paths = sorted(
            path for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".txt"
        )
    else:
        path = input_dir / args.source
        if Path(args.source).name != args.source:
            parser.error("Укажите имя файла без пути.")
        if not path.is_file():
            parser.error(f"Файл «{args.source}» не найден в input.")
        if path.suffix.lower() != ".txt":
            parser.error("Поддерживаются только файлы .txt.")
        paths = [path]

    output_dir.mkdir(exist_ok=True)
    failed = False
    for path in paths:
        try:
            process_file(path, output_dir, ALGORITHMS[args.algorithm])
        except (OSError, UnicodeError) as error:
            print(f"{path.name}: {error}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())