# OCR Engine Alternatives — LekhaJokha

Last updated: 2026-02-23

## Current Setup

**Default engine:** PaddleOCR (PP-OCRv5) — self-hosted, no API key, Apache 2.0 license.

Switch engines via `OCR_ENGINE` env var in `.env`:

```bash
OCR_ENGINE=paddleocr    # default — self-hosted, CPU, best Indic accuracy
OCR_ENGINE=google_vision # Google Cloud Vision API (needs GOOGLE_VISION_API_KEY)
OCR_ENGINE=easyocr       # self-hosted fallback (needs easyocr pip package)
OCR_ENGINE=mock          # returns sample invoice text (dev/testing)
```

---

## Engine Comparison

| Feature | PaddleOCR v5 | Google Vision | EasyOCR | Tesseract |
|---|---|---|---|---|
| **Hindi+English** | Excellent (F1=0.938) | Excellent | Good (~90%) | Fair (F1=0.797) |
| **Table/Layout** | Excellent (PP-Structure) | Good | Basic | Poor |
| **Self-hosted** | Yes | No (API) | Yes | Yes |
| **CPU-only** | Yes (370+ chars/sec) | N/A (cloud) | Slow but works | Yes |
| **API key needed** | No | Yes | No | No |
| **License** | Apache 2.0 | Pay-per-use | Apache 2.0 | Apache 2.0 |
| **Docker image size** | +~800MB | +~50MB | +~2GB (PyTorch) | +~30MB |
| **Fine-tuning** | Yes (PaddlePaddle) | No | Limited | Complex |
| **Active maintenance** | Very active (Baidu) | Google-maintained | Stagnant (last: Nov 2024) | Slow |

---

## 1. PaddleOCR (PP-OCRv5) — DEFAULT

**Why chosen:**
- Best accuracy on Indic scripts among CPU-capable engines
- Built-in table recognition (PP-StructureV3) for invoice line items
- Zero API cost, zero external dependency
- Apache 2.0 — no commercial restrictions
- Fine-tunable on custom Indian invoice datasets

**Install:** Already in `requirements.txt`:
```
paddlepaddle==3.0.0
paddleocr==3.0.0
```

**Dockerfile needs:** `libgl1-mesa-glx libglib2.0-0` (OpenCV deps)

**Config:**
```bash
OCR_ENGINE=paddleocr
OCR_LANG=en    # or "hi" for Hindi, "ch" for Chinese
```

**Fine-tuning (if needed):**
1. Collect 200-500 annotated Indian invoice images
2. Use PaddleOCR's built-in training pipeline:
   ```bash
   python tools/train.py -c configs/rec/PP-OCRv5/en_PP-OCRv5_rec.yml \
     -o Train.dataset.data_dir=./invoice_dataset \
     -o Global.pretrained_model=./pretrain_models/en_PP-OCRv5_rec
   ```
3. Export trained model and point PaddleOCR to it
4. See: https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/finetune.md

---

## 2. Google Cloud Vision

**When to use:** If you need highest possible accuracy and are OK paying per-request.

**Pricing:** ~$1.50 per 1,000 pages (first 1,000 free/month)

**Install:** Add to requirements.txt:
```
google-cloud-vision==3.7.2
```

**Config:**
```bash
OCR_ENGINE=google_vision
GOOGLE_VISION_API_KEY=your-key-here
```

**Setup:**
1. Create GCP project → enable Cloud Vision API
2. Create service account → download JSON key
3. Set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json` or use API key

**Pros:** Best overall accuracy, handles any language, no infrastructure overhead
**Cons:** Costs money at scale, data leaves your servers, API latency

---

## 3. EasyOCR

**When to use:** Lightweight fallback when PaddleOCR has issues.

**Install:** Add to requirements.txt:
```
easyocr==1.7.2
```

**Config:**
```bash
OCR_ENGINE=easyocr
OCR_LANG=en    # auto-adds "hi" for Hindi support
```

**Pros:** Simplest API (2 lines), good Hindi+English mixed text
**Cons:** Development stagnant, no table recognition, PyTorch adds ~2GB to Docker image, slower on CPU

---

## 4. Tesseract (NOT RECOMMENDED)

**Why excluded from the app:** Poor accuracy on structured documents (invoices, tables). No layout understanding. Significantly worse on Hindi (F1=0.797 vs PaddleOCR's 0.938).

**If you still want it:** `apt-get install tesseract-ocr tesseract-ocr-hin` + `pip install pytesseract`

---

## 5. Surya OCR (LICENSE WARNING)

**Do NOT use for commercial SaaS.** Code is GPL, model weights have a revenue-restricted license (free only for startups under $2M revenue). Paid licensing required from datalab.to for commercial use above that threshold. Also requires GPU.

---

## 6. Future: PaddleOCR-VL (GPU upgrade path)

When GPU infrastructure is available, **PaddleOCR-VL** (0.9B params) can:
- Output structured JSON directly from invoice images
- Replace both OCR step AND regex parsing (`invoice_parser.py`)
- Handle 109 languages including all Indic scripts
- Same Apache 2.0 license, same PaddlePaddle ecosystem

This would be the natural evolution: swap `vision_service.py` + `invoice_parser.py` with a single VL model call that returns structured fields (GSTIN, amounts, line items) as JSON.

**Other VLM options (all need GPU):**
- OlmOCR-2 (7.7B, Apache 2.0) — highest accuracy on benchmarks
- DeepSeek-OCR (3B, MIT) — fast inference, MoE architecture
- GOT-OCR2.0 (580M, Apache 2.0) — needs Hindi fine-tuning

---

## Performance Notes

Tested on CPU (Intel Xeon, Docker):

| Engine | Time per page | Accuracy (Indian invoice) |
|---|---|---|
| PaddleOCR | ~2-4 sec | ~94% |
| EasyOCR | ~5-10 sec | ~90% |
| Tesseract | ~1-2 sec | ~75-80% |
| Google Vision | ~1-2 sec (network) | ~96% |

For a typical 2-page invoice, PaddleOCR takes ~5-8 seconds total, which is acceptable for background processing.

---

## Switching Engines

To switch from PaddleOCR to another engine:

1. Update `.env`: `OCR_ENGINE=google_vision` (or `easyocr`)
2. Install the package: add to `requirements.txt`
3. Rebuild: `docker compose up -d --build`
4. No code changes needed — `vision_service.py` handles all engines

The public API (`extract_text_from_image`, `extract_text_from_pdf`) returns the same `(text, confidence)` tuple regardless of engine.
