"""Generate a formatted exam PDF using reportlab."""

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.lib import colors


def _build_styles():
    """Build custom paragraph styles for the exam."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='ExamHeader',
        parent=styles['Title'],
        fontSize=14,
        spaceAfter=4 * mm,
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name='ExamSubHeader',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=2 * mm,
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=11,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
        textColor=colors.HexColor('#1a1a1a'),
        borderWidth=0,
        borderPadding=0,
    ))

    styles.add(ParagraphStyle(
        name='SectionMarks',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#555555'),
        alignment=TA_RIGHT,
    ))

    styles.add(ParagraphStyle(
        name='ReadingPassage',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=3 * mm,
        leftIndent=5 * mm,
        rightIndent=5 * mm,
        borderWidth=0.5,
        borderColor=colors.HexColor('#cccccc'),
        borderPadding=8,
    ))

    styles.add(ParagraphStyle(
        name='QuestionItem',
        parent=styles['Normal'],
        fontSize=10,
        leading=13,
        spaceBefore=2 * mm,
        spaceAfter=1 * mm,
        leftIndent=8 * mm,
    ))

    styles.add(ParagraphStyle(
        name='AnswerLine',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=8 * mm,
        spaceAfter=3 * mm,
        textColor=colors.HexColor('#999999'),
    ))

    styles.add(ParagraphStyle(
        name='CompositionPrompt',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        leftIndent=5 * mm,
        spaceAfter=5 * mm,
    ))

    styles.add(ParagraphStyle(
        name='TotalMarks',
        parent=styles['Normal'],
        fontSize=11,
        spaceBefore=5 * mm,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#333333'),
    ))

    return styles


def generate_exam_pdf(exam, teacher_name="", exam_year="2025-2026"):
    """Generate a PDF for the given exam structure.

    Args:
        exam: Exam dict from exam_builder.build_exam()
        teacher_name: Optional teacher name for the header
        exam_year: Academic year string

    Returns:
        bytes: PDF content as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    styles = _build_styles()
    story = []

    # Header
    header_text = f"Exam / Unit {exam['unit_num']} - {exam['unit_name']} (Scientific)"
    story.append(Paragraph(header_text, styles['ExamHeader']))

    sub_header_parts = [exam_year]
    if teacher_name:
        sub_header_parts.append(teacher_name)
    story.append(Paragraph(" | ".join(sub_header_parts), styles['ExamSubHeader']))

    story.append(Paragraph(
        f"<b>Total Marks: {exam['total_marks']}</b>",
        styles['ExamSubHeader']
    ))

    story.append(Spacer(1, 5 * mm))

    # Sections
    section_num = 0
    roman = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']

    for section in exam['sections']:
        section_num += 1
        rom = roman[section_num - 1] if section_num <= len(roman) else str(section_num)

        # Section title with marks
        marks_text = f"({section['marks']} marks)" if section.get('marks') else ""
        title = f"<b>{rom}. {section['title']}</b> {marks_text}"
        story.append(Paragraph(title, styles['SectionTitle']))

        if section['type'] == 'passage':
            # Reading passage
            passage_text = section['content'].replace('\n', '<br/>')
            story.append(Paragraph(passage_text, styles['ReadingPassage']))

        elif section['type'] in ('questions', 'vocabulary', 'multiple_choice'):
            items = section.get('items', [])
            for idx, item in enumerate(items, 1):
                if isinstance(item, dict):
                    # Vocabulary with word
                    q_text = f"<b>{idx}.</b> {_escape(item.get('word', str(item)))}"
                else:
                    q_text = f"<b>{idx}.</b> {_escape(str(item))}"
                story.append(Paragraph(q_text, styles['QuestionItem']))
                story.append(Paragraph(
                    ".....................................................................................................................................",
                    styles['AnswerLine']
                ))

        elif section['type'] == 'composition':
            story.append(Paragraph(
                _escape(section.get('content', '')),
                styles['CompositionPrompt']
            ))
            # Add lined space for writing
            for _ in range(8):
                story.append(Paragraph(
                    ".....................................................................................................................................",
                    styles['AnswerLine']
                ))

    # Footer
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        "<b>~ The End of The Questions ~</b>",
        styles['TotalMarks']
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _escape(text):
    """Escape special XML/HTML characters for reportlab Paragraph."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))
