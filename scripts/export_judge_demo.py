"""Export the public receipt inspector. Whitelist assets and never copy local state."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {
    "proof.js": "docs/proof.js",
    "settlement.mjs": "docs/settlement.mjs",
    "receipt-keys.json": "host/capmesh/protocol/receipt_keys.json",
    "evidence/device-signed-purchase.json": "docs/evidence/device-signed-purchase.json",
    "evidence/device-signed-contact-states.json": "docs/evidence/device-signed-contact-states.json",
    "assets/fieldproof-signed-receipt.webm": "docs/assets/fieldproof-signed-receipt.webm",
}


def export(output):
    output = output.resolve()
    archive = output.with_name(output.name + ".zip")
    if output.exists() or archive.exists():
        raise ValueError("Output directory or archive already exists. Select a new name to preserve the existing package.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fieldproof-export-", dir=output.parent) as scratch:
        stage = Path(scratch) / "site"
        stage.mkdir()
        for target, source in ASSETS.items():
            destination = stage / target
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / source, destination)
        page = (ROOT / "docs/proof.html").read_text()
        page = page.replace('src="/proof.js"', 'src="./proof.js"')
        page = page.replace('<a href="/">Back to dispatch desk</a>', '<a href="./index.html">Restart inspection</a>')
        page = page.replace('</main>', '<p><a href="./assets/fieldproof-signed-receipt.webm">Watch the captioned 2:30 walkthrough</a></p></main>')
        (stage / "index.html").write_text(page)
        (stage / "README.txt").write_text(
            "FieldProof: inspect recorded physical evidence\n\n"
            "1. Serve this directory on localhost or HTTPS.\n"
            "   python3 -m http.server 8787 --bind 127.0.0.1\n"
            "2. Open http://127.0.0.1:8787.\n"
            "3. Verify the original receipt, then alter its state, challenge, or public key.\n"
            "4. Select Verify recorded payment for a read-only Solana Devnet RPC query.\n"
            "5. Inspect the separately signed BOOT held/released input pair. Those checks moved no funds.\n"
            "6. Watch assets/fieldproof-signed-receipt.webm.\n\n"
            "This package contains recorded evidence, public verification keys, and browser code.\n"
            "It contains no wallet, backend, private key, physical gateway, or payment endpoint.\n"
            "It never charges funds or measures hardware. Authentic expired evidence remains WAIT.\n"
            "The optional RPC check needs internet access and trusts api.devnet.solana.com.\n"
            "The installed code and public pin are the buyer configuration trust root.\n"
            "Use the repository README for the complete live MVP and simulated purchase rehearsal.\n"
        )
        manifest = {str(path.relative_to(stage)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted(stage.rglob("*")) if path.is_file()}
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        stage.rename(output)
    with ZipFile(archive, "x", compression=ZIP_DEFLATED) as bundle:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(output))
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New output directory. Use an ignored .local path.")
    args = parser.parse_args()
    print(export(args.output))
