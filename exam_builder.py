"""Assemble exam questions from the question bank into a formatted exam structure."""

import random
from question_bank import build_question_bank_for_source
from config import UNITS


def build_exam(unit_num, source="textbook", num_comprehension=5, num_vocabulary=6,
               num_rewrite=3, num_choose=6, num_complete=4, num_grammar=5, seed=None):
    """Build an exam for the given unit from a specific source book.

    Args:
        unit_num: Unit number (1-12)
        source: "textbook" or "activity"
        num_comprehension: Number of comprehension questions
        num_vocabulary: Number of vocabulary items
        num_rewrite: Number of rewrite/correction sentences
        num_choose: Number of choose-the-correct questions
        num_complete: Number of complete-the-sentence questions
        num_grammar: Number of grammar exercise questions
        seed: Random seed for reproducibility

    Returns:
        Dict with exam sections ready for display/PDF generation
    """
    if seed is not None:
        random.seed(seed)

    bank = build_question_bank_for_source(unit_num, source)
    unit_info = bank["unit_info"]
    source_label = "Student Book" if source == "textbook" else "Activity Book"

    reading = bank["reading_passage"]

    # Comprehension
    comprehension = _sample(bank["comprehension"], num_comprehension)

    # Vocabulary: prefer word_meanings (definitions to match), fall back to vocabulary pairs
    vocab_items = bank.get("word_meanings", [])
    if not vocab_items:
        vocab_items = [item["word"] if isinstance(item, dict) else item
                       for item in bank.get("vocabulary", [])]
    vocab_items = _sample(vocab_items, num_vocabulary)

    # Rewrite sentences
    rewrite_items = _sample(bank["rewrite"], num_rewrite)

    # Choose correct (bracket-choice questions)
    choose_items = _sample(bank["choose_correct"], num_choose)

    # Complete sentences
    complete_items = _sample(bank["complete_sentences"], num_complete)

    # Grammar exercises
    grammar_items = _sample(bank["grammar"], num_grammar)

    # True/False
    true_false_items = _sample(bank.get("true_false", []), 5)

    # Writing prompt
    writing_prompts = bank["writing_prompts"]
    if writing_prompts:
        writing_prompt = random.choice(writing_prompts)
    else:
        writing_prompt = {
            "prompt": f"Write a composition of no less than 80 words about {unit_info['name'].lower()}.",
            "guiding_questions": [],
        }

    exam = {
        "unit_num": unit_num,
        "unit_name": unit_info["name"],
        "module_name": unit_info["module"],
        "grammar_topic": unit_info["grammar"],
        "source": source,
        "source_label": source_label,
        "sections": []
    }

    section_counter = [0]

    def _next_num():
        section_counter[0] += 1
        return section_counter[0]

    # Reading passage
    if reading:
        exam["sections"].append({
            "num": None,
            "title": "Read the following text then do the tasks below:",
            "content": reading,
            "marks": None,
            "type": "passage",
        })

    # Comprehension
    if comprehension:
        exam["sections"].append({
            "num": _next_num(),
            "title": "Answer the following questions:",
            "items": comprehension,
            "marks": len(comprehension) * 4,
            "type": "questions",
        })

    # Vocabulary
    if vocab_items:
        exam["sections"].append({
            "num": _next_num(),
            "title": "Find words in the text which mean the following:",
            "items": vocab_items,
            "marks": len(vocab_items) * 2,
            "type": "vocabulary",
        })

    # Rewrite to correct
    if rewrite_items:
        exam["sections"].append({
            "num": _next_num(),
            "title": "Rewrite the sentences about the text to correct the information:",
            "items": rewrite_items,
            "marks": len(rewrite_items) * 4,
            "type": "questions",
        })

    # True/False
    if true_false_items:
        exam["sections"].append({
            "num": _next_num(),
            "title": "Read the text and decide whether these statements are True or False:",
            "items": true_false_items,
            "marks": len(true_false_items) * 2,
            "type": "true_false",
        })

    # Choose correct
    if choose_items:
        exam["sections"].append({
            "num": _next_num(),
            "title": "Choose the correct answer between brackets:",
            "items": choose_items,
            "marks": len(choose_items) * 3,
            "type": "choose_correct",
        })

    # Complete sentences
    if complete_items:
        exam["sections"].append({
            "num": _next_num(),
            "title": "Complete the following sentences with information from the text:",
            "items": complete_items,
            "marks": len(complete_items) * 3,
            "type": "questions",
        })

    # Grammar rewrite
    if grammar_items:
        exam["sections"].append({
            "num": _next_num(),
            "title": f"Do as required ({unit_info['grammar']}):",
            "items": grammar_items,
            "marks": len(grammar_items) * 4,
            "type": "questions",
        })

    # Composition
    exam["sections"].append({
        "num": _next_num(),
        "title": "Write a composition of no less than 80 words on the following topic:",
        "content": writing_prompt if isinstance(writing_prompt, dict) else {"prompt": writing_prompt, "guiding_questions": []},
        "marks": 20,
        "type": "composition",
    })

    # Total marks
    exam["total_marks"] = sum(s.get("marks", 0) or 0 for s in exam["sections"])

    return exam


def build_combined_exams(unit_num, seed=None, **kwargs):
    """Build two exams (one per book) for the given unit.

    Returns:
        Tuple of (textbook_exam, activity_exam)
    """
    tb_seed = seed if seed is not None else random.randint(0, 100000)
    act_seed = tb_seed + 1

    textbook_exam = build_exam(unit_num, source="textbook", seed=tb_seed, **kwargs)
    activity_exam = build_exam(unit_num, source="activity", seed=act_seed, **kwargs)

    return textbook_exam, activity_exam


def _sample(items, n):
    """Randomly sample up to n items from list."""
    if not items:
        return []
    n = min(n, len(items))
    return random.sample(items, n)
