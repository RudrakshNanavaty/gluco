"""Turn the walk-through script into narration with Kokoro (offline TTS).

    python speak.py <lines.json> <out_dir> <model_dir>

lines.json is [{"id": ..., "line": ...}]. Writes <out_dir>/<id>.wav (24 kHz mono)
and <out_dir>/durations.json. espeak-ng rejects long data paths, so the bundled
data is copied to ~/.cache/gluco-video once.
"""

import json
import shutil
import sys
from pathlib import Path

import espeakng_loader
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
from kokoro_onnx.config import EspeakConfig

VOICE = "af_heart"
SPEED = 1.0
# A short silence either side so lines never start or stop on a hard cut.
PAD_SECONDS = 0.15

lines_path, out_dir, model_dir = (Path(a) for a in sys.argv[1:4])
out_dir.mkdir(parents=True, exist_ok=True)

data = Path.home() / ".cache" / "gluco-video" / "espeak-ng-data"
if not data.exists():
    shutil.copytree(espeakng_loader.get_data_path(), data)

kokoro = Kokoro(
    str(model_dir / "kokoro-v1.0.onnx"),
    str(model_dir / "voices-v1.0.bin"),
    espeak_config=EspeakConfig(
        lib_path=espeakng_loader.get_library_path(), data_path=str(data)
    ),
)

durations = {}
for item in json.loads(lines_path.read_text()):
    audio, rate = kokoro.create(item["line"], voice=VOICE, speed=SPEED, lang="en-us")
    pad = np.zeros(int(rate * PAD_SECONDS), dtype=audio.dtype)
    audio = np.concatenate([pad, audio, pad])
    sf.write(out_dir / f"{item['id']}.wav", audio, rate)
    durations[item["id"]] = round(len(audio) / rate, 3)
    print(f"{item['id']}: {durations[item['id']]:.1f} s")

(out_dir / "durations.json").write_text(json.dumps(durations, indent=2) + "\n")
