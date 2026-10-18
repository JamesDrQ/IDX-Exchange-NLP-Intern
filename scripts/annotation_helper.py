
from scripts.entity_extractor import EntityExtractor


def generate_candidates(text):
    """Compatibility wrapper returning all exact entity spans."""
    return EntityExtractor().extract_spans(text)
