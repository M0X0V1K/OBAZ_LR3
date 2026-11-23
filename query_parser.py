import json
import re


WHITESPACE = re.compile(r"[ \t\r\n]*")
TOKEN = re.compile(r'"(?:\\.|[^"\\\r\n])*"?|[^\s\[\]{},:"]+|\S')
DECODER = json.JSONDecoder()


class QueryError(ValueError):
    def __init__(self, message, offset, token_start=None):
        super().__init__(message)
        self.offset = offset
        self.token_start = offset if token_start is None else token_start


def parse_query(source):
    position = WHITESPACE.match(source).end()
    if source[position:position + 1] != "[":
        raise QueryError("Ожидалась открывающая скобка '['.", position)

    children = [{"type": "punctuation", "value": "["}]
    texts = []
    position = WHITESPACE.match(source, position + 1).end()
    after_comma = False

    while source[position:position + 1] != "]" or after_comma:
        if source[position:position + 1] != '"':
            expected = "строка" if after_comma else "строка или ']'"
            raise QueryError(f"Ожидалась {expected}.", position)
        try:
            value, end = DECODER.raw_decode(source, position)
        except json.JSONDecodeError as error:
            raise QueryError(error.msg, error.pos, token_start=position) from error
        texts.append(value)
        children.append({"type": "string", "value": value})
        position = WHITESPACE.match(source, end).end()
        if source[position:position + 1] == "]":
            break
        if source[position:position + 1] != ",":
            raise QueryError("Ожидалась запятая или закрывающая скобка ']'.", position)
        children.append({"type": "punctuation", "value": ","})
        position = WHITESPACE.match(source, position + 1).end()
        after_comma = True

    children.append({"type": "punctuation", "value": "]"})
    end = WHITESPACE.match(source, position + 1).end()
    if end != len(source):
        raise QueryError("Лишний токен после массива.", end)
    return texts, {"type": "array", "children": children}


def parse_record(source, start_line=1):
    record = {"query": source, "start_line": start_line}
    try:
        texts, tree = parse_query(source)
    except QueryError as error:
        token = TOKEN.match(source, error.token_start)
        record.update(status="failure", error={
            "message": str(error),
            "token": token.group() if token else "<EOF>",
            "line": start_line + source.count("\n", 0, error.offset),
            "column": error.offset - source.rfind("\n", 0, error.offset),
        })
        return [], record
    record.update(status="success", tree=tree)
    return texts, record


def read_requests(source, input_format):
    lines = [(number, line) for number, line in enumerate(source.split("\n"), 1) if line.strip()]
    if input_format == "auto":
        input_format = "queries" if any(
            line.lstrip().startswith("[") for _, line in lines
        ) else "text"

    if input_format == "text":
        yield [source], {
            "query": source,
            "start_line": 1,
            "status": "success",
            "tree": {"type": "document", "children": [{"type": "text", "value": source}]},
        }
        return

    texts, record = parse_record(source)
    if record["status"] == "success" or len(lines) <= 1:
        yield texts, record
    else:
        for number, line in lines:
            yield parse_record(line, number)
