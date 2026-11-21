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


# Shared syntactic frames with category-specific semantic slots.
PERSON = rf'(?:{RESIDENT}|people|persons)'
CHILD = rf'(?:{DEPENDENT}|a\s+(?:baby|child|toddler)|dependents?\s+under\s+(?:18|eighteen))'
BIRTH = r'(?:born\s+(?:outside\s+(?:the|this)\s+country|abroad|overseas)|(?:who\s+)?(?:were|was)\s+born\s+abroad)'
MOBILITY = r'(?:who\s+)?(?:use|uses|need|needs|rely\s+on)\s+(?:mobility\s+aids|wheelchairs?|walking\s+aids|a\s+walker)'
RELIGIOUS_MEMBER = r'(?:practicing\s+)?members?\s+of\s+(?:(?:our|the|a)\s+)?(?:faith|religion|church|congregation|synagogue|mosque)'
HOME = r'(?:this\s+|the\s+|a\s+)?(?:rental|apartment|home|housing|lease|tenancy|unit)'
EXCLUSIVE = r'(?:is\s+)?(?:reserved\s+for|available\s+only\s+to|restricted\s+to)'
DENIAL = r'(?:will\s+be|is|would\s+be)\s+(?:declined|denied|rejected|refused)'
INDEPENDENCE = r'(?:be\s+)?(?:capable\s+of\s+independent\s+living|able\s+to\s+live\s+independently|self[- ]sufficient)'


def generalized_patterns():
    rules = []
    for category, condition in [('disability', MOBILITY), ('national_origin', BIRTH)]:
        subject = rf'{PERSON}\s+{condition}'
        rules.append((f'{category}.conditional_exclusion', category,
                      rf'\b(?:{subject}\s+{PASSIVE}|(?:we\s+)?{REJECT}\s+{subject})\b', 'error'))
    for category, qualification in [
        ('familial_status', rf'{PERSON}\s+without\s+{CHILD}'),
        ('religion', RELIGIOUS_MEMBER),
    ]:
        rules.append((f'{category}.exclusive_qualification', category,
                      rf'\b{HOME}\s+{EXCLUSIVE}\s+{qualification}\b', 'error'))
    rules.extend([
        ('familial_status.conditional_application', 'familial_status',
         rf'\bif\s+(?:you\s+(?:have|are\s+raising)|your\s+household\s+includes)\s+{CHILD}\s*,?\s*'
         rf'(?:your\s+application\s+{DENIAL}|you\s+{PASSIVE}|you\s+(?:cannot|may\s+not)\s+(?:rent|apply))\b', 'error'),
        ('religion.evidence_requirement', 'religion',
         rf'\b(?:a\s+)?(?:letter|reference|recommendation)\s+from\s+(?:(?:your|a|the)\s+)?'
         rf'(?:pastor|rabbi|imam|priest|religious\s+leader)\s+(?:is|will\s+be)\s+(?:necessary|required)\s+'
         rf'(?:to\s+(?:qualify|apply)\s+for|for)\s+{HOME}\b', 'error'),
        ('familial_status.life_stage_audience', 'familial_status',
         rf'\b(?:best\s+suited\s+to|ideal\s+for|designed\s+for)\s+{PERSON}\s+'
         rf'who\s+(?:have\s+)?(?:finished\s+raising\s+(?:their\s+)?children|no\s+longer\s+have\s+children\s+at\s+home)\b', 'warning'),
        ('disability.independence_expectation', 'disability',
         rf'\b{PERSON}\s+(?:should|(?:are|is)\s+expected\s+to)\s+{INDEPENDENCE}\b', 'warning'),
        ('disability.independence_requirement', 'disability',
         rf'\b{PERSON}\s+{OBLIGATION}\s+{INDEPENDENCE}\b', 'error'),
    ])
    return rules
