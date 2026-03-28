"""Streamlit web app for the Exam Question Generator."""

import streamlit as st
import random
from exam_builder import build_combined_exams
from pdf_generator import generate_combined_pdf
from config import UNITS

st.set_page_config(
    page_title="Exam Question Generator",
    page_icon="📝",
    layout="wide",
)

st.title("Exam Question Generator")
st.markdown("Generate exam papers from the **Emar** Grade 12 Scientific English curriculum.")
st.markdown("Generates **two exams** (one from each book) combined into a single PDF.")

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
num_choose = st.sidebar.slider("Choose correct", 3, 10, 6)
num_complete = st.sidebar.slider("Complete sentences", 2, 6, 4)
num_grammar = st.sidebar.slider("Grammar exercises", 2, 8, 5)

# Generate button
if st.sidebar.button("Generate New Exam", type="primary", use_container_width=True):
    st.session_state["seed"] = random.randint(0, 100000)

if "seed" not in st.session_state:
    st.session_state["seed"] = 42

# Build exams
try:
    tb_exam, act_exam = build_combined_exams(
        unit_num,
        seed=st.session_state["seed"],
        num_comprehension=num_comprehension,
        num_vocabulary=num_vocabulary,
        num_rewrite=num_rewrite,
        num_choose=num_choose,
        num_complete=num_complete,
        num_grammar=num_grammar,
    )
except Exception as e:
    st.error(f"Error generating exam: {e}")
    st.stop()

# Roman numerals
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']


def display_exam(exam, label):
    """Display an exam preview in the Streamlit app."""
    st.markdown(f"### {label}")
    st.markdown(f"**Exam / Unit {exam['unit_num']} - {exam['unit_name']} (Scientific)**")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Year:** {exam_year}")
    with col2:
        st.markdown(f"**Total Marks:** {exam['total_marks']}")

    for section in exam['sections']:
        num = section.get('num')
        marks = section.get('marks')

        if section['type'] == 'passage':
            st.markdown(f"**{section['title']}**")
            st.text_area(
                "Reading Passage",
                value=section['content'],
                height=250,
                disabled=True,
                label_visibility="collapsed",
                key=f"{label}_passage",
            )
        else:
            rom = ROMAN[num - 1] if num and num <= len(ROMAN) else str(num or '')
            marks_str = f" *({marks} marks)*" if marks else ""
            st.markdown(f"**{rom}- {section['title']}**{marks_str}")

            if section['type'] == 'composition':
                content = section.get('content', {})
                if isinstance(content, dict):
                    st.markdown(f"> {content.get('prompt', '')}")
                    for gq in content.get('guiding_questions', []):
                        st.markdown(f"  - {gq}")
                else:
                    st.markdown(f"> {content}")
            elif 'items' in section:
                for idx, item in enumerate(section['items'], 1):
                    if isinstance(item, dict):
                        display = item.get('word', item.get('definition', str(item)))
                    else:
                        display = str(item)
                    st.markdown(f"  {idx}. {display}")

    st.markdown("---")
    st.markdown("**The End Of The Questions**")


# Display both exams in tabs
tab1, tab2 = st.tabs(["Exam A - Student Book", "Exam B - Activity Book"])

with tab1:
    display_exam(tb_exam, "Exam A - Student Book")

with tab2:
    display_exam(act_exam, "Exam B - Activity Book")

# PDF download
st.sidebar.markdown("---")
try:
    pdf_bytes = generate_combined_pdf(
        tb_exam, act_exam,
        teacher_name=teacher_name,
        exam_year=exam_year,
    )
    st.sidebar.download_button(
        label="Download Combined PDF",
        data=pdf_bytes,
        file_name=f"exam_unit_{unit_num}_{tb_exam['unit_name'].replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
except Exception as e:
    st.sidebar.error(f"PDF generation error: {e}")

# Sample exam reference
with st.sidebar.expander("View Sample Exam Format"):
    st.image("example_example_page_1.jpg", caption="Sample Page 1", use_container_width=True)
    st.image("example_example_page_2.jpg", caption="Sample Page 2", use_container_width=True)
