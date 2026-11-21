"""Resolve local assertion scope without document-wide suppression."""
import re


def is_retracted(text, start, end):
    """Require an adjacent policy frame AND an affirmative rescission.

    Historical vocabulary alone is insufficient. Sentence/semicolon boundaries
    prevent an unrelated rescission from licensing an active restriction.
    """
    before = re.split(r'[.!?;\n]', text[:start])[-1]
    after = re.split(r'[.!?;\n]', text[end:])[0]
    policy = re.search(r'\b(?:(?:former|old|previous)\s+)?(?:rule|policy|requirement|restriction)\s+(?:that\s+)?["\x27]?\s*$', before, re.I)
    rescinded = re.match(r'\s*["\x27]?\s*(?:has\s+been|was|is|has\s+now\s+been)\s+(?:abolished|rescinded|revoked|removed|withdrawn)\b', after, re.I)
    return bool(policy and rescinded)
