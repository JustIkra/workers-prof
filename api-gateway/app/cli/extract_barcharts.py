from __future__ import annotations

"""
CLI: Extract numeric values from bar-chart-like images embedded in DOCX files.

Gemini Vision-based extraction using cropped ROIs. Requires API keys
(.env -> GEMINI_API_KEYS, ALLOW_EXTERNAL_NETWORK=1).

Usage (inside container):
  python -m app.cli.extract_barcharts -o /workspace/out.md /workspace/path/file.docx [...]
"""

import argparse
import base64
import io
import json
import os
import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np
from PIL import Image, ImageOps, ImageFilter

from app.core.config import Settings
from app.core.gemini_factory import create_gemini_client
from app.services.docx_extraction import DocxImageExtractor


NUM_RE = re.compile(r"^(?:10|[1-9])([,.][0-9])?$")
CONF_THR = 0.8


@dataclass
class OcrToken:
    text: str
    conf: float
    left: int
    top: int
    width: int
    height: int

    @property
    def y_center(self) -> float:
        return self.top + self.height / 2.0


def crop_bottom_axis(img: Image.Image, drop_ratio: float = 0.18) -> Image.Image:
    w, h = img.size
    bottom = int(h * (1.0 - drop_ratio))
    bottom = max(1, min(h, bottom))
    return img.crop((0, 0, w, bottom))


def preprocess_for_ocr(img: Image.Image) -> Image.Image:
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g)
    g = g.filter(ImageFilter.SHARPEN)
    w, h = g.size
    if max(w, h) < 2200:
        g = g.resize((w * 2, h * 2))
    return g


@lru_cache(maxsize=1)
def _get_paddle_ocr():
    """Lazy init PaddleOCR to avoid heavy startup cost per call.

    Returns None if PaddleOCR is not installed, so callers can fallback.
    """
    try:
        import paddle  # type: ignore
        from paddleocr import PaddleOCR  # type: ignore
    except Exception:
        return None

    try:
        use_gpu = False
        try:
            use_gpu = bool(getattr(paddle.device, "is_compiled_with_cuda", lambda: False)())
        except Exception:
            use_gpu = False
        # ru language uses cyrillic + digits; we filter digits later anyway
        ocr = PaddleOCR(use_angle_cls=True, lang="ru", show_log=False, use_gpu=use_gpu)
        return ocr
    except Exception:
        return None


def run_paddle_tokens(img: Image.Image) -> List[OcrToken]:
    """Run PaddleOCR and convert results into OcrToken list.

    When PaddleOCR is unavailable, returns an empty list to signal fallback.
    """
    ocr = _get_paddle_ocr()
    if ocr is None:
        return []

    try:
        # Paddle expects ndarray (H, W, C) BGR or RGB; PIL -> numpy array (RGB)
        arr = np.array(img.convert("RGB"))
        result = ocr.ocr(arr, cls=True)
    except Exception:
        return []

    tokens: List[OcrToken] = []
    # result is list per image (we pass one image) -> [ [ [box, (text, conf)], ... ] ]
    for line in (result[0] or []):
        try:
            box, rec = line
            text, conf = rec
            # box: 4 points [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            left = int(min(xs))
            top = int(min(ys))
            width = int(max(xs) - left)
            height = int(max(ys) - top)
            tokens.append(
                OcrToken(
                    text=str(text).strip(),
                    conf=float(conf),
                    left=left,
                    top=top,
                    width=max(1, width),
                    height=max(1, height),
                )
            )
        except Exception:
            continue
    return tokens


def run_tesseract_tsv(img: Image.Image) -> List[OcrToken]:
    buf = io.BytesIO(); img.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    tokens: List[OcrToken] = []
    for psm in (11, 6, 12):
        cmd = [
            "tesseract", "stdin", "stdout",
            "-l", "eng+rus", "--oem", "3", "--psm", str(psm),
            "tsv", "-c", "tessedit_char_whitelist=0123456789,.",
        ]
        try:
            res = subprocess.run(cmd, input=png_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError:
            continue
        tsv = res.stdout.decode("utf-8", errors="ignore").splitlines()
        if not tsv:
            continue
        for line in tsv[1:]:
            parts = line.split("\t")
            if len(parts) < 12:
                continue
            text = (parts[11] or "").strip()
            if not text:
                continue
            try:
                conf = float(parts[10]); left = int(parts[6]); top = int(parts[7]); width = int(parts[8]); height = int(parts[9])
            except ValueError:
                continue
            tokens.append(OcrToken(text=text, conf=conf, left=left, top=top, width=width, height=height))
    return tokens


def select_numeric_tokens(tokens: Iterable[OcrToken]) -> List[OcrToken]:
    out: List[OcrToken] = []
    for t in tokens:
        text = t.text.replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1").replace(" ", "")
        if NUM_RE.match(text):
            out.append(OcrToken(text=text, conf=t.conf, left=t.left, top=t.top, width=t.width, height=t.height))
    return out


def cluster_by_row(tokens: List[OcrToken], y_tol: int | None = None) -> List[List[OcrToken]]:
    if not tokens:
        return []
    toks = sorted(tokens, key=lambda t: t.y_center)
    if y_tol is None:
        avg_h = int(sum(t.height for t in toks) / max(1, len(toks)))
        y_tol = max(8, int(avg_h * 0.8))
    rows: List[List[OcrToken]] = []
    cur: List[OcrToken] = [toks[0]]
    for t in toks[1:]:
        if abs(t.y_center - cur[-1].y_center) <= y_tol:
            cur.append(t)
        else:
            rows.append(cur)
            cur = [t]
    rows.append(cur)
    return rows


def pick_best_per_row(rows: List[List[OcrToken]]) -> List[Tuple[str, float]]:
    return [(max(row, key=lambda t: t.conf).text, max(row, key=lambda t: t.conf).conf) for row in rows]


def extract_badge_values_cv2(img: Image.Image) -> List[OcrToken]:
    try:
        import cv2
    except Exception:
        return []
    arr = np.array(img.convert("RGB"))
    h, w = arr.shape[:2]
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((3, 3), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tokens: List[OcrToken] = []
    for cnt in contours:
        x, y, ww, hh = cv2.boundingRect(cnt)
        area = ww * hh
        if x < int(w * 0.25) or y > int(h * 0.9) or area < 1200 or area > (w * h * 0.1):
            continue
        roi = Image.fromarray(arr[max(0, y-4):min(h, y+hh+4), max(0, x-4):min(w, x+ww+4)])
        roi_p = preprocess_for_ocr(roi)
        for t in select_numeric_tokens(run_tesseract_tsv(roi_p)):
            tokens.append(OcrToken(text=t.text, conf=t.conf, left=x + t.left, top=y + t.top, width=t.width, height=t.height))
    return tokens


async def gemini_extract_values(image_data: bytes, settings: Settings) -> list[str] | None:
    if not settings.gemini_keys_list or not settings.ai_vision_fallback_enabled or not settings.allow_external_network:
        return None
    client = create_gemini_client()
    prompt = (
        "Извлеки только числовые оценки из меток на горизонтальном барчарте. "
        "Ответ строго в JSON: {\"values\":[\"x\",...]} где x соответствует регулярному выражению "
        "^(?:10|[1-9])([,.][0-9])?$ и диапазону 1..10. Никакого текста вне JSON."
    )
    try:
        resp = await client.generate_from_image(
            prompt=prompt,
            image_data=image_data,
            mime_type="image/png",
            response_mime_type="application/json",
            timeout=float(settings.gemini_timeout_s),
        )
    except Exception:
        return None

    # Parse JSON from Gemini response
    try:
        # Typical response shape
        txt = resp["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(txt)
        values = data.get("values")
        if not isinstance(values, list):
            return None
        out: list[str] = []
        for v in values:
            if isinstance(v, str) and NUM_RE.match(v):
                out.append(v)
        return out or None
    except Exception:
        return None


def process_docx(docx_path: Path, settings: Settings) -> list[tuple[str, list[tuple[str, float]]]]:
    """Return list of (image_name, [(value, conf), ...])"""
    extractor = DocxImageExtractor()
    images = extractor.extract_images(docx_path)
    results: list[tuple[str, list[tuple[str, float]]]] = []

    for img_meta in images:
        try:
            img = Image.open(io.BytesIO(img_meta.data)).convert("RGB")
        except Exception:
            continue
        crop = crop_bottom_axis(img, 0.18)
        prep = preprocess_for_ocr(crop)

        # Try PaddleOCR first per AGENTS.md
        picked: list[tuple[str, float]] = []
        w, _ = prep.size
        p_tokens = run_paddle_tokens(prep)
        if p_tokens:
            p_roi = [t for t in p_tokens if t.left >= int(w * 0.35)]
            p_rows = cluster_by_row(select_numeric_tokens(p_roi))
            p_picked = pick_best_per_row(p_rows)
            # Enforce confidence threshold; if too low or empty — fallback
            if p_picked and all(conf >= (CONF_THR * 100 if conf > 1 else CONF_THR) for _, conf in p_picked):
                picked = p_picked

        if not picked:
            # Fallback to Tesseract if Paddle is unavailable/insufficient
            t_tokens = run_tesseract_tsv(prep)
            t_roi = [t for t in t_tokens if t.left >= int(w * 0.35)]
            t_rows = cluster_by_row(select_numeric_tokens(t_roi))
            picked = pick_best_per_row(t_rows)

        if not picked:
            # CV-based heuristic
            cv_tokens = extract_badge_values_cv2(crop)
            cv_rows = cluster_by_row(select_numeric_tokens(cv_tokens))
            picked = pick_best_per_row(cv_rows)

        if not picked:
            # Optional Gemini fallback (single image)
            import asyncio

            values = asyncio.run(gemini_extract_values(extractor.convert_to_png(img_meta.data), settings))
            if values:
                picked = [(v, 0.0) for v in values]

        if picked:
            results.append((img_meta.filename, picked))

    return results


def to_markdown(docx_path: Path, charts: list[tuple[str, list[tuple[str, float]]]]) -> str:
    lines: list[str] = []
    lines.append(f"## {docx_path.name}")
    if not charts:
        lines.append("- No bar-chart-like images found")
        lines.append("")
        return "\n".join(lines)
    lines.append(f"- Extracted {len(charts)} chart image(s)")
    lines.append("")
    for idx, (img_name, values) in enumerate(charts, start=1):
        lines.append(f"### Chart {idx} — {img_name}")
        lines.append("| Row | Value | OCR conf |")
        lines.append("| --- | --- | --- |")
        for i, (val, conf) in enumerate(values, start=1):
            lines.append(f"| {i} | {val} | {conf:.0f} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract numeric values from DOCX bar-chart images (Docker CLI)")
    ap.add_argument("docx_files", nargs="+", type=Path, help="Path(s) to .docx files (inside container)")
    ap.add_argument("-o", "--output", type=Path, required=True, help="Output Markdown path")
    args = ap.parse_args()

    settings = Settings()
    all_lines: list[str] = []
    for p in args.docx_files:
        charts = process_docx(p, settings)
        all_lines.append(to_markdown(p, charts))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(all_lines), encoding="utf-8")
    print(f"Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
