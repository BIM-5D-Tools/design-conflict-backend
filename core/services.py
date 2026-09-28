import io
import os
from PIL import Image as PILImage
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.drawing.image import Image as OpenpyxlImage
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def generate_conflict_excel(queryset, project_obj=None):
    wb = Workbook()
    ws = wb.active
    ws.title = "BaoCaoXungDot"
    ws.views.sheetView[0].showGridLines = True

    # 🟢 CẤU HÌNH IN ẤN VỪA KHỔ GIẤY A4 NẰM NGANG
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1  # Tự co giãn vừa khít 1 trang ngang
    ws.page_setup.fitToHeight = 0  # Chiều dài trang tự cuộn xuống trang 2, 3
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins.left = 0.3
    ws.page_margins.right = 0.3
    ws.page_margins.top = 0.4
    ws.page_margins.bottom = 0.4

    # 1. Styles
    font_company = Font(name="Arial", size=9, bold=True, color="1E293B")
    font_dept = Font(name="Arial", size=8, italic=True, color="64748B")
    font_title = Font(name="Arial", size=13, bold=True, color="1E40AF")
    font_header = Font(name="Arial", size=9, bold=True, color="FFFFFF")
    font_cell = Font(name="Arial", size=8, color="334155")
    font_cell_bold = Font(name="Arial", size=8, bold=True, color="1E293B")

    fill_header = PatternFill(
        start_color="1E40AF", end_color="1E40AF", fill_type="solid"
    )
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # 2. Header công ty
    ws.merge_cells("A1:D1")
    ws["A1"] = "CÔNG TY CỔ PHẦN TƯ VẤN VÀ XÂY DỰNG TECHBUILDING"
    ws["A1"].font = font_company

    ws.merge_cells("A2:D2")
    ws["A2"] = ""
    ws["A2"].font = font_dept

    # 3. Tiêu đề
    ws.merge_cells("A4:K4")
    title_text = (
        f"BÁO CÁO XUNG ĐỘT THIẾT KẾ - DỰ ÁN: {str(project_obj.name).upper()}"
        if project_obj
        else "BÁO CÁO XUNG ĐỘT THIẾT KẾ"
    )
    ws["A4"] = title_text
    ws["A4"].font = font_title
    ws["A4"].alignment = align_center
    ws.row_dimensions[4].height = 25

    # 4. Cột (Cân đối tổng width ~ 135 để vừa vặn A4 Ngang)
    headers = [
        ("STT", 5),
        ("Mã Code", 14),
        ("Tên Xung Đột", 16),
        ("Dự Án / Phân Khu", 14),
        ("Bộ Môn", 9),
        ("Vị Trí (Trục / Tầng)", 13),
        ("Mô Tả Lỗi", 18),
        ("Phương Án Xử Lý", 18),
        ("Ý Kiến Phối Hợp", 16),
        ("Hình Ảnh Minh Họa", 16),
        ("Trạng Thái", 10),
    ]

    header_row = 6
    ws.row_dimensions[header_row].height = 24
    for col_idx, (text, width) in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=text)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border
        ws.column_dimensions[cell.column_letter].width = width

    status_map = {
        "NEW": "Mới phát hiện",
        "PENDING": "Đang xử lý",
        "DONE": "Đã hoàn thành",
    }
    current_row = 7
    stt = 1

    for item in queryset:
        images = list(item.images.all()) if hasattr(item, "images") else []
        total_images = len(images)
        row_span = max(total_images, 1)
        start_row = current_row
        end_row = current_row + row_span - 1

        proj_name = item.project.name if item.project else "-"
        zone_name = f"\n({item.zone.name})" if getattr(item, "zone", None) else ""
        axis_text = item.axis or "-"
        floor_name = (
            item.floor.name
            if getattr(item, "floor", None)
            else (getattr(item, "floor_name", None) or "-")
        )
        position_text = f"Trục: {axis_text}\nTầng: {floor_name}"
        category_text = (
            getattr(item, "get_category_display", lambda: item.category)()
            if hasattr(item, "get_category_display")
            else str(item.category)
        )
        status_text = status_map.get(item.status, item.status)

        for r in range(start_row, end_row + 1):
            ws.row_dimensions[r].height = 70 if total_images > 0 else 28
            for c in range(1, 12):
                cell = ws.cell(row=r, column=c)
                cell.border = thin_border
                cell.font = font_cell
                cell.alignment = align_left if c in [3, 4, 7, 8, 9] else align_center

        ws.cell(row=start_row, column=1, value=stt).font = font_cell_bold
        ws.cell(row=start_row, column=2, value=item.code).font = font_cell_bold
        ws.cell(row=start_row, column=3, value=item.name)
        ws.cell(row=start_row, column=4, value=f"{proj_name}{zone_name}")
        ws.cell(row=start_row, column=5, value=category_text)
        ws.cell(row=start_row, column=6, value=position_text)
        ws.cell(row=start_row, column=7, value=item.description or "-")
        ws.cell(row=start_row, column=8, value=item.solution or "-")
        ws.cell(row=start_row, column=9, value=item.comment or "-")
        ws.cell(row=start_row, column=11, value=status_text)

        if total_images > 0:
            for idx, img_obj in enumerate(images):
                img_row = start_row + idx
                img_path = (
                    getattr(img_obj.image, "path", None)
                    if getattr(img_obj, "image", None)
                    else None
                )
                if img_path and os.path.exists(img_path):
                    try:
                        with PILImage.open(img_path) as pil_img:
                            pil_img.thumbnail((110, 85))
                            img_byte_arr = io.BytesIO()
                            pil_img.convert("RGB").save(img_byte_arr, format="JPEG")
                            img_byte_arr.seek(0)
                        excel_img = OpenpyxlImage(img_byte_arr)
                        ws.add_image(excel_img, f"J{img_row}")
                    except Exception:
                        ws.cell(row=img_row, column=10, value="[Lỗi ảnh]")
                else:
                    ws.cell(row=img_row, column=10, value="[K.ảnh]")
        else:
            ws.cell(row=start_row, column=10, value="-")

        if row_span > 1:
            for col_idx in [1, 2, 3, 4, 5, 6, 7, 8, 9, 11]:
                ws.merge_cells(
                    start_row=start_row,
                    start_column=col_idx,
                    end_row=end_row,
                    end_column=col_idx,
                )

        current_row += row_span
        stt += 1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


class NumberedCanvas(canvas.Canvas):
    """Đánh số trang dạng: Trang X / Y ở góc dưới A4"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 7)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawRightString(A4[1] - 20, 15, f"Trang {self._pageNumber} / {page_count}")


def generate_conflict_pdf(queryset, project_obj=None):
    output = io.BytesIO()

    # Khổ A4 Landscape (chiều rộng 841.89 pt, chiều cao 595.27 pt)
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=20,
        rightMargin=20,
        topMargin=20,
        bottomMargin=25,
    )

    # Đăng ký font tiếng Việt hệ thống (Arial có sẵn trên Windows/Linux)
    font_name = "Helvetica"
    font_bold = "Helvetica-Bold"
    font_italic = "Helvetica-Oblique"

    windows_arial = "C:\\Windows\\Fonts\\arial.ttf"
    windows_arial_bd = "C:\\Windows\\Fonts\\arialbd.ttf"
    if os.path.exists(windows_arial):
        pdfmetrics.registerFont(TTFont("ArialVN", windows_arial))
        font_name = "ArialVN"
        if os.path.exists(windows_arial_bd):
            pdfmetrics.registerFont(TTFont("ArialVN-Bold", windows_arial_bd))
            font_bold = "ArialVN-Bold"
        else:
            font_bold = "ArialVN"

    styles = getSampleStyleSheet()
    style_company = ParagraphStyle(
        "Company",
        fontName=font_bold,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B"),
    )
    style_dept = ParagraphStyle(
        "Dept",
        fontName=font_name,
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#64748B"),
    )
    style_title = ParagraphStyle(
        "Title",
        fontName=font_bold,
        fontSize=13,
        leading=16,
        alignment=1,
        textColor=colors.HexColor("#1E40AF"),
    )

    style_th = ParagraphStyle(
        "TH",
        fontName=font_bold,
        fontSize=7.5,
        leading=9,
        alignment=1,
        textColor=colors.white,
    )
    style_td = ParagraphStyle(
        "TD",
        fontName=font_name,
        fontSize=7,
        leading=8.5,
        textColor=colors.HexColor("#334155"),
    )
    style_td_bold = ParagraphStyle(
        "TDBold",
        fontName=font_bold,
        fontSize=7,
        leading=8.5,
        textColor=colors.HexColor("#1E293B"),
    )
    style_td_center = ParagraphStyle(
        "TDCenter",
        fontName=font_name,
        fontSize=7,
        leading=8.5,
        alignment=1,
        textColor=colors.HexColor("#334155"),
    )

    elements = []

    # 1. Header Công ty
    elements.append(
        Paragraph("CÔNG TY CỔ PHẦN TƯ VẤN VÀ XÂY DỰNG TECHBUILDING", style_company)
    )
    elements.append(Paragraph("", style_dept))
    elements.append(Spacer(1, 10))

    # 2. Tiêu đề Báo Cáo
    title_text = (
        f"BÁO CÁO XUNG ĐỘT THIẾT KẾ - DỰ ÁN: {str(project_obj.name).upper()}"
        if project_obj
        else "BÁO CÁO XUNG ĐỘT THIẾT KẾ"
    )
    elements.append(Paragraph(title_text, style_title))
    elements.append(Spacer(1, 12))

    # 3. Bảng dữ liệu (Tổng chiều rộng: 801.89 pt vừa vặn A4 Ngang)
    # [STT, Code, Tên, Dự án, Bộ môn, Vị trí, Lỗi, PA, Ý kiến, Ảnh, Trạng thái]
    col_widths = [22, 68, 80, 75, 45, 65, 105, 105, 95, 85, 56]

    table_data = [
        [
            Paragraph("STT", style_th),
            Paragraph("Mã Code", style_th),
            Paragraph("Tên Xung Đột", style_th),
            Paragraph("Dự Án / Phân Khu", style_th),
            Paragraph("Bộ Môn", style_th),
            Paragraph("Vị Trí (Trục/Tầng)", style_th),
            Paragraph("Mô Tả Lỗi", style_th),
            Paragraph("Phương Án Xử Lý", style_th),
            Paragraph("Ý Kiến Phối Hợp", style_th),
            Paragraph("Hình Ảnh", style_th),
            Paragraph("Trạng Thái", style_th),
        ]
    ]

    table_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E40AF")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]

    status_map = {"NEW": "Mới", "PENDING": "Đang xử lý", "DONE": "Hoàn thành"}
    row_idx = 1
    stt = 1

    for item in queryset:
        images = list(item.images.all()) if hasattr(item, "images") else []
        total_images = len(images)
        row_span = max(total_images, 1)
        start_row = row_idx
        end_row = row_idx + row_span - 1

        proj_name = item.project.name if item.project else "-"
        zone_name = (
            f"<br/><i>({item.zone.name})</i>" if getattr(item, "zone", None) else ""
        )
        proj_text = f"{proj_name}{zone_name}"

        axis_text = item.axis or "-"
        floor_name = (
            item.floor.name
            if getattr(item, "floor", None)
            else (getattr(item, "floor_name", None) or "-")
        )
        pos_text = f"Trục: {axis_text}<br/>Tầng: {floor_name}"

        cat_text = (
            getattr(item, "get_category_display", lambda: item.category)()
            if hasattr(item, "get_category_display")
            else str(item.category)
        )
        st_text = status_map.get(item.status, item.status)

        for i in range(row_span):
            img_cell = Paragraph("-", style_td_center)
            if total_images > i:
                img_path = (
                    getattr(images[i].image, "path", None)
                    if getattr(images[i], "image", None)
                    else None
                )
                if img_path and os.path.exists(img_path):
                    try:
                        img_cell = RLImage(img_path, width=75, height=52)
                    except Exception:
                        img_cell = Paragraph("[Lỗi ảnh]", style_td_center)

            if i == 0:
                table_data.append(
                    [
                        Paragraph(str(stt), style_td_bold),
                        Paragraph(item.code, style_td_bold),
                        Paragraph(item.name, style_td),
                        Paragraph(proj_text, style_td),
                        Paragraph(cat_text, style_td_center),
                        Paragraph(pos_text, style_td),
                        Paragraph(item.description or "-", style_td),
                        Paragraph(item.solution or "-", style_td),
                        Paragraph(item.comment or "-", style_td),
                        img_cell,
                        Paragraph(st_text, style_td_center),
                    ]
                )
            else:
                table_data.append(
                    [
                        Paragraph("", style_td),
                        Paragraph("", style_td),
                        Paragraph("", style_td),
                        Paragraph("", style_td),
                        Paragraph("", style_td),
                        Paragraph("", style_td),
                        Paragraph("", style_td),
                        Paragraph("", style_td),
                        Paragraph("", style_td),
                        img_cell,
                        Paragraph("", style_td),
                    ]
                )

        # Merge các ô khi có nhiều hơn 1 ảnh (SPAN cột 0..8 và cột 10)
        if row_span > 1:
            for c in [0, 1, 2, 3, 4, 5, 6, 7, 8, 10]:
                table_styles.append(("SPAN", (c, start_row), (c, end_row)))

        row_idx += row_span
        stt += 1

    conflict_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    conflict_table.setStyle(TableStyle(table_styles))
    elements.append(conflict_table)

    # Build PDF với canvas đánh số trang
    doc.build(elements, canvasmaker=NumberedCanvas)
    output.seek(0)
    return output
