"""Extract text from the two PDF books and split by unit."""

import os
import re
import subprocess
import functools
from config import TEXTBOOK_PDF, ACTIVITY_PDF, UNITS


def _get_project_dir():
    return os.path.dirname(os.path.abspath(__file__))


@functools.lru_cache(maxsize=4)
def extract_full_text(pdf_filename):
    """Extract all text from a PDF using pdftotext. Results are cached."""
    pdf_path = os.path.join(_get_project_dir(), pdf_filename)
    result = subprocess.run(
        ["pdftotext", pdf_path, "-"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed: {result.stderr}")
    return result.stdout.splitlines()


@functools.lru_cache(maxsize=4)
def _find_unit_boundaries(pdf_filename):
    """Dynamically find unit boundaries in the extracted text.

    Returns a dict mapping unit number to (start_index, end_index) in the lines list.
    We look for lines matching 'Unit N' followed by the unit name on a nearby line.
    We skip table-of-contents occurrences by picking the LAST occurrence of each unit header.
    """
    lines = extract_full_text(pdf_filename)
    unit_positions = {}

    for i, line in enumerate(lines):
        stripped = line.strip()
        match = re.match(r'^Unit\s+(\d+)$', stripped)
        if match:
            unit_num = int(match.group(1))
            if unit_num in UNITS:
                # Verify by checking nearby lines for the unit name
                unit_name = UNITS[unit_num]["name"]
                context = " ".join(
                    lines[j].strip() for j in range(i + 1, min(i + 5, len(lines)))
                )
                # Always take the latest occurrence (skips ToC entries)
                unit_positions[unit_num] = i

    # Convert to (start, end) ranges
    boundaries = {}
    sorted_items = sorted(unit_positions.items(), key=lambda x: x[1])
    for idx, (unit_num, start) in enumerate(sorted_items):
        if idx + 1 < len(sorted_items):
            end = sorted_items[idx + 1][1]
        else:
            end = len(lines)
        boundaries[unit_num] = (start, end)

    return boundaries


def get_unit_text(pdf_filename, unit_num):
    """Get the text for a specific unit from a PDF.

    Args:
        pdf_filename: Name of the PDF file
        unit_num: The unit number (1-12)

    Returns:
        List of text lines for the requested unit
    """
    lines = extract_full_text(pdf_filename)
    boundaries = _find_unit_boundaries(pdf_filename)

    if unit_num not in boundaries:
        return []

    start, end = boundaries[unit_num]
    return lines[start:end]


def get_textbook_unit(unit_num):
    """Get textbook content for a unit."""
    return get_unit_text(TEXTBOOK_PDF, unit_num)


def get_activity_unit(unit_num):
    """Get activity book content for a unit."""
    return get_unit_text(ACTIVITY_PDF, unit_num)
