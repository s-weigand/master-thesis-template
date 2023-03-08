from __future__ import annotations

import os
import re
import subprocess
from contextlib import contextmanager
from pathlib import Path
from shutil import which

import nbformat
import papermill as pm
from nbconvert import LatexExporter

REPO_ROOT = Path(__file__).parent.parent
NOTEBOOK_DIR = REPO_ROOT / "notebooks"
OUTPUT_DIR = REPO_ROOT / "src/notebooks"

CONVERTER = LatexExporter(
    template_file=(REPO_ROOT / "scripts/latex_template.tex").as_posix()
)

NOTEBOOK_BODY_PATTERN = re.compile(
    r".+\\begin{document}(:?\s+\\maketitle)\s*(?P<notebook_body>.+)\s*\\end{document}",
    re.DOTALL,
)

RAISE_HEADING_RULES = (
    (re.compile(r"\\section{"), r"\\chapter{"),
    (re.compile(r"\\subsection{"), r"\\section{"),
    (re.compile(r"\\subsubsection{"), r"\\subsection{"),
    (re.compile(r"\\paragraph{"), r"\\subsubsection{"),
    (re.compile(r"\\subparagraph{"), r"\\paragraph{"),
)


@contextmanager
def chdir_context(path: Path):
    """Context manager to chance current working directory and back."""
    initial_dir = os.curdir
    os.chdir(path)
    yield
    os.chdir(initial_dir)


def extract_notebook_tex_body(notebook_tex: str) -> str:
    """Extract inner body of notebook latex file, omitting the preamble and wrapping document."""
    match = NOTEBOOK_BODY_PATTERN.search(notebook_tex)
    return match["notebook_body"]


def raise_heading_level(notebook_tex: str) -> str:
    """Raise heading levels e.g. ``section`` -> ``chapter``."""
    for pattern, replace_rule in RAISE_HEADING_RULES:
        notebook_tex = pattern.sub(replace_rule, notebook_tex)
    return notebook_tex


def run_notebooks(notebook_path: Path) -> None:
    """Run notebook to update results."""
    pm.execute_notebook(notebook_path, notebook_path)


def convert_notebook(notebook_path: Path) -> None:
    """Convert notebook to latex file."""
    notebook = nbformat.reads(notebook_path.read_bytes(), as_version=4)
    (body, _) = CONVERTER.from_notebook_node(notebook)
    body = extract_notebook_tex_body(body)
    body = raise_heading_level(body)
    rel_path = notebook_path.relative_to(NOTEBOOK_DIR)
    (OUTPUT_DIR / rel_path).parent.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / rel_path).with_suffix(".tex").write_text(body)


def create_notebook_tex_appendix_index():
    """Create index file including the notebooks."""
    notebook_includes = [
        f"\\include{{{notebook_tex_path.relative_to(OUTPUT_DIR.parent)}}}"
        for notebook_tex_path in OUTPUT_DIR.rglob("*.tex")
        if notebook_tex_path.name != "index.tex"
    ]
    (OUTPUT_DIR / "appendix/index.tex").write_text("\n".join(notebook_includes))


def compile_thesis():
    """Compile ``master_thesis.tex`` with ``tectonic``."""
    subprocess.run(
        [which("tectonic"), "-X", "compile", REPO_ROOT / "src/master_thesis.tex"],
        check=True,
    )


def main():
    """Run notebooks and compile thesis with updated values."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with chdir_context(REPO_ROOT):
        for notebook_path in NOTEBOOK_DIR.rglob("*.ipynb"):
            run_notebooks(notebook_path)
            convert_notebook(notebook_path)
    create_notebook_tex_appendix_index()
    compile_thesis()


if __name__ == "__main__":
    main()
