"""Generate a formatted exam PDF matching the sample layout.

Layout: two independent columns on each page.
- Left column: first passage + its questions
- Right column: second passage + its questions
- Arabic+English header in bordered box
- Dotted answer lines after questions
- Continuous section/question numbering across columns
"""

import io
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

# Register DejaVu fonts (Arabic-capable)
pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

PAGE_W, PAGE_H = A4
MARGIN_LEFT = 10 * mm
MARGIN_RIGHT = 10 * mm
MARGIN_TOP = 8 * mm
MARGIN_BOTTOM = 8 * mm
HEADER_HEIGHT = 24 * mm
GUTTER = 4 * mm

CONTENT_W = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT
COL_W = (CONTENT_W - GUTTER) / 2

ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
         'XI', 'XII', 'XIII', 'XIV', 'XV']

DOTS = '.' * 55


def _ar(text):
    """Reshape Arabic text for correct display."""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def _esc(text):
    """Escape XML special characters for reportlab Paragraph."""
    if not text:
        return ""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def _styles():
    """Build paragraph styles matching the sample layout."""
    s = {}
    s['passage_title'] = ParagraphStyle(
        'passage_title', fontSize=9, fontName='Helvetica-Bold',
        leading=11, spaceBefore=0, spaceAfter=1 * mm,
    )
    s['passage'] = ParagraphStyle(
        'passage', fontSize=8, fontName='Times-Roman',
        leading=10, spaceBefore=0, spaceAfter=0.5 * mm,
    )
    s['section_header'] = ParagraphStyle(
        'section_header', fontSize=8.5, fontName='Helvetica-Bold',
        leading=10, spaceBefore=2 * mm, spaceAfter=1 * mm,
    )
    s['question'] = ParagraphStyle(
        'question', fontSize=8, fontName='Times-Roman',
        leading=10, spaceBefore=0.3 * mm, spaceAfter=0,
    )
    s['dots'] = ParagraphStyle(
        'dots', fontSize=7, fontName='Times-Roman',
        leading=8, spaceBefore=0, spaceAfter=0.8 * mm,
        textColor=colors.grey,
    )
    s['mcq_stem'] = ParagraphStyle(
        'mcq_stem', fontSize=8, fontName='Times-Roman',
        leading=10, spaceBefore=0.3 * mm, spaceAfter=0,
    )
    s['mcq_opts'] = ParagraphStyle(
        'mcq_opts', fontSize=7.5, fontName='Times-Roman',
        leading=9, spaceBefore=0, spaceAfter=0.5 * mm,
        leftIndent=3 * mm,
    )
    s['composition_prompt'] = ParagraphStyle(
        'composition_prompt', fontSize=8, fontName='Times-Roman',
        leading=10, spaceBefore=0.5 * mm, spaceAfter=0.5 * mm,
    )
    s['guiding_q'] = ParagraphStyle(
        'guiding_q', fontSize=7.5, fontName='Times-Roman',
        leading=9, leftIndent=3 * mm,
    )
    s['footer'] = ParagraphStyle(
        'footer', fontSize=9, fontName='Helvetica-Bold',
        leading=11, alignment=TA_CENTER, spaceBefore=3 * mm,
    )
    return s


def _draw_header(canvas, exam_info):
    """Draw the Arabic+English header box at the top of each page."""
    canvas.saveState()

    y_top = PAGE_H - MARGIN_TOP
    x_left = MARGIN_LEFT
    x_right = PAGE_W - MARGIN_RIGHT
    box_h = HEADER_HEIGHT
    y_bottom = y_top - box_h

    # Outer box
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(0.8)
    canvas.rect(x_left, y_bottom, x_right - x_left, box_h)

    # Row heights
    row_h = box_h / 3
    y_row1 = y_top - row_h
    y_row2 = y_top - 2 * row_h

    # Horizontal lines between rows
    canvas.setLineWidth(0.4)
    canvas.line(x_left, y_row1, x_right, y_row1)
    canvas.line(x_left, y_row2, x_right, y_row2)

    # Vertical divider in middle
    x_mid = (x_left + x_right) / 2
    canvas.line(x_mid, y_top, x_mid, y_bottom)

    text_offset = 2.5 * mm  # vertical offset from bottom of row

    # --- Row 1 ---
    canvas.setFont('DejaVu-Bold', 9)
    ar_text = _ar('جميع وحدات الكتاب')
    canvas.drawRightString(x_mid - 3 * mm, y_row1 + text_offset, ar_text)

    model_num = exam_info.get('model_num', '')
    en_label = "All Modules"
    ar_label = _ar(f'النموذج ({model_num})')
    canvas.drawString(x_mid + 3 * mm, y_row1 + text_offset,
                      f"{ar_label}     {en_label}")

    # --- Row 2 ---
    canvas.setFont('DejaVu', 8)
    ar_name = _ar('الاسم:')
    canvas.drawRightString(x_mid - 3 * mm, y_row2 + text_offset,
                           f"{'.' * 30}  {ar_name}")

    ar_date = _ar('التاريخ:')
    ar_class = _ar('الصف:')
    canvas.drawString(x_mid + 3 * mm, y_row2 + text_offset,
                      f"{ar_date} {'.' * 10}   {ar_class} {'.' * 10}")

    # --- Row 3 ---
    canvas.setFont('DejaVu-Bold', 8)
    ar_duration = _ar('المدة: ساعتين')
    canvas.drawRightString(x_mid - 3 * mm, y_bottom + text_offset, ar_duration)

    total = exam_info.get('total_marks', 300)
    ar_marks = _ar(f'العلامة الكاملة: {total} درجة')
    canvas.drawString(x_mid + 3 * mm, y_bottom + text_offset, ar_marks)

    # Teacher name (small, top right outside box)
    teacher = exam_info.get('teacher_name', '')
    if teacher:
        canvas.setFont('Helvetica', 7)
        canvas.drawRightString(x_right, y_top + 2 * mm, teacher)

    canvas.restoreState()


def _build_column_flowables(exam, styles, start_sec=1, start_q=1):
    """Build list of flowables for one column (one exam).

    Returns: (flowables_list, next_section_num, next_question_num)
    """
    story = []
    sec_num = start_sec
    q_num = start_q

    for section in exam['sections']:
        marks = section.get('marks')

        if section['type'] == 'passage':
            rom = ROMAN[sec_num - 1] if sec_num <= len(ROMAN) else str(sec_num)
            story.append(Paragraph(
                f"<b><u>{rom} – {_esc(section['title'])}</u></b>",
                styles['section_header']
            ))
            sec_num += 1

            passage_text = section.get('content', '')
            paragraphs = passage_text.split('\n\n')
            for pidx, para in enumerate(paragraphs):
                para = para.strip()
                if not para:
                    continue
                if pidx == 0 and len(para) < 50 and not para.endswith('.'):
                    story.append(Paragraph(
                        f"<b>{_esc(para)}</b>", styles['passage_title']
                    ))
                else:
                    story.append(Paragraph(_esc(para), styles['passage']))

        elif section['type'] == 'composition':
            marks_str = f"  ({marks} marks)" if marks else ""
            story.append(Paragraph(
                f"<b><u>- {_esc(section['title'])}</u></b>{marks_str}",
                styles['section_header']
            ))
            content = section.get('content', {})
            if isinstance(content, dict):
                prompt = content.get('prompt', '')
                guiding = content.get('guiding_questions', [])
            else:
                prompt = str(content)
                guiding = []
            story.append(Paragraph(_esc(prompt), styles['composition_prompt']))
            if guiding:
                story.append(Paragraph(
                    "The answers of these questions can help you:",
                    styles['composition_prompt']
                ))
                for gq in guiding:
                    story.append(Paragraph(f"- {_esc(gq)}", styles['guiding_q']))
            for _ in range(4):
                story.append(Paragraph(DOTS, styles['dots']))

        elif section['type'] == 'mcq':
            marks_str = f"  ({marks} marks)" if marks else ""
            story.append(Paragraph(
                f"<b><u>- Choose the correct answer A, B, C or D:</u></b>{marks_str}",
                styles['section_header']
            ))
            for item in section.get('items', []):
                if isinstance(item, dict):
                    stem = item.get('stem', '')
                    options = item.get('options', [])
                    story.append(Paragraph(
                        f"{q_num}. {_esc(stem)}", styles['mcq_stem']
                    ))
                    if options:
                        opts_line = "    ".join(_esc(o) for o in options)
                        story.append(Paragraph(opts_line, styles['mcq_opts']))
                else:
                    story.append(Paragraph(
                        f"{q_num}. {_esc(str(item))}", styles['question']
                    ))
                q_num += 1

        elif section['type'] == 'do_as_required':
            marks_str = f"  ({marks} marks)" if marks else ""
            title = section.get('title', 'Do as required:')
            story.append(Paragraph(
                f"<b><u>- {_esc(title)}</u></b>{marks_str}",
                styles['section_header']
            ))
            for item in section.get('items', []):
                if isinstance(item, dict):
                    sentence = item.get('sentence', '')
                    instruction = item.get('instruction', '')
                    display = f"{q_num}. {_esc(sentence)}"
                    if instruction:
                        display += f"  <b>({_esc(instruction)})</b>"
                    story.append(Paragraph(display, styles['question']))
                else:
                    story.append(Paragraph(
                        f"{q_num}. {_esc(str(item))}", styles['question']
                    ))
                story.append(Paragraph(DOTS, styles['dots']))
                q_num += 1

        else:
            marks_str = f"  ({marks} marks)" if marks else ""
            title = section.get('title', '')
            story.append(Paragraph(
                f"<b><u>- {_esc(title)}</u></b>{marks_str}",
                styles['section_header']
            ))
            for item in section.get('items', []):
                if isinstance(item, dict):
                    display = item.get('word', item.get('definition', str(item)))
                else:
                    display = str(item)
                story.append(Paragraph(
                    f"{q_num}. {_esc(display)}", styles['question']
                ))
                story.append(Paragraph(DOTS, styles['dots']))
                q_num += 1

    return story, sec_num, q_num


def _render_column_on_canvas(canvas, flowables, x, y_top, width, height):
    """Render a list of flowables into a rectangular area on the canvas.

    Returns the remaining y position after rendering (how far down we got).
    Uses Frame to handle wrapping and overflow.
    """
    from reportlab.platypus.frames import Frame as RLFrame

    f = RLFrame(x, y_top - height, width, height,
                leftPadding=1 * mm, rightPadding=1 * mm,
                topPadding=0, bottomPadding=0,
                showBoundary=0)

    # addFromList modifies the list in place - removes items that fit
    remaining = list(flowables)  # copy
    f.addFromList(remaining, canvas)

    return remaining  # items that didn't fit


def generate_exam_pdf(exam, teacher_name="", exam_year="2025-2026"):
    """Generate a PDF for a single exam."""
    buffer = io.BytesIO()

    total_marks = exam.get('total_marks', 0)
    exam_info = {
        'total_marks': total_marks,
        'teacher_name': teacher_name,
        'model_num': '',
    }

    from reportlab.pdfgen import canvas as canvas_module
    c = canvas_module.Canvas(buffer, pagesize=A4)
    styles = _styles()

    col_y_top = PAGE_H - MARGIN_TOP - HEADER_HEIGHT - 2 * mm
    col_height = col_y_top - MARGIN_BOTTOM

    flowables, _, _ = _build_column_flowables(exam, styles)
    flowables.append(Spacer(1, 3 * mm))
    flowables.append(Paragraph("The End Of The Questions", styles['footer']))

    page_num = 0
    while flowables:
        if page_num > 0:
            c.showPage()
        _draw_header(c, exam_info)

        remaining = _render_column_on_canvas(
            c, flowables, MARGIN_LEFT, col_y_top, CONTENT_W, col_height
        )
        flowables = remaining
        page_num += 1
        if page_num > 20:
            break

    c.showPage()
    c.save()
    result = buffer.getvalue()
    buffer.close()
    return result


def generate_combined_pdf(textbook_exam, activity_exam, teacher_name="", exam_year="2025-2026"):
    """Generate a single PDF with two exams side by side in two columns."""
    return generate_multi_exam_pdf(
        [textbook_exam, activity_exam],
        teacher_name=teacher_name,
        exam_year=exam_year,
    )


def generate_multi_exam_pdf(exams, teacher_name="", exam_year="2025-2026"):
    """Generate a single PDF with exams in two-column pairs.

    Every two exams are placed side by side (left/right columns) on the same
    page(s). Content that overflows continues on subsequent pages.
    """
    if not exams:
        return b""

    buffer = io.BytesIO()
    styles = _styles()

    total_marks = sum(e.get('total_marks', 0) for e in exams)
    exam_info = {
        'total_marks': total_marks,
        'teacher_name': teacher_name,
        'model_num': '',
    }

    from reportlab.pdfgen import canvas as canvas_module
    c = canvas_module.Canvas(buffer, pagesize=A4)

    col_y_top = PAGE_H - MARGIN_TOP - HEADER_HEIGHT - 2 * mm
    col_height = col_y_top - MARGIN_BOTTOM
    left_x = MARGIN_LEFT
    right_x = MARGIN_LEFT + COL_W + GUTTER

    sec_num = 1
    q_num = 1

    # Process exams in pairs
    i = 0
    while i < len(exams):
        if i + 1 < len(exams):
            # Two exams side by side
            left_flows, sec_num, q_num = _build_column_flowables(
                exams[i], styles, sec_num, q_num
            )
            right_flows, sec_num, q_num = _build_column_flowables(
                exams[i + 1], styles, sec_num, q_num
            )

            # Render both columns, handling overflow across pages
            page_num = 0
            while left_flows or right_flows:
                if page_num > 0:
                    c.showPage()
                _draw_header(c, exam_info)

                # Draw vertical separator line
                sep_x = MARGIN_LEFT + COL_W + GUTTER / 2
                c.setStrokeColor(colors.black)
                c.setLineWidth(0.3)
                c.line(sep_x, col_y_top, sep_x, MARGIN_BOTTOM)

                # Render left column
                if left_flows:
                    left_flows = _render_column_on_canvas(
                        c, left_flows, left_x, col_y_top, COL_W, col_height
                    )
                # Render right column
                if right_flows:
                    right_flows = _render_column_on_canvas(
                        c, right_flows, right_x, col_y_top, COL_W, col_height
                    )

                page_num += 1
                if page_num > 20:
                    break

            i += 2
        else:
            # Single exam - full width
            flows, sec_num, q_num = _build_column_flowables(
                exams[i], styles, sec_num, q_num
            )
            flows.append(Spacer(1, 3 * mm))
            flows.append(Paragraph("The End Of The Questions", styles['footer']))

            page_num = 0
            while flows:
                if page_num > 0:
                    c.showPage()
                _draw_header(c, exam_info)
                flows = _render_column_on_canvas(
                    c, flows, MARGIN_LEFT, col_y_top, CONTENT_W, col_height
                )
                page_num += 1
                if page_num > 20:
                    break
            i += 1

    # Add footer on current page if we haven't already (even number of exams)
    if len(exams) % 2 == 0:
        footer_flows = [Spacer(1, 3 * mm),
                        Paragraph("The End Of The Questions", styles['footer'])]
        _render_column_on_canvas(
            c, footer_flows, MARGIN_LEFT, MARGIN_BOTTOM + 20 * mm,
            CONTENT_W, 20 * mm
        )

    c.showPage()
    c.save()
    result = buffer.getvalue()
    buffer.close()
    return result
