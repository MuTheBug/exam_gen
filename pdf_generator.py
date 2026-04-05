"""Generate a formatted exam PDF with two independent columns.

Layout: two independent columns on each page, auto-fitted to 2 pages max.
- Left column: first passage + its questions
- Right column: second passage + its questions
- Simple header line (unit info, year, teacher name)
- Dotted answer lines after questions
- Continuous numbering across columns
"""

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib import colors

PAGE_W, PAGE_H = A4
MARGIN_LEFT = 10 * mm
MARGIN_RIGHT = 10 * mm
MARGIN_TOP = 8 * mm
MARGIN_BOTTOM = 8 * mm
HEADER_HEIGHT = 12 * mm
GUTTER = 4 * mm

CONTENT_W = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT
COL_W = (CONTENT_W - GUTTER) / 2

ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
         'XI', 'XII', 'XIII', 'XIV', 'XV']

DOTS = '.' * 50


def _esc(text):
    """Escape XML special characters for reportlab Paragraph."""
    if not text:
        return ""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def _styles(scale=1.0):
    """Build paragraph styles. scale < 1.0 shrinks everything."""
    def sz(base):
        return base * scale

    def sp(base_mm):
        return base_mm * scale * mm

    s = {}
    s['passage_title'] = ParagraphStyle(
        'passage_title', fontSize=sz(8.5), fontName='Helvetica-Bold',
        leading=sz(10), spaceBefore=0, spaceAfter=sp(0.5),
    )
    s['passage'] = ParagraphStyle(
        'passage', fontSize=sz(7.5), fontName='Times-Roman',
        leading=sz(9), spaceBefore=0, spaceAfter=sp(0.3),
    )
    s['section_header'] = ParagraphStyle(
        'section_header', fontSize=sz(8), fontName='Helvetica-Bold',
        leading=sz(9.5), spaceBefore=sp(1.5), spaceAfter=sp(0.5),
    )
    s['question'] = ParagraphStyle(
        'question', fontSize=sz(7.5), fontName='Times-Roman',
        leading=sz(9), spaceBefore=sp(0.2), spaceAfter=0,
    )
    s['dots'] = ParagraphStyle(
        'dots', fontSize=sz(6), fontName='Times-Roman',
        leading=sz(7), spaceBefore=0, spaceAfter=sp(0.3),
        textColor=colors.grey,
    )
    s['mcq_stem'] = ParagraphStyle(
        'mcq_stem', fontSize=sz(7.5), fontName='Times-Roman',
        leading=sz(9), spaceBefore=sp(0.2), spaceAfter=0,
    )
    s['mcq_opts'] = ParagraphStyle(
        'mcq_opts', fontSize=sz(7), fontName='Times-Roman',
        leading=sz(8.5), spaceBefore=0, spaceAfter=sp(0.3),
        leftIndent=sp(1),
    )
    s['composition_prompt'] = ParagraphStyle(
        'composition_prompt', fontSize=sz(7.5), fontName='Times-Roman',
        leading=sz(9), spaceBefore=sp(0.3), spaceAfter=sp(0.3),
    )
    s['guiding_q'] = ParagraphStyle(
        'guiding_q', fontSize=sz(7), fontName='Times-Roman',
        leading=sz(8.5), leftIndent=sp(1),
    )
    s['footer'] = ParagraphStyle(
        'footer', fontSize=sz(8.5), fontName='Helvetica-Bold',
        leading=sz(10), alignment=TA_CENTER, spaceBefore=sp(1.5),
    )
    return s


def _draw_header(canvas, exam_info):
    """Draw a simple header line at the top of each page."""
    canvas.saveState()

    y = PAGE_H - MARGIN_TOP
    x_left = MARGIN_LEFT
    x_right = PAGE_W - MARGIN_RIGHT

    # Left: exam title
    canvas.setFont('Helvetica-Bold', 9)
    units_str = exam_info.get('units_str', '')
    if units_str:
        title = f"Exam - {units_str}"
    else:
        title = "Exam"
    canvas.drawString(x_left, y - 8, title)

    # Center: year
    canvas.setFont('Helvetica', 9)
    year = exam_info.get('exam_year', '2025-2026')
    canvas.drawCentredString(PAGE_W / 2, y - 8, year)

    # Right: teacher name
    teacher = exam_info.get('teacher_name', '')
    if teacher:
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(x_right, y - 8, teacher)

    # Horizontal line
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(0.5)
    canvas.line(x_left, y - 12, x_right, y - 12)

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
            for _ in range(3):
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


def _render_column(canvas, flowables, x, y_top, width, height):
    """Render flowables into a rectangular area. Returns unrendered items."""
    from reportlab.platypus.frames import Frame as RLFrame

    f = RLFrame(x, y_top - height, width, height,
                leftPadding=1 * mm, rightPadding=1 * mm,
                topPadding=0, bottomPadding=0,
                showBoundary=0)

    remaining = list(flowables)
    f.addFromList(remaining, canvas)
    return remaining


def _count_pages(exams, styles, exam_info, max_pages=10):
    """Dry-run render to count how many pages the content would take."""
    col_y_top = PAGE_H - MARGIN_TOP - HEADER_HEIGHT
    col_height = col_y_top - MARGIN_BOTTOM

    # Build all column flowables
    sec_num = 1
    q_num = 1
    all_left = []
    all_right = []

    i = 0
    while i < len(exams):
        if i + 1 < len(exams):
            left, sec_num, q_num = _build_column_flowables(exams[i], styles, sec_num, q_num)
            right, sec_num, q_num = _build_column_flowables(exams[i + 1], styles, sec_num, q_num)
            all_left.extend(left)
            all_right.extend(right)
            i += 2
        else:
            single, sec_num, q_num = _build_column_flowables(exams[i], styles, sec_num, q_num)
            all_left.extend(single)
            i += 1

    # Simulate rendering
    from reportlab.pdfgen import canvas as cm
    buf = io.BytesIO()
    c = cm.Canvas(buf, pagesize=A4)

    pages = 0
    left_remaining = list(all_left)
    right_remaining = list(all_right)

    while left_remaining or right_remaining:
        if left_remaining:
            left_remaining = _render_column(
                c, left_remaining, MARGIN_LEFT, col_y_top, COL_W, col_height
            )
        if right_remaining:
            right_remaining = _render_column(
                c, right_remaining, MARGIN_LEFT + COL_W + GUTTER, col_y_top, COL_W, col_height
            )
        pages += 1
        if pages >= max_pages:
            break
        if left_remaining or right_remaining:
            c.showPage()

    c.showPage()
    c.save()
    buf.close()
    return pages


def _build_exam_info(exams, teacher_name="", exam_year="2025-2026"):
    """Build exam_info dict from list of exams."""
    total_marks = sum(e.get('total_marks', 0) for e in exams)
    unit_names = []
    for e in exams:
        name = f"Unit {e['unit_num']}"
        if name not in unit_names:
            unit_names.append(name)
    units_str = ", ".join(unit_names)

    return {
        'units_str': units_str,
        'exam_year': exam_year,
        'teacher_name': teacher_name,
        'total_marks': total_marks,
    }


def _render_pdf(exams, styles, exam_info):
    """Render the full PDF and return bytes."""
    from reportlab.pdfgen import canvas as cm

    buffer = io.BytesIO()
    c = cm.Canvas(buffer, pagesize=A4)

    col_y_top = PAGE_H - MARGIN_TOP - HEADER_HEIGHT
    col_height = col_y_top - MARGIN_BOTTOM
    left_x = MARGIN_LEFT
    right_x = MARGIN_LEFT + COL_W + GUTTER

    sec_num = 1
    q_num = 1

    i = 0
    page_count = 0
    while i < len(exams):
        if i + 1 < len(exams):
            left_flows, sec_num, q_num = _build_column_flowables(
                exams[i], styles, sec_num, q_num
            )
            right_flows, sec_num, q_num = _build_column_flowables(
                exams[i + 1], styles, sec_num, q_num
            )

            while left_flows or right_flows:
                if page_count > 0:
                    c.showPage()
                _draw_header(c, exam_info)

                # Vertical separator
                sep_x = MARGIN_LEFT + COL_W + GUTTER / 2
                c.setStrokeColor(colors.black)
                c.setLineWidth(0.3)
                c.line(sep_x, col_y_top, sep_x, MARGIN_BOTTOM)

                if left_flows:
                    left_flows = _render_column(
                        c, left_flows, left_x, col_y_top, COL_W, col_height
                    )
                if right_flows:
                    right_flows = _render_column(
                        c, right_flows, right_x, col_y_top, COL_W, col_height
                    )
                page_count += 1
                if page_count > 20:
                    break
            i += 2
        else:
            flows, sec_num, q_num = _build_column_flowables(
                exams[i], styles, sec_num, q_num
            )
            while flows:
                if page_count > 0:
                    c.showPage()
                _draw_header(c, exam_info)
                flows = _render_column(
                    c, flows, MARGIN_LEFT, col_y_top, CONTENT_W, col_height
                )
                page_count += 1
                if page_count > 20:
                    break
            i += 1

    # Footer on last page
    footer_flows = [
        Spacer(1, 2 * mm),
        Paragraph("The End Of The Questions",
                  ParagraphStyle('ft', fontSize=8, fontName='Helvetica-Bold',
                                 alignment=TA_CENTER))
    ]
    _render_column(c, footer_flows, MARGIN_LEFT, MARGIN_BOTTOM + 15 * mm,
                   CONTENT_W, 15 * mm)

    # Bottom line
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.3)
    c.line(MARGIN_LEFT, MARGIN_BOTTOM + 5 * mm,
           PAGE_W - MARGIN_RIGHT, MARGIN_BOTTOM + 5 * mm)

    c.showPage()
    c.save()
    result = buffer.getvalue()
    buffer.close()
    return result


def generate_exam_pdf(exam, teacher_name="", exam_year="2025-2026"):
    """Generate a PDF for a single exam."""
    exams = [exam]
    exam_info = _build_exam_info(exams, teacher_name, exam_year)
    styles = _styles(scale=1.0)
    return _render_pdf(exams, styles, exam_info)


def generate_combined_pdf(textbook_exam, activity_exam, teacher_name="", exam_year="2025-2026"):
    """Generate a single PDF with two exams side by side, auto-fitted to 2 pages."""
    return generate_multi_exam_pdf(
        [textbook_exam, activity_exam],
        teacher_name=teacher_name,
        exam_year=exam_year,
    )


def generate_multi_exam_pdf(exams, teacher_name="", exam_year="2025-2026", max_pages=2):
    """Generate a PDF with exams in two-column pairs, auto-fitted to max_pages.

    Tries progressively smaller scale factors until content fits.
    """
    if not exams:
        return b""

    exam_info = _build_exam_info(exams, teacher_name, exam_year)

    # Try scale factors from 1.0 down to 0.7
    for scale in [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7]:
        styles = _styles(scale=scale)
        pages = _count_pages(exams, styles, exam_info, max_pages=max_pages + 1)
        if pages <= max_pages:
            break

    # Render with the chosen scale
    styles = _styles(scale=scale)
    return _render_pdf(exams, styles, exam_info)
