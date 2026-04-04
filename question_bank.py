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
        if stripped.isdigit() and len(stripped) <= 3:
            continue
        cleaned.append(stripped)
    return cleaned


def _clean_question_text(text):
    """Clean extracted question text: remove blanks, dots, validate length."""
    # Remove fill-in-the-blank patterns
    text = re.sub(r'[.…·]{3,}', '..........', text)
    # Remove leading/trailing dots and whitespace
    text = text.strip().strip('.').strip()
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text


def _is_valid_question(text):
    """Check if extracted text is a valid question (not garbage)."""
    cleaned = _clean_question_text(text)
    if len(cleaned) < 12:
        return False
    # Reject if it's mostly dots/blanks
    alpha_chars = sum(1 for c in cleaned if c.isalpha())
    if alpha_chars < 8:
        return False
    return True


def _is_section_break(line):
    """Check if a line is a section header that marks a break."""
    lower = line.lower().strip()
    return lower in SECTION_HEADERS


def _join_paragraphs(lines):
    """Join consecutive non-empty lines into paragraphs.
    Blank lines separate paragraphs."""
    paragraphs = []
    current = []
    is_first = True
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            # Treat the very first short line as a title (own paragraph)
            if is_first and not current and len(stripped) < 40 and \
               not stripped.endswith('.') and not stripped.endswith(','):
                paragraphs.append(stripped)
                is_first = False
            else:
                current.append(stripped)
                is_first = False
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def _extract_reading_passage(lines):
    """Extract the main reading passage from unit text."""
    cleaned = _clean_lines(lines)

    reading_start = None
    for i, line in enumerate(cleaned):
        if line.strip().lower() == "reading":
            reading_start = i + 1
            break

    if reading_start is None:
        return ""

    # Skip pre-reading exercises (e.g., "Before you read the text, match...")
    # We need to find where the actual passage starts (usually a title followed by
    # long prose paragraphs), skipping instructions, word lists, and definitions.
    skip_zone = False
    passage_start = reading_start
    found_blank_after_skip = False
    for i in range(reading_start, len(cleaned)):
        line = cleaned[i]
        lower = line.lower().strip()

        # Skip standalone sub-labels
        if re.match(r'^[a-c]$', line):
            skip_zone = True
            found_blank_after_skip = False
            continue
        # Skip instruction lines
        if lower.startswith("before you read") or lower.startswith("match the words") or \
           lower.startswith("match these words") or lower.startswith("in pairs") or \
           lower.startswith("in small groups") or lower.startswith("read the quote") or \
           lower.startswith("discuss"):
            skip_zone = True
            found_blank_after_skip = False
            continue
        # Track blank lines in skip zone
        if not line:
            if skip_zone:
                found_blank_after_skip = True
            continue
        # In skip zone, keep skipping numbered items, lettered defs, and short lines
        if skip_zone:
            if re.match(r'^\d+[\.\)]\s+', line) or re.match(r'^[a-h][\.\)]\s+', line):
                found_blank_after_skip = False
                continue
            # Short continuation lines of definitions (< 50 chars, no capital start after blank)
            if not found_blank_after_skip and len(line) < 50:
                continue
            # After a blank line + a substantial line = likely the passage title or start
            if found_blank_after_skip and len(line) > 10:
                passage_start = i
                skip_zone = False
                break
            continue
        # Not in skip zone: first substantial line is passage start
        if len(line) > 15:
            passage_start = i
            break

    # Now collect the passage text
    passage_lines = []
    for i in range(passage_start, len(cleaned)):
        line = cleaned[i]

        if _is_section_break(line):
            break
        if re.match(r'^[a-c]$', line):
            break
        lower = line.lower()
        if (lower.startswith("answer the following") or
            lower.startswith("read the text") or
            lower.startswith("in pairs") or
            lower.startswith("in small groups") or
            lower.startswith("match these words") or
            lower.startswith("match the words") or
            lower.startswith("find words")):
            break

        passage_lines.append(line)

    return _join_paragraphs(passage_lines)


def _extract_numbered_questions(lines, start_idx, max_questions=10):
    """Extract numbered questions starting from start_idx.
    Returns clean, validated questions only."""
    questions = []
    current_q = ""
    for i in range(start_idx, min(start_idx + 100, len(lines))):
        line = lines[i].strip()
        if not line:
            if current_q:
                # End of multi-line question
                if _is_valid_question(current_q):
                    questions.append(_clean_question_text(current_q))
                current_q = ""
            continue
        if _is_section_break(line):
            break
        match = re.match(r'^(\d+)[\.\)]*\s+(.+)', line)
        if match:
            if current_q and _is_valid_question(current_q):
                questions.append(_clean_question_text(current_q))
            current_q = match.group(2)
        elif line.startswith("........") or line.startswith("……"):
            if current_q and _is_valid_question(current_q):
                questions.append(_clean_question_text(current_q))
            current_q = ""
        elif re.match(r'^[a-d]$', line.lower()):
            if current_q and _is_valid_question(current_q):
                questions.append(_clean_question_text(current_q))
            break
        elif current_q:
            current_q += " " + line

        if len(questions) >= max_questions:
            break

    if current_q and len(questions) < max_questions and _is_valid_question(current_q):
        questions.append(_clean_question_text(current_q))

    return questions


def _extract_comprehension_questions(lines):
    """Extract comprehension questions."""
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
    """Extract vocabulary matching exercises as word-definition pairs."""
    cleaned = _clean_lines(lines)
    words = []
    definitions = []

    # Find words list (numbered: 1. word, 2. word, ...)
    match_start = None
    for i, line in enumerate(cleaned):
        lower = line.lower()
        if ("match" in lower and ("word" in lower or "meaning" in lower)):
            match_start = i
            break

    if match_start is None:
        return []

    # Extract words
    for j in range(match_start + 1, min(match_start + 20, len(cleaned))):
        m = re.match(r'^(\d+)[\.\)]*\s+(.+)', cleaned[j])
        if m:
            words.append(m.group(2).strip())
        elif cleaned[j].strip().startswith("a.") or cleaned[j].strip().startswith("a "):
            break
        elif len(words) >= 8:
            break

    # Extract definitions (a. xxx, b. xxx, ...)
    for j in range(match_start, min(match_start + 40, len(cleaned))):
        m = re.match(r'^([a-h])[\.\)]\s+(.+)', cleaned[j])
        if m:
            # May span multiple lines
            def_text = m.group(2)
            # Check next line for continuation
            if j + 1 < len(cleaned):
                next_line = cleaned[j + 1].strip()
                if next_line and not re.match(r'^[a-h][\.\)]', next_line) and \
                   not re.match(r'^\d+[\.\)]', next_line) and \
                   not _is_section_break(next_line):
                    def_text += " " + next_line
            definitions.append(def_text.strip())

    # Create pairs
    pairs = []
    for idx, word in enumerate(words):
        if idx < len(definitions):
            pairs.append({"word": word, "definition": definitions[idx]})
        else:
            pairs.append({"word": word, "definition": ""})

    return pairs


def _extract_word_meaning_questions(lines):
    """Extract 'guess the meaning' or 'find words that mean' exercises."""
    cleaned = _clean_lines(lines)
    items = []

    for i, line in enumerate(cleaned):
        lower = line.lower()
        if ("guess the meaning" in lower or "find words" in lower or
            "match them with their definitions" in lower or
            "choose the right meaning" in lower):
            for j in range(i + 1, min(i + 30, len(cleaned))):
                m = re.match(r'^(\d+)\s+(.+)', cleaned[j])
                if m:
                    text = m.group(2).strip()
                    # Check for continuation on next line
                    if j + 1 < len(cleaned):
                        next_line = cleaned[j + 1].strip()
                        if next_line and not re.match(r'^\d+\s', next_line) and \
                           not re.match(r'^[a-h][\.\)]', next_line) and \
                           not _is_section_break(next_line) and \
                           not next_line.startswith("……"):
                            text += " " + next_line
                    if len(text) > 5:
                        items.append(text)
                elif len(items) >= 8:
                    break
            if items:
                break

    return items


def _extract_choose_correct(lines):
    """Extract 'choose the correct word' exercises.
    Accepts both (option1/option2) bracket format and a) b) c) d) format."""
    cleaned = _clean_lines(lines)
    questions = []

    for i, line in enumerate(cleaned):
        lower = line.lower()
        if "choose the correct" in lower or "choose the appropriate" in lower or \
           "choose the best" in lower or "circle the correct" in lower or \
           "select the correct" in lower:
            for j in range(i + 1, min(i + 80, len(cleaned))):
                text = cleaned[j]
                if _is_section_break(text):
                    break

                # Match numbered questions
                m = re.match(r'^(\d+)[\.\)]*\s+(.+)', text)
                if m:
                    q_text = m.group(2)
                    # Check continuation on next lines
                    k = j + 1
                    while k < min(j + 5, len(cleaned)):
                        next_line = cleaned[k].strip()
                        if not next_line or re.match(r'^\d+[\.\)]*\s', next_line) or \
                           _is_section_break(next_line):
                            break
                        q_text += " " + next_line
                        k += 1

                    q_text = _clean_question_text(q_text)
                    # Accept bracketed options (word1/word2) OR a)/b)/c)/d) format
                    has_bracket = re.search(r'\([^)]+[/,][^)]+\)', q_text)
                    has_abcd = re.search(r'[ab]\)', q_text) and re.search(r'[cd]\)', q_text)
                    if (has_bracket or has_abcd) and len(q_text) > 15:
                        questions.append(q_text)

    return questions


def _extract_rewrite_sentences(lines):
    """Extract rewrite/correction exercises — only complete sentences."""
    cleaned = _clean_lines(lines)
    sentences = []

    for i, line in enumerate(cleaned):
        lower = line.lower()
        if ("rewrite" in lower and ("correct" in lower or "sentence" in lower or "following" in lower)) or \
           ("correct the following" in lower) or \
           ("fix the mistake" in lower) or \
           ("correct the error" in lower) or \
           ("correct the underlined" in lower):
            found = _extract_numbered_questions(cleaned, i + 1, max_questions=8)
            # Filter: only keep complete sentences without blanks
            for s in found:
                if '……' not in s and '........' not in s and _is_valid_question(s):
                    sentences.append(s)

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
    """Extract grammar exercises — complete sentence transformation tasks."""
    cleaned = _clean_lines(lines)
    exercises = []

    grammar_start = None
    for i, line in enumerate(cleaned):
        if line.strip().lower() == "grammar":
            grammar_start = i
            break

    if grammar_start is None:
        return exercises

    # Also look for grammar exercises outside the Grammar section
    search_ranges = [(grammar_start, min(grammar_start + 200, len(cleaned)))]

    for start, end in search_ranges:
        for i in range(start, end):
            lower = cleaned[i].lower()
            if ("change" in lower and ("passive" in lower or "active" in lower)) or \
               ("rewrite" in lower and i > start) or \
               ("put the verb" in lower) or \
               ("do as required" in lower) or \
               ("join the sentences" in lower) or \
               ("combine" in lower and "sentence" in lower) or \
               ("report" in lower and ("sentence" in lower or "following" in lower)) or \
               ("change" in lower and ("direct" in lower or "indirect" in lower or "reported" in lower)) or \
               ("complete" in lower and ("verb" in lower or "correct form" in lower or
                                          "tense" in lower or "bracket" in lower)) or \
               ("correct" in lower and "form" in lower):
                found = _extract_numbered_questions(cleaned, i + 1, max_questions=8)
                for s in found:
                    clean = _clean_question_text(s)
                    if not re.search(r'[.…]{4,}', s) and not re.search(r'[.…]{4,}', clean) and len(clean) > 20:
                        exercises.append(clean)

            if i > start + 5 and _is_section_break(cleaned[i]) and cleaned[i].strip().lower() != "grammar":
                break

    return exercises


def _extract_true_false(lines):
    """Extract True/False questions. Prefer Reading section, skip Listening."""
    cleaned = _clean_lines(lines)
    statements = []

    for i, line in enumerate(cleaned):
        lower = line.lower()
        if "true" in lower and "false" in lower:
            # Skip if preceded by "Listen" instruction
            context_before = " ".join(cleaned[max(0, i-3):i]).lower()
            if "listen" in context_before:
                continue

            for j in range(i + 1, min(i + 25, len(cleaned))):
                m = re.match(r'^(\d+)[\.\)]*\s+(.+)', cleaned[j])
                if m:
                    text = _clean_question_text(m.group(2))
                    if _is_valid_question(text):
                        statements.append(text)
                elif cleaned[j].strip() == '' and len(statements) > 0:
                    # Allow blank lines between items
                    continue
                elif _is_section_break(cleaned[j]):
                    break
                elif len(statements) >= 8:
                    break
            if statements:
                break

    return statements


def _extract_writing_prompts(lines):
    """Extract writing/composition prompts with guiding questions."""
    cleaned = _clean_lines(lines)
    prompts = []

    for i, line in enumerate(cleaned):
        lower = line.lower()

        if ("write" in lower and ("composition" in lower or "essay" in lower or
                                   "article" in lower)) or \
           ("write" in lower and "words" in lower and ("no" in lower or "less" in lower)):
            prompt_text = line.strip()
            guiding_questions = []

            for j in range(i + 1, min(i + 20, len(cleaned))):
                next_line = cleaned[j].strip()
                if next_line.startswith("........") or next_line.startswith("……"):
                    break
                if _is_section_break(next_line):
                    break
                if re.match(r'^[a-c]$', next_line):
                    break
                # Check for guiding questions (numbered)
                gq = re.match(r'^(\d+)[\.\)]*\s+(.+)', next_line)
                if gq:
                    guiding_questions.append(gq.group(2).strip())
                elif next_line and not next_line.startswith("•"):
                    prompt_text += " " + next_line

            prompts.append({
                "prompt": _clean_question_text(prompt_text),
                "guiding_questions": guiding_questions,
            })

    return prompts


def _extract_idioms_exercises(lines):
    """Extract idiom/phrasal verb exercises — only clean sentences."""
    cleaned = _clean_lines(lines)
    exercises = []

    for i, line in enumerate(cleaned):
        lower = line.lower()
        if ("idiom" in lower or "phrasal verb" in lower) and \
           ("fill" in lower or "use" in lower or "replace" in lower or "correct form" in lower):
            found = _extract_numbered_questions(cleaned, i + 1, max_questions=6)
            for s in found:
                clean = _clean_question_text(s)
                # Only keep sentences without fill-in blanks
                if _is_valid_question(s) and not re.search(r'[.…]{4,}', s):
                    exercises.append(clean)

    return exercises


def _deduplicate(items):
    """Remove duplicate items from a list, preserving order."""
    seen = set()
    result = []
    for item in items:
        key = item.lower().strip() if isinstance(item, str) else str(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def build_question_bank_for_source(unit_num, source="textbook"):
    """Build a question bank for a given unit from a specific source.

    Args:
        unit_num: Unit number (1-12)
        source: "textbook" or "activity"

    Returns:
        Dict with question categories as keys and lists of questions as values.
    """
    if source == "textbook":
        lines = get_textbook_unit(unit_num)
    else:
        lines = get_activity_unit(unit_num)

    bank = {
        "reading_passage": _extract_reading_passage(lines),
        "comprehension": _deduplicate(_extract_comprehension_questions(lines)),
        "vocabulary": _extract_vocabulary_matching(lines),
        "word_meanings": _extract_word_meaning_questions(lines),
        "choose_correct": _deduplicate(_extract_choose_correct(lines)),
        "rewrite": _deduplicate(_extract_rewrite_sentences(lines)),
        "complete_sentences": _deduplicate(_extract_complete_sentences(lines)),
        "grammar": _deduplicate(_extract_grammar_exercises(lines)),
        "true_false": _deduplicate(_extract_true_false(lines)),
        "writing_prompts": _extract_writing_prompts(lines),
        "idioms": _deduplicate(_extract_idioms_exercises(lines)),
        "unit_info": UNITS[unit_num],
        "source": source,
    }

    return bank
