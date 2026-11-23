import argparse
import json
from pathlib import Path
import sys
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

import luhn
import textrank
from preprocessing import preprocess
from query_parser import read_requests


ROOT = Path(__file__).resolve().parent
ALGORITHMS = {"luhn": luhn.summarize, "textrank": textrank.summarize}
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


def process_file(path, output_dir, summarize, input_format):
    source = read_document(path)
    summaries = []
    analysis = []
    for texts, record in read_requests(source, input_format):
        if record["status"] == "success":
            start = len(summaries)
            summaries.extend(summarize(preprocess(text)) for text in texts)
            record["summary_indexes"] = list(range(start, len(summaries)))
        analysis.append(record)

    write_json(output_dir / f"{path.name}.summaries.json", summaries)
    write_json(output_dir / f"{path.name}.analysis.json", analysis)


def main():
    parser = argparse.ArgumentParser(description="Реферирование документов из папки input.")
    parser.add_argument("algorithm", choices=ALGORITHMS, help="Алгоритм реферирования")
    parser.add_argument(
        "--format", choices=("auto", "text", "queries"), default="auto",
        help="Формат содержимого. queries — JSON-массив строк в каждом запросе",
    )
    args = parser.parse_args()
    input_dir = ROOT / "input"
    output_dir = ROOT / "output"
    if not input_dir.is_dir():
        parser.error("Рядом с main.py должна быть папка input.")

    output_dir.mkdir(exist_ok=True)
    failed = False
    for path in sorted(input_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".txt", ".docx"}:
            continue
        try:
            process_file(path, output_dir, ALGORITHMS[args.algorithm], args.format)
        except (OSError, UnicodeError, BadZipFile, KeyError, ElementTree.ParseError) as error:
            print(f"{path.name}: {error}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
