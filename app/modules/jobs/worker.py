from __future__ import annotations

import hashlib
import html
import logging
import os
import shutil
import subprocess
import threading
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.files.model import File, LocalFile

from .model import Job

logger = logging.getLogger(__name__)


def start_job_processing(job_id: int) -> None:
    thread = threading.Thread(
        target=process_job,
        args=(job_id,),
        daemon=True,
        name=f"job-worker-{job_id}",
    )
    thread.start()


def process_job(job_id: int) -> None:
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

        readme_path = _find_readme(extract_dir)
        markdown_text = readme_path.read_text(encoding="utf-8", errors="replace")
        return _render_browser_pdf(markdown_text, readme_path.parent, temp_path)


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
    matches = sorted(path for path in base_dir.rglob("*") if path.is_file() and path.name.lower() == "readme.md")
    if not matches:
        raise FileNotFoundError("README.md not found in repository")
    return matches[0]


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


def _render_browser_pdf(markdown_text: str, asset_root: Path, work_dir: Path) -> bytes:
    html_path = work_dir / "readme.html"
    pdf_path = work_dir / "readme.pdf"
    browser_profile_dir = work_dir / "browser-profile"

    html_path.write_text(
        _build_html_document(markdown_text, asset_root),
        encoding="utf-8",
    )
    browser_profile_dir.mkdir(parents=True, exist_ok=True)

    for browser_binary in _browser_candidates():
        command = _build_browser_command(
            browser_binary=browser_binary,
            html_path=html_path,
            pdf_path=pdf_path,
            browser_profile_dir=browser_profile_dir,
        )
        result = subprocess.run(command, check=False, capture_output=True, text=True)

        if result.returncode == 0 and pdf_path.exists():
            return pdf_path.read_bytes()

        logger.warning(
            "Browser PDF render failed. browser=%s returncode=%s stderr=%s stdout=%s output=%s",
            browser_binary,
            result.returncode,
            result.stderr.strip(),
            result.stdout.strip(),
            pdf_path,
        )

    return _render_text_pdf(markdown_text)


def _build_browser_command(
    browser_binary: str,
    html_path: Path,
    pdf_path: Path,
    browser_profile_dir: Path,
) -> list[str]:
    if _is_windows_browser(browser_binary):
        html_target = _as_windows_file_uri(html_path)
        pdf_target = _as_windows_path(pdf_path)
        profile_target = _as_windows_path(browser_profile_dir)
    else:
        html_target = html_path.as_uri()
        pdf_target = str(pdf_path)
        profile_target = str(browser_profile_dir)

    command = [
        browser_binary,
        "--headless",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--allow-file-access-from-files",
        f"--user-data-dir={profile_target}",
        f"--print-to-pdf={pdf_target}",
        html_target,
    ]
    if not _is_windows_browser(browser_binary):
        command.insert(4, "--no-sandbox")
    return command


def _browser_candidates() -> list[str]:
    candidates = [settings.BROWSER_BINARY]

    if _is_wsl():
        candidates.extend(
            [
                "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
                "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
                "/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe",
                "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            ]
        )

    unique_candidates: list[str] = []
    for candidate in candidates:
        if candidate not in unique_candidates and _browser_exists(candidate):
            unique_candidates.append(candidate)
    return unique_candidates


def _browser_exists(browser_binary: str) -> bool:
    if _is_windows_browser(browser_binary):
        return Path(browser_binary).exists()

    if os.path.sep in browser_binary:
        return Path(browser_binary).exists()

    return shutil.which(browser_binary) is not None


def _is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def _is_windows_browser(browser_binary: str) -> bool:
    return browser_binary.lower().endswith(".exe")


def _as_windows_path(path: Path) -> str:
    result = subprocess.run(
        ["wslpath", "-w", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _as_windows_file_uri(path: Path) -> str:
    windows_path = _as_windows_path(path).replace("\\", "/")
    return f"file:///{windows_path}"


def _build_html_document(markdown_text: str, asset_root: Path) -> str:
    body = _markdown_to_html(markdown_text, asset_root)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>README</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #ffffff;
      --fg: #1f2328;
      --border: #d0d7de;
      --code-bg: #f6f8fa;
      --quote: #656d76;
      --accent: #0969da;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--fg);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }}
    main {{
      max-width: 860px;
      margin: 0 auto;
      padding: 48px 40px 64px;
    }}
    h1, h2, h3, h4, h5, h6 {{
      line-height: 1.25;
      margin: 1.5em 0 0.6em;
    }}
    h1 {{
      font-size: 2.1rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.3em;
      margin-top: 0;
    }}
    h2 {{
      font-size: 1.6rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.25em;
    }}
    p, ul, ol, pre, blockquote {{
      margin: 0 0 1em;
    }}
    ul, ol {{
      padding-left: 1.5em;
    }}
    li + li {{
      margin-top: 0.3em;
    }}
    code {{
      background: var(--code-bg);
      border-radius: 6px;
      padding: 0.15em 0.35em;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 0.9em;
    }}
    pre {{
      background: var(--code-bg);
      border-radius: 10px;
      padding: 16px;
      overflow: hidden;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    pre code {{
      background: transparent;
      padding: 0;
    }}
    blockquote {{
      border-left: 4px solid var(--border);
      color: var(--quote);
      padding-left: 1em;
    }}
    img {{
      max-width: 100%;
      height: auto;
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <main>
    {body}
  </main>
</body>
</html>
"""


def _markdown_to_html(markdown_text: str, asset_root: Path) -> str:
    lines = markdown_text.splitlines()
    parts: list[str] = []
    paragraph: list[str] = []
    list_type: str | None = None
    list_items: list[str] = []
    in_code_block = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            text = " ".join(chunk.strip() for chunk in paragraph if chunk.strip())
            parts.append(f"<p>{_render_inline(text, asset_root)}</p>")
            paragraph.clear()

    def flush_list() -> None:
        nonlocal list_type
        if list_type and list_items:
            items = "".join(f"<li>{item}</li>" for item in list_items)
            parts.append(f"<{list_type}>{items}</{list_type}>")
            list_items.clear()
            list_type = None

    def flush_code() -> None:
        nonlocal in_code_block
        if in_code_block:
            code_html = html.escape("\n".join(code_lines))
            parts.append(f"<pre><code>{code_html}</code></pre>")
            code_lines.clear()
            in_code_block = False

    for raw_line in lines:
        stripped = raw_line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            if in_code_block:
                flush_code()
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(raw_line)
            continue

        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        if stripped.startswith("#"):
            flush_paragraph()
            flush_list()
            level = min(len(stripped) - len(stripped.lstrip("#")), 6)
            content = stripped[level:].strip()
            parts.append(f"<h{level}>{_render_inline(content, asset_root)}</h{level}>")
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            flush_list()
            quote = stripped[1:].strip()
            parts.append(f"<blockquote><p>{_render_inline(quote, asset_root)}</p></blockquote>")
            continue

        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            if list_type not in {None, "ul"}:
                flush_list()
            list_type = "ul"
            list_items.append(_render_inline(stripped[2:].strip(), asset_root))
            continue

        numbered = stripped.split(". ", 1)
        if len(numbered) == 2 and numbered[0].isdigit():
            flush_paragraph()
            if list_type not in {None, "ol"}:
                flush_list()
            list_type = "ol"
            list_items.append(_render_inline(numbered[1].strip(), asset_root))
            continue

        paragraph.append(raw_line)

    flush_paragraph()
    flush_list()
    flush_code()

    return "\n".join(parts)


def _render_inline(text: str, asset_root: Path) -> str:
    text = html.escape(text)
    text = _replace_images(text, asset_root)
    text = _replace_links(text)
    text = _replace_inline_code(text)
    return text


def _replace_inline_code(text: str) -> str:
    parts = text.split("`")
    if len(parts) < 3:
        return text

    rendered: list[str] = []
    for index, part in enumerate(parts):
        if index % 2 == 1:
            rendered.append(f"<code>{part}</code>")
        else:
            rendered.append(part)
    return "".join(rendered)


def _replace_links(text: str) -> str:
    result: list[str] = []
    cursor = 0
    while True:
        start = text.find("[", cursor)
        if start == -1:
            result.append(text[cursor:])
            break
        middle = text.find("](", start)
        end = text.find(")", middle + 2) if middle != -1 else -1
        if middle == -1 or end == -1:
            result.append(text[cursor:])
            break

        result.append(text[cursor:start])
        label = text[start + 1:middle]
        href = text[middle + 2:end]
        result.append(f'<a href="{href}">{label}</a>')
        cursor = end + 1
    return "".join(result)


def _replace_images(text: str, asset_root: Path) -> str:
    result: list[str] = []
    cursor = 0
    while True:
        start = text.find("![", cursor)
        if start == -1:
            result.append(text[cursor:])
            break
        middle = text.find("](", start)
        end = text.find(")", middle + 2) if middle != -1 else -1
        if middle == -1 or end == -1:
            result.append(text[cursor:])
            break

        result.append(text[cursor:start])
        alt = text[start + 2:middle]
        source = text[middle + 2:end]
        if source.startswith(("http://", "https://", "file://", "data:")):
            src = source
        else:
            src = (asset_root / urllib.parse.unquote(source)).resolve().as_uri()
        result.append(f'<img src="{src}" alt="{alt}">')
        cursor = end + 1
    return "".join(result)


def _render_text_pdf(markdown_text: str) -> bytes:
    lines = _normalize_markdown(markdown_text)

    page_width = 612
    page_height = 792
    margin_x = 50
    margin_top = 50
    font_size = 12
    line_height = 16
    lines_per_page = 40

    pages: list[str] = []
    for index in range(0, max(len(lines), 1), lines_per_page):
        page_lines = lines[index:index + lines_per_page] or [""]
        text_commands = ["BT", f"/F1 {font_size} Tf"]
        y = page_height - margin_top
        for line in page_lines:
            escaped = _escape_pdf_text(line)
            text_commands.append(f"1 0 0 1 {margin_x} {y} Tm ({escaped}) Tj")
            y -= line_height
        text_commands.append("ET")
        pages.append("\n".join(text_commands))

    objects: list[bytes] = []

    def add_object(content: str | bytes) -> int:
        data = content.encode("latin-1") if isinstance(content, str) else content
        objects.append(data)
        return len(objects)

    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_ids: list[int] = []
    content_ids: list[int] = []
    for page in pages:
        stream = page.encode("latin-1")
        content_id = add_object(
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        )
        content_ids.append(content_id)
        page_ids.append(0)

    kids_placeholder = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_id = add_object(f"<< /Type /Pages /Count {len(pages)} /Kids [{kids_placeholder}] >>")

    for i, content_id in enumerate(content_ids):
        page_ids[i] = add_object(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Count {len(pages)} /Kids [{kids}] >>".encode("latin-1")

    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF"
        ).encode("ascii")
    )
    return bytes(pdf)


def _normalize_markdown(markdown_text: str) -> list[str]:
    normalized_lines: list[str] = []
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        if line.startswith(("- ", "* ")):
            line = f"- {line[2:].strip()}"
        line = " ".join(line.split())
        if not line:
            normalized_lines.append("")
            continue
        normalized_lines.extend(_wrap_line(line, 90))
    return normalized_lines or [""]


def _wrap_line(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _escape_pdf_text(text: str) -> str:
    safe = text.encode("latin-1", errors="replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
