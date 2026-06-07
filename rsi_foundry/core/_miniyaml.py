"""A tiny dependency-free YAML reader/writer for the subset this repo uses.

The foundry ships policy and RunPack files as YAML for human readability, but it
must run on the standard library alone. This parser handles exactly the subset we
emit: nested mappings (2-space indent), block lists of scalars or mappings,
inline ``[a, b]`` / ``{}`` empties, ``#`` comments, and scalar coercion
(int/float/bool/null/str). It is deliberately small; it is not a general YAML
implementation, and it raises on constructs it does not support.
"""

from __future__ import annotations

from typing import Any, List, Tuple


def _coerce(token: str) -> Any:
    t = token.strip()
    if t == "" or t in ("~", "null", "None"):
        return None
    if t in ("true", "True"):
        return True
    if t in ("false", "False"):
        return False
    if (t[0] == t[-1]) and t[0] in ("'", '"') and len(t) >= 2:
        return t[1:-1]
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        pass
    return t


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def loads(text: str) -> Any:
    raw = [_strip_comment(ln) for ln in text.splitlines()]
    lines = [(i, _indent(ln), ln.strip()) for i, ln in enumerate(raw) if ln.strip()]
    value, _ = _parse_block(lines, 0, lines[0][1] if lines else 0)
    return value


def _parse_block(lines: List[Tuple[int, int, str]], pos: int, indent: int):
    if pos >= len(lines):
        return None, pos
    if lines[pos][2].startswith("- "):
        return _parse_list(lines, pos, indent)
    return _parse_map(lines, pos, indent)


def _parse_map(lines, pos, indent):
    result = {}
    while pos < len(lines):
        _, ind, content = lines[pos]
        if ind < indent:
            break
        if ind > indent:
            raise ValueError(f"unexpected indent in mapping: {content!r}")
        if ":" not in content:
            raise ValueError(f"expected 'key: value', got {content!r}")
        key, _, rest = content.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            child_indent = lines[pos + 1][1] if pos + 1 < len(lines) else indent
            if pos + 1 < len(lines) and child_indent > indent:
                value, pos = _parse_block(lines, pos + 1, child_indent)
            else:
                value, pos = None, pos + 1
        else:
            value, pos = _coerce(rest), pos + 1
        result[key] = value
    return result, pos


def _parse_list(lines, pos, indent):
    result = []
    while pos < len(lines):
        _, ind, content = lines[pos]
        if ind < indent or not content.startswith("- "):
            break
        if ind > indent:
            raise ValueError(f"unexpected indent in list: {content!r}")
        item = content[2:].strip()
        if ":" in item and not (item and item[0] in ("'", '"')):
            # Inline mapping entry: re-parse as a one-key map line at deeper indent.
            synthetic = [(lines[pos][0], indent + 2, item)]
            nxt = pos + 1
            while nxt < len(lines) and lines[nxt][1] > indent:
                synthetic.append((lines[nxt][0], lines[nxt][1], lines[nxt][2]))
                nxt += 1
            value, _ = _parse_map(synthetic, 0, indent + 2)
            result.append(value)
            pos = nxt
        else:
            result.append(_coerce(item))
            pos += 1
    return result, pos


def dumps(value: Any, indent: int = 0) -> str:
    pad = "  " * indent
    lines: List[str] = []
    if isinstance(value, dict):
        if not value:
            return f"{pad}{{}}"
        for k, v in value.items():
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{pad}{k}:")
                lines.append(dumps(v, indent + 1))
            else:
                lines.append(f"{pad}{k}: {_scalar(v)}")
    elif isinstance(value, list):
        if not value:
            return f"{pad}[]"
        for item in value:
            if isinstance(item, dict) and item:
                block = dumps(item, indent + 1).split("\n")
                first = block[0].lstrip()
                lines.append(f"{pad}- {first}")
                lines.extend(block[1:])
            else:
                lines.append(f"{pad}- {_scalar(item)}")
    else:
        return f"{pad}{_scalar(value)}"
    return "\n".join(lines)


def _scalar(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(round(v, 6))
    return str(v)
