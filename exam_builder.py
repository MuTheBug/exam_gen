"""Assemble exam questions from the question bank into a formatted exam structure.

Merges questions extracted from PDFs with curated grammar templates to
produce comprehensive exams matching the sample format.
"""

import random
from question_bank import build_question_bank_for_source
from config import UNITS


def _sample(items, n):
    """Randomly sample up to n items from list."""
    if not items:
        return []
    n = min(n, len(items))
    return random.sample(items, n)


def _merge_lists(*lists):
    """Merge multiple lists, deduplicating by lowercase text."""
    seen = set()
    result = []
    for lst in lists:
        for item in lst:
            key = str(item).lower().strip() if isinstance(item, str) else str(item).lower()
            if key not in seen:
                seen.add(key)
                result.append(item)
    return result


def _get_curated_bank(unit_num):
    """Get curated grammar template bank for unit, or empty dict if not available."""
    try:
        from grammar_templates import GRAMMAR_BANK
        return GRAMMAR_BANK.get(unit_num, {})
    except (ImportError, Exception):
        return {}


def build_exam(unit_num, source="textbook", num_comprehension=5, num_vocabulary=6,
               num_rewrite=4, num_choose=6, num_complete=4, num_grammar=5,
               num_mcq=8, num_true_false=5, seed=None):
    """Build an exam for the given unit from a specific source book.

    Merges PDF-extracted questions with curated templates to ensure
    every exam has rich, diverse content.
    """
    if seed is not None:
        random.seed(seed)

    bank = build_question_bank_for_source(unit_num, source)
    curated = _get_curated_bank(unit_num)
    unit_info = bank["unit_info"]
    source_label = "Student Book" if source == "textbook" else "Activity Book"

    reading = bank["reading_passage"]

    # Comprehension questions
    comprehension = _sample(bank["comprehension"], num_comprehension)

    # Vocabulary: prefer word_meanings, fall back to vocabulary pairs
    vocab_items = bank.get("word_meanings", [])
    if not vocab_items:
        vocab_items = [item["word"] if isinstance(item, dict) else item
                       for item in bank.get("vocabulary", [])]
    vocab_items = _sample(vocab_items, num_vocabulary)

    # True/False - merge extracted + curated
    tf_extracted = bank.get("true_false", [])
    tf_curated = curated.get("true_false", [])
    true_false_pool = _merge_lists(tf_extracted, tf_curated)
    true_false_items = _sample(true_false_pool, num_true_false)

    # Choose correct (bracket-choice from PDF)
    choose_items = _sample(bank["choose_correct"], num_choose)

    # MCQ from curated bank (a/b/c/d format)
    mcq_curated = curated.get("grammar_mcq", [])
    vocab_mcq_curated = curated.get("vocabulary_mcq", [])
    mcq_pool = _merge_lists(mcq_curated, vocab_mcq_curated)
    mcq_items = _sample(mcq_pool, num_mcq)

    # Rewrite sentences - merge extracted + curated
    rewrite_extracted = bank["rewrite"]
    rewrite_curated = curated.get("rewrite_correct", [])
    rewrite_pool = _merge_lists(rewrite_extracted, rewrite_curated)
    rewrite_items = _sample(rewrite_pool, num_rewrite)

    # Complete sentences - merge extracted + curated
    complete_extracted = bank["complete_sentences"]
    complete_curated = curated.get("complete_sentences", [])
    complete_pool = _merge_lists(complete_extracted, complete_curated)
    complete_items = _sample(complete_pool, num_complete)

    # Grammar exercises - merge extracted + curated "do as required"
    grammar_extracted = bank["grammar"]
    grammar_curated = curated.get("grammar_rewrite", [])
    # For grammar_curated, each item is a dict with sentence + instruction
    grammar_items = _sample(grammar_extracted, min(num_grammar, len(grammar_extracted)))
    grammar_curated_items = _sample(grammar_curated, num_grammar - len(grammar_items))

    # Writing prompt
    writing_prompts = bank["writing_prompts"]
    if writing_prompts:
        writing_prompt = random.choice(writing_prompts)
    else:
        writing_prompt = {
            "prompt": f"Write a composition of no less than 80 words about {unit_info['name'].lower()}.",
            "guiding_questions": curated.get("writing_guiding", [])[:5],
        }

    # Build exam structure
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

    # I - Reading passage
    if reading:
        exam["sections"].append({
            "num": None,
            "title": "Read the following text then do the tasks below:",
            "content": reading,
            "marks": None,
            "type": "passage",
        })

    # II - Comprehension
    if comprehension:
        exam["sections"].append({
            "num": _next_num(),
            "title": "Answer the following questions:",
            "items": comprehension,
            "marks": len(comprehension) * 4,
            "type": "questions",
        })

    # III - Vocabulary
    if vocab_items:
        exam["sections"].append({
            "num": _next_num(),
            "title": "Find words in the text which mean the following:",
            "items": vocab_items,
            "marks": len(vocab_items) * 2,
            "type": "vocabulary",
        })

    # IV - Rewrite to correct
    if rewrite_items:
        exam["sections"].append({
            "num": _next_num(),
            "title": "Rewrite the sentences about the text to correct the information:",
            "items": rewrite_items,
            "marks": len(rewrite_items) * 3,
            "type": "questions",
        })

    # V - True/False
    if true_false_items:
        exam["sections"].append({
            "num": _next_num(),
            "title": "Read the text and decide whether these statements are True or False:",
            "items": true_false_items,
            "marks": len(true_false_items) * 2,
            "type": "true_false",
        })

    # VI - Choose correct answer (MCQ with a/b/c/d)
    if mcq_items:
        exam["sections"].append({
            "num": _next_num(),
            "title": "Choose the correct answer A, B, C or D:",
            "items": mcq_items,
            "marks": len(mcq_items) * 3,
            "type": "mcq",
        })

    # VII - Choose correct (bracket format from PDF)
    if choose_items:
        exam["sections"].append({
            "num": _next_num(),
            "title": "Choose the correct answer between brackets:",
            "items": choose_items,
            "marks": len(choose_items) * 3,
            "type": "questions",
        })

    # VIII - Complete sentences
    if complete_items:
        exam["sections"].append({
            "num": _next_num(),
            "title": "Complete the following sentences with information from the text:",
            "items": complete_items,
            "marks": len(complete_items) * 3,
            "type": "questions",
        })

    # IX - Do as required (Grammar)
    if grammar_items or grammar_curated_items:
        all_grammar = []
        # Add extracted grammar items as plain strings
        for g in grammar_items:
            all_grammar.append(g)
        # Add curated grammar items as dicts with instruction
        for g in grammar_curated_items:
            if isinstance(g, dict):
                all_grammar.append(g)
            else:
                all_grammar.append(str(g))

        exam["sections"].append({
            "num": _next_num(),
            "title": f"Do as required ({unit_info['grammar']}):",
            "items": all_grammar,
            "marks": len(all_grammar) * 4,
            "type": "do_as_required",
        })

    # X - Composition
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


def build_mixed_exam(selections, seed=None, **kwargs):
    """Build a list of exams from arbitrary unit/source combinations.

    Args:
        selections: List of dicts, each with 'unit' (int) and 'source' ("textbook"/"activity")
        seed: Random seed
        **kwargs: Passed to build_exam (num_comprehension, etc.)

    Returns:
        List of exam dicts, one per selection
    """
    base_seed = seed if seed is not None else random.randint(0, 100000)
    exams = []
    for i, sel in enumerate(selections):
        exam = build_exam(
            sel['unit'],
            source=sel['source'],
            seed=base_seed + i,
            **kwargs,
        )
        exams.append(exam)
    return exams


def build_single_model_exam(unit_nums, seed=None,
                            num_comprehension=3, num_vocabulary=5,
                            num_rewrite=3, num_complete=3,
                            num_mcq=6, num_grammar=5,
                            num_true_false=4):
    """Build a single unified exam (two columns A+B) from multiple units.

    Picks two passages from different units/sources. Text-related questions
    (comprehension, vocabulary, rewrite, complete, true/false) stay with their
    passage. Non-text questions (MCQ, grammar, composition) are pooled from
    all selected units.

    Args:
        unit_nums: List of unit numbers to draw from (e.g. [1, 3, 5, 7])
        seed: Random seed

    Returns:
        Tuple of (exam_a, exam_b) where each is an exam dict for one column
    """
    if seed is not None:
        random.seed(seed)

    if not unit_nums:
        unit_nums = [1]

    # Collect banks from all selected units, both sources
    all_banks = []
    for u in unit_nums:
        for src in ['textbook', 'activity']:
            bank = build_question_bank_for_source(u, src)
            curated = _get_curated_bank(u)
            if bank['reading_passage'] and len(bank['reading_passage']) > 100:
                all_banks.append({
                    'unit': u,
                    'source': src,
                    'bank': bank,
                    'curated': curated,
                    'unit_info': bank['unit_info'],
                })

    if len(all_banks) < 2:
        # Fallback: duplicate
        all_banks = all_banks * 2

    # Pick 2 different passage sources randomly
    chosen = random.sample(all_banks, min(2, len(all_banks)))

    # Pool non-text questions from ALL selected units
    all_mcq = []
    all_grammar_rewrite = []
    all_grammar_extracted = []
    all_writing_prompts = []

    for entry in all_banks:
        bank = entry['bank']
        curated = entry['curated']
        all_mcq.extend(curated.get('grammar_mcq', []))
        all_mcq.extend(curated.get('vocabulary_mcq', []))
        all_grammar_rewrite.extend(curated.get('grammar_rewrite', []))
        all_grammar_extracted.extend(bank.get('grammar', []))
        all_writing_prompts.extend(bank.get('writing_prompts', []))

    # Deduplicate pooled questions
    all_mcq = _deduplicate_dicts(all_mcq, key='stem')
    all_grammar_rewrite = _deduplicate_dicts(all_grammar_rewrite, key='sentence')
    all_grammar_extracted = list({s: s for s in all_grammar_extracted}.values())

    # Split pooled questions between the two exams
    mcq_a = _sample(all_mcq, num_mcq)
    remaining_mcq = [q for q in all_mcq if q not in mcq_a]
    mcq_b = _sample(remaining_mcq, num_mcq)

    grammar_pool = all_grammar_extracted + [
        g.get('sentence', str(g)) if isinstance(g, dict) else str(g)
        for g in all_grammar_rewrite
    ]
    random.shuffle(grammar_pool)
    grammar_a = grammar_pool[:num_grammar]
    grammar_b = grammar_pool[num_grammar:num_grammar * 2]

    # Build each exam column
    exams = []
    for idx, entry in enumerate(chosen):
        bank = entry['bank']
        curated = entry['curated']
        unit_info = entry['unit_info']

        reading = bank['reading_passage']
        source_label = "Student Book" if entry['source'] == 'textbook' else "Activity Book"

        # Text-related questions (from THIS passage's unit only)
        comprehension = _sample(bank['comprehension'], num_comprehension)

        vocab_items = bank.get('word_meanings', [])
        if not vocab_items:
            vocab_items = [item['word'] if isinstance(item, dict) else item
                           for item in bank.get('vocabulary', [])]
        vocab_items = _sample(vocab_items, num_vocabulary)

        rewrite_extracted = bank.get('rewrite', [])
        rewrite_curated = curated.get('rewrite_correct', [])
        rewrite_pool = _merge_lists(rewrite_extracted, rewrite_curated)
        rewrite_items = _sample(rewrite_pool, num_rewrite)

        tf_extracted = bank.get('true_false', [])
        tf_curated = curated.get('true_false', [])
        tf_pool = _merge_lists(tf_extracted, tf_curated)
        true_false_items = _sample(tf_pool, num_true_false)

        complete_extracted = bank.get('complete_sentences', [])
        complete_curated = curated.get('complete_sentences', [])
        complete_pool = _merge_lists(complete_extracted, complete_curated)
        complete_items = _sample(complete_pool, num_complete)

        # Use pooled non-text questions
        my_mcq = mcq_a if idx == 0 else mcq_b
        my_grammar = grammar_a if idx == 0 else grammar_b

        # Writing prompt
        if all_writing_prompts:
            writing_prompt = random.choice(all_writing_prompts)
        else:
            writing_prompt = {
                "prompt": f"Write a composition of no less than 80 words about "
                          f"{unit_info['name'].lower()}.",
                "guiding_questions": curated.get('writing_guiding', [])[:5],
            }

        # Build exam structure
        exam = {
            "unit_num": entry['unit'],
            "unit_name": unit_info['name'],
            "source": entry['source'],
            "source_label": source_label,
            "sections": [],
        }

        section_counter = [0]
        def _next():
            section_counter[0] += 1
            return section_counter[0]

        # Reading passage
        if reading:
            exam["sections"].append({
                "num": None,
                "title": "Read the following text then do the tasks below:",
                "content": reading, "marks": None, "type": "passage",
            })

        # Comprehension
        if comprehension:
            exam["sections"].append({
                "num": _next(),
                "title": "Answer the following questions:",
                "items": comprehension, "marks": len(comprehension) * 4,
                "type": "questions",
            })

        # Vocabulary
        if vocab_items:
            exam["sections"].append({
                "num": _next(),
                "title": "Find words in the text which mean the following:",
                "items": vocab_items, "marks": len(vocab_items) * 2,
                "type": "vocabulary",
            })

        # Rewrite to correct
        if rewrite_items:
            exam["sections"].append({
                "num": _next(),
                "title": "Rewrite to correct the information:",
                "items": rewrite_items, "marks": len(rewrite_items) * 3,
                "type": "questions",
            })

        # True/False
        if true_false_items:
            exam["sections"].append({
                "num": _next(),
                "title": "True or False:",
                "items": true_false_items, "marks": len(true_false_items) * 2,
                "type": "true_false",
            })

        # MCQ (pooled)
        if my_mcq:
            exam["sections"].append({
                "num": _next(),
                "title": "Choose the correct answer A, B, C or D:",
                "items": my_mcq, "marks": len(my_mcq) * 3,
                "type": "mcq",
            })

        # Complete sentences
        if complete_items:
            exam["sections"].append({
                "num": _next(),
                "title": "Complete from the text:",
                "items": complete_items, "marks": len(complete_items) * 3,
                "type": "questions",
            })

        # Grammar (pooled)
        if my_grammar:
            grammar_topic = unit_info.get('grammar', 'Grammar')
            exam["sections"].append({
                "num": _next(),
                "title": f"Do as required ({grammar_topic}):",
                "items": my_grammar, "marks": len(my_grammar) * 4,
                "type": "do_as_required",
            })

        # Composition (only on the second column to save space)
        if idx == 1:
            exam["sections"].append({
                "num": _next(),
                "title": "Write a composition of no less than 80 words on the "
                         "following topic:",
                "content": writing_prompt if isinstance(writing_prompt, dict)
                           else {"prompt": writing_prompt, "guiding_questions": []},
                "marks": 20,
                "type": "composition",
            })

        exam["total_marks"] = sum(s.get("marks", 0) or 0 for s in exam["sections"])
        exams.append(exam)

    return exams[0], exams[1]


def _deduplicate_dicts(items, key='stem'):
    """Remove duplicate dicts by a key field, preserving order."""
    seen = set()
    result = []
    for item in items:
        if isinstance(item, dict):
            k = item.get(key, '').lower().strip()
        else:
            k = str(item).lower().strip()
        if k and k not in seen:
            seen.add(k)
            result.append(item)
    return result
