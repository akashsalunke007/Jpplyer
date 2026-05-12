"""Build HTML summary + CSV from results.json — triggered every N jobs."""
import csv
import io
from datetime import datetime, timezone
from loguru import logger
from src.phase3_apply.result_logger import get_results


_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Job Application Report — Batch {batch_num}</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; }}
    h1 {{ color: #2c3e50; }}
    .summary {{ background: #ecf0f1; padding: 16px; border-radius: 6px; margin-bottom: 24px; }}
    .summary span {{ font-weight: bold; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ background: #2c3e50; color: white; padding: 10px; text-align: left; }}
    td {{ padding: 8px 10px; border-bottom: 1px solid #ddd; }}
    tr:nth-child(even) {{ background: #f9f9f9; }}
    .applied {{ color: green; font-weight: bold; }}
    .failed {{ color: red; font-weight: bold; }}
    .needs_human {{ color: orange; font-weight: bold; }}
  </style>
</head>
<body>
  <h1>Job Application Report — Batch {batch_num}</h1>
  <p>{date}</p>
  <div class="summary">
    <p>Applied: <span>{applied}</span> &nbsp;|&nbsp;
       Failed: <span>{failed}</span> &nbsp;|&nbsp;
       Needs Human: <span>{needs_human}</span> &nbsp;|&nbsp;
       Avg ATS Score: <span>{avg_ats}%</span> &nbsp;|&nbsp;
       Avg Compatibility: <span>{avg_compat}%</span>
    </p>
  </div>
  <table>
    <tr>
      <th>Title</th><th>Company</th><th>Compat %</th>
      <th>ATS %</th><th>Status</th><th>URL</th><th>Timestamp</th>
    </tr>
    {rows}
  </table>
</body>
</html>
"""

_ROW_TEMPLATE = """
<tr>
  <td>{title}</td>
  <td>{company}</td>
  <td>{compatibility_score}</td>
  <td>{ats_score}</td>
  <td class="{status}">{status}</td>
  <td><a href="{url}" target="_blank">Link</a></td>
  <td>{timestamp}</td>
</tr>
"""


def generate_report(batch_num: int) -> tuple[str, str]:
    """
    Build and return (html_string, csv_string) for the latest batch.
    Uses all results in results.json.
    """
    records = get_results()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    applied = sum(1 for r in records if r["status"] == "applied")
    failed = sum(1 for r in records if r["status"] == "failed")
    needs_human = sum(1 for r in records if r["status"] == "needs_human")

    ats_scores = [r["ats_score"] for r in records if r.get("ats_score")]
    compat_scores = [r["compatibility_score"] for r in records if r.get("compatibility_score")]
    avg_ats = round(sum(ats_scores) / len(ats_scores)) if ats_scores else 0
    avg_compat = round(sum(compat_scores) / len(compat_scores)) if compat_scores else 0

    rows_html = "".join(
        _ROW_TEMPLATE.format(**{**r, "timestamp": r["timestamp"][:19]})
        for r in records
    )

    html = _HTML_TEMPLATE.format(
        batch_num=batch_num,
        date=date_str,
        applied=applied,
        failed=failed,
        needs_human=needs_human,
        avg_ats=avg_ats,
        avg_compat=avg_compat,
        rows=rows_html,
    )

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["job_id", "title", "company", "compatibility_score", "ats_score", "status", "url", "timestamp"],
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(records)
    csv_data = buf.getvalue()

    logger.info(f"Report generated: batch {batch_num}, {len(records)} records")
    return html, csv_data
