#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1. Render 4 HTML diagram files → PNG using Playwright (headless Chromium)
2. Insert PNGs into DDC_Books_Report_EN.docx at the correct figure positions
3. Save as DDC_Books_Report_EN_Final.docx

Run: python insert_diagrams.py
"""
import os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
DIAGRAMS_DIR = os.path.join(ROOT, "diagrams")
WORD_IN  = os.path.join(ROOT, "DDC_Books_Report_EN.docx")
WORD_OUT = os.path.join(ROOT, "DDC_Books_Report_EN_Final.docx")

# ─── Install dependencies ─────────────────────────────────────────────────────
def pip(*args):
    subprocess.check_call([sys.executable, "-m", "pip", "install", *args, "--quiet"])

print("[1/5] Installing dependencies...")
pip("playwright", "python-docx")

# Install Chromium browser
print("[2/5] Installing Chromium for Playwright...")
subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

# ─── Render HTML → PNG ───────────────────────────────────────────────────────
from playwright.sync_api import sync_playwright

HTML_FILES = [
    ("fig1_use_case.html",            "fig1_use_case.png",          1080, 980),
    ("fig2_sequence_shopping.html",   "fig2_shopping_sequence.png", 1060, 800),
    ("fig3_sequence_ai_rag.html",     "fig3_ai_rag_sequence.png",   1110, 900),
    ("fig4_project_structure.html",   "fig4_project_structure.png", 820,  820),
]

png_paths = {}

print("[3/5] Rendering HTML diagrams to PNG...")
with sync_playwright() as p:
    browser = p.chromium.launch()
    for html_name, png_name, vw, vh in HTML_FILES:
        html_path = os.path.join(DIAGRAMS_DIR, html_name)
        png_path  = os.path.join(DIAGRAMS_DIR, png_name)

        page = browser.new_page(viewport={"width": vw, "height": vh})
        page.goto(f"file:///{html_path.replace(os.sep, '/')}")
        page.wait_for_timeout(800)

        # Screenshot full page (white bg)
        page.screenshot(path=png_path, full_page=True)
        page.close()

        key = html_name.replace(".html", "")
        png_paths[key] = png_path
        print(f"   OK: {png_name}")

    browser.close()

# ─── Insert images into Word ──────────────────────────────────────────────────
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

print("[4/5] Inserting diagrams into Word document...")

doc = Document(WORD_IN)

# Map: which figure number → which PNG file key
FIG_PNG_MAP = {
    "Figure 1:": "fig1_use_case",
    "Figure 2:": "fig2_sequence_shopping",
    "Figure 3:": "fig3_sequence_ai_rag",
    "Figure 4:": "fig4_project_structure",
}

# Width for each figure in the Word document
FIG_WIDTH = {
    "Figure 1:": Cm(14.0),
    "Figure 2:": Cm(14.5),
    "Figure 3:": Cm(14.5),
    "Figure 4:": Cm(10.0),
}

def make_img_para(doc_obj, img_path, width_cm, caption_text):
    """
    Insert: [blank line] [centered image] [caption] into the document XML
    by appending to doc_obj.paragraphs. Returns list of new paragraph elements.
    """
    new_paras = []

    # 1. Blank line before image
    p_blank = doc_obj.add_paragraph()
    pf = p_blank.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after  = Pt(0)
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(6)
    new_paras.append(p_blank)

    # 2. Image paragraph (centered)
    p_img = doc_obj.add_paragraph()
    p_img.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(0)
    p_img.paragraph_format.space_after  = Pt(4)
    p_img.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    p_img.paragraph_format.line_spacing = Pt(17)
    run = p_img.add_run()
    run.add_picture(img_path, width=width_cm)
    new_paras.append(p_img)

    # 3. Caption paragraph (centered, italic)
    p_cap = doc_obj.add_paragraph()
    p_cap.paragraph_format.alignment    = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(2)
    p_cap.paragraph_format.space_after  = Pt(6)
    p_cap.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    p_cap.paragraph_format.line_spacing = Pt(17)
    run2 = p_cap.add_run(caption_text)
    run2.font.name    = 'Times New Roman'
    run2.font.size    = Pt(11)
    run2.italic       = True
    # Fix font for cross-platform
    r = run2._r
    rPr = r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')
    for old in rPr.findall(qn('w:rFonts')):
        rPr.remove(old)
    rPr.insert(0, rFonts)
    new_paras.append(p_cap)

    return new_paras


# We need to rebuild the document:
# Strategy: iterate paragraphs, collect them. When we find a caption paragraph
# ("Figure 1:", "Figure 2:", etc.) followed by the *** CHEN ANH *** note,
# replace those 2 paragraphs with [image + caption].

from docx.oxml.ns import nsmap

# Get the body element
body = doc.element.body

# Build list of paragraph elements with their text
paras = list(doc.paragraphs)

# Find pairs: (caption_para_index, note_para_index) for figs 1-4
to_replace = {}   # caption_para_index → (fig_key, caption_text, note_para_index)

for i, para in enumerate(paras):
    txt = para.text.strip()
    for fig_prefix in FIG_PNG_MAP:
        if txt.startswith(fig_prefix) and i + 1 < len(paras):
            next_txt = paras[i+1].text.strip()
            if "CHEN ANH" in next_txt:
                to_replace[i] = (FIG_PNG_MAP[fig_prefix], txt, i+1)
                break

print(f"   Found {len(to_replace)} figure placeholder(s) to replace: {list(to_replace.keys())}")

if not to_replace:
    print("   WARNING: No placeholders found - saving document as-is.")
    doc.save(WORD_OUT)
else:
    # We rebuild by creating a new document that mirrors the old one
    # but swaps the placeholder pairs with actual images.
    # python-docx doesn't support in-place paragraph replacement cleanly,
    # so we use XML manipulation.

    skip_indices = set()
    for cap_i, (fig_key, cap_text, note_i) in to_replace.items():
        skip_indices.add(cap_i)    # skip old caption paragraph
        skip_indices.add(note_i)   # skip note paragraph

    # We insert image paragraphs by manipulating XML directly.
    # Approach: for each caption paragraph element, insert image XML before it,
    # then remove caption + note paragraphs.

    from lxml import etree

    def build_img_xml(img_path, width_cm, cap_text, doc_obj):
        """Build XML elements for: blank + image + caption paragraphs."""
        elements = []

        # --- Image paragraph ---
        # Create a new in-memory document to generate the image run XML
        tmp_doc = Document()
        tmp_sec = tmp_doc.sections[0]

        p_img = tmp_doc.add_paragraph()
        p_img.paragraph_format.alignment    = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(4)
        p_img.paragraph_format.space_after  = Pt(4)
        p_img.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        p_img.paragraph_format.line_spacing  = Pt(17)
        run = p_img.add_run()
        run.add_picture(img_path, width=width_cm)

        # Copy the paragraph XML element (deep copy)
        img_el = p_img._element
        elements.append(img_el)

        # --- Caption paragraph ---
        p_cap = tmp_doc.add_paragraph()
        p_cap.paragraph_format.alignment    = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(2)
        p_cap.paragraph_format.space_after  = Pt(8)
        p_cap.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        p_cap.paragraph_format.line_spacing  = Pt(17)
        run2 = p_cap.add_run(cap_text)
        run2.font.name  = 'Times New Roman'
        run2.font.size  = Pt(11)
        run2.italic     = True
        r = run2._r
        rPr = r.get_or_add_rPr()
        rFonts = OxmlElement('w:rFonts')
        rFonts.set(qn('w:ascii'), 'Times New Roman')
        rFonts.set(qn('w:hAnsi'), 'Times New Roman')
        for old in rPr.findall(qn('w:rFonts')):
            rPr.remove(old)
        rPr.insert(0, rFonts)
        cap_el = p_cap._element
        elements.append(cap_el)

        return elements

    # For each figure to replace, insert image XML before the caption para,
    # then remove caption + note paras from the body.
    from copy import deepcopy

    # We need to work with the actual XML body
    body_el = doc.element.body
    all_p_els = body_el.findall(f'.//{{{body_el.nsmap.get("w", "http://schemas.openxmlformats.org/wordprocessingml/2006/main")}}}p')

    # Actually, paragraphs are direct children of body (and sectPr at end)
    W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

    # Get direct paragraph children
    direct_children = [child for child in body_el]

    # Build a mapping: paragraph object → body child element
    # paras[i]._element should be a direct child of body
    for cap_idx, (fig_key, cap_text, note_idx) in sorted(to_replace.items(), reverse=True):
        cap_para  = paras[cap_idx]
        note_para = paras[note_idx]
        cap_el    = cap_para._element
        note_el   = note_para._element

        # Build new image + caption XML elements
        img_path   = png_paths[fig_key]
        width_cm   = FIG_WIDTH[list(FIG_PNG_MAP.keys())[list(FIG_PNG_MAP.values()).index(fig_key)]]

        new_els = build_img_xml(img_path, width_cm, cap_text, doc)

        # Insert new elements before cap_el
        parent = cap_el.getparent()
        cap_pos = list(parent).index(cap_el)
        for i, el in enumerate(new_els):
            parent.insert(cap_pos + i, deepcopy(el))

        # Remove old caption + note paragraphs
        parent.remove(cap_el)
        if note_el.getparent() is not None:
            note_el.getparent().remove(note_el)

        print(f"   Replaced Figure placeholder: {cap_text[:50]}")

    doc.save(WORD_OUT)

print(f"[5/5] Done! Saved: {WORD_OUT}")
print("")
print("File Word da duoc cap nhat voi 4 diagram (Fig 1-4).")
print("Cac figure con lai (Fig 5-14) van giu chu thich de ban tu chup anh.")
