from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


def find_browser() -> Path:
    candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not find Edge or Chrome. Install one of them to render markdown PDFs."
    )


def run_pandoc(markdown_path: Path, html_path: Path, css_path: Path, title: str) -> None:
    command = [
        "pandoc",
        str(markdown_path),
        "--from=gfm",
        "--to=html5",
        "--standalone",
        "--embed-resources",
        f"--metadata=title:{title}",
        f"--css={css_path}",
        "-o",
        str(html_path),
    ]
    subprocess.run(command, check=True)


def render_pdf(html_path: Path, pdf_path: Path, browser_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(browser_path),
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=4000",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a markdown file to a styled PDF using pandoc and a headless browser.",
    )
    parser.add_argument("markdown_path", type=Path)
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument(
        "--css",
        type=Path,
        default=Path(__file__).resolve().parent / "assets" / "markdown-preview.css",
        help="CSS file used to style the HTML before printing.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional document title. Defaults to the markdown file stem.",
    )
    parser.add_argument(
        "--keep-html",
        action="store_true",
        help="Keep the generated intermediate HTML file next to the PDF.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    markdown_path = args.markdown_path.resolve()
    pdf_path = args.pdf_path.resolve()
    css_path = args.css.resolve()
    title = args.title or markdown_path.stem.replace("-", " ").replace("_", " ").title()

    if not markdown_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {markdown_path}")
    if not css_path.exists():
        raise FileNotFoundError(f"CSS file not found: {css_path}")

    browser_path = find_browser()

    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        html_path = temp_dir / f"{markdown_path.stem}.html"
        run_pandoc(markdown_path, html_path, css_path, title)
        render_pdf(html_path, pdf_path, browser_path)
        if args.keep_html:
            kept_html_path = pdf_path.with_suffix(".html")
            shutil.copyfile(html_path, kept_html_path)


if __name__ == "__main__":
    main()
