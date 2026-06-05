from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model"


MODEL_SPECS = [
    {
        "title": "gemma-2-9b-it-kor-BCGPT",
        "hf_repo": "BCCard/gemma-2-9b-it-kor-BCGPT",
        "local_dir": r"C:\ollama-hf\gemma-2-9b-it-kor-BCGPT",
        "ollama_model": "bc-gemma-9b-bcgpt:q4",
        "temperature": 0.6,
        "top_p": 0.9,
        "num_ctx": 4096,
        "settings_note": "generation_config.json has no temperature/top_p. This notebook uses 0.6/0.9 for consistent sampling.",
    },
    {
        "title": "DeepSeek-R1-Distill-Llama-8B-BCGPT",
        "hf_repo": "BCCard/DeepSeek-R1-Distill-Llama-8B-BCGPT",
        "local_dir": r"C:\ollama-hf\DeepSeek-R1-Distill-Llama-8B-BCGPT",
        "ollama_model": "bc-deepseek-8b-bcgpt-chat:q4",
        "temperature": 0.6,
        "top_p": 0.95,
        "num_ctx": 4096,
        "settings_note": "generation_config.json sets do_sample=true, temperature=0.6, top_p=0.95. Ollama uses the chat-template alias.",
    },
    {
        "title": "Llama-3.1-Kor-BCCard-Finance-8B",
        "hf_repo": "BCCard/Llama-3.1-Kor-BCCard-Finance-8B",
        "local_dir": r"C:\ollama-hf\llama31-bc-finance-8b",
        "ollama_model": "bc-llama31-finance-8b:q4",
        "temperature": 0.6,
        "top_p": 0.9,
        "num_ctx": 4096,
        "settings_note": "generation_config.json sets do_sample=true, temperature=0.6, top_p=0.9.",
    },
    {
        "title": "Llama-3-Kor-BCCard-Finance-8B",
        "hf_repo": "BCCard/Llama-3-Kor-BCCard-Finance-8B",
        "local_dir": r"C:\ollama-hf\Llama-3-Kor-BCCard-Finance-8B",
        "ollama_model": "bc-llama3-finance-8b:q4",
        "temperature": 0.6,
        "top_p": 0.9,
        "num_ctx": 4096,
        "settings_note": "generation_config.json has no temperature/top_p. This notebook uses 0.6/0.9 for consistent sampling.",
    },
    {
        "title": "Llama-3-Kor-BCCard-Finance-12B",
        "hf_repo": "BCCard/Llama-3-Kor-BCCard-Finance-12B",
        "local_dir": r"C:\ollama-hf\llama3-bc-finance-12b",
        "ollama_model": "bc-llama3-finance-12b:q4",
        "temperature": 0.6,
        "top_p": 0.9,
        "num_ctx": 4096,
        "settings_note": "generation_config.json has no temperature/top_p. Context is set conservatively for local q4 inference.",
    },
    {
        "title": "Llama-3-Kor-BCCard-Finance-20B",
        "hf_repo": "BCCard/Llama-3-Kor-BCCard-Finance-20B",
        "local_dir": r"C:\ollama-hf\llama3-bc-finance-20b",
        "ollama_model": "bc-llama3-finance-20b:q4",
        "temperature": 0.6,
        "top_p": 0.9,
        "num_ctx": 4096,
        "settings_note": "generation_config.json has no temperature/top_p. Context is set conservatively for local q4 inference.",
    },
    {
        "title": "gemma-2-27b-it-kor-BCGPT",
        "hf_repo": "BCCard/gemma-2-27b-it-kor-BCGPT",
        "local_dir": r"C:\ollama-hf\gemma-2-27b-it-kor-BCGPT",
        "ollama_model": "bc-gemma-27b-bcgpt:q4",
        "temperature": 0.6,
        "top_p": 0.9,
        "num_ctx": 2048,
        "settings_note": "generation_config.json has no temperature/top_p. Context is set low because this q4 model is still large.",
    },
    {
        "title": "gemma-2-27b-it-Korean",
        "hf_repo": "BCCard/gemma-2-27b-it-Korean",
        "local_dir": r"C:\ollama-hf\gemma-2-27b-it-Korean",
        "ollama_model": "bc-gemma-27b-korean:q4",
        "temperature": 0.6,
        "top_p": 0.9,
        "num_ctx": 2048,
        "settings_note": "generation_config.json has no temperature/top_p. Context is set low because this q4 model is still large.",
    },
]


def src(text: str) -> list[str]:
    return [line + "\n" for line in text.splitlines()]


def cmd_block(spec: dict[str, object]) -> tuple[str, str]:
    ollama_model = str(spec["ollama_model"])
    title = str(spec["title"])
    download_cmd = (
        "powershell -ExecutionPolicy Bypass -File .\\scripts\\create_bccard_ollama_models.ps1 "
        f"-BaseDir C:\\ollama-hf -Only {title}.ipynb -ValidateOnly -ContinueOnError"
    )
    create_cmd = (
        "powershell -ExecutionPolicy Bypass -File .\\scripts\\create_bccard_gguf_q4_models.ps1 "
        f"-Only {ollama_model}"
    )
    return download_cmd, create_cmd


def make_notebook(spec: dict[str, object]) -> dict[str, object]:
    download_cmd, create_cmd = cmd_block(spec)
    title = str(spec["title"])
    hf_repo = str(spec["hf_repo"])
    local_dir = str(spec["local_dir"])
    ollama_model = str(spec["ollama_model"])
    temperature = float(spec["temperature"])
    top_p = float(spec["top_p"])
    num_ctx = int(spec["num_ctx"])
    settings_note = str(spec["settings_note"])

    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": src(
                f"""# {title}

- Hugging Face repo: `{hf_repo}`
- Ollama model tag: `{ollama_model}`
- Local HF path: `{local_dir}`
- Default options used here: `temperature={temperature}`, `top_p={top_p}`, `num_ctx={num_ctx}`
- Note: {settings_note}
"""
            ),
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": src(
                f'''import json
import urllib.error
import urllib.request
from pathlib import Path

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "{ollama_model}"
HF_REPO = "{hf_repo}"
LOCAL_MODEL_DIR = Path(r"{local_dir}")

DEFAULT_OPTIONS = {{
    "temperature": {temperature},
    "top_p": {top_p},
    "num_ctx": {num_ctx},
}}

PROMPT = "비씨카드 연체가 발생했을 때 고객이 먼저 확인해야 할 사항을 설명해줘."

DOWNLOAD_CMD = {download_cmd!r}
CREATE_CMD = {create_cmd!r}
'''
            ),
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": src(
                '''def ollama_request(method: str, path: str, payload: dict | None = None, timeout: int = 180) -> dict:
    url = OLLAMA_BASE_URL.rstrip("/") + path
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama server is not reachable at {OLLAMA_BASE_URL}. Start Ollama and rerun.") from exc


def installed_models() -> list[str]:
    data = ollama_request("GET", "/api/tags")
    return sorted(model.get("name", "") for model in data.get("models", []))


def ensure_model_ready() -> None:
    names = installed_models()
    print("Installed Ollama models:")
    for name in names:
        print(" -", name)

    if OLLAMA_MODEL in names:
        print(f"\\nReady: {OLLAMA_MODEL}")
        return

    print(f"\\nMissing Ollama model: {OLLAMA_MODEL}")
    print("\\n1) Download the Hugging Face model:")
    print(DOWNLOAD_CMD)
    print("\\n2) Register it in Ollama:")
    print(CREATE_CMD)
    raise SystemExit("Run the commands above, then rerun this notebook.")
'''
            ),
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": src(
                '''ensure_model_ready()

payload = {
    "model": OLLAMA_MODEL,
    "messages": [
        {"role": "user", "content": PROMPT},
    ],
    "stream": False,
    "options": DEFAULT_OPTIONS,
}

response = ollama_request("POST", "/api/chat", payload, timeout=600)
print(response.get("message", {}).get("content", ""))
'''
            ),
        },
    ]

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for spec in MODEL_SPECS:
        output_path = MODEL_DIR / f"{spec['title']}.ipynb"
        notebook = make_notebook(spec)
        output_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(output_path)


if __name__ == "__main__":
    main()
