# Third-Party Licenses

LOCAL-LAB-AI's own code is MIT-licensed (see `LICENSE`). It bundles/downloads
the following third-party components, each under its own license:

| Component | License | Source |
|---|---|---|
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | MIT | Fetched by `engine/acquire_engine.py` during `prepare` |
| [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF) | Apache 2.0 | Fetched by `engine/acquire_model.py` during `prepare` |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) | Apache 2.0 | pip dependency (`rapidocr-onnxruntime`) |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | MIT | pip dependency |
| [FastAPI](https://github.com/tiangolo/fastapi) | MIT | pip dependency |
| [Uvicorn](https://github.com/encode/uvicorn) | BSD-3-Clause | pip dependency |
| [pypdf](https://github.com/py-pdf/pypdf) | BSD-3-Clause | pip dependency |
| [python-docx](https://github.com/python-openxml/python-docx) | MIT | pip dependency |
| [Pillow](https://github.com/python-pillow/Pillow) | HPND | pip dependency |
| [NumPy](https://github.com/numpy/numpy) | BSD-3-Clause | pip dependency |
| [httpx](https://github.com/encode/httpx) | BSD-3-Clause | pip dependency |
| [PyYAML](https://github.com/yaml/pyyaml) | MIT | pip dependency |
| [psutil](https://github.com/giampaolo/psutil) | BSD-3-Clause | pip dependency |

None of these are modified from upstream; they are used as-is via `pip
install` or a direct binary/model download. No license text is embedded in
this repository's own source files beyond this summary and each project's
own `LICENSE`/`NOTICE` file as distributed with the package or release.
