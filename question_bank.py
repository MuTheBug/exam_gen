"""Parse extracted text into structured question objects by unit."""

import re
from pdf_extractor import get_textbook_unit, get_activity_unit
from config import UNITS

# Section headers that mark the end of a section
SECTION_HEADERS = frozenset([
    "vocabulary", "grammar", "listening", "speaking", "writing",
    "pronunciation", "everyday english", "preview",
])


def _clean_lines(lines):
    """Remove page numbers, return cleaned text lines."""
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip standalone page numbers
        if stripped.isdigit() and len(stripped) <= 3:
            continue
        cleaned.append(stripped)
    return cleaned


def _is_section_break(line):
    """Check if a line is a section header that marks a break."""
    lower = line.lower().strip()
    return lower in SECTION_HEADERS


def _extract_reading_passage(lines):
    """Extract the main reading passage from unit text."""
    cleaned = _clean_lines(lines)

    # Find the standalone "Reading" section header (not "Reading: ..." metadata)
    reading_start = None
    for i, line in enumerate(cleaned):
        # Match standalone "Reading" header, not metadata like "Reading: History of Medicine"
        if line.strip().lower() == "reading":
            reading_start = i + 1
            break

    if reading_start is None:
        return ""

    # Skip past any sub-labels (a, b) and instruction lines until we hit passage text
    # The passage is the main block of text after "Reading" before exercise markers
    passage_lines = []
    in_passage = False
    for i in range(reading_start, len(cleaned)):
        line = cleaned[i]

        # Stop at section breaks
        if _is_section_break(line):
            break
        # Stop at exercise markers (standalone a, b, c)
        if re.match(r'^[a-c]$', line) and in_passage:
            break
        # Stop at question/instruction markers
        lower = line.lower()
        if in_passage and (
            lower.startswith("answer the following") or
            lower.startswith("read the text") or
            lower.startswith("in pairs") or
            lower.startswith("in small groups") or
            lower.startswith("match these words") or
            lower.startswith("match the words") or
            lower.startswith("before you read") or
            lower.startswith("find words")
        ):
            break

        # Skip empty lines and sub-labels before passage starts
        if not in_passage:
            if not line or re.match(r'^[a-c]$', line):
                continue
            # Skip instruction lines
            if lower.startswith("in pairs") or lower.startswith("in small groups"):
                continue
            if lower.startswith("read the quote") or lower.startswith("discuss"):
                continue
            in_passage = True

        if in_passage:
            passage_lines.append(line)

    passage = "\n".join(passage_lines).strip()
    return passage


def _extract_numbered_questions(lines, start_idx, max_questions=10):
    """Extract numbered questions (1. xxx, 2. xxx, ...) starting from start_idx."""
    questions = []
    current_q = ""
    for i in range(start_idx, min(start_idx + 100, len(lines))):
        line = lines[i].strip()
        if not line:
            continue
        # Check for section breaks
        if _is_section_break(line):
            break
        # Check if this is a new numbered question
        match = re.match(r'^(\d+)[\.\)]*\s+(.+)', line)
        if match:
            if current_q:
                questions.append(current_q.strip())
            current_q = match.group(2)
        elif line.startswith("........") or line.startswith("……"):
            # Answer line, skip
            if current_q:
                questions.append(current_q.strip())
                current_q = ""
        elif re.match(r'^[a-d]$', line.lower()):
            # Exercise sub-label, stop
            if current_q:
                questions.append(current_q.strip())
            break
        elif current_q:
            # Continuation of current question
            current_q += " " + line

        if len(questions) >= max_questions:
            break

    if current_q and len(questions) < max_questions:
        questions.append(current_q.strip())

    return questions


def _extract_comprehension_questions(lines):
    """Extract comprehension questions from text."""
    cleaned = _clean_lines(lines)
    questions = []

    for i, line in enumerate(cleaned):
        lower = line.lower()
        if ("answer the following" in lower or
            "read the text, then answer" in lower or
            "read the text and answer" in lower):
            questions.extend(_extract_numbered_questions(cleaned, i + 1))
            if questions:
                break

    return questions


def _extract_vocabulary_matching(lines):
    """Extract vocabulary matching exercises (words and their definitions)."""
    cleaned = _clean_lines(lines)
    items = []

    for i, line in enumerate(cleaned):
        lower = line.lower()
        if ("match" in lower and ("word" in lower or "meaning" in lower)):
            # Extract word list
            for j in range(i + 1, min(i + 30, len(cleaned))):
                match = re.match(r'^(\d+)\.\s+(.+)', cleaned[j])
                if match:
                    items.append(match.group(2))
                elif cleaned[j].strip().startswith("a."):
                    break
                elif len(items) >= 8:
                    break
            if items:
                break

    # Also look for definitions list (a. xxx, b. xxx)
    definitions = []
    for i, line in enumerate(cleaned):
        match = re.match(r'^([a-h])\.\s+(.+)', line)
        if match and len(definitions) < len(items) + 2:
            definitions.append(match.group(2))

    return [{"word": w, "definitions": definitions} for w in items] if items else []


def _extract_word_meaning_questions(lines):
    """Extract 'find words in the text which mean' or vocabulary definition matching."""
    cleaned = _clean_lines(lines)
    items = []

    # Pattern 1: "In pairs, try to guess the meaning of the highlighted words"
    for i, line in enumerate(cleaned):
        lower = line.lower()
        if ("guess the meaning" in lower or "find words" in lower or
            "match them with their definitions" in lower):
            for j in range(i + 1, min(i + 30, len(cleaned))):
                match = re.match(r'^(\d+)\s+(.+)', cleaned[j])
                if match:
                    items.append(match.group(2))
                elif len(items) >= 8:
                    break
            if items:
                break

    return items


def _extract_choose_correct(lines):
    """Extract multiple choice / choose the correct word exercises."""
    cleaned = _clean_lines(lines)
    questions = []

    for i, line in enumerate(cleaned):
        lower = line.lower()
        if "choose the correct" in lower or "choose the appropriate" in lower or \
           "choose the best" in lower:
            questions.extend(_extract_numbered_questions(cleaned, i + 1, max_questions=8))

    return questions


def _extract_rewrite_sentences(lines):
    """Extract rewrite/correction exercises."""
    cleaned = _clean_lines(lines)
    sentences = []

    for i, line in enumerate(cleaned):
        lower = line.lower()
        if "rewrite" in lower and ("correct" in lower or "sentence" in lower or "following" in lower):
            found = _extract_numbered_questions(cleaned, i + 1, max_questions=6)
            sentences.extend(found)

    return sentences


def _extract_complete_sentences(lines):
    """Extract 'complete the following sentences' exercises."""
    cleaned = _clean_lines(lines)
    sentences = []

    for i, line in enumerate(cleaned):
        lower = line.lower()
        if "complete the following sentence" in lower:
            found = _extract_numbered_questions(cleaned, i + 1, max_questions=6)
            sentences.extend(found)

    return sentences


def _extract_grammar_exercises(lines):
    """Extract grammar exercises (passive voice, tenses, etc.)."""
    cleaned = _clean_lines(lines)
    exercises = []

    grammar_start = None
    for i, line in enumerate(cleaned):
        if line.strip().lower() == "grammar":
            grammar_start = i
            break

    if grammar_start is None:
        return exercises

    for i in range(grammar_start, min(grammar_start + 200, len(cleaned))):
        lower = cleaned[i].lower()
        if ("change" in lower and ("passive" in lower or "active" in lower)) or \
           ("rewrite" in lower and i > grammar_start) or \
           ("put the verb" in lower) or \
           ("complete" in lower and ("verb" in lower or "correct form" in lower or
                                      "tense" in lower or "bracket" in lower)) or \
           ("correct" in lower and "form" in lower):
            exercises.extend(_extract_numbered_questions(cleaned, i + 1, max_questions=6))

        # Stop at next major section
        if i > grammar_start + 5 and _is_section_break(cleaned[i]):
            break

    return exercises


def _extract_true_false(lines):
    """Extract True/False questions."""
    cleaned = _clean_lines(lines)
    statements = []

    for i, line in enumerate(cleaned):
        if "true" in line.lower() and "false" in line.lower():
            for j in range(i + 1, min(i + 20, len(cleaned))):
                match = re.match(r'^(\d+)\.\s+(.+)', cleaned[j])
                if match:
                    statements.append(match.group(2))
                elif len(statements) >= 6:
                    break
            if statements:
                break

    return statements


def _extract_writing_prompts(lines):
    """Extract writing/composition prompts."""
    cleaned = _clean_lines(lines)
    prompts = []

    writing_section = False
    for i, line in enumerate(cleaned):
        lower = line.lower()

        if line.strip().lower() == "writing":
            writing_section = True
            continue

        if writing_section and _is_section_break(line) and line.strip().lower() != "writing":
            break

        if ("write" in lower and ("composition" in lower or "essay" in lower or
                                   "article" in lower)) or \
           ("write" in lower and "words" in lower and "no" in lower):
            prompt_text = line.strip()
            for j in range(i + 1, min(i + 10, len(cleaned))):
                next_line = cleaned[j].strip()
                if next_line.startswith("........") or next_line.startswith("……"):
                    break
                if _is_section_break(next_line):
                    break
                if re.match(r'^[a-c]$', next_line):
                    break
                if next_line.startswith("The answer"):
                    prompt_text += " " + next_line
                    break
                prompt_text += " " + next_line
            prompts.append(prompt_text.strip())

    return prompts


def _extract_idioms_exercises(lines):
    """Extract idiom/phrasal verb fill-in exercises."""
    cleaned = _clean_lines(lines)
    exercises = []

    for i, line in enumerate(cleaned):
        lower = line.lower()
        if ("idiom" in lower or "phrasal verb" in lower) and \
           ("fill" in lower or "use" in lower or "replace" in lower or "correct form" in lower):
            exercises.extend(_extract_numbered_questions(cleaned, i + 1, max_questions=6))

    return exercises


def build_question_bank(unit_num):
    """Build a complete question bank for a given unit.

    Returns a dict with question categories as keys and lists of questions as values.
    """
    textbook_lines = get_textbook_unit(unit_num)
    activity_lines = get_activity_unit(unit_num)

    # Get reading passages from both sources
    tb_passage = _extract_reading_passage(textbook_lines)
    act_passage = _extract_reading_passage(activity_lines)

    bank = {
        "reading_passage": tb_passage,
        "reading_passage_activity": act_passage,
        "comprehension": (
            _extract_comprehension_questions(textbook_lines) +
            _extract_comprehension_questions(activity_lines)
        ),
        "vocabulary": _extract_vocabulary_matching(textbook_lines) +
                       _extract_vocabulary_matching(activity_lines),
        "word_meanings": _extract_word_meaning_questions(textbook_lines) +
                          _extract_word_meaning_questions(activity_lines),
        "choose_correct": (
            _extract_choose_correct(textbook_lines) +
            _extract_choose_correct(activity_lines)
        ),
        "rewrite": (
            _extract_rewrite_sentences(textbook_lines) +
            _extract_rewrite_sentences(activity_lines)
        ),
        "complete_sentences": (
            _extract_complete_sentences(textbook_lines) +
            _extract_complete_sentences(activity_lines)
        ),
        "grammar": (
            _extract_grammar_exercises(textbook_lines) +
            _extract_grammar_exercises(activity_lines)
        ),
        "true_false": (
            _extract_true_false(textbook_lines) +
            _extract_true_false(activity_lines)
        ),
        "writing_prompts": (
            _extract_writing_prompts(textbook_lines) +
            _extract_writing_prompts(activity_lines)
        ),
        "idioms": (
            _extract_idioms_exercises(textbook_lines) +
            _extract_idioms_exercises(activity_lines)
        ),
        "unit_info": UNITS[unit_num],
    }

    return bank
