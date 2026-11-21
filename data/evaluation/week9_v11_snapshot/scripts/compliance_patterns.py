"""Versioned, configurable screening rules; matches are not legal determinations."""
from dataclasses import dataclass
from scripts.compliance_context_patterns import context_patterns

CATEGORIES = frozenset({'race', 'color', 'religion', 'sex', 'national_origin',
                        'familial_status', 'disability'})
SEVERITIES = {'none': 0, 'info': 1, 'warning': 2, 'error': 3}
LIBRARY_VERSION = '1.1'


@dataclass(frozen=True)
class ComplianceRule:
    rule_id: str
    category: str
    pattern: str
    severity: str
    explanation: str
    recommended_action: str


def default_rules():
    """Return fresh immutable rules. Callers may supply a replacement collection."""
    groups = {
        'race': r'(?:white|black|asian|african[- ]american|caucasian)(?:s| people| tenants| applicants| residents)?',
        'color': r'(?:light|dark|fair)[- ]skinned(?: people| tenants| applicants| residents)?',
        'religion': r'(?:christians?|muslims?|jews|jewish(?: people)?|catholics?|hindus?|atheists?)',
        'sex': r'(?:men|women|males?|females?|transgender(?: people)?|gay(?: people)?|lesbians?)(?: applicants| tenants| residents)?',
        'national_origin': r'(?:mexicans?|chinese(?: people)?|indians?|americans?|immigrants?|foreigners?|hispanics?|latinos?)',
        'familial_status': r'(?:children|kids|babies|families with (?:children|kids)|pregnant women)',
        'disability': r'(?:wheelchair users|disabled (?:people|persons|tenants)|people with disabilities|wheelchairs)',
    }
    rules = []
    for category, group in groups.items():
        # Restriction grammar, never an isolated demographic keyword.
        pattern = (rf'\b(?:no\s+{group}(?!\s+(?:restrictions?|limits?)\b)|'
                   rf'{group}\s+(?:(?:are\s+)?(?:not allowed|not welcome)|need not apply|only|preferred)|'
                   rf'only\s+{group}|(?:prefer|preference for)\s+{group}|'
                   rf'(?:do not|don[’\x27]t|will not|won[’\x27]t)\s+(?:rent|sell)\s+to\s+{group})\b')
        rules.append(ComplianceRule(f'{category}.restriction', category, pattern, 'error',
            f'Apparent resident preference or exclusion related to {category.replace("_", " ")}.',
            'Remove the resident restriction and describe the property; obtain compliance review if disputed.'))
    extra = [
        ('familial_status.adults', 'familial_status', r'\b(?:adults?[-\s]+only|no\s+families|must\s+be\s+childless)\b', 'error'),
        ('disability.ability', 'disability', r'\b(?:must\s+be\s+able[-\s]bodied|no\s+(?:service|assistance|emotional support)\s+animals)\b', 'error'),
        ('familial_status.audience', 'familial_status', r'\b(?:perfect|ideal)\s+for\s+(?:singles|adults|couples)|\badult\s+community\b', 'warning'),
        ('race.neighborhood', 'race', r'\b(?:white|black|asian)\s+(?:neighborhood|community)\b', 'warning'),
        ('religion.community', 'religion', r'\b(?:christian|jewish|muslim)\s+(?:community|neighborhood)\b', 'warning'),
        ('national_origin.language', 'national_origin', r'\b(?:english[-\s]+speakers?\s+only|must\s+speak\s+english)\b', 'warning'),
        ('sex.roommate', 'sex', r'\b(?:female|male)\s+roommate\s+(?:wanted|preferred|only)\b', 'warning'),
        ('familial_status.senior', 'familial_status', r'\b(?:55\+|62\+|senior housing|housing for older persons)', 'warning'),
        ('disability.access', 'disability', r'\b(?:wheelchair[-\s]+accessible|step[-\s]+free|accessible entrance)\b', 'info'),
    ]
    extra.extend(context_patterns())
    for rule_id, category, pattern, severity in extra:
        explanation = {'error': 'Apparent exclusion of residents based on a protected characteristic.',
                       'warning': 'Context or eligibility needs review; this phrase alone does not establish discrimination.',
                       'info': 'Positive accessibility feature description; verify factual accuracy.'}[severity]
        action = {'error': 'Remove the exclusion or obtain compliance review of an applicable exception.',
                  'warning': 'Review context and any claimed exception before publication; prefer objective property facts.',
                  'info': 'Keep accurate accessibility details; do not infer accessibility certification.'}[severity]
        rules.append(ComplianceRule(rule_id, category, pattern, severity, explanation, action))
    return tuple(rules)
