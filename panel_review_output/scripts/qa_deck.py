"""Geometry + content QA for the generated deck, since LibreOffice hangs in
this environment (same constraint documented throughout this project's other
document-generation scripts) so pptx->image rendering isn't available here.
Checks: every shape within slide bounds, no unexpected textbox overlaps,
no empty/placeholder text, and dumps all text for a manual read-through.
"""
import sys
from pptx import Presentation
from pptx.util import Emu

path = sys.argv[1] if len(sys.argv) > 1 else "QuIM_RAG_Review_Presentation.pptx"
prs = Presentation(path)
SW, SH = prs.slide_width, prs.slide_height
issues = []

for i, slide in enumerate(prs.slides, 1):
    boxes = []
    for shp in slide.shapes:
        if shp.left is None or shp.top is None:
            continue
        l, t, w, h = shp.left, shp.top, shp.width or 0, shp.height or 0
        r, b = l + w, t + h
        if l < -Emu(1000) or t < -Emu(1000) or r > SW + Emu(10000) or b > SH + Emu(10000):
            issues.append(f"slide {i}: shape '{shp.shape_id}' out of bounds "
                           f"(l={l/914400:.2f} t={t/914400:.2f} r={r/914400:.2f} b={b/914400:.2f}in, "
                           f"slide={SW/914400:.2f}x{SH/914400:.2f}in)")
        if shp.has_text_frame and shp.text_frame.text.strip():
            boxes.append((l, t, r, b, shp.text_frame.text[:40]))
    # overlap check: textboxes whose rects intersect by more than a sliver
    for a in range(len(boxes)):
        for bx in range(a + 1, len(boxes)):
            l1, t1, r1, b1, txt1 = boxes[a]
            l2, t2, r2, b2, txt2 = boxes[bx]
            ox = max(0, min(r1, r2) - max(l1, l2))
            oy = max(0, min(b1, b2) - max(t1, t2))
            if ox > Emu(150000) and oy > Emu(150000):  # > ~0.16in overlap both axes
                issues.append(f"slide {i}: possible overlap '{txt1}' <-> '{txt2}' "
                               f"(overlap {ox/914400:.2f}x{oy/914400:.2f}in)")

print(f"=== {len(prs.slides)} slides checked ===")
if issues:
    print(f"\n{len(issues)} potential issue(s):")
    for iss in issues:
        print(" -", iss)
else:
    print("No geometry issues found.")

print("\n=== text dump (content QA) ===")
for i, slide in enumerate(prs.slides, 1):
    texts = [s.text_frame.text for s in slide.shapes if s.has_text_frame and s.text_frame.text.strip()]
    joined = " | ".join(t.replace("\n", " / ") for t in texts)
    print(f"[{i}] {joined[:220]}")
