"""Create a self-contained DOCX and Markdown GT handoff for Hung, 09/11.

Uses standard-library OOXML only; copies exact reviewed overlays unchanged.
Run from the project root: python tools/create_gt_handoff_09_11.py
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.eval.metric_utils import validate_inputs

OUT = ROOT / "docs/09_11"
STEM = "GUI_HUNG_GROUND_TRUTH_09_11"


def paragraph(text, style=None, bold=False, center=False, size=None):
    ppr = (f'<w:pStyle w:val="{style}"/>' if style else "") + ('<w:jc w:val="center"/>' if center else "")
    rpr = ('<w:b/>' if bold else "") + (f'<w:sz w:val="{size}"/>' if size else "")
    return f'<w:p><w:pPr>{ppr}</w:pPr><w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def table(headers, rows):
    widths = [1800, 4200, 3638]
    def cell(text, index, header=False):
        shade = '<w:shd w:fill="E6F1F4"/>' if header else ""
        return f'<w:tc><w:tcPr><w:tcW w:w="{widths[index]}" w:type="dxa"/>{shade}</w:tcPr>{paragraph(text, bold=header, size=20)}</w:tc>'
    head = '<w:tr><w:trPr><w:tblHeader/></w:trPr>' + ''.join(cell(t, i, True) for i, t in enumerate(headers)) + '</w:tr>'
    body = ''.join('<w:tr><w:trPr><w:cantSplit/></w:trPr>' + ''.join(cell(t, i) for i, t in enumerate(row)) + '</w:tr>' for row in rows)
    return '<w:tbl><w:tblPr><w:tblW w:w="9638" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblBorders>' + ''.join(f'<w:{k} w:val="single" w:sz="4" w:color="CBD9DE"/>' for k in ['top','left','bottom','right','insideH','insideV']) + '</w:tblBorders><w:tblCellMar><w:top w:w="85" w:type="dxa"/><w:left w:w="100" w:type="dxa"/><w:bottom w:w="85" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>' + ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths) + '</w:tblGrid>' + head + body + '</w:tbl>'


def picture(rel, ident, name, width_cm, height_cm):
    cx, cy = int(width_cm*360000), int(height_cm*360000)
    return f'''<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">
<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{ident}" name="{escape(name)}" descr="{escape(name)}"/>
<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>
<pic:nvPicPr><pic:cNvPr id="0" name="{escape(name)}"/><pic:cNvPicPr/></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="{rel}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'''


def main():
    gt, evidence = validate_inputs()
    bsds = [r for r in gt if r['kind'] == 'bsds']
    counts = [r['annotators'] for r in bsds]
    cell = json.loads((ROOT / 'data/gt/blob/blob_05.json').read_text(encoding='utf-8'))
    assert len(cell['objects']) == 276 and len(cell['ignore_regions']) == 15
    figures = OUT / 'ground_truth_figures'
    figures.mkdir(parents=True, exist_ok=True)
    selected = [('bsds_01', '01_bsds_01_overlay.png'), ('blob_05', '02_blob_05_overlay.png')]
    for image, name in selected:
        shutil.copyfile(ROOT / f'data/gt/previews/{image}_overlay.png', figures / name)
    summary_rows = [
        ('BSDS500 — 10 ảnh', f'{min(counts)}–{max(counts)} người gán nhãn/ảnh; tổng {sum(counts)} bộ nhãn biên/phân vùng. Giữ riêng mọi annotator.', 'data/gt/bsds/: .mat gốc; boundaries PNG uint8 0/255; segments TIFF uint16.'),
        ('DRIVE — 10 ảnh', 'Mỗi ảnh có mask mạch máu 1st_manual và FOV mask cùng kích thước. Trắng=255, đen=0. FOV xác định vùng được phép đánh giá.', 'data/gt/drive/*_vessels.png và *_fov.png. FOV gốc chưa xói mòn.'),
        ('Blob tổng hợp — 4 ảnh', '4 đối tượng/ảnh, tổng 16; tâm và bán kính từ công thức sinh ảnh, gồm cực tính bright/dark.', 'data/gt/blob/blob_01.json đến blob_04.json.'),
        ('Tế bào — blob_05', '276 đối tượng dương tính đã duyệt + 15 vùng loại trừ; ảnh 512×512, polarity=bright; READY, reviewer=Duc.', 'data/gt/blob/blob_05.json: objects, ignore_regions, tâm (x,y), bán kính và bbox.'),
    ]
    count_text = '; '.join(f"{r['image']}: {r['annotators']}" for r in bsds)
    note = 'Lưu ý kiểm kê BSDS: yêu cầu trao đổi nhắc khoảng 4–8 người/ảnh; riêng 10 ảnh thực nghiệm đã chọn có 5–7 người/ảnh, tổng 56 bộ nhãn. Khi mô tả bộ mẫu của nhóm, dùng con số kiểm đếm này. 56 là số bộ nhãn theo ảnh, không phải 56 người khác nhau.'
    ignore = '15 vùng loại trừ hiện lưu dưới dạng các hình chữ nhật trong ignore_regions của JSON, không phải 15 đối tượng âm tính và không phải một mask PNG độc lập. Khi đánh giá, dự đoán có tâm nằm trong vùng này (kể cả biên) được bỏ khỏi ghép nhãn và tính FP. Không dùng ảnh overlay màu thay cho dữ liệu GT.'
    paragraph_for_report = 'Bộ dữ liệu thực nghiệm gồm 25 ảnh với nhãn tham chiếu tương ứng. Với 10 ảnh BSDS500, nhóm giữ riêng toàn bộ nhãn của 5–7 người gán nhãn cho mỗi ảnh, tổng cộng 56 bộ nhãn biên/phân vùng. Với 10 ảnh DRIVE, nhãn mạch máu được dùng cùng mặt nạ trường quan sát (FOV) để giới hạn vùng đánh giá. Bốn ảnh blob tổng hợp có 16 đối tượng được xác định giải tích. Ảnh sinh học blob_05 có 276 nhân/tế bào được gán nhãn dương tính và 15 vùng loại trừ đã được Đức rà soát. Nhãn tế bào là nhãn do nhóm xây dựng, có hỗ trợ gợi ý và kiểm duyệt thủ công; không xem là nhãn chuyên gia chính thức từ nhà cung cấp dữ liệu.'
    caption1 = 'Hình 4.x. Ground truth biên của ảnh bsds_01 chồng lên ảnh xám gốc. Đường cyan là biên của annotator 01; ảnh này có 6 bộ nhãn độc lập được giữ riêng. Hình minh họa một bộ nhãn, không phải hợp nhất của 6 annotator và không phải kết quả phát hiện của thuật toán.'
    caption2 = 'Hình 4.y. Ground truth của ảnh tế bào blob_05: vòng xanh lá biểu diễn tâm/bán kính quy ước của 276 đối tượng đã duyệt; số vàng là ID đối tượng; khung cam là 15 vùng loại trừ. Các khung cam chỉ hiển thị biên vùng ignore, không phải mask phân đoạn tế bào.'
    sources = 'Căn cứ kiểm kê: data/metadata/ground_truth_inventory.csv; data/gt/manifest.json; data/gt/blob/blob_05.json. Đã đối chiếu SHA-256 input và nhãn, đủ 25/25 READY tại thời điểm chuẩn bị 08/11/2026. Đây là tài liệu chuẩn bị để gửi ngày 09/11, chưa thực hiện gửi cho Hưng.'
    md = ['# Cần gửi Hưng ngày 09/11 — Tóm tắt Ground Truth', '',
          '**Người chuẩn bị:** Đức. **Người nhận dự kiến:** Hưng. **Mục đích:** bảng và hình minh họa cho Chương 4.', '',
          'File Word cùng tên đã nhúng hai ảnh: có thể gửi riêng file `.docx` mà không cần kèm thư mục ảnh.', '',
          '## 1. Bảng tóm tắt', '', '| Nhóm dữ liệu | Thông số Ground Truth | Tệp và quy ước |', '| --- | --- | --- |']
    md += ['| ' + ' | '.join(row) + ' |' for row in summary_rows]
    md += ['', '**Số người gán nhãn trên từng ảnh BSDS:** ' + count_text + '.', '', note, '',
           '**FOV DRIVE:** mask trắng là vùng quan sát hợp lệ; không chấm nền ngoài FOV. FOV gốc giữ nguyên; bước đánh giá Frangi mới xói mòn theo support kernel/scale (bộ đa tỷ lệ hiện tại dùng giao vùng hợp lệ, tương ứng 32 px). Không nhầm FOV với mask mạch máu.', '',
           '**Ignore của ảnh tế bào:** ' + ignore, '', '## 2. Đoạn có thể đưa vào Chương 4', '', paragraph_for_report, '',
           '## 3. Hai hình minh họa và chú thích', '', '### BSDS500 — biên của annotator 01', '',
           '![Overlay BSDS](ground_truth_figures/01_bsds_01_overlay.png)', '', caption1, '',
           'Tệp ảnh gốc: `data/raw/bsds_01.png` (481×321); mask: `data/gt/bsds/bsds_01/annotator_01_boundaries.png`. PNG được sao chép nguyên vẹn từ preview đã kiểm tra; không đổi kích thước hay làm dày biên.', '',
           '### blob_05 — tế bào và vùng ignore', '', '![Overlay tế bào](ground_truth_figures/02_blob_05_overlay.png)', '', caption2, '',
           'Tệp ảnh gốc: `data/raw/blob_05.png` (512×512); nhãn: `data/gt/blob/blob_05.json`. Vòng tròn chỉ minh họa tâm/bán kính, không phải contour phân đoạn chính xác từng tế bào.', '',
           '## 4. Cách dùng và nguồn kiểm tra', '',
           '- Hưng mở DOCX bằng Word, lấy bảng và hai hình/chú thích để chèn vào Chương 4; đổi 4.x/4.y theo số hình thực tế.',
           '- Muốn chèn PNG riêng: dùng hai file trong `ground_truth_figures/`; giữ nguyên tỷ lệ khung hình. Ảnh có độ phân giải gốc, không tăng kích thước để giả lập thêm chi tiết.',
           '- Overlay dùng minh họa, không được dùng làm mask đầu vào tính metric. Khi tính metric, đọc nhãn/mask/JSON đã nêu.', '', sources, '']
    (OUT / f'{STEM}.md').write_text('\n'.join(md), encoding='utf-8')

    body = [paragraph('GROUND TRUTH — GỬI HƯNG 09/11', 'Title'),
            paragraph('Đức chuẩn bị 08/11/2026 • Dùng cho Chương 4 • Chưa gửi', 'Subtitle'),
            paragraph('1. Bảng tóm tắt thông số', 'Heading1'), table(['Dữ liệu', 'Thông số đã kiểm tra', 'Tệp / quy ước'], summary_rows),
            paragraph('Kiểm đếm người gán nhãn BSDS', 'Heading2'), paragraph(count_text, size=19), paragraph(note, size=19),
            paragraph('FOV và vùng loại trừ', 'Heading2'),
            paragraph('FOV DRIVE: trắng là vùng quan sát hợp lệ, nền ngoài FOV không được chấm. Mask FOV gốc chưa xói mòn; xói mòn theo scale chỉ thuộc bước đánh giá. Không nhầm FOV với mask mạch máu.', size=20),
            paragraph(ignore, size=20),
            '<w:p><w:r><w:br w:type="page"/></w:r></w:p>',
            paragraph('2. Minh họa Ground Truth — BSDS500', 'Heading1'),
            picture('rIdImage1', 1, 'BSDS annotator 01 overlay', 15.2, 15.2*321/481), paragraph(caption1, 'Caption'),
            paragraph('Nguồn: data/gt/previews/bsds_01_overlay.png; input 481×321 px. Cyan = biên GT, nền = ảnh xám gốc. Các bộ nhãn còn lại vẫn giữ riêng trong data/gt/bsds/bsds_01/.', size=20),
            paragraph('Đoạn tóm tắt để đưa vào Chương 4', 'Heading2'), paragraph(paragraph_for_report),
            '<w:p><w:r><w:br w:type="page"/></w:r></w:p>',
            paragraph('3. Minh họa Ground Truth — tế bào', 'Heading1'),
            picture('rIdImage2', 2, '276 reviewed cells and 15 ignore rectangles', 14.0, 14.0), paragraph(caption2, 'Caption'),
            paragraph('Nguồn: data/gt/previews/blob_05_overlay.png; input 512×512 px; nhãn data/gt/blob/blob_05.json. Vòng tròn minh họa tâm/bán kính quy ước, không phải contour phân đoạn chính xác.', size=20),
            paragraph('Gợi ý dùng: giữ tỷ lệ ảnh; đổi số hình 4.x/4.y theo bản thảo. Hai PNG đã được nhúng vào Word; có thể gửi riêng file DOCX. Overlay chỉ để xem, không dùng tính metric.', size=20),
            paragraph(sources, size=18)]
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {ns}><w:body>' + ''.join(body) + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1000" w:right="1134" w:bottom="1000" w:left="1134" w:header="500" w:footer="500"/></w:sectPr></w:body></w:document>'
    styles = '''<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="21"/><w:lang w:val="vi-VN"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="90" w:line="260" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="0" w:after="80"/></w:pPr><w:rPr><w:b/><w:color w:val="0F4C5C"/><w:sz w:val="34"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:rPr><w:color w:val="5C707B"/><w:sz w:val="20"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="150" w:after="100"/></w:pPr><w:rPr><w:b/><w:color w:val="0F4C5C"/><w:sz w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="100" w:after="70"/></w:pPr><w:rPr><w:b/><w:sz w:val="22"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="Caption"/><w:basedOn w:val="Normal"/><w:rPr><w:i/><w:sz w:val="20"/></w:rPr></w:style>
</w:styles>'''
    types = '''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
    relroot = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    root_rels = relroot + '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    doc_rels = relroot + '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' + ''.join(f'<Relationship Id="rIdImage{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image{i}.png"/>' for i in [1,2]) + '</Relationships>'
    path = OUT / f'{STEM}.docx'
    with ZipFile(path, 'w', ZIP_DEFLATED) as z:
        for name, text in [('[Content_Types].xml', types), ('_rels/.rels', root_rels), ('word/document.xml', document), ('word/styles.xml', styles), ('word/_rels/document.xml.rels', doc_rels)]:
            z.writestr(name, text.encode('utf-8'))
        for i, (_, name) in enumerate(selected, 1):
            z.write(figures / name, f'word/media/image{i}.png')
    validate_inputs()
    output_paths = [path, OUT / f'{STEM}.md'] + [figures / name for _, name in selected]
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    report = dict(prepared_on='2026-11-08', intended_handoff='2026-11-09', recipient='Hung', sent=False,
                  ready_images=len(gt), bsds_annotators_by_image={r['image']:r['annotators'] for r in bsds},
                  total_bsds_annotations=sum(counts), cells=276, ignore_rectangles=15,
                  files={str(p.relative_to(OUT)):digest(p) for p in output_paths},
                  overlay_source_sha256={f'data/gt/previews/{image}_overlay.png':digest(ROOT/f'data/gt/previews/{image}_overlay.png') for image,_ in selected})
    (OUT / 'GROUND_TRUTH_HANDOFF_MANIFEST.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(path)
    print('DOCX contains 2 exact reviewed PNG overlays; GT and input hashes unchanged.')


if __name__ == '__main__':
    main()
