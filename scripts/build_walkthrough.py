"""Compose a 150-second presentation from the verified simulator recording.

Requires ffmpeg with libvpx and drawtext, ffprobe, and the system Lato fonts.
This script does not record hardware or execute payments.
It reproduces the earlier presentation before public payment and human input verification.
Read docs/VERIFICATION.md for current results.
"""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/assets/fieldproof-demo.webm"
OUTPUT = ROOT / "docs/assets/fieldproof-walkthrough.webm"
FONT = Path("/usr/share/fonts/truetype/lato/Lato-Regular.ttf")
BOLD = Path("/usr/share/fonts/truetype/lato/Lato-Bold.ttf")
SOURCE_HASH = "185cfda71111873ff5051603e1f8ecf72c6ab918882e76c2ebc186e519a889ba"


def probe(path):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size:stream=width,height,codec_type,codec_name,r_frame_rate",
        "-of", "json", str(path),
    ], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def render_card(work, number, duration, title, body, note):
    for name, content in (("title", title), ("body", body), ("note", note)):
        (work / f"{number}-{name}.txt").write_text(content)
    # Text files keep prose outside ffmpeg's filter expression syntax.
    filters = [
        "drawbox=x=64:y=126:w=8:h=560:color=0x146b8d:t=fill",
        f"drawtext=fontfile='{BOLD}':text='FIELDPROOF / LOCAL PROTOTYPE':fontsize=21:fontcolor=0x146b8d:x=98:y=76",
        f"drawtext=fontfile='{BOLD}':textfile='{work}/{number}-title.txt':expansion=none:fontsize=58:fontcolor=0x183146:x=98:y=155",
        f"drawtext=fontfile='{FONT}':textfile='{work}/{number}-body.txt':expansion=none:fontsize=31:line_spacing=16:fontcolor=0x183146:x=98:y=310",
        "drawbox=x=64:y=735:w=1152:h=118:color=0xdfeaf1:t=fill",
        f"drawtext=fontfile='{FONT}':textfile='{work}/{number}-note.txt':expansion=none:fontsize=24:line_spacing=10:fontcolor=0x39576b:x=98:y=766",
    ]
    target = work / f"card-{number}.webm"
    subprocess.run([
        "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=0xeef4f8:s=1280x900:r=25",
        "-t", str(duration), "-vf", ",".join(filters), "-c:v", "libvpx", "-deadline", "realtime",
        "-cpu-used", "4", "-threads", "4", "-b:v", "1M", "-pix_fmt", "yuv420p", "-an", str(target),
    ], check=True)
    return target


def main():
    if sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_HASH:
        raise ValueError("The source recording changed. Review it before updating its expected hash.")
    source = probe(SOURCE)
    if source["streams"][0]["width"] != 1280 or source["streams"][0]["height"] != 900:
        raise ValueError("The source recording requires a reviewed layout update")
    for font in (FONT, BOLD):
        if not font.is_file():
            raise FileNotFoundError(f"Required font is unavailable: {font.name}")
    source_duration = float(source["format"]["duration"])
    cards = [
        (12, "The gate decides the next move", "Autonomous logistics agent\nOne external facility\nOne fresh contact observation\n\nNo fresh evidence -> WAIT",
         "Presentation from recorded simulator footage.\nNo public paid settlement is verified."),
        (17, "Buy one useful physical fact", "Location: demo-gate\nMetric: gate.closed\nFreshness: 10 seconds\nPrice: 0.001 Devnet USDC\nDecision: DISPATCH or WAIT",
         "Next: actual simulator recording.\nContact and settlement are simulated."),
        (18, "Evidence must pass the buyer", "Pin the observer identity\nMatch location, nonce, result, and time\nReject old, changed, or replayed evidence\nRequire five matching contact samples\nKeep sample agreement separate from confidence\nPublic demo key. No production identity",
         "BLE and Wi-Fi passed on the attached ESP32-C6.\nHuman press/release evidence remains incomplete."),
        (18, "Payment before measurement", "Real x402 V2 SDK / Solana Devnet\nVerify -> reserve proof -> settle -> sample\nRetry -> original evidence, never a new charge\nUnknown settlement -> review before retry\nPublic paid purchase: not yet verified",
         "Simulation exercises the ordering without moving funds.\nPurchase IDs support review after delivery failures."),
        (150 - source_duration - 65, "Build around recurring demand", "Buyer hypothesis: mobile logistics and robotics\nRecord served and unmet demand locally\nNext: one buyer pilot and an external contact\nLater: independent observers and quality history",
         "No customer demand or peaq activation is established.\nIntegration and submission gates remain open."),
    ]
    local = ROOT / ".local"
    local.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="walkthrough-", dir=local) as folder:
        work = Path(folder)
        rendered = [render_card(work, i, *card) for i, card in enumerate(cards)]
        clips = [rendered[0], rendered[1], SOURCE, *rendered[2:]]
        (work / "clips.txt").write_text("\n".join(f"file '{path}'" for path in clips))
        finished = work / "complete.webm"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(work / "clips.txt"),
                        "-c", "copy", "-an", str(finished)], check=True)
        metadata = probe(finished)
        if abs(float(metadata["format"]["duration"]) - 150) > 0.1:
            raise ValueError("The presentation does not meet the planned 150-second duration")
        if any(stream["codec_type"] != "video" for stream in metadata["streams"]):
            raise ValueError("The presentation unexpectedly contains a non-video stream")
        finished.replace(OUTPUT)
    print(json.dumps({"artifact": str(OUTPUT.relative_to(ROOT)), "duration_seconds": metadata["format"]["duration"],
                      "size_bytes": metadata["format"]["size"], "sha256": sha256(OUTPUT.read_bytes()).hexdigest(),
                      "source_sha256": SOURCE_HASH, "mode": "recorded simulation with explanatory title cards; no audio"}, indent=2))


if __name__ == "__main__":
    main()
