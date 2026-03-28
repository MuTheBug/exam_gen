"""Assemble exam questions from the question bank into a formatted exam structure."""

import random
from question_bank import build_question_bank
from config import UNITS


def build_exam(unit_num, num_comprehension=5, num_vocabulary=6, num_rewrite=3,
               num_choose=6, num_complete=4, num_grammar=5, seed=None):
    """Build an exam for the given unit by selecting questions from the question bank.

    Args:
        unit_num: Unit number (1-12)
        num_comprehension: Number of comprehension questions
        num_vocabulary: Number of vocabulary items
        num_rewrite: Number of rewrite/correction sentences
        num_choose: Number of multiple choice questions
        num_complete: Number of complete-the-sentence questions
        num_grammar: Number of grammar exercise questions
        seed: Random seed for reproducibility (None for random)

    Returns:
        Dict with exam sections ready for display/PDF generation
    """
    if seed is not None:
        random.seed(seed)

    bank = build_question_bank(unit_num)
    unit_info = bank["unit_info"]

    # Pick reading passage (prefer textbook, fallback to activity)
    reading = bank["reading_passage"] or bank["reading_passage_activity"]

    # Select comprehension questions
    comprehension = _sample(bank["comprehension"], num_comprehension)

    # Vocabulary: use word meanings or vocabulary matching
    vocab_items = bank.get("word_meanings", [])
    if not vocab_items and bank["vocabulary"]:
        vocab_items = [item["word"] if isinstance(item, dict) else item
                       for item in bank["vocabulary"]]
    vocab_items = _sample(vocab_items, num_vocabulary)

    # Rewrite sentences
    rewrite_items = _sample(bank["rewrite"], num_rewrite)

    # Multiple choice / choose correct
    choose_items = _sample(bank["choose_correct"], num_choose)

    # Complete sentences
    complete_items = _sample(bank["complete_sentences"], num_complete)

    # Grammar exercises
    grammar_items = _sample(bank["grammar"], num_grammar)
    if not grammar_items:
        # Fall back to rewrite items not already used
        remaining = [q for q in bank["rewrite"] if q not in rewrite_items]
        grammar_items = _sample(remaining, num_grammar)

    # True/False (bonus section if available)
    true_false_items = _sample(bank.get("true_false", []), 5)

    # Writing prompt
    writing_prompts = bank["writing_prompts"]
    writing_prompt = random.choice(writing_prompts) if writing_prompts else (
        f"Write a composition of no less than 80 words about {unit_info['name'].lower()}."
    )

    # Idiom exercises
    idiom_items = _sample(bank.get("idioms", []), 6)

    exam = {
        "unit_num": unit_num,
        "unit_name": unit_info["name"],
        "module_name": unit_info["module"],
        "grammar_topic": unit_info["grammar"],
        "sections": []
    }

    # Section I: Reading passage
    if reading:
        exam["sections"].append({
            "id": "reading",
            "title": "Read the following text then do the tasks below:",
            "content": reading,
            "marks": None,
            "type": "passage",
        })

    # Section II: Comprehension questions
    if comprehension:
        exam["sections"].append({
            "id": "comprehension",
            "title": "Answer the following questions:",
            "items": comprehension,
            "marks": len(comprehension) * 4,
            "type": "questions",
        })

    # Section III: Vocabulary - Find words
    if vocab_items:
        exam["sections"].append({
            "id": "vocabulary",
            "title": "Find words in the text which mean the following:",
            "items": vocab_items,
            "marks": len(vocab_items) * 2,
            "type": "vocabulary",
        })

    # Section IV: Rewrite to correct information
    if rewrite_items:
        exam["sections"].append({
            "id": "rewrite_correct",
            "title": "Rewrite the sentences about the text to correct the information:",
            "items": rewrite_items,
            "marks": len(rewrite_items) * 4,
            "type": "questions",
        })

    # Section V: Choose the correct answer
    if choose_items:
        exam["sections"].append({
            "id": "choose_correct",
            "title": "Choose the correct answer A, B, C or D:",
            "items": choose_items,
            "marks": len(choose_items) * 3,
            "type": "multiple_choice",
        })

    # Section VI: Complete sentences
    if complete_items:
        exam["sections"].append({
            "id": "complete_sentences",
            "title": "Complete the following sentences with information from the text:",
            "items": complete_items,
            "marks": len(complete_items) * 3,
            "type": "questions",
        })

    # Section VII: Grammar rewrite
    if grammar_items:
        exam["sections"].append({
            "id": "grammar_rewrite",
            "title": f"Rewrite the following sentences as required ({unit_info['grammar']}):",
            "items": grammar_items,
            "marks": len(grammar_items) * 4,
            "type": "questions",
        })

    # Section VIII: Composition
    exam["sections"].append({
        "id": "composition",
        "title": "Write a composition of no less than 80 words on the following topic:",
        "content": writing_prompt,
        "marks": 20,
        "type": "composition",
    })

    # Calculate total marks
    exam["total_marks"] = sum(
        s.get("marks", 0) or 0 for s in exam["sections"]
    )

    return exam


def _sample(items, n):
    """Randomly sample up to n items from list. Returns all if fewer than n available."""
    if not items:
        return []
    n = min(n, len(items))
    return random.sample(items, n)
