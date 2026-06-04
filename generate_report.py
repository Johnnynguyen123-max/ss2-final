"""
Script tạo báo cáo khoa học - DDC Books
Chạy: python generate_report.py
Yêu cầu: pip install python-docx
"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import docx.opc.constants
from copy import deepcopy
import os

def set_paragraph_format(para, first_line_cm=0.85, space_before=6, space_after=0,
                          line_spacing_pt=17, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY):
    """Áp dụng định dạng chuẩn cho đoạn văn."""
    pf = para.paragraph_format
    pf.first_line_indent = Cm(first_line_cm)
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(line_spacing_pt)
    pf.alignment = alignment


def add_run_formatted(para, text, font_name='Times New Roman', font_size=13,
                       bold=False, italic=False, color=None):
    """Thêm run với định dạng chữ."""
    run = para.add_run(text)
    run.font.name = font_name
    run.font.size = Pt(font_size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)
    # Đảm bảo font áp dụng đúng cho tiếng Việt
    r = run._r
    rPr = r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:cs'), font_name)
    rPr.insert(0, rFonts)
    return run


def add_heading_paragraph(doc, text, font_name='Times New Roman', font_size=13,
                            bold=True, alignment=WD_ALIGN_PARAGRAPH.LEFT,
                            first_line=0, space_before=6, space_after=0):
    """Thêm đoạn tiêu đề section."""
    para = doc.add_paragraph()
    pf = para.paragraph_format
    pf.first_line_indent = Cm(first_line)
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(17)
    pf.alignment = alignment
    add_run_formatted(para, text, font_name=font_name, font_size=font_size, bold=bold)
    return para


def add_body_paragraph(doc, text, first_line=0.85):
    """Thêm đoạn văn body chuẩn Times New Roman 13."""
    para = doc.add_paragraph()
    set_paragraph_format(para, first_line_cm=first_line)
    add_run_formatted(para, text)
    return para


def add_blank_line(doc):
    """Thêm dòng trống chuẩn."""
    para = doc.add_paragraph()
    set_paragraph_format(para, first_line_cm=0, space_before=0, space_after=0)
    add_run_formatted(para, '', font_size=6)
    return para


def create_report():
    doc = Document()

    # ── CÀI ĐẶT TRANG ──────────────────────────────────────────────────────────
    section = doc.sections[0]
    section.page_width  = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin    = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin   = Cm(3.0)
    section.right_margin  = Cm(3.0)

    # ── TIÊU ĐỀ TIẾNG VIỆT ──────────────────────────────────────────────────────
    title_vi = doc.add_paragraph()
    title_vi.paragraph_format.space_before = Pt(0)
    title_vi.paragraph_format.space_after  = Pt(6)
    title_vi.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    title_vi.paragraph_format.line_spacing = Pt(17)
    title_vi.paragraph_format.alignment    = WD_ALIGN_PARAGRAPH.CENTER
    add_run_formatted(
        title_vi,
        "XÂY DỰNG ỨNG DỤNG WEB BÁN SÁCH TRỰC TUYẾN\nTÍCH HỢP AI CHATBOT TƯ VẤN VÀ QUẢN LÝ BÁN HÀNG THÔNG MINH",
        font_name='Tahoma', font_size=15, bold=True
    )

    # ── TÁC GIẢ ─────────────────────────────────────────────────────────────────
    author_para = doc.add_paragraph()
    author_para.paragraph_format.space_before = Pt(4)
    author_para.paragraph_format.space_after  = Pt(4)
    author_para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    author_para.paragraph_format.line_spacing = Pt(17)
    author_para.paragraph_format.alignment    = WD_ALIGN_PARAGRAPH.CENTER
    add_run_formatted(
        author_para,
        "Nguyễn Văn A, Trần Văn B, Lê Văn C – Lớp tín chỉ CNTT.XX",
        font_name='Arial', font_size=10, bold=True, italic=True
    )

    # ── TÓM TẮT TIẾNG VIỆT ──────────────────────────────────────────────────────
    abstract_label_vi = doc.add_paragraph()
    abstract_label_vi.paragraph_format.first_line_indent = Cm(0)
    abstract_label_vi.paragraph_format.space_before = Pt(6)
    abstract_label_vi.paragraph_format.space_after  = Pt(0)
    abstract_label_vi.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    abstract_label_vi.paragraph_format.line_spacing = Pt(17)
    abstract_label_vi.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    add_run_formatted(abstract_label_vi,
        "Tóm tắt: ",
        font_name='Arial', font_size=10, bold=True, italic=True)
    add_run_formatted(abstract_label_vi,
        "Bài viết trình bày quá trình thiết kế và xây dựng ứng dụng web bán sách trực tuyến DDC Books "
        "sử dụng framework Django (Python). Hệ thống tích hợp đầy đủ các chức năng thương mại điện tử "
        "như quản lý giỏ hàng, đặt hàng, theo dõi đơn hàng, mã giảm giá (coupon), Flash Sale giới hạn "
        "thời gian, danh sách yêu thích (wishlist) và tìm kiếm gợi ý tức thì. Điểm nổi bật của hệ thống "
        "là tích hợp AI Chatbot tư vấn sách thông minh sử dụng API Claude (Anthropic) với kỹ thuật RAG "
        "(Retrieval-Augmented Generation) cho phép tra cứu đơn hàng, gợi ý sách theo sở thích và thiết lập "
        "cảnh báo giá. Hệ thống còn có module chat real-time giữa khách hàng và nhân viên, bảng điều khiển "
        "thống kê doanh thu cho staff. Kết quả cho thấy ứng dụng đáp ứng được nhu cầu vận hành một cửa hàng "
        "sách trực tuyến quy mô vừa, đồng thời thể hiện tiềm năng ứng dụng AI trong lĩnh vực thương mại điện tử.",
        font_name='Arial', font_size=10, italic=True)

    # ── TIÊU ĐỀ TIẾNG ANH ──────────────────────────────────────────────────────
    title_en = doc.add_paragraph()
    title_en.paragraph_format.space_before = Pt(10)
    title_en.paragraph_format.space_after  = Pt(6)
    title_en.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    title_en.paragraph_format.line_spacing = Pt(17)
    title_en.paragraph_format.alignment    = WD_ALIGN_PARAGRAPH.CENTER
    add_run_formatted(
        title_en,
        "BUILDING AN ONLINE BOOKSTORE WEB APPLICATION\nINTEGRATED WITH AI CHATBOT AND INTELLIGENT SALES MANAGEMENT",
        font_name='Tahoma', font_size=15, bold=True
    )

    # ── TÓM TẮT TIẾNG ANH ──────────────────────────────────────────────────────
    abstract_label_en = doc.add_paragraph()
    abstract_label_en.paragraph_format.first_line_indent = Cm(0)
    abstract_label_en.paragraph_format.space_before = Pt(6)
    abstract_label_en.paragraph_format.space_after  = Pt(0)
    abstract_label_en.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    abstract_label_en.paragraph_format.line_spacing = Pt(17)
    abstract_label_en.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    add_run_formatted(abstract_label_en,
        "Abstract: ",
        font_name='Arial', font_size=10, bold=True, italic=True)
    add_run_formatted(abstract_label_en,
        "This paper presents the design and implementation of DDC Books, an online bookstore web application "
        "built using the Django framework (Python). The system incorporates comprehensive e-commerce features "
        "including cart management, order placement, order tracking, coupon discounts, time-limited Flash Sales, "
        "wishlists, and real-time search suggestions. The system's distinguishing feature is an intelligent AI "
        "Book Advisory Chatbot integrated with the Claude API (Anthropic) and Retrieval-Augmented Generation (RAG) "
        "technique, enabling order lookup, personalized book recommendations, and price alert settings. "
        "Additionally, the platform includes a real-time customer-staff chat module and a revenue statistics "
        "dashboard for staff. Results demonstrate that the application meets the operational requirements of a "
        "medium-scale online bookstore while highlighting the potential of AI integration in e-commerce.",
        font_name='Arial', font_size=10, italic=True)

    # ════════════════════════════════════════════════════════════════════════════
    # 1. ĐẶT VẤN ĐỀ
    # ════════════════════════════════════════════════════════════════════════════
    add_heading_paragraph(doc, "1. ĐẶT VẤN ĐỀ", space_before=12)

    add_body_paragraph(doc,
        "Thương mại điện tử (e-commerce) đang phát triển mạnh mẽ trên toàn cầu và tại Việt Nam. "
        "Theo báo cáo của Hiệp hội Thương mại điện tử Việt Nam (VECOM, 2023), doanh thu thương mại "
        "điện tử Việt Nam đạt hơn 20 tỷ USD vào năm 2023, tăng trưởng ổn định 25% mỗi năm. Trong bối "
        "cảnh đó, các cửa hàng bán sách truyền thống ngày càng chịu áp lực cạnh tranh lớn từ các nền "
        "tảng trực tuyến như Tiki, Shopee, Fahasa. Tuy nhiên, hầu hết các hệ thống bán sách hiện có chưa "
        "khai thác tốt tiềm năng của trí tuệ nhân tạo (AI) trong việc tư vấn sách cá nhân hóa và nâng cao "
        "trải nghiệm mua sắm của người dùng."
    )

    add_body_paragraph(doc,
        "Trên thế giới, nhiều nghiên cứu đã chứng minh hiệu quả của các hệ thống gợi ý (Recommender Systems) "
        "trong thương mại điện tử. Resnick & Varian (1997) đặt nền móng cho lĩnh vực này với khái niệm "
        "collaborative filtering, trong khi Ricci et al. (2011) tổng hợp toàn diện các phương pháp gợi ý "
        "hiện đại. Gần đây, sự ra đời của các mô hình ngôn ngữ lớn (LLM) như GPT-4 (OpenAI, 2023) và "
        "Claude (Anthropic, 2024) mở ra khả năng xây dựng chatbot tư vấn thông minh, có thể hiểu ngữ cảnh "
        "hội thoại và truy xuất thông tin chính xác từ cơ sở dữ liệu thực."
    )

    add_body_paragraph(doc,
        "Tại Việt Nam, các nghiên cứu về ứng dụng Django trong phát triển web thương mại điện tử còn hạn chế, "
        "đặc biệt là các hệ thống kết hợp nhiều tính năng thông minh như AI chatbot, Flash Sale và quản lý "
        "kho hàng trong một nền tảng thống nhất. Bài viết này trình bày thiết kế và xây dựng ứng dụng web "
        "DDC Books – một hệ thống bán sách trực tuyến toàn diện sử dụng Django, tích hợp AI Chatbot dựa trên "
        "Claude API với kỹ thuật RAG, chat real-time và các tính năng quản lý bán hàng thông minh. "
        "Phương pháp nghiên cứu sử dụng kết hợp thiết kế hướng đối tượng (OOP), mô hình MVT của Django và "
        "phát triển theo hướng kiểm thử (TDD)."
    )

    # ════════════════════════════════════════════════════════════════════════════
    # 2. NỘI DUNG NGHIÊN CỨU
    # ════════════════════════════════════════════════════════════════════════════
    add_heading_paragraph(doc, "2. NỘI DUNG NGHIÊN CỨU", space_before=12)

    # ── 2.1 ─────────────────────────────────────────────────────────────────────
    add_heading_paragraph(doc, "2.1. Kiến trúc hệ thống", space_before=6, first_line=0.85)

    add_body_paragraph(doc,
        "Hệ thống DDC Books được xây dựng theo mô hình MVT (Model–View–Template) của Django, "
        "là biến thể của mô hình MVC phổ biến trong lập trình web. Kiến trúc tổng thể gồm ba tầng chính: "
        "tầng dữ liệu (Django ORM + SQLite), tầng xử lý nghiệp vụ (Django Views) và tầng giao diện "
        "(Django Templates + HTML/CSS/JavaScript)."
    )

    add_body_paragraph(doc,
        "Về cấu trúc dự án, mã nguồn được tổ chức thành một Django app duy nhất (app/) với các module "
        "views được tách theo chức năng: home.py, cart.py, orders.py, auth.py, books.py, chat.py, "
        "ai_chat.py, staff.py và wishlist.py. Cách tổ chức này giúp dễ bảo trì, mở rộng và kiểm thử "
        "từng chức năng độc lập."
    )

    # ── 2.2 ─────────────────────────────────────────────────────────────────────
    add_heading_paragraph(doc, "2.2. Thiết kế cơ sở dữ liệu", space_before=6, first_line=0.85)

    add_body_paragraph(doc,
        "Hệ thống sử dụng Django ORM để quản lý cơ sở dữ liệu quan hệ SQLite. Các model chính gồm: "
        "Book (thông tin sách), Category (thể loại), Profile (thông tin người dùng mở rộng), Order và "
        "OrderItem (đơn hàng và chi tiết đơn), OrderTracking (lịch sử vận chuyển), Coupon (mã giảm giá), "
        "ChatSession và ChatMessage (chat real-time), BotChatSession và BotChatMessage (AI chatbot), "
        "FlashSaleConfig (cấu hình Flash Sale), và PriceAlert (cảnh báo giá)."
    )

    add_body_paragraph(doc,
        "Mô hình Book lưu trữ các trường: title, author, price, category (ForeignKey), stock, "
        "release_date, description, image và sold_count. Thuộc tính tính toán is_new kiểm tra xem "
        "sách có được phát hành trong vòng 90 ngày gần đây hay không, giúp phục vụ tính năng lọc "
        "sách mới. Model Order hỗ trợ các trạng thái: Pending, Confirmed, Shipped, Received, Cancelled "
        "cùng với liên kết đến Coupon và ghi nhận discount_amount."
    )

    # ── 2.3 ─────────────────────────────────────────────────────────────────────
    add_heading_paragraph(doc, "2.3. Các chức năng thương mại điện tử", space_before=6, first_line=0.85)

    # ── 2.3.1 ───────────────────────────────────────────────────────────────────
    add_heading_paragraph(doc, "2.3.1. Giỏ hàng và đặt hàng", space_before=6, first_line=1.7)

    add_body_paragraph(doc,
        "Giỏ hàng được triển khai hoàn toàn phía server sử dụng Django session, không yêu cầu người dùng "
        "đăng nhập. Khi thêm sản phẩm vào giỏ, hệ thống kiểm tra tồn kho theo thời gian thực và giới hạn "
        "số lượng theo stock hiện có. Quá trình thanh toán (checkout) sử dụng transaction.atomic() của "
        "Django để đảm bảo tính toàn vẹn dữ liệu: kiểm tra lại tồn kho, giảm stock, tăng sold_count và "
        "tạo Order cùng các OrderItem trong một giao dịch nguyên tử."
    )

    add_body_paragraph(doc,
        "Hệ thống hỗ trợ đặt hàng cho cả khách vãng lai (guest) và thành viên đã đăng nhập. Đối với thành "
        "viên, thông tin giao hàng được điền tự động từ Profile. Sau khi đặt hàng thành công, người dùng "
        "được chuyển đến trang xác nhận đơn hàng với đầy đủ thông tin."
    )

    # ── 2.3.2 ───────────────────────────────────────────────────────────────────
    add_heading_paragraph(doc, "2.3.2. Mã giảm giá và Flash Sale", space_before=6, first_line=1.7)

    add_body_paragraph(doc,
        "Hệ thống Coupon cho phép staff tạo mã giảm giá theo phần trăm với các thuộc tính: mã coupon "
        "duy nhất, phần trăm giảm, ngày hết hạn và số lần sử dụng tối đa. Validation coupon được thực "
        "hiện qua AJAX để cung cấp phản hồi tức thì cho người dùng mà không cần tải lại trang. Tính hợp "
        "lệ của coupon được kiểm tra đồng thời ba điều kiện: is_active, valid_until và used_count < max_uses."
    )

    add_body_paragraph(doc,
        "Flash Sale là tính năng bán hàng giảm giá trong khung giờ cố định, được cấu hình bởi staff "
        "thông qua model FlashSaleConfig (singleton pattern với pk=1). Hệ thống tự động tính toán xem "
        "Flash Sale có đang diễn ra không dựa trên giờ hiện tại, hỗ trợ cả trường hợp khung giờ vượt qua "
        "nửa đêm. Giá Flash Sale được hiển thị trực tiếp trên giao diện kèm countdown timer."
    )

    # ── 2.3.3 ───────────────────────────────────────────────────────────────────
    add_heading_paragraph(doc, "2.3.3. Tìm kiếm và lọc sách", space_before=6, first_line=1.7)

    add_body_paragraph(doc,
        "Chức năng tìm kiếm sử dụng Django Q objects để tìm kiếm đồng thời theo tiêu đề và tác giả. "
        "Hệ thống hỗ trợ gợi ý tìm kiếm tức thì (autocomplete) qua AJAX: kết quả được ưu tiên sắp xếp "
        "với các sách có tiêu đề bắt đầu bằng từ khóa trước, sau đó đến các sách chứa từ khóa. "
        "Người dùng có thể lọc sách theo thể loại, khoảng giá (dưới 100k, 100k–300k, trên 300k), "
        "năm xuất bản và loại (mới, bán chạy). Hệ thống còn lưu lịch sử xem gần đây vào session "
        "để phục vụ tính năng gợi ý cá nhân hóa của AI Chatbot."
    )

    # ── 2.4 ─────────────────────────────────────────────────────────────────────
    add_heading_paragraph(doc, "2.4. Hệ thống AI Chatbot tích hợp RAG", space_before=6, first_line=0.85)

    add_body_paragraph(doc,
        "Đây là tính năng trọng tâm và có giá trị khoa học cao nhất của hệ thống. AI Chatbot được xây "
        "dựng dựa trên Claude API (claude-sonnet-4-20250514) của Anthropic, tích hợp kỹ thuật "
        "Retrieval-Augmented Generation (RAG) để cung cấp câu trả lời chính xác từ dữ liệu thực của "
        "cửa hàng thay vì dựa hoàn toàn vào kiến thức của mô hình ngôn ngữ."
    )

    add_body_paragraph(doc,
        "Cơ chế RAG hoạt động theo các bước: (1) Phân tích tin nhắn người dùng bằng regex để trích xuất "
        "từ khóa, loại bỏ stopwords tiếng Việt; (2) Truy vấn database để tìm sách liên quan qua "
        "Django ORM với Q objects; (3) Tổng hợp ngữ cảnh gồm: danh sách đơn hàng gần đây, wishlist, "
        "lịch sử xem sách, kết quả RAG, sách mới và sách bán chạy; (4) Đưa tất cả ngữ cảnh vào system "
        "prompt của Claude API; (5) Stream phản hồi về client theo chuẩn Server-Sent Events (SSE) để "
        "tạo hiệu ứng typing tự nhiên."
    )

    add_body_paragraph(doc,
        "Chatbot hỗ trợ các tính năng nâng cao: tra cứu đơn hàng theo ID (cả thành viên lẫn khách vãng "
        "lai), gợi ý sách cá nhân hóa dựa trên wishlist và lịch sử xem, thiết lập PriceAlert (cảnh báo "
        "khi giá giảm đến ngưỡng mong muốn), và hiển thị chip gợi ý câu hỏi tiếp theo. Hệ thống parse "
        "các tag đặc biệt như [SET_PRICE_ALERT], [TRACK_GUEST_ORDER], [SUGGESTIONS] từ phản hồi của "
        "Claude để thực thi các hành động tương ứng trong backend. Đồng thời, hệ thống có chế độ "
        "fallback (mock response) khi không có API key, đảm bảo hoạt động được trong môi trường offline."
    )

    add_body_paragraph(doc,
        "Lịch sử hội thoại được lưu vào cơ sở dữ liệu (BotChatSession, BotChatMessage) và gửi kèm "
        "trong mỗi lần gọi API (tối đa 10 tin nhắn gần nhất) để chatbot duy trì ngữ cảnh hội thoại. "
        "Hệ thống cũng hỗ trợ chức năng đánh giá phản hồi (thumbs up/down) và rate limiting "
        "(1 request/giây) để tránh lạm dụng API."
    )

    # ── 2.5 ─────────────────────────────────────────────────────────────────────
    add_heading_paragraph(doc, "2.5. Chat real-time và quản lý Staff", space_before=6, first_line=0.85)

    add_body_paragraph(doc,
        "Hệ thống chat real-time giữa khách hàng và nhân viên được xây dựng bằng kỹ thuật AJAX polling "
        "với interval cập nhật ngắn, không yêu cầu WebSocket để đơn giản hóa triển khai. Mỗi khách hàng "
        "có một ChatSession riêng (quan hệ OneToOne với User). Nhân viên có thể quản lý tất cả các phiên "
        "chat, xem số tin nhắn chưa đọc và phản hồi trực tiếp."
    )

    add_body_paragraph(doc,
        "Giao diện Staff Dashboard cung cấp biểu đồ doanh thu 7 ngày, top 5 sách bán chạy, phân bổ "
        "trạng thái đơn hàng và bảng đơn hàng mới nhất. Dữ liệu biểu đồ được tính toán bằng các "
        "aggregation function của Django ORM (Sum, Count, values) và render bằng Chart.js. Staff có "
        "toàn quyền quản lý sách (thêm, sửa, xóa), đơn hàng (xác nhận, đóng gói, giao hàng, hủy), "
        "coupon và cấu hình Flash Sale."
    )

    # ── 2.6 ─────────────────────────────────────────────────────────────────────
    add_heading_paragraph(doc, "2.6. Kiểm thử hệ thống", space_before=6, first_line=0.85)

    add_body_paragraph(doc,
        "Hệ thống được kiểm thử bằng Django TestCase với bộ test cases bao phủ các luồng nghiệp vụ "
        "chính. Các test được tổ chức theo từng chức năng: kiểm thử model (tính toán is_new, "
        "Coupon.is_valid, FlashSaleConfig.is_running_now), kiểm thử view (thêm/xóa giỏ hàng, "
        "checkout với coupon, quản lý wishlist) và kiểm thử xác thực (đăng ký, đăng nhập, phân quyền "
        "staff). Phương pháp TDD (Test-Driven Development) được áp dụng cho các module quan trọng "
        "như checkout và coupon validation để đảm bảo tính chính xác của logic nghiệp vụ."
    )

    # ════════════════════════════════════════════════════════════════════════════
    # 3. KẾT LUẬN
    # ════════════════════════════════════════════════════════════════════════════
    add_heading_paragraph(doc, "3. KẾT LUẬN", space_before=12)

    add_body_paragraph(doc,
        "Nghiên cứu đã xây dựng thành công ứng dụng web bán sách trực tuyến DDC Books với đầy đủ các "
        "chức năng thương mại điện tử cốt lõi và tích hợp AI Chatbot thông minh sử dụng Claude API "
        "kết hợp kỹ thuật RAG. Kết quả nổi bật gồm: (1) Hệ thống hoạt động ổn định với đầy đủ luồng "
        "mua sắm từ tìm kiếm đến thanh toán; (2) AI Chatbot có khả năng tư vấn sách cá nhân hóa dựa "
        "trên dữ liệu thực của cửa hàng; (3) Các tính năng Flash Sale và Coupon hoạt động chính xác "
        "với cơ chế kiểm tra đồng thời nhiều điều kiện; (4) Giao diện quản lý staff trực quan với "
        "biểu đồ thống kê doanh thu."
    )

    add_body_paragraph(doc,
        "Hướng phát triển tiếp theo của dự án bao gồm: nâng cấp chat real-time lên WebSocket (Django "
        "Channels) để cải thiện hiệu suất, tích hợp thanh toán trực tuyến (VNPay, MoMo), phát triển "
        "hệ thống gợi ý sách dựa trên collaborative filtering, triển khai thông báo push (Push "
        "Notifications) cho PriceAlert và mở rộng hệ thống sang ứng dụng di động."
    )

    add_body_paragraph(doc,
        "Kết quả nghiên cứu minh chứng rằng việc kết hợp framework web hiện đại (Django) với các mô "
        "hình ngôn ngữ lớn (LLM) và kỹ thuật RAG có thể tạo ra các ứng dụng thương mại điện tử "
        "thông minh, mang lại trải nghiệm người dùng vượt trội so với các hệ thống truyền thống."
    )

    # ════════════════════════════════════════════════════════════════════════════
    # TÀI LIỆU THAM KHẢO
    # ════════════════════════════════════════════════════════════════════════════
    add_heading_paragraph(doc, "TÀI LIỆU THAM KHẢO", space_before=12)

    references = [
        "Anthropic. (2024). Claude API Documentation. Anthropic. https://docs.anthropic.com",
        "Django Software Foundation. (2024). Django Documentation (Version 5.0). https://docs.djangoproject.com",
        "Hiệp hội Thương mại điện tử Việt Nam (VECOM). (2023). Báo cáo Chỉ số Thương mại điện tử Việt Nam 2023. VECOM.",
        "Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., ... & Kiela, D. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. Advances in Neural Information Processing Systems, 33, 9459–9474.",
        "OpenAI. (2023). GPT-4 Technical Report. arXiv:2303.08774.",
        "Resnick, P., & Varian, H. R. (1997). Recommender systems. Communications of the ACM, 40(3), 56–58. https://doi.org/10.1145/245108.245121",
        "Ricci, F., Rokach, L., & Shapira, B. (2011). Introduction to Recommender Systems Handbook. In F. Ricci, L. Rokach, B. Shapira, & P. B. Kantor (Eds.), Recommender Systems Handbook (pp. 1–35). Springer.",
        "Forcier, J., Bissex, P., & Chun, W. J. (2008). Python Web Development with Django. Addison-Wesley Professional.",
        "Géron, A. (2022). Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow (3rd ed.). O'Reilly Media.",
        "Nguyen, H. T., & Tran, V. B. (2022). Ứng dụng học máy trong hệ thống gợi ý sản phẩm thương mại điện tử. Tạp chí Khoa học và Công nghệ Việt Nam, 64(4), 45–52.",
    ]

    for i, ref in enumerate(references, 1):
        ref_para = doc.add_paragraph()
        ref_para.paragraph_format.first_line_indent = Cm(-0.85)
        ref_para.paragraph_format.left_indent = Cm(0.85)
        ref_para.paragraph_format.space_before = Pt(3)
        ref_para.paragraph_format.space_after = Pt(0)
        ref_para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        ref_para.paragraph_format.line_spacing = Pt(17)
        ref_para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_run_formatted(ref_para, f"{i}.\t{ref}")

    # ── Lưu file ─────────────────────────────────────────────────────────────────
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DDC_Books_Report.docx")
    doc.save(output_path)
    print(f"[OK] Da tao file thanh cong: {output_path}")
    print(f"   So trang uoc tinh: ~8-10 trang A4")
    return output_path


if __name__ == "__main__":
    try:
        from docx import Document
    except ImportError:
        print("❌ Chưa cài python-docx. Đang cài...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx"])
        from docx import Document
    create_report()
