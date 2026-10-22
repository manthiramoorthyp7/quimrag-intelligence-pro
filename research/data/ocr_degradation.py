"""Synthetic, controlled OCR degradation conditions for Gap B. Each function
takes a PIL image and returns a degraded PIL image. These are SYNTHETIC
degradations applied to real document text (rendered from real, human-
verified OHR-Bench ground truth) -- not genuine scanner/camera noise. That
distinction is kept explicit throughout research/OCR_ROBUSTNESS_STUDY.md;
synthetic corruption demonstrates a controlled, repeatable dose-response
relationship, not proof of real-world robustness.
"""
import io

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

SEVERITIES = ["mild", "moderate", "severe"]

_PARAMS = {
    "mild":     dict(blur=0.6, noise_std=6,  jpeg_quality=70, rotate_deg=0.6, contrast=0.9, scale=0.9),
    "moderate": dict(blur=1.2, noise_std=14, jpeg_quality=45, rotate_deg=1.8, contrast=0.72, scale=0.75),
    "severe":   dict(blur=2.0, noise_std=26, jpeg_quality=25, rotate_deg=3.5, contrast=0.55, scale=0.55),
}


def degrade(im: Image.Image, severity: str, seed: int = 0) -> Image.Image:
    """Applies a composite of blur, resolution reduction, skew/rotation,
    JPEG compression artifacts, noise and reduced contrast, scaled by
    severity -- combining several of the conditions OHR-Bench itself studies
    (formatting noise, semantic/visual noise) into one graduated dose."""
    if severity not in _PARAMS:
        raise ValueError(f"Unknown severity: {severity}")
    p = _PARAMS[severity]
    rng = np.random.default_rng(seed)
    out = im.convert("L")

    # 1. resolution reduction (downscale then upscale back)
    w, h = out.size
    out = out.resize((max(1, int(w * p["scale"])), max(1, int(h * p["scale"]))), Image.BILINEAR)
    out = out.resize((w, h), Image.BILINEAR)

    # 2. skew/rotation
    out = out.rotate(p["rotate_deg"], expand=False, fillcolor=255)

    # 3. gaussian blur
    out = out.filter(ImageFilter.GaussianBlur(radius=p["blur"]))

    # 4. contrast reduction
    out = ImageEnhance.Contrast(out).enhance(p["contrast"])

    # 5. additive noise
    arr = np.asarray(out, dtype=np.float32)
    noise = rng.normal(0, p["noise_std"], arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    out = Image.fromarray(arr)

    # 6. JPEG compression artifacts
    buf = io.BytesIO()
    out.convert("RGB").save(buf, format="JPEG", quality=p["jpeg_quality"])
    buf.seek(0)
    out = Image.open(buf).convert("L")
    return out


def render_text_page(text: str, width=1240, height=1754, fontsize=15) -> Image.Image:
    """Renders text onto a clean page image via a temporary PDF page (so we
    get real font rasterization, not a PIL-drawn approximation), matching the
    same rendering path used by the real OCR pipeline in quimrag/core.py.

    PyMuPDF's insert_textbox renders NOTHING (a fully blank page, not a
    truncated one) when the text overflows the box at the given fontsize --
    confirmed by direct pixel inspection during this study's development, not
    assumed. So this shrinks fontsize until the text fits (non-negative
    return value) before rendering, with a floor to avoid illegibly small text."""
    import pymupdf
    rect = pymupdf.Rect(36, 36, width / 2 - 36, height / 2 - 36)
    size = fontsize
    doc = page = None
    while size >= 6:
        doc = pymupdf.open()
        page = doc.new_page(width=width / 2, height=height / 2)
        rc = page.insert_textbox(rect, text, fontsize=size, fontname="helv")
        if rc >= 0:
            break
        doc.close()
        size -= 1
    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
    im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    doc.close()
    return im
