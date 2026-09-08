"""Agent (4): publisher.

Copies QA-approved articles into the static-site content collection, skipping any
filing that was already published (deduped by SEC filing URL). Optionally makes a
git commit to trigger the deploy pipeline.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .articles import split_markdown
from .config import settings


def _load_ledger(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"published": {}}


def _save_ledger(path: Path, ledger: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")


def _git_commit(paths: list[Path], message: str) -> bool:
    root = settings.sp500_ciks_path.parent.parent
    if not (root / ".git").exists():
        print("  (no git repo — skipping commit)", file=sys.stderr)
        return False
    try:
        subprocess.run(["git", "-C", str(root), "add", *map(str, paths)], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-m", message], check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"  ! git commit failed: {exc}", file=sys.stderr)
        return False


def run(
    date_str: str,
    output_dir: Path | None = None,
    commit: bool = False,
    dry_run: bool = False,
) -> Path:
    base = (output_dir or settings.output_dir) / date_str
    qa_path = base / "qa.json"
    if not qa_path.exists():
        raise FileNotFoundError(f"{qa_path} not found — run the QA agent first.")

    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    ledger_path = settings.published_index_path
    ledger = _load_ledger(ledger_path)
    published = ledger["published"]

    content_dir = settings.site_content_dir
    content_dir.mkdir(parents=True, exist_ok=True)

    newly_published: list[dict] = []
    skipped_dupe = 0
    skipped_unapproved = 0
    written_paths: list[Path] = []

    for res in qa["results"]:
        if res["status"] != "approved":
            skipped_unapproved += 1
            continue
        source_url = res.get("source_url") or ""
        if source_url in published:
            skipped_dupe += 1
            continue

        src = Path(res["article_path"])
        markdown = src.read_text(encoding="utf-8")
        fm, _ = split_markdown(markdown)
        dest = content_dir / f"{res['slug']}.md"

        if dry_run:
            print(f"  [dry-run] would publish {dest.name}")
        else:
            shutil.copyfile(src, dest)
            written_paths.append(dest)

        entry = {
            "slug": res["slug"],
            "title": fm.get("title"),
            "path": str(dest),
            "published_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "filing_date": fm.get("date"),
        }
        published[source_url] = entry
        newly_published.append({"source_url": source_url, **entry})
        print(f"  + {res['slug']} :: {fm.get('title')}")

    if not dry_run:
        _save_ledger(ledger_path, ledger)
        written_paths.append(ledger_path)
        if commit and newly_published:
            _git_commit(written_paths, f"Publish {len(newly_published)} insider-trade articles ({date_str})")

    report_path = base / "publish.json"
    report = {
        "date": date_str,
        "published": len(newly_published),
        "skipped_duplicate": skipped_dupe,
        "skipped_unapproved": skipped_unapproved,
        "dry_run": dry_run,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "articles": newly_published,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"[publish] {len(newly_published)} published, {skipped_dupe} dupes, "
        f"{skipped_unapproved} unapproved -> {report_path}"
    )
    return report_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Publish approved articles to the site.")
    p.add_argument("--date", required=True)
    p.add_argument("--commit", action="store_true", help="git commit the new articles")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    run(args.date, commit=args.commit, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
