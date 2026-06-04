#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate 4 professional draw.io XML diagram files for DDC Books report.
Run: python generate_drawio.py
Output: diagrams/*.drawio  ->  import to https://app.diagrams.net
"""
import os, textwrap

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagrams")
os.makedirs(OUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
_id = 1
def nid():
    global _id; _id += 1; return str(_id)

def reset():
    global _id; _id = 1

def wrap(inner, pw=1169, ph=827):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" '
        f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        f'pageWidth="{pw}" pageHeight="{ph}" math="0" shadow="0">\n'
        '  <root>\n'
        '    <mxCell id="0"/>\n'
        '    <mxCell id="1" parent="0"/>\n'
        + inner +
        '  </root>\n</mxGraphModel>\n'
    )

def vertex(id, label, style, x, y, w, h, parent="1"):
    label = label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'    <mxCell id="{id}" value="{label}" style="{style}" '
        f'vertex="1" parent="{parent}">\n'
        f'      <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>\n'
        f'    </mxCell>\n'
    )

def edge(id, label, style, src, tgt, parent="1", points=None):
    label = label.replace("&", "&amp;")
    geo = '      <mxGeometry relative="1" as="geometry"'
    if points:
        pts = "".join(f'<mxPoint x="{p[0]}" y="{p[1]}" as="sourcePoint"/>' for p in points)
        geo += f'>{pts}</mxGeometry>\n'
    else:
        geo += '/>\n'
    return (
        f'    <mxCell id="{id}" value="{label}" style="{style}" '
        f'edge="1" source="{src}" target="{tgt}" parent="{parent}">\n'
        + geo +
        f'    </mxCell>\n'
    )

# Styles
ACTOR   = "shape=mxgraph.uml.actor;whiteSpace=wrap;html=1;fontSize=11;fontStyle=1;"
UC      = "ellipse;whiteSpace=wrap;html=1;fontSize=10;"
BOUND   = "swimlane;startSize=28;fontStyle=1;fontSize=12;"
ASSOC   = "endArrow=none;html=1;"
EXTEND  = "endArrow=open;endFill=0;dashed=1;html=1;fontSize=9;"
INCLUDE = "endArrow=open;endFill=0;dashed=1;html=1;fontSize=9;startArrow=none;"
NOTE    = "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontSize=9;fontStyle=2;"


# ═══════════════════════════════════════════════════════════════════════════
# FIG 1 – USE CASE DIAGRAM
# ═══════════════════════════════════════════════════════════════════════════
def fig1():
    reset()
    cells = ""

    # ── System boundary ──────────────────────────────────────────────────
    B = nid()
    cells += vertex(B, "DDC Books Web Application",
                    BOUND + "fillColor=#f5f5f5;strokeColor=#666;fontColor=#333;",
                    160, 20, 740, 870)

    # ── Actors ───────────────────────────────────────────────────────────
    A_guest = nid()
    cells += vertex(A_guest, "Guest\n(Anonymous)",
                    ACTOR + "fillColor=#dae8fc;strokeColor=#6c8ebf;",
                    30, 120, 60, 90)

    A_cust = nid()
    cells += vertex(A_cust, "Customer\n(Authenticated)",
                    ACTOR + "fillColor=#d5e8d4;strokeColor=#82b366;",
                    30, 560, 60, 90)

    A_staff = nid()
    cells += vertex(A_staff, "Staff\n(Employee)",
                    ACTOR + "fillColor=#e1d5e7;strokeColor=#9673a6;",
                    970, 120, 60, 90)

    A_sys = nid()
    cells += vertex(A_sys, "&lt;&lt;System&gt;&gt;\nClaude AI",
                    ACTOR + "fillColor=#ffe6cc;strokeColor=#d6b656;",
                    970, 600, 60, 90)

    # ── Guest Use Cases ──────────────────────────────────────────────────
    uc_style = lambda c, s: (f"ellipse;whiteSpace=wrap;html=1;fontSize=10;"
                              f"fillColor={c};strokeColor={s};")

    uc1 = nid(); cells += vertex(uc1, "Browse\nBook Catalog",      uc_style("#dae8fc","#6c8ebf"), 195, 80,  140, 50)
    uc2 = nid(); cells += vertex(uc2, "Search &amp; Filter\nBooks", uc_style("#dae8fc","#6c8ebf"), 195, 145, 140, 50)
    uc3 = nid(); cells += vertex(uc3, "View Book\nDetail",          uc_style("#dae8fc","#6c8ebf"), 195, 210, 140, 50)
    uc4 = nid(); cells += vertex(uc4, "Add to Cart",                uc_style("#dae8fc","#6c8ebf"), 195, 275, 140, 50)
    uc5 = nid(); cells += vertex(uc5, "Checkout /\nPlace Order",    uc_style("#dae8fc","#6c8ebf"), 195, 340, 140, 50)
    uc6 = nid(); cells += vertex(uc6, "Track Order\n(Guest Mode)",  uc_style("#dae8fc","#6c8ebf"), 195, 405, 140, 50)

    # Guest associations
    for uc in [uc1,uc2,uc3,uc4,uc5,uc6]:
        cells += edge(nid(), "", ASSOC, A_guest, uc)

    # ── Customer-only Use Cases ──────────────────────────────────────────
    uc7  = nid(); cells += vertex(uc7,  "Register / Login",            uc_style("#d5e8d4","#82b366"), 195, 560, 140, 50)
    uc8  = nid(); cells += vertex(uc8,  "Manage Profile\n&amp; Avatar", uc_style("#d5e8d4","#82b366"), 195, 625, 140, 50)
    uc9  = nid(); cells += vertex(uc9,  "Add to\nWishlist",            uc_style("#d5e8d4","#82b366"), 195, 690, 140, 50)
    uc10 = nid(); cells += vertex(uc10, "View Order\nHistory",         uc_style("#d5e8d4","#82b366"), 195, 755, 140, 50)
    uc11 = nid(); cells += vertex(uc11, "Apply Coupon",                uc_style("#d5e8d4","#82b366"), 195, 820, 140, 50)

    for uc in [uc7,uc8,uc9,uc10,uc11]:
        cells += edge(nid(), "", ASSOC, A_cust, uc)

    # ── Shared: AI Chatbot UCs (center column) ───────────────────────────
    uc12 = nid(); cells += vertex(uc12, "Chat with\nAI Chatbot",        uc_style("#fff2cc","#d6b656"), 420, 560, 150, 50)
    uc13 = nid(); cells += vertex(uc13, "Get Personalized\nRecommendations", uc_style("#fff2cc","#d6b656"), 420, 625, 150, 50)
    uc14 = nid(); cells += vertex(uc14, "Track Order\nvia AI",          uc_style("#fff2cc","#d6b656"), 420, 690, 150, 50)
    uc15 = nid(); cells += vertex(uc15, "Set Price\nAlert",             uc_style("#fff2cc","#d6b656"), 420, 755, 150, 50)
    uc16 = nid(); cells += vertex(uc16, "Rate AI\nResponse",            uc_style("#fff2cc","#d6b656"), 420, 820, 150, 50)

    for uc in [uc12,uc13,uc14,uc15,uc16]:
        cells += edge(nid(), "", ASSOC, A_cust, uc)
        cells += edge(nid(), "", ASSOC, A_sys, uc)

    # Real-time chat shared
    uc17 = nid(); cells += vertex(uc17, "Real-time Chat\nwith Staff",   uc_style("#d5e8d4","#82b366"), 420, 480, 150, 50)
    cells += edge(nid(), "", ASSOC, A_cust, uc17)
    cells += edge(nid(), "", ASSOC, A_staff, uc17)

    # ── Staff Use Cases ──────────────────────────────────────────────────
    uc18 = nid(); cells += vertex(uc18, "View Staff\nDashboard",        uc_style("#e1d5e7","#9673a6"), 640, 80,  150, 50)
    uc19 = nid(); cells += vertex(uc19, "Manage Orders\n(Confirm/Ship/Cancel)", uc_style("#e1d5e7","#9673a6"), 640, 145, 150, 50)
    uc20 = nid(); cells += vertex(uc20, "Manage Books\n(CRUD)",         uc_style("#e1d5e7","#9673a6"), 640, 210, 150, 50)
    uc21 = nid(); cells += vertex(uc21, "Configure\nFlash Sale",        uc_style("#e1d5e7","#9673a6"), 640, 275, 150, 50)
    uc22 = nid(); cells += vertex(uc22, "Manage\nCoupons",              uc_style("#e1d5e7","#9673a6"), 640, 340, 150, 50)
    uc23 = nid(); cells += vertex(uc23, "View Revenue\nDashboard",      uc_style("#e1d5e7","#9673a6"), 640, 405, 150, 50)

    for uc in [uc18,uc19,uc20,uc21,uc22,uc23]:
        cells += edge(nid(), "", ASSOC, A_staff, uc)

    # ── extends arrow: Customer generalizes Guest ─────────────────────────
    cells += edge(nid(), "&lt;&lt;extends&gt;&gt;",
                  "endArrow=block;endFill=0;dashed=1;html=1;fontSize=9;exitX=0.5;exitY=0;",
                  A_cust, A_guest)

    # ── Legend ───────────────────────────────────────────────────────────
    cells += vertex(nid(), "Guest UC",    uc_style("#dae8fc","#6c8ebf") + "fontSize=9;", 175, 900, 100, 28)
    cells += vertex(nid(), "Customer UC", uc_style("#d5e8d4","#82b366") + "fontSize=9;", 285, 900, 100, 28)
    cells += vertex(nid(), "AI Chatbot UC",uc_style("#fff2cc","#d6b656") + "fontSize=9;",395, 900, 110, 28)
    cells += vertex(nid(), "Staff UC",    uc_style("#e1d5e7","#9673a6") + "fontSize=9;", 515, 900, 100, 28)

    with open(os.path.join(OUT_DIR, "fig1_use_case.drawio"), "w", encoding="utf-8") as f:
        f.write(wrap(cells, pw=1070, ph=960))
    print("[OK] fig1_use_case.drawio")


# ═══════════════════════════════════════════════════════════════════════════
# FIG 2 – SEQUENCE DIAGRAM: SHOPPING WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════
def fig2():
    reset()
    cells = ""

    # Participant header style
    PH = "rounded=1;whiteSpace=wrap;html=1;arcSize=50;fontSize=10;fontStyle=1;"
    # Lifeline
    LL = "endArrow=none;dashed=1;strokeColor=#999;strokeWidth=1;html=1;"
    # Activation box
    ACT = "html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=9;"
    # Message solid
    MSG = "endArrow=block;endFill=1;html=1;fontSize=9;"
    # Return dashed
    RET = "endArrow=open;endFill=0;dashed=1;html=1;fontSize=9;"
    # Note box
    NB  = "shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;fontSize=9;fillColor=#fffacd;strokeColor=#aaa;"

    # X positions for each participant
    xs = {"user": 80, "cart": 260, "session": 440, "orm": 620, "db": 800}
    pw = {"user":"#dae8fc","cart":"#d5e8d4","session":"#fff2cc","orm":"#e1d5e7","db":"#ffe6cc"}
    pc = {"user":"#6c8ebf","cart":"#82b366","session":"#d6b656","orm":"#9673a6","db":"#d79b00"}

    # Headers
    ids = {}
    labels = {"user":"User / Browser","cart":"Django\ncart.py","session":"Session\nStore","orm":"Django ORM\n(transaction)","db":"SQLite\nDatabase"}
    for k in ["user","cart","session","orm","db"]:
        i = nid(); ids[k] = i
        cells += vertex(i, labels[k], PH+f"fillColor={pw[k]};strokeColor={pc[k]};", xs[k]-55, 20, 110, 46)

    # Lifelines (y from 66 to 820)
    for k in ["user","cart","session","orm","db"]:
        cells += edge(nid(), "", LL+f"strokeColor={pc[k]};",
                      ids[k], ids[k])   # self-loop trick doesn't work; use vertex line instead

    # Use vertex rectangles as lifelines
    LL2 = "html=1;fillColor=none;strokeColor=#bbb;dashed=1;strokeWidth=1;"
    for k in ["user","cart","session","orm","db"]:
        cells += vertex(nid(), "", LL2, xs[k]-1, 66, 2, 760)

    # Activation boxes
    cells += vertex(nid(), "", ACT+"fillColor=#dae8fc;", xs["user"]-5,   80, 10, 720)
    cells += vertex(nid(), "", ACT+"fillColor=#d5e8d4;", xs["cart"]-5,   100, 10, 690)
    cells += vertex(nid(), "", ACT+"fillColor=#fff2cc;", xs["session"]-5, 160, 10, 200)
    cells += vertex(nid(), "", ACT+"fillColor=#e1d5e7;", xs["orm"]-5,    470, 10, 280)
    cells += vertex(nid(), "", ACT+"fillColor=#ffe6cc;", xs["db"]-5,     500, 10, 250)

    # ── Step labels (band backgrounds) ──────────────────────────────────
    def band(label, y, color="#f0f4ff"):
        cells = vertex(nid(), label,
                       f"text;html=1;strokeColor=none;fillColor={color};align=left;"
                       f"verticalAlign=middle;fontSize=9;fontStyle=2;",
                       10, y, 850, 18)
        return cells

    # ── Messages ─────────────────────────────────────────────────────────
    def msg(src, tgt, label, y, dashed=False, ret=False):
        s = RET if (dashed or ret) else MSG
        cells = (
            f'    <mxCell id="{nid()}" value="{label}" style="{s}" '
            f'edge="1" parent="1">\n'
            f'      <mxGeometry relative="1" as="geometry">\n'
            f'        <mxPoint x="{xs[src]}" y="{y}" as="sourcePoint"/>\n'
            f'        <mxPoint x="{xs[tgt]}" y="{y}" as="targetPoint"/>\n'
            f'      </mxGeometry>\n'
            f'    </mxCell>\n'
        )
        return cells

    cells += band("1. Browse Book Catalog", 88, "#eff6ff")
    cells += msg("user","cart","GET / (q, category, filter)", 104)
    cells += msg("cart","user","render(home.html, books)", 122, ret=True)

    cells += band("2. Add to Cart", 136, "#f0fdf4")
    cells += msg("user","cart","POST /cart/add/{book_id}/", 152)
    cells += msg("cart","session","check book.stock > 0", 168)
    cells += msg("session","cart","stock ok", 184, ret=True)
    cells += msg("cart","session","session['cart'][book_id] += qty", 200)
    cells += msg("cart","user","JsonResponse {status, total_items}", 218, ret=True)

    cells += band("3. View Cart", 234, "#fffbeb")
    cells += msg("user","cart","GET /cart/", 250)
    cells += msg("cart","session","read session['cart']", 266)
    cells += msg("session","cart","cart dict {book_id: qty}", 282, ret=True)
    cells += msg("cart","user","render(cart.html, items, total)", 298, ret=True)

    cells += band("4. GET Checkout Form", 314, "#fdf4ff")
    cells += msg("user","cart","GET /checkout/", 330)
    cells += msg("cart","user","render(checkout.html, items, coupons)", 346, ret=True)

    cells += band("5. Validate Coupon (AJAX)", 362, "#ecfdf5")
    cells += msg("user","cart","POST /cart/coupon/validate/ {code, total}", 378)
    cells += msg("cart","user","JsonResponse {valid, discount_percent, new_total}", 394, ret=True)

    # Atomic transaction box
    cells += vertex(nid(), "transaction.atomic()",
                    "swimlane;startSize=22;dashed=1;fillColor=#f9f0ff;strokeColor=#9673a6;fontSize=9;",
                    xs["cart"]+10, 420, xs["db"]-xs["cart"]+50, 290)

    cells += band("6. POST Checkout — Atomic Transaction", 410, "#fff1f2")
    cells += msg("user","cart","POST /checkout/ {name, phone, address, coupon}", 428)
    cells += msg("cart","orm","Book.filter(stock>=qty).update(stock-=qty, sold+=qty)", 448)
    cells += msg("orm","db","UPDATE books SET stock, sold_count", 468)
    cells += msg("db","orm","1 row updated", 486, ret=True)
    cells += msg("orm","db","INSERT INTO orders (user, total, coupon...)", 504)
    cells += msg("db","orm","order.id = N", 522, ret=True)
    cells += msg("orm","db","INSERT INTO order_items (order, book, qty, price)", 540)
    cells += msg("db","orm","items created", 558, ret=True)
    cells += msg("orm","db","UPDATE coupon SET used_count += 1", 576)
    cells += msg("db","orm","ok", 594, ret=True)
    cells += msg("cart","session","session['cart'] = {}", 614)

    cells += band("7. Order Success", 636, "#eff6ff")
    cells += msg("cart","user","redirect(/orders/success/N/)", 654, ret=True)
    cells += msg("user","cart","GET /orders/success/N/", 672)
    cells += msg("cart","user","render(order_success.html)", 690, ret=True)

    with open(os.path.join(OUT_DIR, "fig2_shopping_sequence.drawio"), "w", encoding="utf-8") as f:
        f.write(wrap(cells, pw=900, ph=840))
    print("[OK] fig2_shopping_sequence.drawio")


# ═══════════════════════════════════════════════════════════════════════════
# FIG 3 – SEQUENCE DIAGRAM: AI CHATBOT RAG WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════
def fig3():
    reset()
    cells = ""

    PH  = "rounded=1;whiteSpace=wrap;html=1;arcSize=50;fontSize=10;fontStyle=1;"
    LL2 = "html=1;fillColor=none;strokeColor=#bbb;dashed=1;strokeWidth=1;"
    ACT = "html=1;strokeWidth=1;"
    MSG = "endArrow=block;endFill=1;html=1;fontSize=9;"
    RET = "endArrow=open;endFill=0;dashed=1;html=1;fontSize=9;"
    SSE = "endArrow=block;endFill=1;dashed=1;strokeColor=#dc2626;fontColor=#dc2626;html=1;fontSize=9;"

    xs = {"user":70, "ai":230, "db":420, "prompt":610, "claude":800, "botdb":990}
    labels = {
        "user":  "User\n/ Browser",
        "ai":    "Django\nai_chat.py",
        "db":    "SQLite DB\n(Context)",
        "prompt":"System Prompt\nBuilder",
        "claude":"Claude API\n(Anthropic)",
        "botdb": "BotChat DB\n(History)"
    }
    colors = {
        "user":  ("#dae8fc","#6c8ebf"),
        "ai":    ("#d5e8d4","#82b366"),
        "db":    ("#fff2cc","#d6b656"),
        "prompt":("#e1d5e7","#9673a6"),
        "claude":("#ffe6cc","#d79b00"),
        "botdb": ("#f8cecc","#b85450"),
    }

    ids = {}
    for k in xs:
        i = nid(); ids[k] = i
        cells += vertex(i, labels[k],
                        PH+f"fillColor={colors[k][0]};strokeColor={colors[k][1]};",
                        xs[k]-55, 10, 110, 46)

    for k in xs:
        cells += vertex(nid(), "", LL2, xs[k]-1, 56, 2, 870)

    # Activation boxes
    cells += vertex(nid(), "", ACT+f"fillColor={colors['user'][0]};strokeColor={colors['user'][1]};",  xs["user"]-5,   70, 10, 820)
    cells += vertex(nid(), "", ACT+f"fillColor={colors['ai'][0]};strokeColor={colors['ai'][1]};",      xs["ai"]-5,     88, 10, 790)
    cells += vertex(nid(), "", ACT+f"fillColor={colors['db'][0]};strokeColor={colors['db'][1]};",      xs["db"]-5,    180, 10, 370)
    cells += vertex(nid(), "", ACT+f"fillColor={colors['prompt'][0]};strokeColor={colors['prompt'][1]};",xs["prompt"]-5, 560, 10, 130)
    cells += vertex(nid(), "", ACT+f"fillColor={colors['claude'][0]};strokeColor={colors['claude'][1]};",xs["claude"]-5, 640, 10, 150)
    cells += vertex(nid(), "", ACT+f"fillColor={colors['botdb'][0]};strokeColor={colors['botdb'][1]};", xs["botdb"]-5,  88, 10, 400)

    def band(label, y, color="#f0f4ff"):
        return vertex(nid(), label,
                      f"text;html=1;strokeColor=none;fillColor={color};align=left;"
                      f"verticalAlign=middle;fontSize=9;fontStyle=2;",
                      5, y, 1060, 18)

    def msg(src, tgt, label, y, style=None):
        s = style or MSG
        return (
            f'    <mxCell id="{nid()}" value="{label}" style="{s}" edge="1" parent="1">\n'
            f'      <mxGeometry relative="1" as="geometry">\n'
            f'        <mxPoint x="{xs[src]}" y="{y}" as="sourcePoint"/>\n'
            f'        <mxPoint x="{xs[tgt]}" y="{y}" as="targetPoint"/>\n'
            f'      </mxGeometry>\n'
            f'    </mxCell>\n'
        )

    cells += band("Step 1 – User submits message", 78, "#eff6ff")
    cells += msg("user","ai","POST /chat/bot/stream/ { message }", 96)
    cells += vertex(nid(),"Rate limit check (1 req/s)",
                    "rounded=1;fillColor=#fff7ed;strokeColor=#fb923c;fontSize=9;",
                    xs["ai"]-60, 106, 120, 22)

    cells += band("Step 2 – Save user message", 136, "#f0fdf4")
    cells += msg("ai","botdb","BotChatMessage.create(role='user', content)", 152)
    cells += msg("botdb","ai","saved (msg_id)", 168, RET)

    cells += band("Step 3 – RAG Context Retrieval (5 queries)", 186, "#fffbeb")
    cells += msg("ai","db","Query recent orders + trackings (last 5)", 204)
    cells += msg("db","ai","orders_info string", 220, RET)
    cells += msg("ai","db","Query wishlist + category frequency", 238)
    cells += msg("db","ai","wishlist_info + fav_categories", 254, RET)
    cells += msg("ai","db","Query session recently_viewed books", 272)
    cells += msg("db","ai","viewed_info string", 288, RET)
    cells += msg("ai","db","RAG: keywords → Q(title|author|category icontains)", 306)
    cells += msg("db","ai","rag_books queryset (max 8 results)", 322, RET)
    cells += msg("ai","db","Query new arrivals (90d) + bestsellers (top 5)", 340)
    cells += msg("db","ai","new_books_info + bestseller_info", 356, RET)
    cells += msg("ai","botdb","Load conversation history (last 10 msgs)", 374)
    cells += msg("botdb","ai","messages_payload list", 392, RET)

    cells += band("Step 4 – Build System Prompt with all context", 412, "#fdf4ff")
    cells += msg("ai","prompt","build_system_prompt(store_info + all_context)", 430)
    cells += vertex(nid(),
                    "Includes: store info · orders · wishlist\nRAG results · new arrivals · bestsellers",
                    "rounded=1;fillColor=#faf5ff;strokeColor=#c084fc;fontSize=8;",
                    xs["prompt"]-75, 445, 150, 38)
    cells += msg("prompt","ai","system_prompt string", 496, RET)

    cells += band("Step 5 – Call Claude API (SSE Streaming)", 516, "#fff1f2")
    cells += msg("ai","claude","POST api.anthropic.com/v1/messages (stream=True, model=claude-sonnet-4)", 534)
    cells += msg("claude","user",'SSE: {"chunk": "Chao..."} token 1', 560, SSE)
    cells += msg("claude","user",'SSE: {"chunk": " ban ..."} token 2', 578, SSE)
    cells += vertex(nid(),"... streaming token by token ...",
                    "text;html=1;fillColor=none;strokeColor=none;fontSize=9;fontStyle=2;fontColor=#dc2626;",
                    xs["user"]+20, 593, 200, 16)
    cells += msg("claude","user",'SSE: {"chunk": "[SUGGESTIONS:...]"} final', 614, SSE)

    cells += band("Step 6 – Post-processing: Parse special tags", 638, "#f0fdf4")
    cells += vertex(nid(),
                    "[SUGGESTIONS] → extract chip list\n"
                    "[SET_PRICE_ALERT: book_id=X, target=Y] → PriceAlert.create()\n"
                    "[TRACK_GUEST_ORDER: order_id=Z] → session update",
                    "rounded=1;fillColor=#f0fdf4;strokeColor=#4ade80;fontSize=9;align=left;",
                    xs["ai"]-60, 656, 350, 52)

    cells += band("Step 7 – Save AI response + send metadata", 722, "#ecfdf5")
    cells += msg("ai","botdb","BotChatMessage.create(role='assistant', content)", 740)
    cells += msg("ai","user",'SSE: {"metadata": {books, orders, suggestions, alert}}', 760, RET)

    cells += band("Step 8 – Browser renders response + book cards + chips", 780, "#eff6ff")
    cells += vertex(nid(),"Typing animation complete\nBook cards + suggestion chips rendered",
                    "rounded=1;fillColor=#dbeafe;strokeColor=#2563eb;fontSize=9;",
                    xs["user"]-60, 796, 120, 38)

    with open(os.path.join(OUT_DIR, "fig3_ai_rag_sequence.drawio"), "w", encoding="utf-8") as f:
        f.write(wrap(cells, pw=1100, ph=920))
    print("[OK] fig3_ai_rag_sequence.drawio")


# ═══════════════════════════════════════════════════════════════════════════
# FIG 4 – SYSTEM ARCHITECTURE DIAGRAM
# ═══════════════════════════════════════════════════════════════════════════
def fig4():
    reset()
    cells = ""

    COMP  = "rounded=1;whiteSpace=wrap;html=1;fontSize=10;fontStyle=1;arcSize=10;"
    LAYER = "swimlane;startSize=28;fontStyle=1;fontSize=11;horizontal=1;"
    DB    = "shape=mxgraph.flowchart.database;whiteSpace=wrap;html=1;fontSize=10;fontStyle=1;"
    EXT   = "shape=mxgraph.aws4.traditional_server;whiteSpace=wrap;html=1;fontSize=10;"
    ARR   = "endArrow=block;endFill=1;html=1;fontSize=9;"
    DARR  = "endArrow=block;endFill=0;dashed=1;html=1;fontSize=9;"
    USER_S= "shape=mxgraph.uml.actor;whiteSpace=wrap;html=1;fontSize=10;fontStyle=1;"

    # ── Title ────────────────────────────────────────────────────────────
    cells += vertex(nid(), "DDC Books – System Architecture Diagram",
                    "text;html=1;strokeColor=none;fillColor=none;align=center;"
                    "fontStyle=1;fontSize=14;",
                    0, 10, 1000, 30)

    # ── User Actors ──────────────────────────────────────────────────────
    cells += vertex(nid(), "Guest\nUser",    USER_S+"fillColor=#dae8fc;strokeColor=#6c8ebf;", 20, 180, 60, 80)
    cells += vertex(nid(), "Customer",       USER_S+"fillColor=#d5e8d4;strokeColor=#82b366;", 20, 330, 60, 80)
    cells += vertex(nid(), "Staff /\nAdmin", USER_S+"fillColor=#e1d5e7;strokeColor=#9673a6;", 20, 480, 60, 80)

    # ── Browser Layer ─────────────────────────────────────────────────────
    BL = nid()
    cells += vertex(BL, "Browser Layer (HTML/CSS/JavaScript)",
                    LAYER+"fillColor=#fffde7;strokeColor=#f9a825;",
                    120, 100, 740, 570)

    cells += vertex(nid(), "Homepage\n& Catalog",      COMP+"fillColor=#fff9c4;strokeColor=#f9a825;", 140, 140, 110, 50)
    cells += vertex(nid(), "Cart &\nCheckout",          COMP+"fillColor=#fff9c4;strokeColor=#f9a825;", 265, 140, 110, 50)
    cells += vertex(nid(), "Order\nTracking",           COMP+"fillColor=#fff9c4;strokeColor=#f9a825;", 390, 140, 110, 50)
    cells += vertex(nid(), "User Profile\n& Auth",      COMP+"fillColor=#fff9c4;strokeColor=#f9a825;", 515, 140, 110, 50)
    cells += vertex(nid(), "Wishlist",                  COMP+"fillColor=#fff9c4;strokeColor=#f9a825;", 640, 140, 110, 50)

    cells += vertex(nid(), "AI Chatbot UI\n(SSE Stream + Book Cards)",
                    COMP+"fillColor=#ffe0b2;strokeColor=#ef6c00;",     140, 210, 200, 50)
    cells += vertex(nid(), "Real-time Chat UI\n(AJAX Polling)",
                    COMP+"fillColor=#ffe0b2;strokeColor=#ef6c00;",     360, 210, 180, 50)
    cells += vertex(nid(), "Staff Dashboard\n(Chart.js)",
                    COMP+"fillColor=#ffe0b2;strokeColor=#ef6c00;",     560, 210, 180, 50)

    # ── Django Backend Layer ──────────────────────────────────────────────
    DL = nid()
    cells += vertex(DL, "Django Backend (Python 3 / Django 6.0 – MVT Architecture)",
                    LAYER+"fillColor=#e8f5e9;strokeColor=#388e3c;",
                    120, 300, 740, 260)

    # Views modules
    cells += vertex(nid(), "home.py\nSearch & Filter", COMP+"fillColor=#c8e6c9;strokeColor=#388e3c;", 140, 340, 100, 50)
    cells += vertex(nid(), "cart.py\nAtomic Checkout", COMP+"fillColor=#c8e6c9;strokeColor=#388e3c;", 255, 340, 100, 50)
    cells += vertex(nid(), "orders.py\nTracking",       COMP+"fillColor=#c8e6c9;strokeColor=#388e3c;", 370, 340, 100, 50)
    cells += vertex(nid(), "auth.py\nRBAC",             COMP+"fillColor=#c8e6c9;strokeColor=#388e3c;", 485, 340, 100, 50)
    cells += vertex(nid(), "staff.py\nDashboard",       COMP+"fillColor=#c8e6c9;strokeColor=#388e3c;", 600, 340, 100, 50)
    cells += vertex(nid(), "wishlist.py\nFavorites",    COMP+"fillColor=#c8e6c9;strokeColor=#388e3c;", 715, 340, 100, 50)

    cells += vertex(nid(),
                    "ai_chat.py  –  AI Chatbot + RAG Pipeline\n"
                    "RAG Search · System Prompt Builder · SSE Stream · Tag Parser · PriceAlert",
                    COMP+"fillColor=#a5d6a7;strokeColor=#2e7d32;fontStyle=1;",
                    140, 408, 390, 50)

    cells += vertex(nid(),
                    "chat.py  –  Real-time Customer↔Staff Chat\n"
                    "AJAX Polling · Session Management · Unread Badges",
                    COMP+"fillColor=#a5d6a7;strokeColor=#2e7d32;",
                    545, 408, 270, 50)

    cells += vertex(nid(), "models.py  (12 Models: Book · Order · Chat · Bot · FlashSale · Coupon · PriceAlert)",
                    COMP+"fillColor=#81c784;strokeColor=#1b5e20;fontStyle=1;",
                    140, 474, 680, 36)

    # ── Data Layer ────────────────────────────────────────────────────────
    cells += vertex(nid(), "SQLite Database\n(Django ORM)",
                    DB+"fillColor=#fff3e0;strokeColor=#ef6c00;",
                    185, 590, 130, 70)

    cells += vertex(nid(), "Session Store\n(Django Sessions)",
                    DB+"fillColor=#f3e5f5;strokeColor=#7b1fa2;",
                    335, 590, 130, 70)

    cells += vertex(nid(), "Media Files\n(Pillow / images)",
                    DB+"fillColor=#e8eaf6;strokeColor=#3949ab;",
                    490, 590, 130, 70)

    # ── External Services ─────────────────────────────────────────────────
    cells += vertex(nid(), "Claude API\n(Anthropic)\nclaude-sonnet-4",
                    COMP+"fillColor=#ffcdd2;strokeColor=#c62828;fontStyle=1;",
                    900, 350, 140, 70)

    cells += vertex(nid(), ".env\nANTHROPIC_API_KEY\nSECRET_KEY\nDEBUG",
                    COMP+"fillColor=#f0f4ff;strokeColor=#4338ca;fontSize=9;",
                    900, 470, 140, 60)

    # ── Arrows ───────────────────────────────────────────────────────────
    # Users → Browser
    for y in [210, 360, 510]:
        cells += (
            f'    <mxCell id="{nid()}" value="" style="{ARR}" edge="1" parent="1">\n'
            f'      <mxGeometry relative="1" as="geometry">\n'
            f'        <mxPoint x="80" y="{y}" as="sourcePoint"/>\n'
            f'        <mxPoint x="120" y="{y}" as="targetPoint"/>\n'
            f'      </mxGeometry>\n'
            f'    </mxCell>\n'
        )
    # Django ↔ DB
    cells += (
        f'    <mxCell id="{nid()}" value="ORM Queries" style="{DARR}" edge="1" parent="1">\n'
        f'      <mxGeometry relative="1" as="geometry">\n'
        f'        <mxPoint x="400" y="560" as="sourcePoint"/>\n'
        f'        <mxPoint x="280" y="590" as="targetPoint"/>\n'
        f'      </mxGeometry>\n'
        f'    </mxCell>\n'
    )
    # Django ↔ Claude
    cells += (
        f'    <mxCell id="{nid()}" value="HTTPS / SSE Stream" style="{DARR}strokeColor=#c62828;fontColor=#c62828;" edge="1" parent="1">\n'
        f'      <mxGeometry relative="1" as="geometry">\n'
        f'        <mxPoint x="860" y="420" as="sourcePoint"/>\n'
        f'        <mxPoint x="900" y="390" as="targetPoint"/>\n'
        f'      </mxGeometry>\n'
        f'    </mxCell>\n'
    )

    with open(os.path.join(OUT_DIR, "fig4_architecture.drawio"), "w", encoding="utf-8") as f:
        f.write(wrap(cells, pw=1100, ph=720))
    print("[OK] fig4_architecture.drawio")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    print("")
    print("=== DONE ===")
    print("4 file .drawio da duoc tao trong thu muc: diagrams/")
    print("")
    print("HUONG DAN IMPORT:")
    print("1. Mo trinh duyet, vao: https://app.diagrams.net")
    print("2. Chon File > Import from > Device")
    print("3. Chon file .drawio can mo")
    print("4. Chinh sua neu can, sau do: File > Export as > PNG (300 DPI)")
