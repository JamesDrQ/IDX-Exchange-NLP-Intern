"""Compositional English resident/condition/action grammars.

No unbounded wildcards: a protected term elsewhere in a description cannot bind
an unrelated action across clauses. These are screening heuristics, not a parser.
"""
RESIDENT = r'(?:applicants?|tenants?|residents?|renters?|occupants?|households?|families|parents?)'
DEPENDENT = r'(?:children|kids|babies|infants|toddlers|little ones|school[- ]age children|minors)'
FAMILY = rf'{RESIDENT}\s+(?:with|raising|having|caring for)\s+(?:young\s+)?{DEPENDENT}'
PASSIVE = r'(?:will\s+be|are|is|would\s+be)\s+(?:turned\s+away|rejected|excluded|refused|denied\s+(?:housing|tenancy|a\s+lease))'
REJECT = r'(?:reject|exclude|turn\s+away|refuse\s+to\s+(?:rent|lease)\s+to)'
# Religious activity rather than an architectural style or a nearby landmark.
WORSHIP = r'(?:(?:our|the|a|an|local)\s+)?(?:church|mosque|synagogue|temple|worship\s+services?|religious\s+services?|prayer\s+meetings?)'
ACTIVITY = (rf'(?:attend\s+{WORSHIP}(?!\s+(?:inspection|tour|orientation|safety|renovation|maintenance)\b)|'
            rf'participate\s+in\s+(?:(?:our|the)\s+)?(?:worship|prayer|religious\s+services)|'
            rf'(?:be|become)\s+(?:a\s+)?members?\s+of\s+{WORSHIP})')
OBLIGATION = r'(?:must|shall|have\s+to|has\s+to|(?:are|is)\s+required\s+to)'


def context_patterns():
    """Tuples accepted by the common metadata builder in compliance_patterns."""
    return [
        ('familial_status.indirect_exclusion', 'familial_status',
         rf'\b(?:{FAMILY}\s+(?:{PASSIVE}|(?:cannot|may\s+not)\s+(?:apply|rent|lease))|'
         rf'(?:we\s+)?{REJECT}\s+{FAMILY})\b', 'error'),
        ('familial_status.discouragement', 'familial_status',
         rf'\b{FAMILY}\s+(?:(?:are|is)\s+)?(?:discouraged\s+from\s+applying|not\s+(?:a\s+)?(?:good\s+fit|suitable))\b', 'warning'),
        ('religion.participation_condition', 'religion',
         rf'\b(?:{RESIDENT}\s+{OBLIGATION}\s+{ACTIVITY}|'
         rf'(?:we\s+)?require\s+{RESIDENT}\s+to\s+{ACTIVITY})\b', 'error'),
        ('religion.participation_preference', 'religion',
         rf'\b{RESIDENT}\s+(?:(?:are|is)\s+)?(?:expected|encouraged)\s+to\s+{ACTIVITY}\b', 'warning'),
    ]
