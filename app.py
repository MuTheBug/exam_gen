"""Streamlit web app for the Exam Question Generator."""

import streamlit as st
import random
from exam_builder import build_exam, build_combined_exams, build_mixed_exam
from pdf_generator import generate_combined_pdf, generate_multi_exam_pdf
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

# Mode selection
mode = st.sidebar.radio(
    "Exam Mode",
    ["Single Unit (2 exams)", "Mixed (custom selections)"],
    help="Single Unit: one exam per book for one unit.\nMixed: pick any combination of units and books.",
)

exam_year = st.sidebar.text_input("Academic Year", value="2025-2026")
teacher_name = st.sidebar.text_input("Teacher Name (optional)", value="")

st.sidebar.markdown("---")
st.sidebar.subheader("Question Counts")
num_comprehension = st.sidebar.slider("Comprehension questions", 3, 8, 5)
num_vocabulary = st.sidebar.slider("Vocabulary items", 3, 8, 6)
num_rewrite = st.sidebar.slider("Rewrite sentences", 2, 6, 4)
num_choose = st.sidebar.slider("Choose correct (brackets)", 3, 10, 6)
num_mcq = st.sidebar.slider("MCQ (A/B/C/D)", 4, 12, 8)
num_true_false = st.sidebar.slider("True/False statements", 3, 8, 5)
num_complete = st.sidebar.slider("Complete sentences", 2, 6, 4)
num_grammar = st.sidebar.slider("Grammar exercises", 2, 8, 5)

Q_KWARGS = dict(
    num_comprehension=num_comprehension,
    num_vocabulary=num_vocabulary,
    num_rewrite=num_rewrite,
    num_choose=num_choose,
    num_mcq=num_mcq,
    num_true_false=num_true_false,
    num_complete=num_complete,
    num_grammar=num_grammar,
)

# Roman numerals
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
         'XI', 'XII', 'XIII', 'XIV', 'XV']

UNIT_LABELS = {n: f"Unit {n}: {info['name']}" for n, info in UNITS.items()}
SOURCE_LABELS = {"textbook": "Student Book", "activity": "Activity Book"}


def display_exam(exam, label, key_prefix):
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
                key=f"{key_prefix}_passage",
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
            elif section['type'] == 'mcq':
                for idx, item in enumerate(section['items'], 1):
                    if isinstance(item, dict):
                        st.markdown(f"  {idx}. {item.get('stem', '')}")
                        opts = "  |  ".join(item.get('options', []))
                        st.markdown(f"  &nbsp;&nbsp;&nbsp;&nbsp;{opts}")
                    else:
                        st.markdown(f"  {idx}. {item}")
            elif section['type'] == 'do_as_required':
                for idx, item in enumerate(section['items'], 1):
                    if isinstance(item, dict):
                        sent = item.get('sentence', '')
                        instr = item.get('instruction', '')
                        st.markdown(f"  {idx}. {sent}  **({instr})**" if instr else f"  {idx}. {sent}")
                    else:
                        st.markdown(f"  {idx}. {item}")
            elif 'items' in section:
                for idx, item in enumerate(section['items'], 1):
                    if isinstance(item, dict):
                        display = item.get('word', item.get('definition', str(item)))
                    else:
                        display = str(item)
                    st.markdown(f"  {idx}. {display}")

    st.markdown("---")
    st.markdown("**The End Of The Questions**")


# ── Generate button ──
if st.sidebar.button("Generate New Exam", type="primary", use_container_width=True):
    st.session_state["seed"] = random.randint(0, 100000)

if "seed" not in st.session_state:
    st.session_state["seed"] = 42


# ══════════════════════════════════════════════════════════════
# Single Unit Mode
# ══════════════════════════════════════════════════════════════
if mode == "Single Unit (2 exams)":
    selected_label = st.sidebar.selectbox("Select Unit", list(UNIT_LABELS.values()))
    unit_num = [n for n, lbl in UNIT_LABELS.items() if lbl == selected_label][0]

    try:
        tb_exam, act_exam = build_combined_exams(
            unit_num, seed=st.session_state["seed"], **Q_KWARGS,
        )
    except Exception as e:
        st.error(f"Error generating exam: {e}")
        st.stop()

    tab1, tab2 = st.tabs(["Exam A - Student Book", "Exam B - Activity Book"])
    with tab1:
        display_exam(tb_exam, "Exam A - Student Book", "single_tb")
    with tab2:
        display_exam(act_exam, "Exam B - Activity Book", "single_act")

    # PDF download
    st.sidebar.markdown("---")
    try:
        pdf_bytes = generate_combined_pdf(
            tb_exam, act_exam,
            teacher_name=teacher_name, exam_year=exam_year,
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


# ══════════════════════════════════════════════════════════════
# Mixed Mode
# ══════════════════════════════════════════════════════════════
else:
    st.markdown("### Build a Mixed Exam")
    st.markdown("Select different units and books. Each selection becomes a separate exam section in the PDF.")

    # Initialize selections in session state
    if "mix_selections" not in st.session_state:
        st.session_state["mix_selections"] = [
            {"unit": 1, "source": "textbook"},
            {"unit": 1, "source": "activity"},
        ]

    # Add / remove controls
    col_add, col_remove = st.columns(2)
    with col_add:
        if st.button("+ Add Exam Section"):
            st.session_state["mix_selections"].append({"unit": 1, "source": "textbook"})
            st.rerun()
    with col_remove:
        if len(st.session_state["mix_selections"]) > 1:
            if st.button("- Remove Last"):
                st.session_state["mix_selections"].pop()
                st.rerun()

    # Selection rows
    selections = st.session_state["mix_selections"]
    for i, sel in enumerate(selections):
        c1, c2 = st.columns(2)
        with c1:
            unit_choice = st.selectbox(
                f"Exam {chr(65+i)} - Unit",
                list(UNIT_LABELS.values()),
                index=list(UNIT_LABELS.keys()).index(sel["unit"]),
                key=f"mix_unit_{i}",
            )
            selections[i]["unit"] = [n for n, lbl in UNIT_LABELS.items() if lbl == unit_choice][0]
        with c2:
            src_choice = st.selectbox(
                f"Exam {chr(65+i)} - Book",
                ["Student Book", "Activity Book"],
                index=0 if sel["source"] == "textbook" else 1,
                key=f"mix_src_{i}",
            )
            selections[i]["source"] = "textbook" if src_choice == "Student Book" else "activity"

    st.markdown("---")

    # Build mixed exams
    try:
        exams = build_mixed_exam(selections, seed=st.session_state["seed"], **Q_KWARGS)
    except Exception as e:
        st.error(f"Error generating exams: {e}")
        st.stop()

    # Display in tabs
    tab_labels = [
        f"Exam {chr(65+i)} - Unit {sel['unit']} ({SOURCE_LABELS[sel['source']]})"
        for i, sel in enumerate(selections)
    ]
    tabs = st.tabs(tab_labels)
    for i, tab in enumerate(tabs):
        with tab:
            display_exam(exams[i], tab_labels[i], f"mix_{i}")

    # PDF download
    st.sidebar.markdown("---")
    try:
        pdf_bytes = generate_multi_exam_pdf(
            exams, teacher_name=teacher_name, exam_year=exam_year,
        )
        units_str = "_".join(f"u{s['unit']}" for s in selections)
        st.sidebar.download_button(
            label="Download Combined PDF",
            data=pdf_bytes,
            file_name=f"exam_mixed_{units_str}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as e:
        st.sidebar.error(f"PDF generation error: {e}")


# Sample exam reference
with st.sidebar.expander("View Sample Exam Format"):
    st.image("example_example_page_1.jpg", caption="Sample Page 1", use_container_width=True)
    st.image("example_example_page_2.jpg", caption="Sample Page 2", use_container_width=True)
