"""
Piper TTS model manager.

Run as a script to download the default model:
    python -m vello.tts.piper_setup
"""
import os
import urllib.request
import urllib.error

MODEL_DIR = os.path.expanduser("~/.vello/models/piper")
DEFAULT   = "en_US-amy-medium"

PIPER_MODELS = {
    "en_US-amy-medium": {
        "onnx": (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
            "en/en_US/amy/medium/en_US-amy-medium.onnx"
        ),
        "json": (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
            "en/en_US/amy/medium/en_US-amy-medium.onnx.json"
        ),
    },
    "en_US-lessac-medium": {
        "onnx": (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
            "en/en_US/lessac/medium/en_US-lessac-medium.onnx"
        ),
        "json": (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
            "en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
        ),
    },
}


def get_model_path(model_name: str = DEFAULT) -> str | None:
    """Return .onnx path if both .onnx and .onnx.json exist, else None."""
    onnx_path = os.path.join(MODEL_DIR, f"{model_name}.onnx")
    json_path  = f"{onnx_path}.json"
    if os.path.isfile(onnx_path) and os.path.isfile(json_path):
        return onnx_path
    return None


def download_model(model_name: str = DEFAULT) -> str | None:
    """Download Piper model if not already present. Returns .onnx path."""
    if model_name not in PIPER_MODELS:
        print(f"[Piper] Unknown model: {model_name}")
        return None

    existing = get_model_path(model_name)
    if existing:
        print(f"[Piper] Model already downloaded: {existing}")
        return existing

    os.makedirs(MODEL_DIR, exist_ok=True)
    urls      = PIPER_MODELS[model_name]
    onnx_path = os.path.join(MODEL_DIR, f"{model_name}.onnx")
    json_path  = f"{onnx_path}.json"

    print(f"[Piper] Downloading model: {model_name} (~65 MB)...")
    try:
        print(f"  → {urls['onnx']}")
        urllib.request.urlretrieve(urls["onnx"], onnx_path)
        print(f"  → {urls['json']}")
        urllib.request.urlretrieve(urls["json"], json_path)
        print(f"[Piper] Model ready: {onnx_path}")
        return onnx_path
    except urllib.error.URLError as e:
        print(f"[Piper] Download failed: {e}")
        print("[Piper] Falling back to espeak.")
        for path in (onnx_path, json_path):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
        return None
    except Exception as e:
        print(f"[Piper] Unexpected error: {e}")
        return None


if __name__ == "__main__":
    path = download_model(DEFAULT)
    if path:
        print(f"Model ready: {path}")
        print("Restart Vello to use Piper TTS.")
    else:
        print("Download failed. espeak will be used as the TTS engine.")
