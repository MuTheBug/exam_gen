"""Generate a formatted exam PDF strictly matching the sample exam layout.

The sample uses a two-column layout:
- Page 1: Reading passage fills the left column, questions start in the right column
- Page 2+: Questions flow across both columns
- Header drawn at the top of every page
- Footer "The End Of The Questions" at the very end
"""

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    Table, TableStyle, PageBreak, FrameBreak
)
from reportlab.lib import colors

PAGE_W, PAGE_H = A4
MARGIN_LEFT = 12 * mm
MARGIN_RIGHT = 12 * mm
MARGIN_TOP = 10 * mm
MARGIN_BOTTOM = 10 * mm
HEADER_HEIGHT = 18 * mm
GUTTER = 6 * mm

# Column dimensions
CONTENT_W = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT
COL_W = (CONTENT_W - GUTTER) / 2
COL_H = PAGE_H - MARGIN_TOP - MARGIN_BOTTOM - HEADER_HEIGHT

ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
         'XI', 'XII', 'XIII', 'XIV', 'XV']


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
    """Build paragraph styles matching the dense sample exam layout."""
    s = {}
    s['passage_title'] = ParagraphStyle(
        'passage_title', fontSize=8.5, fontName='Helvetica-Bold',
        leading=10, spaceBefore=0, spaceAfter=1 * mm,
    )
    s['passage'] = ParagraphStyle(
        'passage', fontSize=8, fontName='Times-Roman',
        leading=9.5, spaceBefore=0, spaceAfter=0.5 * mm,
    )
    s['section_title'] = ParagraphStyle(
        'section_title', fontSize=8.5, fontName='Helvetica-Bold',
        leading=10, spaceBefore=2.5 * mm, spaceAfter=1 * mm,
    )
    s['instruction'] = ParagraphStyle(
        'instruction', fontSize=8.5, fontName='Helvetica-Bold',
        leading=10, spaceBefore=1 * mm, spaceAfter=1 * mm,
    )
    s['question'] = ParagraphStyle(
        'question', fontSize=8, fontName='Times-Roman',
        leading=9.5, spaceBefore=0.3 * mm, spaceAfter=0.3 * mm,
        leftIndent=3 * mm,
    )
    s['mcq_options'] = ParagraphStyle(
        'mcq_options', fontSize=7.5, fontName='Times-Roman',
        leading=9, spaceBefore=0, spaceAfter=0.5 * mm,
        leftIndent=6 * mm,
    )
    s['composition_prompt'] = ParagraphStyle(
        'composition_prompt', fontSize=8, fontName='Times-Roman',
        leading=9.5, spaceBefore=0.5 * mm, spaceAfter=0.5 * mm,
        leftIndent=3 * mm,
    )
    s['guiding_q'] = ParagraphStyle(
        'guiding_q', fontSize=7.5, fontName='Times-Roman',
        leading=9, leftIndent=6 * mm,
    )
    s['footer'] = ParagraphStyle(
        'footer', fontSize=9, fontName='Helvetica-Bold',
        leading=11, alignment=TA_CENTER, spaceBefore=3 * mm,
    )
    s['source_label'] = ParagraphStyle(
        'source_label', fontSize=9, fontName='Helvetica-Bold',
        leading=11, alignment=TA_CENTER, spaceBefore=1 * mm, spaceAfter=1 * mm,
    )
    return s


def _draw_header(canvas, doc, exam_info):
    """Draw the header at the top of each page, matching sample exactly."""
    canvas.saveState()

    y = PAGE_H - MARGIN_TOP
    x_left = MARGIN_LEFT
    x_right = PAGE_W - MARGIN_RIGHT

    # Left: Exam title
    canvas.setFont('Helvetica-Bold', 9)
    title = f"Exam Sample/Unit {exam_info['unit_num']} {exam_info['unit_name']}"
    canvas.drawString(x_left, y - 10, title)

    # Center: Year
    canvas.setFont('Helvetica', 9)
    year = exam_info.get('exam_year', '2025-2026')
    canvas.drawCentredString(PAGE_W / 2, y - 10, year)

    # Right: Teacher name
    teacher = exam_info.get('teacher_name', '')
    if teacher:
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(x_right, y - 10, teacher)

    # Horizontal line below header
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(0.5)
    canvas.line(x_left, y - 15, x_right, y - 15)

    canvas.restoreState()


def _build_exam_story(exam, styles):
    """Build the reportlab story for one exam in two-column flowing layout."""
    story = []

    # Build all content that will flow through two columns
    for section in exam['sections']:
        num = section.get('num')
        marks = section.get('marks')

        if section['type'] == 'passage':
            # Instruction line
            story.append(Paragraph(
                f"<b>{_esc(section['title'])}</b>",
                styles['instruction']
            ))

            # Reading passage - split into paragraphs
            passage_text = section.get('content', '')
            paragraphs = passage_text.split('\n\n')
            for pidx, para in enumerate(paragraphs):
                para = para.strip()
                if not para:
                    continue
                # First paragraph might be a title (short, no period at end)
                if pidx == 0 and len(para) < 50 and not para.endswith('.'):
                    story.append(Paragraph(
                        f"<b>{_esc(para)}</b>",
                        styles['passage_title']
                    ))
                else:
                    story.append(Paragraph(_esc(para), styles['passage']))

        else:
            # Section header
            rom = ROMAN[num - 1] if num and num <= len(ROMAN) else str(num or '')
            marks_str = f"  ({marks} marks)" if marks else ""
            story.append(Paragraph(
                f"<b>{rom}- {_esc(section['title'])}{marks_str}</b>",
                styles['section_title']
            ))

            if section['type'] == 'composition':
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

            elif 'items' in section:
                for idx, item in enumerate(section.get('items', []), 1):
                    if isinstance(item, dict):
                        display = item.get('word', item.get('definition', str(item)))
                    else:
                        display = str(item)
                    story.append(Paragraph(
                        f"{idx}. {_esc(display)}",
                        styles['question']
                    ))

    # Footer
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("The End Of The Questions", styles['footer']))

    return story


class _ExamDocTemplate(BaseDocTemplate):
    """Custom doc template that draws per-exam headers."""

    def __init__(self, buffer, exam_info, **kwargs):
        self.exam_info = exam_info
        super().__init__(buffer, **kwargs)

    def afterPage(self):
        """Called after each page is done."""
        pass


def _make_two_col_template(exam_info):
    """Create a two-column PageTemplate with header callback."""

    col_top = MARGIN_BOTTOM + COL_H

    frame_left = Frame(
        MARGIN_LEFT, MARGIN_BOTTOM,
        COL_W, COL_H,
        id='left',
        leftPadding=0, rightPadding=2 * mm,
        topPadding=0, bottomPadding=0,
    )
    frame_right = Frame(
        MARGIN_LEFT + COL_W + GUTTER, MARGIN_BOTTOM,
        COL_W, COL_H,
        id='right',
        leftPadding=2 * mm, rightPadding=0,
        topPadding=0, bottomPadding=0,
    )

    def on_page(canvas, doc):
        _draw_header(canvas, doc, exam_info)

    return PageTemplate(
        id='twocol',
        frames=[frame_left, frame_right],
        onPage=on_page,
    )


def generate_exam_pdf(exam, teacher_name="", exam_year="2025-2026"):
    """Generate a PDF for a single exam with two-column layout."""
    buffer = io.BytesIO()

    exam_info = {
        'unit_num': exam['unit_num'],
        'unit_name': exam['unit_name'],
        'exam_year': exam_year,
        'teacher_name': teacher_name,
        'total_marks': exam['total_marks'],
    }

    doc = _ExamDocTemplate(
        buffer, exam_info,
        pagesize=A4,
        topMargin=MARGIN_TOP + HEADER_HEIGHT,
        bottomMargin=MARGIN_BOTTOM,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
    )

    template = _make_two_col_template(exam_info)
    doc.addPageTemplates([template])

    styles = _styles()
    story = _build_exam_story(exam, styles)

    doc.build(story)
    result = buffer.getvalue()
    buffer.close()
    return result


def generate_combined_pdf(textbook_exam, activity_exam, teacher_name="", exam_year="2025-2026"):
    """Generate a single PDF containing both exams with two-column layout."""
    buffer = io.BytesIO()

    # We need to handle two different exams with different headers.
    # Use a single doc with page templates that switch between exams.

    tb_info = {
        'unit_num': textbook_exam['unit_num'],
        'unit_name': textbook_exam['unit_name'],
        'exam_year': exam_year,
        'teacher_name': teacher_name,
        'total_marks': textbook_exam['total_marks'],
        'source_label': 'Student Book',
    }
    act_info = {
        'unit_num': activity_exam['unit_num'],
        'unit_name': activity_exam['unit_name'],
        'exam_year': exam_year,
        'teacher_name': teacher_name,
        'total_marks': activity_exam['total_marks'],
        'source_label': 'Activity Book',
    }

    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=MARGIN_TOP + HEADER_HEIGHT,
        bottomMargin=MARGIN_BOTTOM,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
    )

    # Template for Exam A
    tb_template = _make_two_col_template(tb_info)
    tb_template.id = 'exam_a'

    # Template for Exam B
    act_template = _make_two_col_template(act_info)
    act_template.id = 'exam_b'

    doc.addPageTemplates([tb_template, act_template])

    styles = _styles()
    story = []

    # Exam A label + content
    story.append(Paragraph(
        "<b>Exam A - Student Book</b>",
        styles['source_label']
    ))
    story.extend(_build_exam_story(textbook_exam, styles))

    # Switch to Exam B template and start new page
    from reportlab.platypus.doctemplate import NextPageTemplate
    story.append(NextPageTemplate('exam_b'))
    story.append(PageBreak())

    # Exam B label + content
    story.append(Paragraph(
        "<b>Exam B - Activity Book</b>",
        styles['source_label']
    ))
    story.extend(_build_exam_story(activity_exam, styles))

    doc.build(story)
    result = buffer.getvalue()
    buffer.close()
    return result
