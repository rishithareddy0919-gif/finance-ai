"""CSV import with row-level validation. Good rows are saved; bad rows are reported, never silently dropped."""
import csv
import io

from transactions import add_transaction

REQUIRED_HEADERS = ["date", "time", "merchant", "amount"]


def import_csv(conn, raw):
    """raw is bytes or str. Returns a report dict."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig")            # utf-8-sig also strips an Excel BOM
    reader = csv.DictReader(io.StringIO(raw))
    headers = [(h or "").strip().lower() for h in (reader.fieldnames or [])]
    missing = [h for h in REQUIRED_HEADERS if h not in headers]
    report = {"total_rows": 0, "imported": 0, "rejected": 0, "missing_headers": missing, "errors": []}
    if missing:                                  # without the required columns nothing can be saved
        return report
    reader.fieldnames = headers
    for row in reader:
        values = {k: v for k, v in row.items() if isinstance(v, str)}
        if not any(v.strip() for v in values.values()):
            continue                             # skip blank lines
        report["total_rows"] += 1
        _, errors = add_transaction(conn, row, source="csv")
        if errors:
            report["rejected"] += 1
            report["errors"].append({"row": reader.line_num, "messages": errors,
                                     "values": {k: row.get(k) for k in REQUIRED_HEADERS}})
        else:
            report["imported"] += 1
    return report
