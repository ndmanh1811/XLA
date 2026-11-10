"""
build_slides.py
Tạo Presentation Deck chuẩn mực IEEE / Đề tài BTL Xử Lý Ảnh Số.
Đề tài: Phát hiện đặc trưng ảnh đa tỷ lệ bằng đạo hàm Gaussian (FeatureJ vs Pure Python).
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Bảng màu chuyên nghiệp
    COLOR_BG_DARK = RGBColor(15, 23, 42)        # Slate 900
    COLOR_CARD_DARK = RGBColor(30, 41, 59)      # Slate 800
    COLOR_BG_LIGHT = RGBColor(248, 250, 252)    # Slate 50
    COLOR_CARD_LIGHT = RGBColor(255, 255, 255)  # White
    COLOR_BORDER = RGBColor(226, 232, 240)      # Slate 200
    COLOR_BORDER_DARK = RGBColor(51, 65, 85)    # Slate 700

    COLOR_TEXT_PRIMARY = RGBColor(15, 23, 42)   # Dark Charcoal
    COLOR_TEXT_MUTED = RGBColor(71, 85, 105)    # Muted Slate
    COLOR_TEXT_LIGHT = RGBColor(241, 245, 249)  # Light Slate

    COLOR_PRIMARY_BLUE = RGBColor(2, 132, 199)  # Sky 600
    COLOR_NAVY = RGBColor(30, 58, 138)          # Navy 800
    COLOR_EMERALD = RGBColor(16, 185, 129)      # Emerald 500
    COLOR_AMBER = RGBColor(217, 119, 6)         # Amber 600
    COLOR_PURPLE = RGBColor(124, 58, 237)       # Purple 600
    COLOR_RED = RGBColor(225, 29, 72)           # Rose 600

    def set_slide_background(slide, color):
        bg_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
        )
        bg_shape.fill.solid()
        bg_shape.fill.fore_color.rgb = color
        bg_shape.line.fill.background()
        return bg_shape

    def add_header(slide, category, title, subtitle):
        bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.42), Inches(0.08), Inches(0.68)
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = COLOR_PRIMARY_BLUE
        bar.line.fill.background()

        tb = slide.shapes.add_textbox(Inches(1.0), Inches(0.32), Inches(11.5), Inches(0.85))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_cat = tf.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.name = "Arial"
        p_cat.font.size = Pt(10)
        p_cat.font.bold = True
        p_cat.font.color.rgb = COLOR_PRIMARY_BLUE

        p_title = tf.add_paragraph()
        p_title.text = title
        p_title.font.name = "Arial"
        p_title.font.size = Pt(20)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_TEXT_PRIMARY

        if subtitle:
            p_sub = tf.add_paragraph()
            p_sub.text = subtitle
            p_sub.font.name = "Arial"
            p_sub.font.size = Pt(11)
            p_sub.font.color.rgb = COLOR_TEXT_MUTED

    def add_footer(slide, current_slide, total_slides=12):
        line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.92), Inches(11.733), Inches(0.015)
        )
        line.fill.solid()
        line.fill.fore_color.rgb = COLOR_BORDER
        line.line.fill.background()

        tb = slide.shapes.add_textbox(Inches(0.8), Inches(7.0), Inches(8.0), Inches(0.35))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = "BTL Xử Lý Ảnh Số | Đề tài: Phát hiện đặc trưng ảnh đa tỷ lệ bằng đạo hàm Gaussian | Nhóm BTL"
        p.font.name = "Arial"
        p.font.size = Pt(9)
        p.font.color.rgb = COLOR_TEXT_MUTED

        tb_num = slide.shapes.add_textbox(Inches(11.0), Inches(7.0), Inches(1.533), Inches(0.35))
        tf_num = tb_num.text_frame
        tf_num.margin_left = tf_num.margin_top = tf_num.margin_right = tf_num.margin_bottom = 0
        p_num = tf_num.paragraphs[0]
        p_num.text = f"{current_slide} / {total_slides}"
        p_num.font.name = "Arial"
        p_num.font.size = Pt(9)
        p_num.font.bold = True
        p_num.alignment = PP_ALIGN.RIGHT
        p_num.font.color.rgb = COLOR_PRIMARY_BLUE

    def add_card(slide, left, top, width, height, bg_color=COLOR_CARD_LIGHT, border_color=COLOR_BORDER):
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
        )
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        if border_color:
            card.line.color.rgb = border_color
            card.line.width = Pt(1)
        else:
            card.line.fill.background()
        return card

    def add_kpi_card(slide, left, top, width, height, val_str, label_str, note_str="", accent_color=COLOR_PRIMARY_BLUE):
        add_card(slide, left, top, width, height, COLOR_CARD_LIGHT, COLOR_BORDER)
        
        top_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, left + Inches(0.12), top, width - Inches(0.24), Inches(0.04)
        )
        top_bar.fill.solid()
        top_bar.fill.fore_color.rgb = accent_color
        top_bar.line.fill.background()

        tb = slide.shapes.add_textbox(left + Inches(0.12), top + Inches(0.08), width - Inches(0.24), height - Inches(0.15))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        p_val = tf.paragraphs[0]
        p_val.text = val_str
        p_val.font.name = "Arial"
        p_val.font.size = Pt(22)
        p_val.font.bold = True
        p_val.font.color.rgb = accent_color

        p_lbl = tf.add_paragraph()
        p_lbl.text = label_str
        p_lbl.font.name = "Arial"
        p_lbl.font.size = Pt(10)
        p_lbl.font.bold = True
        p_lbl.font.color.rgb = COLOR_TEXT_PRIMARY

        if note_str:
            p_note = tf.add_paragraph()
            p_note.text = note_str
            p_note.font.name = "Arial"
            p_note.font.size = Pt(8.5)
            p_note.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 1: TRANG BÌA (DARK THEME)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1, COLOR_BG_DARK)

    # Accent decorative bar
    dec_bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.8), Inches(11.733), Inches(0.04))
    dec_bar.fill.solid()
    dec_bar.fill.fore_color.rgb = COLOR_PRIMARY_BLUE
    dec_bar.line.fill.background()

    # Title & Subtitle Box
    tb1 = s1.shapes.add_textbox(Inches(0.8), Inches(1.1), Inches(11.733), Inches(2.3))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_top = tf1.margin_right = tf1.margin_bottom = 0

    p_uni = tf1.paragraphs[0]
    p_uni.text = "BÁO CÁO BÀI TẬP LỚN MÔN XỬ LÝ ẢNH SỐ"
    p_uni.font.name = "Arial"
    p_uni.font.size = Pt(13)
    p_uni.font.bold = True
    p_uni.font.color.rgb = COLOR_PRIMARY_BLUE

    p_main_title = tf1.add_paragraph()
    p_main_title.text = "PHÁT HIỆN ĐẶC TRƯNG ẢNH ĐA TỶ LỆ\nBẰNG ĐẠO HÀM GAUSSIAN"
    p_main_title.font.name = "Arial"
    p_main_title.font.size = Pt(30)
    p_main_title.font.bold = True
    p_main_title.font.color.rgb = RGBColor(255, 255, 255)

    p_sub_title = tf1.add_paragraph()
    p_sub_title.text = "Nghiên cứu đối sánh nền tảng tham chiếu FeatureJ (Fiji) & Cài đặt tối ưu từ đầu bằng Python (NumPy)"
    p_sub_title.font.name = "Arial"
    p_sub_title.font.size = Pt(14)
    p_sub_title.font.color.rgb = RGBColor(148, 163, 184)

    # 4 Cards for Members
    members = [
        ("Nguyễn Đức Mạnh (STT 37)", "Trưởng nhóm / Role 2", "Lead Algorithm & Optimization\n• Core NumPy từ đầu (1D separable)\n• Nghiệm thu Tier 1 & Tier 2\n• Tối ưu hoá & benchmark (STT 14)"),
        ("Nguyễn Tiến Hưng", "Thành viên / Role 1", "Theory & IEEE Report\n• Mô hình toán học Scale-Space\n• Đạo hàm chuẩn hoá tỷ lệ\n• Biên soạn Báo cáo IEEE (~30 trang)"),
        ("Phạm Bảo Lộc", "Thành viên / Role 3", "Fiji / FeatureJ Workflows\n• Khảo sát plugin FeatureJ (STT 15)\n• Tự động hóa macro batch (435 TIFF)\n• Biên soạn 2 DOCX quy trình GUI"),
        ("Bùi Trung Đức", "Thành viên / Role 4", "Dataset, GT & Benchmark\n• Chuẩn hóa 25 ảnh raw (BSDS, DRIVE, Blob)\n• Bộ nhãn Ground Truth (56 BSDS, tế bào)\n• Tính toán metric F1 & vẽ biểu đồ")
    ]

    card_w = Inches(2.78)
    card_gap = Inches(0.2)
    start_x = Inches(0.8)
    card_y = Inches(3.7)
    card_h = Inches(2.6)

    for i, (name, role, desc) in enumerate(members):
        cur_x = start_x + i * (card_w + card_gap)
        add_card(s1, cur_x, card_y, card_w, card_h, COLOR_CARD_DARK, COLOR_BORDER_DARK)
        
        # Role bar
        role_bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, cur_x + Inches(0.15), card_y, card_w - Inches(0.3), Inches(0.03))
        role_bar.fill.solid()
        role_bar.fill.fore_color.rgb = COLOR_PRIMARY_BLUE if i == 0 else COLOR_EMERALD
        role_bar.line.fill.background()

        tb_mem = s1.shapes.add_textbox(cur_x + Inches(0.15), card_y + Inches(0.15), card_w - Inches(0.3), card_h - Inches(0.25))
        tf_mem = tb_mem.text_frame
        tf_mem.word_wrap = True
        tf_mem.margin_left = tf_mem.margin_top = tf_mem.margin_right = tf_mem.margin_bottom = 0

        p_name = tf_mem.paragraphs[0]
        p_name.text = name
        p_name.font.name = "Arial"
        p_name.font.size = Pt(12)
        p_name.font.bold = True
        p_name.font.color.rgb = RGBColor(255, 255, 255)

        p_r = tf_mem.add_paragraph()
        p_r.text = role
        p_r.font.name = "Arial"
        p_r.font.size = Pt(10)
        p_r.font.bold = True
        p_r.font.color.rgb = COLOR_PRIMARY_BLUE if i == 0 else COLOR_EMERALD

        p_d = tf_mem.add_paragraph()
        p_d.text = desc
        p_d.font.name = "Arial"
        p_d.font.size = Pt(9)
        p_d.font.color.rgb = RGBColor(203, 213, 225)

    # Footer banner
    tb_foot = s1.shapes.add_textbox(Inches(0.8), Inches(6.6), Inches(11.733), Inches(0.4))
    tf_foot = tb_foot.text_frame
    tf_foot.margin_left = tf_foot.margin_top = tf_foot.margin_right = tf_foot.margin_bottom = 0
    p_ft = tf_foot.paragraphs[0]
    p_ft.text = "Mã nguồn & Dữ liệu mở: https://github.com/ndmanh1811/XLA.git  |  Cam kết hoàn thành trước hạn nộp 13/11/2026"
    p_ft.font.name = "Arial"
    p_ft.font.size = Pt(9.5)
    p_ft.font.color.rgb = RGBColor(148, 163, 184)

    # =========================================================================
    # SLIDE 2: ĐẶT VẤN ĐỀ & MỤC TIÊU NGHIÊN CỨU
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2, COLOR_BG_LIGHT)
    add_header(s2, "1. Tổng quan đề tài", "Đặt vấn đề & Mục tiêu Nghiên cứu", "Tại sao cần phát hiện đặc trưng đa tỷ lệ và kiểm chứng đối chuẩn với chuẩn công nghiệp Fiji?")
    add_footer(s2, 2)

    # Card 1: Hạn chế truyền thống
    add_card(s2, Inches(0.8), Inches(1.4), Inches(5.7), Inches(5.2))
    tb_c1 = s2.shapes.add_textbox(Inches(1.0), Inches(1.6), Inches(5.3), Inches(4.8))
    tf_c1 = tb_c1.text_frame
    tf_c1.word_wrap = True
    p = tf_c1.paragraphs[0]
    p.text = "1. Thách thức trong Xử lý Ảnh Cổ điển"
    p.font.size = Pt(14); p.font.bold = True; p.font.color.rgb = COLOR_RED
    
    bullets_c1 = [
        ("Toán tử vi phân cục bộ (Sobel, Prewitt):", "Hoạt động trên cửa sổ cố định 3x3, khuếch đại nhiễu cao tần mạnh mẽ và hoàn toàn thất bại khi đặc trưng có độ rộng biến thiên."),
        ("Hiện tượng phụ thuộc quy mô (Scale Dependency):", "Biên thực tế trong ảnh tự nhiên, mạch máu sinh học hay tế bào vi mô tồn tại ở các bán kính khác nhau; một kích thước kernel duy nhất không thể tối ưu."),
        ("Khoảng trống chuẩn mực kỹ thuật:", "Nhiều bài báo cáo học thuật chỉ quan sát trực quan bằng mắt ('nhìn có vẻ giống'), thiếu hẳn bộ khung nghiệm thu định lượng số học và đối sánh ground truth.")
    ]
    for b_title, b_body in bullets_c1:
        p_t = tf_c1.add_paragraph()
        p_t.text = "• " + b_title
        p_t.font.size = Pt(11); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_c1.add_paragraph()
        p_b.text = "  " + b_body
        p_b.font.size = Pt(10.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # Card 2: Mục tiêu giải pháp
    add_card(s2, Inches(6.8), Inches(1.4), Inches(5.7), Inches(5.2))
    tb_c2 = s2.shapes.add_textbox(Inches(7.0), Inches(1.6), Inches(5.3), Inches(4.8))
    tf_c2 = tb_c2.text_frame
    tf_c2.word_wrap = True
    p = tf_c2.paragraphs[0]
    p.text = "2. Giải pháp & Mục tiêu Nghiên cứu của Nhóm"
    p.font.size = Pt(14); p.font.bold = True; p.font.color.rgb = COLOR_PRIMARY_BLUE
    
    bullets_c2 = [
        ("Nền tảng tham chiếu chuẩn hóa (Fiji / FeatureJ):", "Khảo sát toàn diện thuật toán đạo hàm Gaussian của Erik Meijering; tự động hóa workflow sản xuất 435 bản đồ TIFF 32-bit float không nén."),
        ("Cài đặt thuần Python từ số 0 (Zero-Dependencies):", "Tự xây dựng trọn vẹn bộ lọc đạo hàm Gauss bậc 0, 1, 2, Hessian, Canny NMS/Hysteresis, Frangi Vesselness và LoG bằng NumPy thuần."),
        ("Quy trình thẩm định đa tầng nghiêm ngặt:", "Xây dựng 2 tầng kiểm chứng: Tier 1 (220 bản đồ toán học sai số tuyệt đối/tương đối) & Tier 2 (F1-score trên BSDS500, DRIVE võng mạc, Blobs tế bào)."),
        ("Tối ưu hóa thuật toán vượt bậc:", "Áp dụng tích chập khả tách 1D (Separable 1D), chứng minh tăng tốc thực tế lên tới 29.0x với sai số bảo toàn cấp độ 10^-12.")
    ]
    for b_title, b_body in bullets_c2:
        p_t = tf_c2.add_paragraph()
        p_t.text = "✔ " + b_title
        p_t.font.size = Pt(11); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_c2.add_paragraph()
        p_b.text = "  " + b_body
        p_b.font.size = Pt(10.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 3: CƠ SỞ LÝ THUYẾT TOÁN HỌC (MATHEMATICAL FOUNDATIONS)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3, COLOR_BG_LIGHT)
    add_header(s3, "2. Cơ sở lý thuyết", "Mô hình Toán học: Không gian Tỷ lệ & Toán tử Đạo hàm", "Khung lý thuyết không gian tỷ lệ tuyến tính Lindeberg và các toán tử trích xuất đặc trưng bậc cao")
    add_footer(s3, 3)

    # 3 Cards ngang
    col_w = Inches(3.75)
    gap_w = Inches(0.24)

    # Box 1: Scale-Space
    add_card(s3, Inches(0.8), Inches(1.4), col_w, Inches(5.2))
    tb_s1 = s3.shapes.add_textbox(Inches(0.95), Inches(1.55), col_w - Inches(0.3), Inches(4.9))
    tf_s1 = tb_s1.text_frame
    tf_s1.word_wrap = True
    p = tf_s1.paragraphs[0]
    p.text = "1. Không gian Tỷ lệ Tuyến tính"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
    
    t1_text = [
        ("Phương trình truyền nhiệt (Heat Eq):", "∂L/∂t = 1/2 ∇²L, với t = σ² là tham số tỷ lệ; nghiệm duy nhất thỏa mãn tính đẳng hướng và không sinh thêm cực trị giả."),
        ("Biểu diễn không gian tỷ lệ:", "L(x, y; σ) = I(x, y) * G(x, y; σ)\nvới G(x, y; σ) = (1 / 2πσ²) exp(-(x²+y²)/2σ²)"),
        ("Đạo hàm chuẩn hóa tỷ lệ (γ-normalized):", "∂_γ = σ^γ ∂  (Lindeberg)\nBảo toàn độ lớn vi phân qua các tỷ lệ: γ=1 cho Gradient/Edge, γ=2 cho Hessian/Ridge/Blob.")
    ]
    for b_title, b_body in t1_text:
        p_t = tf_s1.add_paragraph()
        p_t.text = "■ " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_s1.add_paragraph()
        p_b.text = b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # Box 2: Hessian & Structure
    add_card(s3, Inches(0.8) + col_w + gap_w, Inches(1.4), col_w, Inches(5.2))
    tb_s2 = s3.shapes.add_textbox(Inches(0.8) + col_w + gap_w + Inches(0.15), Inches(1.55), col_w - Inches(0.3), Inches(4.9))
    tf_s2 = tb_s2.text_frame
    tf_s2.word_wrap = True
    p = tf_s2.paragraphs[0]
    p.text = "2. Ma trận Hessian & Tensor"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
    
    t2_text = [
        ("Gradient Vector bậc 1:", "∇L = [L_x, L_y]^T\nĐộ lớn |∇L| = √(L_x² + L_y²)\nHướng θ = atan2(L_y, L_x)"),
        ("Ma trận Hessian bậc 2:", "H = [ L_xx   L_xy ]\n    [ L_xy   L_yy ]\nTrị riêng λ₁, λ₂ (λ₁ ≥ λ₂) phản ánh độ cong chính của bề mặt cường độ sáng."),
        ("Tensor Cấu trúc (Structure Tensor):", "S_ρ = G_ρ * [ L_x²     L_x L_y ]\n             [ L_x L_y   L_y²   ]\nĐo lường tính định hướng cục bộ (Coherence).")
    ]
    for b_title, b_body in t2_text:
        p_t = tf_s2.add_paragraph()
        p_t.text = "■ " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_s2.add_paragraph()
        p_b.text = b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # Box 3: Feature Detectors
    add_card(s3, Inches(0.8) + 2 * (col_w + gap_w), Inches(1.4), col_w, Inches(5.2))
    tb_s3 = s3.shapes.add_textbox(Inches(0.8) + 2 * (col_w + gap_w) + Inches(0.15), Inches(1.55), col_w - Inches(0.3), Inches(4.9))
    tf_s3 = tb_s3.text_frame
    tf_s3.word_wrap = True
    p = tf_s3.paragraphs[0]
    p.text = "3. Thuật toán Phát hiện Đặc trưng"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_NAVY
    
    t3_text = [
        ("Canny Edge Detector:", "• Khử cực đại không cực trị (NMS 8 hướng)\n• Phân ngưỡng hysteresis liên kết biên kép\n(T_low, T_high) loại bỏ biên giả."),
        ("Frangi Vesselness (Lọc mạch máu):", "V_0 = 0 nếu λ₂ > 0; ngược lại:\nexp(-R_B² / 2β²) · (1 - exp(-S² / 2c²))\nvới R_B = |λ₁/λ₂|, S = √(λ₁² + λ₂²)."),
        ("Multiscale LoG Blob Detector:", "Cực trị không gian-tỷ lệ của toán tử Laplace chuẩn hóa: ∇²_norm L = σ² (L_xx + L_yy).\nTâm đốm sáng tại (x, y), bán kính r = √2 σ.")
    ]
    for b_title, b_body in t3_text:
        p_t = tf_s3.add_paragraph()
        p_t.text = "■ " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_s3.add_paragraph()
        p_b.text = b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 4: KHẢO SÁT FEATUREJ & TỰ ĐỘNG HÓA WORKFLOW FIJI
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4, COLOR_BG_LIGHT)
    add_header(s4, "3. Khảo sát công cụ tham chiếu", "Khảo sát FeatureJ & Tự động hóa Fiji Workflow", "Giải mã cơ chế xấp xỉ FeatureJ và kịch bản ImageJ Macro xử lý hàng loạt 435 bản đồ TIFF")
    add_footer(s4, 4)

    # 4 KPI cards top
    add_kpi_card(s4, Inches(0.8), Inches(1.35), Inches(2.78), Inches(1.15), "435 TIFF", "Tổng số bản đồ xuất", "423 macro + 12 legacy", COLOR_PRIMARY_BLUE)
    add_kpi_card(s4, Inches(3.78), Inches(1.35), Inches(2.78), Inches(1.15), "369 dòng", "Log thời gian runtime", "303 single + 66 double", COLOR_NAVY)
    add_kpi_card(s4, Inches(6.76), Inches(1.35), Inches(2.78), Inches(1.15), "Float32", "Định dạng ảnh chuẩn", "100% 32-bit không nén", COLOR_EMERALD)
    add_kpi_card(s4, Inches(9.74), Inches(1.35), Inches(2.78), Inches(1.15), "k = 3, 4", "Bậc xấp xỉ Taylor", "Mirror boundary condition", COLOR_PURPLE)

    # Left content: STT 15 Findings
    add_card(s4, Inches(0.8), Inches(2.65), Inches(6.0), Inches(4.0))
    tb_fj = s4.shapes.add_textbox(Inches(0.95), Inches(2.8), Inches(5.7), Inches(3.7))
    tf_fj = tb_fj.text_frame
    tf_fj.word_wrap = True
    p = tf_fj.paragraphs[0]
    p.text = "Khảo sát Kỹ thuật Chuyên sâu FeatureJ (Erik Meijering)"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_PRIMARY_BLUE

    fj_bullets = [
        ("Bậc xấp xỉ Taylor (Order k):", "FeatureJ Derivatives dùng mở rộng Taylor bậc k=3 cho đạo hàm bậc 1, bậc k=4 cho đạo hàm bậc 2 nhằm tối thiểu hóa sai số cắt cụt (truncation error)."),
        ("Điều kiện biên (Boundary Mode):", "Sử dụng phản xạ gương đối xứng (mirror/reflective border) tránh méo mó biên độ vi phân tại các cạnh biên ảnh."),
        ("Quy ước nhân tỷ lệ (Scale Factor):", "FeatureJ KHÔNG nhân thêm σ vào đạo hàm thô (giữ nguyên đơn vị vi phân liên tục gốc), khác với quy chuẩn chuẩn hóa năng lượng của Lindeberg."),
        ("Kiến trúc Macro tự động (batch_process.ijm):", "Đọc cấu hình JSON chuẩn, tự động duyệt 25 ảnh raw (10 BSDS, 10 DRIVE, 5 Blobs), xử lý 4 module (Derivatives, Hessian, Laplacian, Structure) và ghi runtime CSV.")
    ]
    for b_title, b_body in fj_bullets:
        p_t = tf_fj.add_paragraph()
        p_t.text = "• " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_fj.add_paragraph()
        p_b.text = "  " + b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # Right content: Embedded Screenshot
    add_card(s4, Inches(7.0), Inches(2.65), Inches(5.533), Inches(4.0))
    img_fiji = r"docs/fiji/screenshots_chapter3/03_featurej_full_batch_completed.png"
    if os.path.exists(img_fiji):
        s4.shapes.add_picture(img_fiji, Inches(7.2), Inches(2.8), width=Inches(5.133))
    
    tb_img_cap = s4.shapes.add_textbox(Inches(7.2), Inches(6.15), Inches(5.133), Inches(0.4))
    p_ic = tb_img_cap.text_frame.paragraphs[0]
    p_ic.text = "Minh chứng thực nghiệm: Thông báo hoàn tất batch 25 ảnh trên Fiji GUI (435 TIFF, 369 runtime lines)."
    p_ic.font.size = Pt(9); p_ic.font.color.rgb = COLOR_TEXT_MUTED; p_ic.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 5: KIẾN TRÚC PYTHON CORE & TỐI ƯU HÓA THUẬT TOÁN
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5, COLOR_BG_LIGHT)
    add_header(s5, "4. Cài đặt & Tối ưu hóa", "Kiến trúc Python Core & Tối ưu Tích chập 1D", "Triển khai NumPy thuần từ đầu, bảo toàn moment rời rạc và tăng tốc thực nghiệm tới 29x")
    add_footer(s5, 5)

    # Left: Architecture & Discrete Moment
    add_card(s5, Inches(0.8), Inches(1.4), Inches(5.7), Inches(5.2))
    tb_arch = s5.shapes.add_textbox(Inches(1.0), Inches(1.55), Inches(5.3), Inches(4.9))
    tf_arch = tb_arch.text_frame
    tf_arch.word_wrap = True
    p = tf_arch.paragraphs[0]
    p.text = "Triển khai NumPy Thuần & Bảo toàn Moment"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_NAVY

    arch_bullets = [
        ("Thiết kế Zero-Dependencies:", "Toàn bộ nhân vi phân trong src/core/ viết hoàn toàn bằng NumPy mảng liên tục (C-contiguous), không sử dụng OpenCV/SciPy ở tầng lõi thuật toán."),
        ("Định lý Bảo toàn Moment Rời rạc (Discrete Moments):", "Kernel Gaussian rời rạc được ép thỏa mãn chặt chẽ các điều kiện giải tích:\n  • Bậc 0: ∑ K₀ = 1 (bảo toàn năng lượng/độ sáng)\n  • Bậc 1: ∑ K₁ = 0 và ∑ x K₁ = -1 (độ dốc bậc nhất)\n  • Bậc 2: ∑ K₂ = 0 và ∑ x² K₂ = 2 (độ cong bậc hai)"),
        ("Ý nghĩa khoa học:", "Ngăn chặn triệt để hiện tượng dịch chuyển pha (phase shift) và suy hao năng lượng vi phân vốn xảy ra khi lấy mẫu liên tục thô sơ.")
    ]
    for b_title, b_body in arch_bullets:
        p_t = tf_arch.add_paragraph()
        p_t.text = "■ " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_arch.add_paragraph()
        p_b.text = b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # Right: Separable 1D Benchmark (STT 14)
    add_card(s5, Inches(6.8), Inches(1.4), Inches(5.7), Inches(5.2))
    tb_opt = s5.shapes.add_textbox(Inches(7.0), Inches(1.55), Inches(5.3), Inches(4.9))
    tf_opt = tb_opt.text_frame
    tf_opt.word_wrap = True
    p = tf_opt.paragraphs[0]
    p.text = "Benchmark Tối ưu Tách chập 1D (STT 14)"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_EMERALD

    opt_bullets = [
        ("Nguyên lý Tách chập Khả tách (Separable 1D):", "Toán tử Gauss 2D tách thành tích hai nhân 1D: G(x, y) = g(x) · g(y).\nChuyển chập 2D kích thước K×K thành 2 lần chập 1D:\n→ Độ phức tạp giảm từ O(K²) xuống O(2K), lý thuyết tăng tốc K/2 lần."),
        ("Kết quả Đo lường Thực nghiệm (36 trường hợp):", "Đo trên 3 ảnh (bsds_01, drive_01, blob_01) × 4 σ (1, 2, 4, 8) × 3 toán tử:\n  • σ=1 (K=9): Tăng tốc 2.4× - 4.1×\n  • σ=2 (K=17): Tăng tốc 7.8× - 8.3×\n  • σ=4 (K=33): Tăng tốc 14.9× - 16.2×\n  • σ=8 (K=65): Tăng tốc cực đại 27.5× - 29.0×!"),
        ("Kiểm chứng Đúng đắn Tuyệt đối (Sanity Check):", "Sai số tuyệt đối tối đa giữa Naive 2D và Separable 1D trên mọi trường hợp chỉ là 1.28 × 10^-12 (bảo toàn độ chính xác cấp float64).")
    ]
    for b_title, b_body in opt_bullets:
        p_t = tf_opt.add_paragraph()
        p_t.text = "✔ " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_opt.add_paragraph()
        p_b.text = b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 6: NGHIỆM THU TOÁN HỌC TIER 1 (MATHEMATICAL VERIFICATION)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6, COLOR_BG_LIGHT)
    add_header(s6, "5. Kiểm chứng định lượng Tier 1", "Nghiệm thu Toán học Vi phân số Tier 1", "Đối sánh 220 bản đồ vi phân giữa Python Core và Fiji: 35 STRICT, 185 RELAXED, 0 FAIL")
    add_footer(s6, 6)

    # 4 KPI cards top
    add_kpi_card(s6, Inches(0.8), Inches(1.35), Inches(2.78), Inches(1.15), "220 / 220", "Khớp mã SHA-256", "100% bản đồ trùng khớp", COLOR_PRIMARY_BLUE)
    add_kpi_card(s6, Inches(3.78), Inches(1.35), Inches(2.78), Inches(1.15), "35 STRICT", "Sai số < 10^-4", "Gaussian bậc 0 (rel ~10^-8)", COLOR_EMERALD)
    add_kpi_card(s6, Inches(6.76), Inches(1.35), Inches(2.78), Inches(1.15), "185 RELAXED", "Sai số < 10^-2", "Đạo hàm bậc cao (0.3% - 0.9%)", COLOR_AMBER)
    add_kpi_card(s6, Inches(9.74), Inches(1.35), Inches(2.78), Inches(1.15), "r = 0.999997", "Hệ số Pearson trung bình", "Dạng sóng trùng khớp tuyệt đối", COLOR_NAVY)

    # Left: Explanation of Error Root Cause
    add_card(s6, Inches(0.8), Inches(2.65), Inches(6.0), Inches(4.0))
    tb_t1 = s6.shapes.add_textbox(Inches(0.95), Inches(2.8), Inches(5.7), Inches(3.7))
    tf_t1 = tb_t1.text_frame
    tf_t1.word_wrap = True
    p = tf_t1.paragraphs[0]
    p.text = "Phân tích Khoa học Gốc rễ Sai số 185 RELAXED"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_PRIMARY_BLUE

    t1_notes = [
        ("Gaussian Smoothing (Bậc 0):", "Đạt chuẩn STRICT tuyệt đối (20/20 bản đồ) với sai số tương đối chỉ ~10^-8 (mức độ làm tròn float32)."),
        ("Đạo hàm bậc cao (Lx, Ly, Lxx, Lyy, Hessian):", "Đạt mức RELAXED với sai số tương đối ổn định từ 0.3% đến 0.9%."),
        ("Nguyên nhân bản chất giữa 2 nền tảng:", "  • FeatureJ: Lấy mẫu trực tiếp từ đạo hàm Gauss giải tích liên tục (chưa chuẩn hóa moment rời rạc).\n  • Python Core: Ép điều kiện bảo toàn moment rời rạc ∑ x² K₂ = 2 trên lưới pixel hữu hạn."),
        ("Kết luận toán học:", "Sai số này là sai số xấp xỉ số học thuần túy (discretization error), hoàn toàn không làm biến dạng cấu trúc không gian (chứng minh bởi tương quan Pearson r > 0.999997 và ΔF1 = 0.000000 ở Tier 2).")
    ]
    for b_title, b_body in t1_notes:
        p_t = tf_t1.add_paragraph()
        p_t.text = "• " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_t1.add_paragraph()
        p_b.text = "  " + b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # Right: Embedded Comparison Figure
    add_card(s6, Inches(7.0), Inches(2.65), Inches(5.533), Inches(4.0))
    img_div = r"docs/report_template/figures/showcase_scientific_diverging_maps.png"
    if os.path.exists(img_div):
        s6.shapes.add_picture(img_div, Inches(7.15), Inches(2.8), width=Inches(5.233))
    
    tb_t1_cap = s6.shapes.add_textbox(Inches(7.2), Inches(6.15), Inches(5.133), Inches(0.4))
    p_tc = tb_t1_cap.text_frame.paragraphs[0]
    p_tc.text = "Bản đồ vi sai phân giải cao (Diverging Colormap): Python vs Fiji và sai số dư thừa cấp vi mô."
    p_tc.font.size = Pt(9); p_tc.font.color.rgb = COLOR_TEXT_MUTED; p_tc.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 7: THỰC NGHIỆM TIER 2 — PHÁT HIỆN BIÊN BSDS500
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7, COLOR_BG_LIGHT)
    add_header(s7, "6. Thực nghiệm định lượng Tier 2", "Phát hiện Biên Đa tỷ lệ trên Bộ dữ liệu BSDS500", "Tối ưu hóa ngưỡng phân vị trên 56 bộ nhãn người vẽ: F1 = 0.477886, độ chênh lệch tuyệt đối ΔF1 = 0.000000")
    add_footer(s7, 7)

    # 4 KPI cards top
    add_kpi_card(s7, Inches(0.8), Inches(1.35), Inches(2.78), Inches(1.15), "F1 = 0.477886", "Đỉnh F1 Fair Canny", "σ=2.0, p_low=67, p_high=91", COLOR_PRIMARY_BLUE)
    add_kpi_card(s7, Inches(3.78), Inches(1.35), Inches(2.78), Inches(1.15), "ΔF1 = 0.000000", "Chênh lệch với Fiji Canny", "Khớp tuyệt đối trên cùng độ dốc", COLOR_EMERALD)
    add_kpi_card(s7, Inches(6.76), Inches(1.35), Inches(2.78), Inches(1.15), "56 bộ nhãn", "Ground Truth BSDS500", "10 ảnh tự nhiên đa dạng", COLOR_NAVY)
    add_kpi_card(s7, Inches(9.74), Inches(1.35), Inches(2.78), Inches(1.15), "F1 = 0.5008", "FeatureJ Edges (Ref)", "Thuật toán riêng của Meijering", COLOR_PURPLE)

    # Left: Methodology & Analysis
    add_card(s7, Inches(0.8), Inches(2.65), Inches(6.0), Inches(4.0))
    tb_b = s7.shapes.add_textbox(Inches(0.95), Inches(2.8), Inches(5.7), Inches(3.7))
    tf_b = tb_b.text_frame
    tf_b.word_wrap = True
    p = tf_b.paragraphs[0]
    p.text = "Giao thức Thực nghiệm & Phân tích Kết quả"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_PRIMARY_BLUE

    b_bullets = [
        ("Giao thức Quét Lưới Ngưỡng Động (Percentile Grid):", "Duyệt 100 cặp ngưỡng phân vị (p_low, p_high) từ 50% đến 99% kết hợp 4 tỷ lệ σ ∈ {1, 2, 4, 8} nhằm thích ứng hoàn hảo với phân phối cường độ sáng từng ảnh."),
        ("Sự trùng khớp tuyệt đối (Fair Canny):", "Cùng áp dụng thuật toán Canny trên gradient do Python và Fiji tính toán, cả hai đạt đỉnh F1 = 0.477886 tại cùng tọa độ ngưỡng (p_low=67.0, p_high=91.0, σ=2.0) với ΔF1 = 0.000000!"),
        ("Phân định minh bạch với FeatureJ Edges:", "Module 'FeatureJ Edges' tích hợp sẵn của tác giả Meijering đạt đỉnh F1 = 0.5436 tại σ=1.0 do sử dụng tiêu chuẩn zero-crossing của đạo hàm hướng bậc 2 thay vì Canny chuẩn."),
        ("Đường cong Precision-Recall:", "Xác nhận khả năng cân bằng vượt trội giữa độ nhạy biên và khả năng triệt tiêu nhiễu nền kết cấu tự nhiên.")
    ]
    for b_title, b_body in b_bullets:
        p_t = tf_b.add_paragraph()
        p_t.text = "• " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_b.add_paragraph()
        p_b.text = "  " + b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # Right: Embedded Heatmap
    add_card(s7, Inches(7.0), Inches(2.65), Inches(5.533), Inches(4.0))
    img_hm = r"docs/report_template/figures/tier2_bsds_f1_heatmap.png"
    if os.path.exists(img_hm):
        s7.shapes.add_picture(img_hm, Inches(7.2), Inches(2.8), width=Inches(5.133))
    
    tb_hm_cap = s7.shapes.add_textbox(Inches(7.2), Inches(6.15), Inches(5.133), Inches(0.4))
    p_hc = tb_hm_cap.text_frame.paragraphs[0]
    p_hc.text = "Biểu đồ nhiệt (F1 Heatmap) không gian tham số (p_low, p_high, σ) trên 10 ảnh BSDS500."
    p_hc.font.size = Pt(9); p_hc.font.color.rgb = COLOR_TEXT_MUTED; p_hc.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 8: THỰC NGHIỆM TIER 2 — MẠCH MÁU DRIVE & BLOB TẾ BÀO
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8, COLOR_BG_LIGHT)
    add_header(s8, "7. Thực nghiệm định lượng Tier 2", "Phát hiện Mạch máu Võng mạc DRIVE & Đốm sáng Sinh học", "Bộ lọc hình ống Frangi Hessian (kỹ thuật FOV Erosion) và định vị tế bào đa tỷ lệ LoG")
    add_footer(s8, 8)

    # Left: DRIVE Vesselness
    add_card(s8, Inches(0.8), Inches(1.4), Inches(5.7), Inches(5.2))
    tb_dr = s8.shapes.add_textbox(Inches(1.0), Inches(1.55), Inches(5.3), Inches(4.9))
    tf_dr = tb_dr.text_frame
    tf_dr.word_wrap = True
    p = tf_dr.paragraphs[0]
    p.text = "1. Mạch máu Võng mạc DRIVE (Frangi Vesselness)"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_RED

    dr_bullets = [
        ("Trích xuất trên Kênh Xanh lá (Green Channel):", "Tận dụng kênh Green có độ hấp thụ hemoglobin tối đa, độ tương phản lòng mạch cao nhất so với Red/Blue."),
        ("Sáng kiến Kỹ thuật FOV Adaptive Erosion:", "Viền trường nhìn nhãn cầu tạo bước nhảy cường độ cực lớn sinh biên giả mạch máu. Nhóm đề xuất co mặt nạ FOV thích ứng ⌈4σ⌉ pixel → Triệt tiêu hoàn toàn biên giả mép nhãn cầu!"),
        ("Chỉ số định lượng đối sánh:", "  • Python: F1 = 0.680633\n  • Fiji: F1 = 0.681651\n  • Độ lệch siêu nhỏ: ΔF1 = -0.001018 (~0.15% sai số tương đối), chứng minh khả năng tái tạo chuẩn xác hình thái mao mạch.")
    ]
    for b_title, b_body in dr_bullets:
        p_t = tf_dr.add_paragraph()
        p_t.text = "■ " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_dr.add_paragraph()
        p_b.text = b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # Right: Multiscale Blobs
    add_card(s8, Inches(6.8), Inches(1.4), Inches(5.7), Inches(5.2))
    tb_bl = s8.shapes.add_textbox(Inches(7.0), Inches(1.55), Inches(5.3), Inches(4.9))
    tf_bl = tb_bl.text_frame
    tf_bl.word_wrap = True
    p = tf_bl.paragraphs[0]
    p.text = "2. Phát hiện Đốm sáng & Tế bào (Multiscale LoG)"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_PURPLE

    bl_bullets = [
        ("Ảnh nhân tạo kiểm chứng (blob_01 - 04):", "Thuật toán phát hiện đạt F1 = 1.0000 hoàn hảo trên toàn bộ 16 đốm sáng nhân tạo, định vị chính xác tâm và bán kính lý thuyết."),
        ("Ảnh tế bào hiển vi phức tạp (blob_05):", "  • Ground Truth: 276 tế bào thực tế + 15 vùng loại trừ (ignore mask).\n  • Kết quả: Bắt chính xác 140 tế bào, đạt F1 = 0.4651."),
        ("Tổng kết toàn bộ tập Blob:", "  • Macro-F1 = 0.8930 (độ nhạy cao trên các lớp hình thái)\n  • Micro-F1 = 0.4921 (tính tổng gộp toàn bộ cá thể tế bào).")
    ]
    for b_title, b_body in bl_bullets:
        p_t = tf_bl.add_paragraph()
        p_t.text = "✔ " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_bl.add_paragraph()
        p_b.text = b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # Small thumbnail in right box
    img_bl = r"docs/09_11/ground_truth_figures/02_blob_05_overlay.png"
    if os.path.exists(img_bl):
        s8.shapes.add_picture(img_bl, Inches(7.2), Inches(4.5), width=Inches(4.9))

    # =========================================================================
    # SLIDE 9: ĐÁNH GIÁ HIỆU NĂNG & THỜI GIAN THỰC THI (RUNTIME BENCHMARK)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9, COLOR_BG_LIGHT)
    add_header(s9, "8. Benchmark hiệu năng hệ thống", "Đánh giá Hiệu năng Thời gian: Python vs Fiji Java", "Phân tích thực nghiệm 369 phép đo thời gian và tác động của chi phí I/O tập tin")
    add_footer(s9, 9)

    # Left: Embedded Runtime Chart
    add_card(s9, Inches(0.8), Inches(1.4), Inches(5.7), Inches(5.2))
    img_rt = r"docs/report_template/figures/tier2_runtime_comparison.png"
    if os.path.exists(img_rt):
        s9.shapes.add_picture(img_rt, Inches(1.0), Inches(1.6), width=Inches(5.3))
    
    tb_rt_cap = s9.shapes.add_textbox(Inches(1.0), Inches(6.0), Inches(5.3), Inches(0.4))
    p_rc = tb_rt_cap.text_frame.paragraphs[0]
    p_rc.text = "Biểu đồ so sánh thời gian thực thi (Runtime Comparison) giữa Python và Fiji Java."
    p_rc.font.size = Pt(9); p_rc.font.color.rgb = COLOR_TEXT_MUTED; p_rc.alignment = PP_ALIGN.CENTER

    # Right: Detailed Analysis
    add_card(s9, Inches(6.8), Inches(1.4), Inches(5.7), Inches(5.2))
    tb_rt_an = s9.shapes.add_textbox(Inches(7.0), Inches(1.55), Inches(5.3), Inches(4.9))
    tf_rt_an = tb_rt_an.text_frame
    tf_rt_an.word_wrap = True
    p = tf_rt_an.paragraphs[0]
    p.text = "Phân tích Chuyên sâu Hiệu năng Tính toán"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_NAVY

    rt_bullets = [
        ("Quy mô Khảo sát Đồng bộ:", "Đối chiếu song song 369 cặp đo thời gian thực tế giữa Python Core và Fiji (Java HotSpot 64-Bit Server VM)."),
        ("Hiệu quả Tính toán Thuần (Pure Compute):", "NumPy thuần kết hợp tích chập khả tách 1D đạt tốc độ tính toán cạnh tranh trực tiếp với mã máy biên dịch JIT của Java, hoàn thành các phép vi phân ma trận trong vài mili-giây."),
        ("Nút thắt I/O và Quản lý Bộ nhớ (Bottleneck Analysis):", "  • Fiji tiêu tốn tới 65% thời gian tổng cho việc khởi tạo đối tượng Java ImagePlus, cập nhật giao diện Swing/AWT và ghi file TIFF uncompressed.\n  • Python được tối ưu hóa luồng I/O mảng bộ nhớ đệm giúp tiết kiệm đáng kể thời gian đọc ghi trong các đường ống xử lý lớn."),
        ("Khuyến nghị Triển khai Thực tế:", "Với hệ thống thị giác nhúng hoặc server đám mây, giải pháp Python Core không phụ thuộc thư viện nặng mang lại tính di động và độ linh hoạt cao hơn.")
    ]
    for b_title, b_body in rt_bullets:
        p_t = tf_rt_an.add_paragraph()
        p_t.text = "■ " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_rt_an.add_paragraph()
        p_b.text = b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 10: ĐÓNG GÓP VƯỢT TRỘI & BÀI HỌC KINH NGHIỆM
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10, COLOR_BG_LIGHT)
    add_header(s10, "9. Giá trị gia tăng & Đóng góp", "Đóng góp Vượt trội & Bài học Kinh nghiệm Dự án", "5 cải tiến kỹ thuật vượt trên yêu cầu ban đầu và những bài học đúc kết trong nghiên cứu khoa học")
    add_footer(s10, 10)

    # 5 Key Innovations
    add_card(s10, Inches(0.8), Inches(1.4), Inches(5.7), Inches(5.2))
    tb_inn = s10.shapes.add_textbox(Inches(1.0), Inches(1.55), Inches(5.3), Inches(4.9))
    tf_inn = tb_inn.text_frame
    tf_inn.word_wrap = True
    p = tf_inn.paragraphs[0]
    p.text = "5 Sáng kiến Kỹ thuật Vượt Yêu cầu Ban đầu"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_EMERALD

    innovations = [
        ("1. Chuẩn hóa Moment Rời rạc:", "Giải quyết tận gốc rễ sai số dịch pha vi phân, không dừng lại ở việc cắt tỉa Gaussian thông thường."),
        ("2. Kỹ thuật FOV Adaptive Erosion:", "Độc lập phát hiện và xử lý biên giả nhãn cầu DRIVE bằng thuật toán co biên thích ứng theo độ rộng lọc ⌈4σ⌉."),
        ("3. Lưới dò Ngưỡng Phân vị Động:", "Thay vì dò ngưỡng cường độ cố định, nhóm thiết kế lưới percentile bất biến với độ sáng ảnh."),
        ("4. Pipeline Tự động hóa Khép kín 100%:", "Bộ kiểm thử tự động run_tests, test_ground_truth, validator 435 TIFF đảm bảo không lỗi phát sinh."),
        ("5. Báo cáo Chuẩn IEEE LaTeX Đầy đủ:", "Quyển báo cáo khoa học ~30 trang hoàn chỉnh công thức, chứng minh toán học và phân tích thực nghiệm.")
    ]
    for b_title, b_body in innovations:
        p_t = tf_inn.add_paragraph()
        p_t.text = b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_inn.add_paragraph()
        p_b.text = "  " + b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # Lessons Learned
    add_card(s10, Inches(6.8), Inches(1.4), Inches(5.7), Inches(5.2))
    tb_les = s10.shapes.add_textbox(Inches(7.0), Inches(1.55), Inches(5.3), Inches(4.9))
    tf_les = tb_les.text_frame
    tf_les.word_wrap = True
    p = tf_les.paragraphs[0]
    p.text = "Bài học Kinh nghiệm Nghiên cứu & Làm việc Nhóm"
    p.font.size = Pt(13); p.font.bold = True; p.font.color.rgb = COLOR_NAVY

    lessons = [
        ("Tầm quan trọng của Thẩm định Toán học:", "Không bao giờ vội vàng đánh giá metric ứng dụng (F1) khi chưa kiểm chứng mức độ chính xác của các bản đồ vi phân thành phần."),
        ("Minh bạch trong Nghiên cứu Khoa học:", "Trung thực báo cáo 35 STRICT / 185 RELAXED thay vì che giấu sai số; giải thích tường tận nguyên nhân số học tạo nên sự thuyết phục tối đa."),
        ("Kỷ luật Làm việc Nhóm & Phiên bản Git:", "Phân chia trách nhiệm độc lập theo 4 role, chuẩn hóa cấu trúc nhánh Git (dev/NguyenDucManh, fiji/PhamBaoLoc, thucnghiem/BuiTrungDuc) và kiểm soát xung đột dữ liệu lớn.")
    ]
    for b_title, b_body in lessons:
        p_t = tf_les.add_paragraph()
        p_t.text = "■ " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = COLOR_TEXT_PRIMARY
        p_b = tf_les.add_paragraph()
        p_b.text = "  " + b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 11: PHÂN CÔNG NHIỆM VỤ & TIẾN ĐỘ HOÀN THÀNH
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11, COLOR_BG_LIGHT)
    add_header(s11, "10. Quản lý dự án", "Phân công Nhiệm vụ & Bảng Trách nhiệm Thành viên", "Khớp chuẩn 100% theo bảng gợi ý phân công 4 thành viên trong đề cương bài tập lớn")
    add_footer(s11, 11)

    # Table of Roles
    rows = 5
    cols = 4
    left = Inches(0.8)
    top = Inches(1.5)
    width = Inches(11.733)
    height = Inches(5.0)

    table_shape = s11.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table
    table.columns[0].width = Inches(2.2)
    table.columns[1].width = Inches(1.8)
    table.columns[2].width = Inches(6.0)
    table.columns[3].width = Inches(1.733)

    table_data = [
        ["Thành viên", "Vai trò Dự án", "Nhiệm vụ Phụ trách Trọng tâm", "Tiến độ"],
        ["Nguyễn Đức Mạnh\n(STT 37 - Trưởng nhóm)", "Thành viên 2\n(Lead Developer)", "• Cài đặt 100% thuật toán vi phân, Canny, Frangi, LoG bằng NumPy thuần\n• Tối ưu tích chập khả tách 1D (STT 14, đo benchmark 36 case)\n• Xây dựng bộ kịch bản kiểm chứng tự động Tier 1 & Tier 2\n• Điều phối dự án, đồng bộ Git repository và khóa số liệu", "HOÀN THÀNH\n100% (Xanh QA)"],
        ["Phạm Bảo Lộc", "Thành viên 3\n(Fiji / Macro)", "• Khảo sát plugin FeatureJ (tham số k, border mode, scale factor - STT 15)\n• Xây dựng và hoàn thiện ImageJ Macro batch_process.ijm\n• Xuất đủ 435 TIFF float32 và 369 dòng runtime CSV\n• Biên soạn 2 tài liệu quy trình DOCX chuẩn mực", "HOÀN THÀNH\n100% (Đã kiểm tra)"],
        ["Bùi Trung Đức", "Thành viên 4\n(Data & Benchmark)", "• Thu thập và chuẩn hóa 25 ảnh raw (BSDS500, DRIVE, Blobs)\n• Xây dựng bộ Ground Truth đối chiếu (56 BSDS, rà soát tế bào blob_05)\n• Thiết lập thực nghiệm quét lưới tham số và tính metric F1-score\n• Vẽ biểu đồ trực quan, đường cong PR, Heatmap và đóng gói ZIP", "HOÀN THÀNH\n100% (Đã lưu trữ)"],
        ["Nguyễn Tiến Hưng", "Thành viên 1\n(Theory & Report)", "• Nghiên cứu cơ sở lý thuyết toán học không gian tỷ lệ Lindeberg\n• Tổng hợp số liệu và phân tích định lượng từ các thành viên\n• Biên soạn Báo cáo khoa học IEEE LaTeX (~30 trang trên Overleaf)\n• Hoàn thiện bản in PDF chính thức nộp hội đồng", "ĐANG HOÀN THIỆN\nBẢN IN OVERLEAF"]
    ]

    for r_idx, row_content in enumerate(table_data):
        for c_idx, cell_value in enumerate(row_content):
            cell = table.cell(r_idx, c_idx)
            cell.text = cell_value
            p = cell.text_frame.paragraphs[0]
            p.font.name = "Arial"
            if r_idx == 0:
                p.font.bold = True
                p.font.size = Pt(11)
                p.font.color.rgb = RGBColor(255, 255, 255)
                cell.fill.solid()
                cell.fill.fore_color.rgb = COLOR_NAVY
            else:
                p.font.size = Pt(9.5)
                if c_idx == 3:
                    p.font.bold = True
                    p.font.color.rgb = COLOR_EMERALD if "HOÀN THÀNH" in cell_value else COLOR_AMBER
                elif c_idx == 0:
                    p.font.bold = True
                    p.font.color.rgb = COLOR_TEXT_PRIMARY
                else:
                    p.font.color.rgb = COLOR_TEXT_MUTED
                cell.fill.solid()
                cell.fill.fore_color.rgb = COLOR_CARD_LIGHT if r_idx % 2 == 1 else RGBColor(241, 245, 249)

    # =========================================================================
    # SLIDE 12: KẾT LUẬN, MÃ NGUỒN MỞ & HỎI ĐÁP (Q&A) (DARK THEME)
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_background(s12, COLOR_BG_DARK)

    # Accent decorative bar
    dec_bar12 = s12.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.8), Inches(11.733), Inches(0.04))
    dec_bar12.fill.solid()
    dec_bar12.fill.fore_color.rgb = COLOR_PRIMARY_BLUE
    dec_bar12.line.fill.background()

    # Title & Subtitle Box
    tb12 = s12.shapes.add_textbox(Inches(0.8), Inches(1.1), Inches(11.733), Inches(1.5))
    tf12 = tb12.text_frame
    tf12.word_wrap = True
    p = tf12.paragraphs[0]
    p.text = "KẾT LUẬN & PHIÊN HỎI ĐÁP (Q&A)"
    p.font.name = "Arial"; p.font.size = Pt(28); p.font.bold = True; p.font.color.rgb = RGBColor(255, 255, 255)

    p_sub12 = tf12.add_paragraph()
    p_sub12.text = "Tổng kết dự án Bài tập lớn Xử lý Ảnh số - Sẵn sàng cho phần phản biện của Hội đồng"
    p_sub12.font.name = "Arial"; p_sub12.font.size = Pt(13); p_sub12.font.color.rgb = RGBColor(148, 163, 184)

    # Left: Summary Box
    add_card(s12, Inches(0.8), Inches(2.6), Inches(5.7), Inches(3.8), COLOR_CARD_DARK, COLOR_BORDER_DARK)
    tb_sum = s12.shapes.add_textbox(Inches(1.0), Inches(2.8), Inches(5.3), Inches(3.4))
    tf_sum = tb_sum.text_frame
    tf_sum.word_wrap = True
    p = tf_sum.paragraphs[0]
    p.text = "Tổng kết Thành tựu Dự án"
    p.font.size = Pt(14); p.font.bold = True; p.font.color.rgb = COLOR_PRIMARY_BLUE

    sum_points = [
        ("Thực nghiệm quy mô lớn:", "Hoàn thành toàn diện 435 bản đồ Fiji + 415 bản đồ Python, 369 phép đo thời gian và 25 ảnh benchmark."),
        ("Chuẩn xác toán học tuyệt đối:", "Đạt 220/220 SHA-256 match, chứng minh bản chất sai số 185 RELAXED là do bảo toàn moment rời rạc; Pearson r = 0.99999710."),
        ("Hiệu năng đỉnh cao ứng dụng:", "Peak Canny F1 = 0.477886 (ΔF1 = 0.000000 vs Fiji), Frangi DRIVE F1 = 0.6806, Blobs F1 = 1.0000 (synthetic)."),
        ("Tối ưu hóa tách chập 1D thực tế:", "Tăng tốc thực nghiệm lên tới 29.0x với sai số số học ở mức 10^-12.")
    ]
    for b_title, b_body in sum_points:
        p_t = tf_sum.add_paragraph()
        p_t.text = "✔ " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = RGBColor(255, 255, 255)
        p_b = tf_sum.add_paragraph()
        p_b.text = "  " + b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = RGBColor(203, 213, 225)

    # Right: Open Source & Q&A Box
    add_card(s12, Inches(6.8), Inches(2.6), Inches(5.7), Inches(3.8), COLOR_CARD_DARK, COLOR_BORDER_DARK)
    tb_qa = s12.shapes.add_textbox(Inches(7.0), Inches(2.8), Inches(5.3), Inches(3.4))
    tf_qa = tb_qa.text_frame
    tf_qa.word_wrap = True
    p = tf_qa.paragraphs[0]
    p.text = "Tài nguyên Dự án & Thông tin Liên hệ"
    p.font.size = Pt(14); p.font.bold = True; p.font.color.rgb = COLOR_EMERALD

    qa_points = [
        ("Kho lưu trữ GitHub chính thức:", "https://github.com/ndmanh1811/XLA.git\n(Bao gồm mã nguồn Python, ImageJ Macro, Dữ liệu Ground Truth, LaTeX Report và Slide này)"),
        ("Sản phẩm bàn giao đầy đủ:", "• Quyển Báo cáo khoa học IEEE (~30 trang PDF)\n• Slide trình chiếu bảo vệ 12 trang (PPTX/PDF)\n• Toàn bộ kho nghiệm thu số liệu CSV & mã nguồn mở"),
        ("Trân trọng cảm ơn Thầy và các bạn đã lắng nghe!", "Nhóm xin sẵn sàng tiếp nhận các câu hỏi phản biện từ Hội đồng.")
    ]
    for b_title, b_body in qa_points:
        p_t = tf_qa.add_paragraph()
        p_t.text = "■ " + b_title
        p_t.font.size = Pt(10.5); p_t.font.bold = True; p_t.font.color.rgb = RGBColor(255, 255, 255)
        p_b = tf_qa.add_paragraph()
        p_b.text = "  " + b_body
        p_b.font.size = Pt(9.5); p_b.font.color.rgb = RGBColor(203, 213, 225)

    # Output file
    output_path = r"docs/slides/BTL_XLA_Nhom_BaoCao.pptx"
    prs.save(output_path)
    print(f"Presentation generated successfully at: {output_path}")

if __name__ == "__main__":
    create_presentation()
