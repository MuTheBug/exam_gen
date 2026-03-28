"""Configuration for exam generator: unit definitions, page ranges, mark allocations."""

UNITS = {
    1: {"name": "Life Choices", "module": "Learning for Life", "module_num": 1,
        "grammar": "Revision of Tenses 1"},
    2: {"name": "Success", "module": "Learning for Life", "module_num": 1,
        "grammar": "Revision of Tenses 2"},
    3: {"name": "Medicine", "module": "Sciences", "module_num": 2,
        "grammar": "Passive Voice"},
    4: {"name": "Engineering", "module": "Sciences", "module_num": 2,
        "grammar": "Causative"},
    5: {"name": "Civil Rights", "module": "Politics", "module_num": 3,
        "grammar": "Relative Clauses"},
    6: {"name": "United Nations", "module": "Politics", "module_num": 3,
        "grammar": "Future Forms"},
    7: {"name": "Microorganisms", "module": "Biology", "module_num": 4,
        "grammar": "Conditionals II, III"},
    8: {"name": "Facts about Human Body", "module": "Biology", "module_num": 4,
        "grammar": "Expressing Wishes"},
    9: {"name": "Citizenship", "module": "Culture", "module_num": 5,
        "grammar": "Paired Conjunctions"},
    10: {"name": "Culture Shock", "module": "Culture", "module_num": 5,
         "grammar": "Reported Speech"},
    11: {"name": "Artificial Intelligence", "module": "Technology", "module_num": 6,
         "grammar": "Linking Words"},
    12: {"name": "Digital Literacy", "module": "Technology", "module_num": 6,
         "grammar": "Revision"},
}


# PDF file paths (relative to project root)
TEXTBOOK_PDF = "E-G12-Scientific-SB.pdf"
ACTIVITY_PDF = "Activity.pdf"
