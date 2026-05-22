from __future__ import annotations

import hashlib
import html
import logging
import threading
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from markdown import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer
from weasyprint import CSS, HTML

from app.core.database import SessionLocal
from app.core.config import settings
from app.modules.files.model import File, LocalFile

from .model import Job

logger = logging.getLogger(__name__)
PYTHON_FORMATTER = HtmlFormatter(cssclass="codehilite", linenos=True)


README_PDF_CSS = CSS(
    string="""
    @page {
      size: A4;
      margin: 20mm 16mm;
    }

    :root {
      --bg: #ffffff;
      --fg: #1f2328;
      --border: #d0d7de;
      --muted: #656d76;
      --code-bg: #f6f8fa;
      --accent: #0969da;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      color: var(--fg);
      background: var(--bg);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 12px;
      line-height: 1.6;
      word-break: break-word;
    }

    main {
      max-width: 100%;
    }

    .cover-page,
    .divider-page {
      min-height: 250mm;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }

    .page-break {
      page-break-before: always;
      break-before: page;
    }

    .cover-page h1,
    .divider-page h1 {
      border-bottom: 0;
      padding-bottom: 0;
      margin-bottom: 0.2em;
    }

    .cover-page p,
    .divider-page p,
    .toc-meta {
      color: var(--muted);
      font-size: 14px;
    }

    .toc-list {
      list-style: none;
      padding-left: 0;
      margin: 0;
    }

    .toc-list li {
      margin: 0 0 0.7em;
      padding-bottom: 0.7em;
      border-bottom: 1px solid var(--border);
    }

    .toc-list a {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      color: inherit;
    }

    .toc-label {
      font-weight: 600;
    }

    .toc-kind {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      white-space: nowrap;
    }

    .section-intro {
      color: var(--muted);
      margin-bottom: 2em;
    }

    .file-path {
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 14px;
      color: var(--muted);
      margin: 0;
    }

    h1, h2, h3, h4, h5, h6 {
      line-height: 1.25;
      margin: 1.4em 0 0.5em;
    }

    h1 {
      font-size: 26px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.3em;
      margin-top: 0;
    }

    h2 {
      font-size: 21px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.25em;
    }

    h3 {
      font-size: 17px;
    }

    p, ul, ol, pre, blockquote, table {
      margin: 0 0 1em;
    }

    ul, ol {
      padding-left: 1.6em;
    }

    li + li {
      margin-top: 0.25em;
    }

    a {
      color: var(--accent);
      text-decoration: none;
    }

    code {
      background: var(--code-bg);
      border-radius: 4px;
      padding: 0.15em 0.3em;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 0.9em;
    }

    pre {
      background: var(--code-bg);
      border-radius: 8px;
      padding: 14px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    pre code {
      background: transparent;
      padding: 0;
    }

    blockquote {
      color: var(--muted);
      border-left: 4px solid var(--border);
      padding-left: 1em;
    }

    img {
      max-width: 100%;
      height: auto;
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    th, td {
      border: 1px solid var(--border);
      padding: 8px 10px;
      vertical-align: top;
      text-align: left;
    }

    .codehilite {
      background: var(--code-bg);
      border-radius: 8px;
      overflow: hidden;
      margin: 0 0 1em;
    }

    .codehilite pre {
      margin: 0;
      border-radius: 0;
      background: transparent;
    }

    .codehilite table {
      margin: 0;
      width: 100%;
      border-collapse: collapse;
    }

    .codehilite td {
      border: 0;
      padding: 0;
      vertical-align: top;
    }

    .codehilite .linenos {
      width: 1%;
      white-space: pre;
      user-select: none;
      color: var(--muted);
      border-right: 1px solid var(--border);
      padding: 14px 12px;
    }

    .codehilite .linenodiv pre,
    .codehilite .highlight pre {
      margin: 0;
    }

    .codehilite .highlight {
      padding: 14px 16px;
    }
    """
    + PYTHON_FORMATTER.get_style_defs(".codehilite")
)


def start_job_processing(job_id: int) -> None:
    thread = threading.Thread(
        target=process_job,
        args=(job_id,),
        daemon=True,
        name=f"job-worker-{job_id}",
    )
    thread.start()


def process_job(job_id: int) -> None:
    logger.info("Starting processing job %s", job_id)
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job is None:
            return

        pdf_bytes = _build_pdf_from_repository(job.url)
        stored_file = _store_pdf(db, job.user_id, pdf_bytes)

        job.file_id = stored_file.id
        job.finished = True
        job.updated_at = datetime.utcnow()
        db.add(job)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to process job %s", job_id)
    finally:
        db.close()


def _build_pdf_from_repository(repo_url: str) -> bytes:
    archive_url = _build_archive_url(repo_url)

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        archive_path = temp_path / "repository.zip"

        urllib.request.urlretrieve(archive_url, archive_path)

        extract_dir = temp_path / "repo"
        with zipfile.ZipFile(archive_path, "r") as zip_file:
            zip_file.extractall(extract_dir)

        repo_root = _find_repo_root(extract_dir)
        readme_path = _find_readme(extract_dir)
        markdown_text = readme_path.read_text(encoding="utf-8", errors="replace")
        python_files = _find_python_files(repo_root)
        repo_name = _repo_name_from_url(repo_url)
        return _render_repository_pdf(
            repo_name=repo_name,
            repo_url=repo_url,
            markdown_text=markdown_text,
            asset_root=readme_path.parent,
            repo_root=repo_root,
            python_files=python_files,
        )


def _build_archive_url(repo_url: str) -> str:
    parsed = urllib.parse.urlparse(repo_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Invalid repository URL")

    normalized_path = parsed.path.rstrip("/")
    if normalized_path.endswith(".git"):
        normalized_path = normalized_path[:-4]

    if normalized_path.endswith(".zip"):
        return urllib.parse.urlunparse(parsed)

    repo_name = normalized_path.rsplit("/", 1)[-1]

    if "github.com" in parsed.netloc:
        return urllib.parse.urlunparse(
            (parsed.scheme, parsed.netloc, f"{normalized_path}/archive/HEAD.zip", "", "", "")
        )

    if "gitlab.com" in parsed.netloc:
        return urllib.parse.urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                f"{normalized_path}/-/archive/HEAD/{repo_name}-HEAD.zip",
                "",
                "",
                "",
            )
        )

    raise ValueError("Unsupported repository host")


def _find_readme(base_dir: Path) -> Path:
    matches = sorted(
        path for path in base_dir.rglob("*") if path.is_file() and path.name.lower() == "readme.md"
    )
    if not matches:
        raise FileNotFoundError("README.md not found in repository")
    return matches[0]


def _find_repo_root(base_dir: Path) -> Path:
    directories = [path for path in base_dir.iterdir() if path.is_dir()]
    if len(directories) == 1:
        return directories[0]
    return base_dir


def _find_python_files(repo_root: Path) -> list[Path]:
    excluded_dirs = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        "dist",
        "build",
    }
    python_files = []
    for path in repo_root.rglob("*.py"):
        if any(part in excluded_dirs for part in path.parts):
            continue
        python_files.append(path)
    return sorted(python_files)


def _repo_name_from_url(repo_url: str) -> str:
    parsed = urllib.parse.urlparse(repo_url)
    repo_name = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    return repo_name or "repository"


def _render_repository_pdf(
    repo_name: str,
    repo_url: str,
    markdown_text: str,
    asset_root: Path,
    repo_root: Path,
    python_files: list[Path],
) -> bytes:
    toc_entries = [
        {"id": "readme", "label": "README", "kind": "Documentation"},
        *[
            {
                "id": f"python-file-{index}",
                "label": path.relative_to(repo_root).as_posix(),
                "kind": "Python Source",
            }
            for index, path in enumerate(python_files, start=1)
        ],
    ]

    html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(repo_name)}</title>
</head>
<body>
  <main class="document">
    {_build_cover_page(repo_name, repo_url, len(python_files))}
    {_build_table_of_contents(toc_entries)}
    {_build_readme_section(markdown_text, asset_root)}
    {_build_python_sections(repo_root, python_files)}
  </main>
</body>
</html>
"""
    return HTML(string=html_document, base_url=str(asset_root)).write_pdf(stylesheets=[README_PDF_CSS])


def _build_cover_page(repo_name: str, repo_url: str, python_file_count: int) -> str:
    return f"""
<section class="cover-page">
  <p class="toc-kind">Repository Export</p>
  <h1>{html.escape(repo_name)}</h1>
  <p>{html.escape(repo_url)}</p>
  <p>Includes README and {python_file_count} Python file(s).</p>
</section>
"""


def _build_table_of_contents(toc_entries: list[dict[str, str]]) -> str:
    items = []
    for entry in toc_entries:
        item_id = html.escape(entry["id"])
        item_label = html.escape(entry["label"])
        item_kind = html.escape(entry["kind"])
        items.append(
            f"""
<li>
  <a href="#{item_id}">
    <span class="toc-label">{item_label}</span>
    <span class="toc-kind">{item_kind}</span>
  </a>
</li>
"""
        )
    return f"""
<section class="page-break" id="table-of-contents">
  <h1>Table of Contents</h1>
  <p class="toc-meta">Sections included in this generated PDF.</p>
  <ol class="toc-list">
    {"".join(items)}
  </ol>
</section>
"""


def _build_readme_section(markdown_text: str, asset_root: Path) -> str:
    rendered_markdown = markdown(
        markdown_text,
        extensions=[
            "extra",
            "fenced_code",
            "tables",
            "toc",
            "sane_lists",
        ],
        output_format="html5",
    )
    return f"""
<section class="page-break" id="readme">
  <h1>README</h1>
  <p class="section-intro">Repository documentation rendered from <code>README.md</code>.</p>
  <div class="markdown-body">
    {rendered_markdown}
  </div>
</section>
"""


def _build_python_sections(repo_root: Path, python_files: list[Path]) -> str:
    sections = []
    for index, path in enumerate(python_files, start=1):
        relative_path = path.relative_to(repo_root).as_posix()
        file_id = f"python-file-{index}"
        source = path.read_text(encoding="utf-8", errors="replace")
        highlighted = highlight(source, PythonLexer(), PYTHON_FORMATTER)
        sections.append(
            f"""
<section class="page-break divider-page">
  <p class="toc-kind">Upcoming File</p>
  <h1>{html.escape(path.name)}</h1>
  <p class="file-path">{html.escape(relative_path)}</p>
</section>
<section class="page-break" id="{file_id}">
  <h1>{html.escape(path.name)}</h1>
  <p class="file-path">{html.escape(relative_path)}</p>
  {highlighted}
</section>
"""
        )
    return "".join(sections)


def _store_pdf(db, user_id: int, pdf_bytes: bytes) -> File:
    file_uuid = uuid.uuid4()
    relative_path = str(Path("repo-pdfs") / f"{file_uuid}.pdf")
    storage_path = Path(settings.STORAGE_DIR) / relative_path
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(pdf_bytes)

    now = datetime.utcnow()
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    local_file = LocalFile(
        uuid=file_uuid,
        original_name="README.pdf",
        mime_type="application/pdf",
        size=len(pdf_bytes),
        sha256=sha256,
        relative_path=relative_path,
        created_at=now,
        updated_at=now,
    )
    db.add(local_file)
    db.flush()

    stored_file = File(
        user_id=user_id,
        storage_service="local",
        identifier=file_uuid,
        created_at=now,
        updated_at=now,
    )
    db.add(stored_file)
    db.flush()
    db.commit()
    db.refresh(stored_file)
    return stored_file
