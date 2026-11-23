import argparse
import json
from pathlib import Path
import sys
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

import luhn
import textrank
from preprocessing import preprocess


ROOT = Path(__file__).resolve().parent
ALGORITHMS = {"luhn": luhn.summarize, "textrank": textrank.summarize}
SUPPORTED_EXTENSIONS = {".txt", ".docx"}
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOCX_TEXT = {WORD_NS + "tab": "\t", WORD_NS + "br": "\n", WORD_NS + "cr": "\n"}


def read_document(path):
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8-sig")

    with ZipFile(path) as document:
        root = ElementTree.fromstring(document.read("word/document.xml"))
    paragraphs = root.findall(f"{WORD_NS}body//{WORD_NS}p")
    return "\n\n".join(
        "".join(
            node.text or "" if node.tag == WORD_NS + "t" else DOCX_TEXT.get(node.tag, "")
            for node in paragraph.iter()
        )
        for paragraph in paragraphs
    )


def write_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        errors="backslashreplace",
    )


def process_file(path, output_dir, summarize):
    source = read_document(path)
    summary = summarize(preprocess(source))
    analysis = [{
        "query": source,
        "start_line": 1,
        "status": "success",
        "tree": {"type": "document", "children": [{"type": "text", "value": source}]},
        "summary_indexes": [0],
    }]
    write_json(output_dir / f"{path.name}.summaries.json", [summary])
    write_json(output_dir / f"{path.name}.analysis.json", analysis)


def main():
    parser = argparse.ArgumentParser(description="Реферирование документов из папки input.")
    parser.add_argument("algorithm", choices=ALGORITHMS, help="Алгоритм реферирования")
    parser.add_argument("source", help="Имя файла с расширением или all для всех файлов")
    args = parser.parse_args()
    input_dir = ROOT / "input"
    output_dir = ROOT / "output"
    if not input_dir.is_dir():
        parser.error("Рядом с main.py должна быть папка input.")

    if args.source == "all":
        paths = sorted(
            path for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )
    else:
        path = input_dir / args.source
        if Path(args.source).name != args.source:
            parser.error("Укажите имя файла без пути.")
        if not path.is_file():
            parser.error(f"Файл «{args.source}» не найден в input.")
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            parser.error("Поддерживаются файлы .txt и .docx.")
        paths = [path]

    output_dir.mkdir(exist_ok=True)
    failed = False
    for path in paths:
        try:
            process_file(path, output_dir, ALGORITHMS[args.algorithm])
        except (OSError, UnicodeError, BadZipFile, KeyError, ElementTree.ParseError) as error:
            print(f"{path.name}: {error}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
