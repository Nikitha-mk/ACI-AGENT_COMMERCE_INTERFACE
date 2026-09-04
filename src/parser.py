"""
parser.py — Stage 1 of the ACI pipeline.

Turns raw merchant input (any CSV shape, a plain-text return policy) into a
rough internal structure with a FIXED set of canonical keys, regardless of
what the merchant actually named their columns. This is what makes the
pipeline work on a merchant's real file instead of only the bundled demo
CSV: it doesn't assume the merchant calls the ID column "product_id" or
uses a comma delimiter.

Deliberately does NOT clean up values here — that's the normalizer's job
(Stage 2). The parser's only contract is: consistent shape in, even if the
values inside are still messy strings.
"""

import csv
import io
from pathlib import Path

# Canonical field -> every header spelling we've seen or expect a merchant
# to use. Matching is case-insensitive and ignores surrounding whitespace/
# underscores, so "Product ID", "product_id", "SKU", "Item Id" all resolve.
CANONICAL_FIELDS = {
    "product_id": ["product_id", "id", "sku", "item_id", "product id", "item id", "code"],
    "title": ["title", "name", "product_name", "product name", "item_name",
              "item name", "product_title"],
    "price": ["price", "cost", "mrp", "selling_price", "selling price",
              "rate", "unit_price", "unit price"],
    "stock": ["stock", "quantity", "qty", "inventory", "stock_qty",
              "stock qty", "available_qty", "available qty", "in_stock",
              "availability"],
    "category": ["category", "type", "product_type", "product type",
                 "product_category", "product category", "collection"],
    "variants": ["variants", "variant", "options", "attributes", "specs",
                 "size_color", "size/color"],
    "description": ["description", "desc", "details", "product_description",
                     "product description", "summary", "notes"],
}


def _normalize_header(header: str) -> str:
    return header.strip().lower().replace("_", " ")


def _resolve_columns(fieldnames: list) -> dict:
    """Map each canonical field to whichever actual CSV header matches it,
    or None if the merchant's file doesn't have that column at all.
    """
    normalized_lookup = {_normalize_header(fn): fn for fn in fieldnames}
    resolved = {}
    for canonical, aliases in CANONICAL_FIELDS.items():
        match = None
        for alias in aliases:
            if alias in normalized_lookup:
                match = normalized_lookup[alias]
                break
        resolved[canonical] = match
    return resolved


_CANDIDATE_DELIMITERS = [",", ";", "\t", "|"]


def _detect_delimiter(raw_text: str) -> str:
    """Pick the delimiter that appears most in the header row specifically
    — more robust than csv.Sniffer here, since data rows can contain stray
    commas inside free-text fields (variants, descriptions) that fool a
    sniffer looking at the whole sample.
    """
    header_line = raw_text.splitlines()[0] if raw_text else ""
    counts = {d: header_line.count(d) for d in _CANDIDATE_DELIMITERS}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def _as_text_stream(source):
    """Accept a filesystem path (str/Path) or an already-open/uploaded
    file-like object (e.g. Streamlit's UploadedFile) and return a text
    stream either way.
    """
    if hasattr(source, "read"):
        if hasattr(source, "seek"):
            source.seek(0)
        content = source.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        return io.StringIO(content)
    return open(source, encoding="utf-8")


def parse_product_csv(source) -> list:
    """Read a merchant product file into a list of rough dicts with fixed
    canonical keys, regardless of the merchant's actual column names or
    delimiter.

    `source` can be a file path (str/Path) or a file-like object (e.g. a
    Streamlit file upload). Every value stays a raw string exactly as the
    merchant wrote it — no trimming assumptions, no type coercion. That
    judgment happens downstream in normalizer.py / validator.py.
    """
    stream = _as_text_stream(source)
    raw_text = stream.read()
    stream.seek(0)

    delimiter = _detect_delimiter(raw_text)

    reader = csv.DictReader(stream, delimiter=delimiter)
    fieldnames = reader.fieldnames or []
    columns = _resolve_columns(fieldnames)

    rows = []
    for i, raw_row in enumerate(reader):
        def get(canonical):
            col = columns.get(canonical)
            return (raw_row.get(col) or "").strip() if col else ""

        product_id = get("product_id") or ("AUTO-%04d" % (i + 1))
        rows.append({
            "product_id": product_id,
            "title": get("title"),
            "price_raw": get("price"),
            "stock_raw": get("stock"),
            "category_raw": get("category"),
            "variants_raw": get("variants"),
            "description_raw": get("description"),
        })

    if not hasattr(source, "read"):
        stream.close()

    return rows


def unresolved_columns(source) -> dict:
    """Diagnostic helper: which canonical fields the parser could NOT find
    a matching column for, given this file's actual headers. Useful for
    surfacing a warning in the dashboard rather than silently defaulting
    everything to empty strings.
    """
    stream = _as_text_stream(source)
    raw_text = stream.read()
    stream.seek(0)
    delimiter = _detect_delimiter(raw_text)
    reader = csv.DictReader(stream, delimiter=delimiter)
    columns = _resolve_columns(reader.fieldnames or [])
    if not hasattr(source, "read"):
        stream.close()
    return {k: v for k, v in columns.items() if v is None}


def parse_policy_text(source) -> str:
    """Read the raw plain-text return policy. Parsing here means just
    getting the raw text into memory as a single string — the normalizer
    is what extracts structure (windows, exceptions, conflicts) from it.

    `source` can be a file path (str/Path) or a file-like object.
    """
    if hasattr(source, "read"):
        stream = _as_text_stream(source)
        return stream.read().strip()
    return Path(source).read_text(encoding="utf-8").strip()


if __name__ == "__main__":
    import json

    base = Path(__file__).resolve().parent.parent / "data"
    products = parse_product_csv(str(base / "merchant_products_raw.csv"))
    policy = parse_policy_text(str(base / "return_policy.txt"))
    print("Parsed %d product rows." % len(products))
    print(json.dumps(products[0], indent=2))
    print("\nPolicy text length:", len(policy), "chars")
