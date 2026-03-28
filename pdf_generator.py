"""Generate a formatted exam PDF matching the sample exam layout."""

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib import colors

PAGE_W, PAGE_H = A4

# Roman numerals for section numbering
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
         'XI', 'XII', 'XIII', 'XIV', 'XV']


def _build_styles():
    """Build paragraph styles matching the dense exam sample layout."""
    s = {}

    s['header_left'] = ParagraphStyle(
        'header_left', fontSize=10, fontName='Helvetica-Bold',
        leading=12, alignment=TA_LEFT,
    )
    s['header_center'] = ParagraphStyle(
        'header_center', fontSize=10, fontName='Helvetica',
        leading=12, alignment=TA_CENTER,
    )
    s['header_right'] = ParagraphStyle(
        'header_right', fontSize=9, fontName='Helvetica',
        leading=12, alignment=TA_RIGHT,
    )
    s['passage'] = ParagraphStyle(
        'passage', fontSize=9, fontName='Times-Roman',
        leading=11.5, spaceBefore=1 * mm, spaceAfter=2 * mm,
        leftIndent=3 * mm, rightIndent=3 * mm,
    )
    s['section_title'] = ParagraphStyle(
        'section_title', fontSize=10, fontName='Helvetica-Bold',
        leading=12, spaceBefore=4 * mm, spaceAfter=1.5 * mm,
    )
    s['question'] = ParagraphStyle(
        'question', fontSize=9.5, fontName='Times-Roman',
        leading=12, spaceBefore=0.5 * mm, spaceAfter=0.5 * mm,
        leftIndent=5 * mm,
    )
    s['sub_item'] = ParagraphStyle(
        'sub_item', fontSize=9, fontName='Times-Roman',
        leading=11, spaceBefore=0, spaceAfter=0.5 * mm,
        leftIndent=10 * mm,
    )
    s['composition_prompt'] = ParagraphStyle(
        'composition_prompt', fontSize=9.5, fontName='Times-Roman',
        leading=12, spaceBefore=1 * mm, spaceAfter=1 * mm,
        leftIndent=5 * mm,
    )
    s['guiding_q'] = ParagraphStyle(
        'guiding_q', fontSize=9, fontName='Times-Roman',
        leading=11, leftIndent=10 * mm,
    )
    s['footer'] = ParagraphStyle(
        'footer', fontSize=10, fontName='Helvetica-Bold',
        leading=12, alignment=TA_CENTER, spaceBefore=6 * mm,
    )
    s['source_label'] = ParagraphStyle(
        'source_label', fontSize=11, fontName='Helvetica-Bold',
        leading=14, alignment=TA_CENTER, spaceBefore=3 * mm, spaceAfter=2 * mm,
        textColor=colors.HexColor('#333333'),
    )

    return s


def _esc(text):
    """Escape XML special characters for reportlab Paragraph."""
    if not text:
        return ""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def _build_header(exam, styles, exam_year, teacher_name):
    """Build the three-column header row matching the sample."""
    left = Paragraph(
        f"Exam Sample / Unit {exam['unit_num']} {_esc(exam['unit_name'])} (Scientific)",
        styles['header_left']
    )
    center = Paragraph(exam_year, styles['header_center'])
    right_text = _esc(teacher_name) if teacher_name else ""
    right = Paragraph(right_text, styles['header_right'])

    col_w = (PAGE_W - 40 * mm) / 3
    header_table = Table(
        [[left, center, right]],
        colWidths=[col_w, col_w, col_w],
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
        ('TOPPADDING', (0, 0), (-1, 0), 0),
    ]))
    return header_table


def _build_exam_story(exam, styles, exam_year, teacher_name):
    """Build the reportlab story (list of flowables) for one exam."""
    story = []

    # Header
    story.append(_build_header(exam, styles, exam_year, teacher_name))
    story.append(Spacer(1, 3 * mm))

    # Total marks line
    story.append(Paragraph(
        f"<b>Total Marks: {exam['total_marks']}</b>",
        ParagraphStyle('marks_line', fontSize=9, fontName='Helvetica-Bold',
                        leading=11, alignment=TA_RIGHT, spaceAfter=2 * mm)
    ))

    # Sections
    for section in exam['sections']:
        num = section.get('num')
        marks = section.get('marks')

        # Section title
        if section['type'] == 'passage':
            title_text = f"<b>{_esc(section['title'])}</b>"
        else:
            rom = ROMAN[num - 1] if num and num <= len(ROMAN) else str(num or '')
            marks_str = f"  ({marks} marks)" if marks else ""
            title_text = f"<b>{rom}- {_esc(section['title'])}{marks_str}</b>"

        story.append(Paragraph(title_text, styles['section_title']))

        # Content based on type
        if section['type'] == 'passage':
            passage = _esc(section['content']).replace('\n', '<br/>')
            story.append(Paragraph(passage, styles['passage']))

        elif section['type'] in ('questions', 'vocabulary', 'true_false'):
            for idx, item in enumerate(section.get('items', []), 1):
                if isinstance(item, dict):
                    display = item.get('word', item.get('definition', str(item)))
                else:
                    display = str(item)
                story.append(Paragraph(
                    f"{idx}. {_esc(display)}",
                    styles['question']
                ))

        elif section['type'] == 'choose_correct':
            for idx, item in enumerate(section.get('items', []), 1):
                story.append(Paragraph(
                    f"{idx}. {_esc(str(item))}",
                    styles['question']
                ))

        elif section['type'] == 'composition':
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
                for gidx, gq in enumerate(guiding, 1):
                    story.append(Paragraph(
                        f"{gidx}. {_esc(gq)}",
                        styles['guiding_q']
                    ))

    # Footer
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("The End Of The Questions", styles['footer']))

    return story


def generate_exam_pdf(exam, teacher_name="", exam_year="2025-2026"):
    """Generate a PDF for a single exam.

    Args:
        exam: Exam dict from exam_builder.build_exam()
        teacher_name: Teacher name for header
        exam_year: Academic year string

    Returns:
        bytes: PDF content
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=12 * mm, bottomMargin=12 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
    )
    styles = _build_styles()
    story = _build_exam_story(exam, styles, exam_year, teacher_name)
    doc.build(story)
    result = buffer.getvalue()
    buffer.close()
    return result


def generate_combined_pdf(textbook_exam, activity_exam, teacher_name="", exam_year="2025-2026"):
    """Generate a single PDF containing both exams (one per book).

    Args:
        textbook_exam: Exam dict from Student Book
        activity_exam: Exam dict from Activity Book
        teacher_name: Teacher name for header
        exam_year: Academic year string

    Returns:
        bytes: PDF content
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=12 * mm, bottomMargin=12 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
    )
    styles = _build_styles()

    story = []

    # Exam A: Student Book
    story.append(Paragraph("Exam A - Student Book", styles['source_label']))
    story.extend(_build_exam_story(textbook_exam, styles, exam_year, teacher_name))

    # Page break
    story.append(PageBreak())

    # Exam B: Activity Book
    story.append(Paragraph("Exam B - Activity Book", styles['source_label']))
    story.extend(_build_exam_story(activity_exam, styles, exam_year, teacher_name))

    doc.build(story)
    result = buffer.getvalue()
    buffer.close()
    return result
