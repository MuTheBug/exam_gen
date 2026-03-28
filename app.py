"""Streamlit web app for the Exam Question Generator."""

import streamlit as st
import random
from exam_builder import build_exam
from pdf_generator import generate_exam_pdf
from config import UNITS

st.set_page_config(
    page_title="Exam Question Generator",
    page_icon="📝",
    layout="wide",
)

st.title("Exam Question Generator")
st.markdown("Generate exam papers from the **Emar** Grade 12 Scientific English curriculum.")

# Sidebar controls
st.sidebar.header("Exam Settings")

unit_options = {f"Unit {n}: {info['name']}": n for n, info in UNITS.items()}
selected_label = st.sidebar.selectbox("Select Unit", list(unit_options.keys()))
unit_num = unit_options[selected_label]

exam_year = st.sidebar.text_input("Academic Year", value="2025-2026")
teacher_name = st.sidebar.text_input("Teacher Name (optional)", value="")

st.sidebar.markdown("---")
st.sidebar.subheader("Question Counts")
num_comprehension = st.sidebar.slider("Comprehension questions", 3, 8, 5)
num_vocabulary = st.sidebar.slider("Vocabulary items", 3, 8, 6)
num_rewrite = st.sidebar.slider("Rewrite sentences", 2, 6, 3)
num_choose = st.sidebar.slider("Multiple choice questions", 3, 10, 6)
num_complete = st.sidebar.slider("Complete sentences", 2, 6, 4)
num_grammar = st.sidebar.slider("Grammar exercises", 2, 8, 5)

# Generate button
if st.sidebar.button("Generate New Exam", type="primary", use_container_width=True):
    st.session_state["seed"] = random.randint(0, 100000)

if "seed" not in st.session_state:
    st.session_state["seed"] = 42

# Build exam
try:
    exam = build_exam(
        unit_num,
        num_comprehension=num_comprehension,
        num_vocabulary=num_vocabulary,
        num_rewrite=num_rewrite,
        num_choose=num_choose,
        num_complete=num_complete,
        num_grammar=num_grammar,
        seed=st.session_state["seed"],
    )
except Exception as e:
    st.error(f"Error generating exam: {e}")
    st.stop()

# Display exam preview
st.markdown("---")

# Header
st.markdown(f"### Exam / Unit {exam['unit_num']} - {exam['unit_name']} (Scientific)")
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**Year:** {exam_year}")
with col2:
    st.markdown(f"**Total Marks:** {exam['total_marks']}")

if teacher_name:
    st.markdown(f"**Teacher:** {teacher_name}")

st.markdown("---")

# Display sections
roman = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
for idx, section in enumerate(exam['sections']):
    rom = roman[idx] if idx < len(roman) else str(idx + 1)
    marks_text = f"*({section['marks']} marks)*" if section.get('marks') else ""

    st.markdown(f"**{rom}. {section['title']}** {marks_text}")

    if section['type'] == 'passage':
        with st.container():
            st.text_area(
                "Reading Passage",
                value=section['content'],
                height=300,
                disabled=True,
                label_visibility="collapsed",
            )
    elif section['type'] in ('questions', 'vocabulary', 'multiple_choice'):
        for q_idx, item in enumerate(section.get('items', []), 1):
            if isinstance(item, dict):
                display = item.get('word', str(item))
            else:
                display = str(item)
            st.markdown(f"  {q_idx}. {display}")
            st.markdown(
                '<p style="color: #999; margin-left: 20px;">'
                '.......................................................................</p>',
                unsafe_allow_html=True,
            )
    elif section['type'] == 'composition':
        st.markdown(f"> {section.get('content', '')}")
        st.markdown(
            '<p style="color: #999;">'
            '(Write your composition here)</p>',
            unsafe_allow_html=True,
        )

    st.markdown("")

st.markdown("---")
st.markdown("**~ The End of The Questions ~**", unsafe_allow_html=True)

# PDF download
st.sidebar.markdown("---")
try:
    pdf_bytes = generate_exam_pdf(exam, teacher_name=teacher_name, exam_year=exam_year)
    st.sidebar.download_button(
        label="Download Exam as PDF",
        data=pdf_bytes,
        file_name=f"exam_unit_{unit_num}_{exam['unit_name'].replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
except Exception as e:
    st.sidebar.error(f"PDF generation error: {e}")

# Sample exam reference
with st.sidebar.expander("View Sample Exam Format"):
    st.image("example_example_page_1.jpg", caption="Sample Page 1", use_container_width=True)
    st.image("example_example_page_2.jpg", caption="Sample Page 2", use_container_width=True)
