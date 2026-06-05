# BCCard Ollama 모델 노트북

현재 기준은 GGUF `Q4_K_M` 등록입니다. Ollama 0.23.2 Windows 환경에서 Hugging Face safetensors를 `ollama create --quantize q4_K_M`로 바로 처리하면 일부 모델에서 임시 safetensors 로딩 실패가 발생했습니다. 그래서 llama.cpp로 HF safetensors를 F16 GGUF로 변환한 뒤 `llama-quantize.exe`로 q4 GGUF를 만들고, 그 GGUF를 Ollama에 등록합니다.

## 전체 실행

먼저 다운로드되지 않은 Hugging Face 원본 모델을 받거나, 이미 받은 모델을 검증합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\create_bccard_ollama_models.ps1 -BaseDir C:\ollama-hf -ValidateOnly -ContinueOnError
```

그다음 GGUF/q4 변환, Ollama 등록, API 호출 테스트를 수행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\create_bccard_gguf_q4_models.ps1 -ContinueOnError
```

특정 모델만 다시 처리할 때는 `-Only`를 붙입니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\create_bccard_gguf_q4_models.ps1 -Only bc-gemma-9b-bcgpt:q4
```

이 스크립트는 기존 `C:\rdna4-rocm-clean\Scripts\python.exe` 환경을 사용합니다. 새 venv를 만들지 않습니다.

## 생성 노트북 목록

개발 중 생성된 `.ipynb` 파일은 `_unused_files/20260524_dev_cleanup/model/notebooks/` 아래로 보관했습니다. 필요하면 아래 스크립트로 다시 생성합니다.

| 노트북 | Hugging Face repo | Ollama 태그 | 로컬 HF 경로 | 기본 옵션 |
|---|---|---|---|---|
| `gemma-2-9b-it-kor-BCGPT.ipynb` | `BCCard/gemma-2-9b-it-kor-BCGPT` | `bc-gemma-9b-bcgpt:q4` | `C:\ollama-hf\gemma-2-9b-it-kor-BCGPT` | `temperature=0.6`, `top_p=0.9`, `num_ctx=4096` |
| `DeepSeek-R1-Distill-Llama-8B-BCGPT.ipynb` | `BCCard/DeepSeek-R1-Distill-Llama-8B-BCGPT` | `bc-deepseek-8b-bcgpt-chat:q4` | `C:\ollama-hf\DeepSeek-R1-Distill-Llama-8B-BCGPT` | `temperature=0.6`, `top_p=0.95`, `num_ctx=4096` |
| `Llama-3.1-Kor-BCCard-Finance-8B.ipynb` | `BCCard/Llama-3.1-Kor-BCCard-Finance-8B` | `bc-llama31-finance-8b:q4` | `C:\ollama-hf\llama31-bc-finance-8b` | `temperature=0.6`, `top_p=0.9`, `num_ctx=4096` |
| `Llama-3-Kor-BCCard-Finance-8B.ipynb` | `BCCard/Llama-3-Kor-BCCard-Finance-8B` | `bc-llama3-finance-8b:q4` | `C:\ollama-hf\Llama-3-Kor-BCCard-Finance-8B` | `temperature=0.6`, `top_p=0.9`, `num_ctx=4096` |
| `Llama-3-Kor-BCCard-Finance-12B.ipynb` | `BCCard/Llama-3-Kor-BCCard-Finance-12B` | `bc-llama3-finance-12b:q4` | `C:\ollama-hf\llama3-bc-finance-12b` | `temperature=0.6`, `top_p=0.9`, `num_ctx=4096` |
| `Llama-3-Kor-BCCard-Finance-20B.ipynb` | `BCCard/Llama-3-Kor-BCCard-Finance-20B` | `bc-llama3-finance-20b:q4` | `C:\ollama-hf\llama3-bc-finance-20b` | `temperature=0.6`, `top_p=0.9`, `num_ctx=4096` |
| `gemma-2-27b-it-kor-BCGPT.ipynb` | `BCCard/gemma-2-27b-it-kor-BCGPT` | `bc-gemma-27b-bcgpt:q4` | `C:\ollama-hf\gemma-2-27b-it-kor-BCGPT` | `temperature=0.6`, `top_p=0.9`, `num_ctx=2048` |
| `gemma-2-27b-it-Korean.ipynb` | `BCCard/gemma-2-27b-it-Korean` | `bc-gemma-27b-korean:q4` | `C:\ollama-hf\gemma-2-27b-it-Korean` | `temperature=0.6`, `top_p=0.9`, `num_ctx=2048` |

Use `bc-deepseek-8b-bcgpt-chat:q4` for DeepSeek `/api/chat` eval runs.

## 실행 확인

```powershell
ollama list
ollama ps
```

여러 모델을 연속 테스트할 때는 이전 모델을 내려서 메모리를 비우면 좋습니다.

```powershell
ollama stop bc-gemma-9b-bcgpt:q4
```

노트북은 아래 스크립트에서 재생성합니다.

```powershell
py scripts\create_ollama_model_notebooks.py
```
