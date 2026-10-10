"""Package all delivered evidence and verify archive bytes against SHA256.

Run after the simulations and document build. The output must be outside ROOT.
"""
from pathlib import Path
import argparse
import hashlib
import json
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def included(path):
    rel = path.relative_to(ROOT)
    if any(p in {"__pycache__", ".venv", ".git", "reproduced"} for p in rel.parts):
        return False
    if path.suffix in {".pyc", ".aux", ".out", ".toc", ".xdv"} or path.name.endswith(".synctex.gz"):
        return False
    if rel.parts[0] == "deliverables" and path.suffix == ".log":
        return False
    return path.is_file() and path.name != "MANIFEST.sha256"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise SystemExit("Choose an output outside the research directory.")
    from PIL import Image
    from pypdf import PdfReader
    checked = {"pdf": 0, "png": 0, "npz": 0, "docx": 0}
    for p in sorted(ROOT.rglob("*")):
        if not included(p):
            continue
        if p.suffix == ".pdf":
            assert len(PdfReader(p).pages) > 0
            checked["pdf"] += 1
        elif p.suffix == ".png":
            with Image.open(p) as im:
                im.load()
            checked["png"] += 1
        elif p.suffix in {".npz", ".docx"}:
            with ZipFile(p) as z:
                assert z.testzip() is None, str(p)
            checked[p.suffix[1:]] += 1
    (ROOT / "results/file_integrity.json").write_text(json.dumps({"readable": checked}, indent=2))
    files = sorted(p for p in ROOT.rglob("*") if included(p))
    digests = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in files}
    manifest = ROOT / "MANIFEST.sha256"
    manifest.write_text("".join(f"{value}  {name}\n" for name, value in digests.items()))
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=6) as z:
        for p in files + [manifest]:
            z.write(p, "Pesquisa_Operacao_PG_EB/" + p.relative_to(ROOT).as_posix())
    with ZipFile(output) as z:
        assert z.testzip() is None
        for name, expected in digests.items():
            assert sha(z.read("Pesquisa_Operacao_PG_EB/" + name)) == expected, name
    print(json.dumps({"archive": str(output), "files": len(files) + 1,
                      "bytes": output.stat().st_size, "sha256": sha(output.read_bytes()),
                      "verified": True, "readable": checked}, indent=2), flush=True)


if __name__ == "__main__":
    main()
