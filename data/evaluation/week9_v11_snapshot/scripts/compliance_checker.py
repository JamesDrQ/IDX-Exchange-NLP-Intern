"""Offline Fair Housing language screening with exact original-text evidence."""
import re
from scripts.compliance_patterns import CATEGORIES, SEVERITIES, ComplianceRule, default_rules


class ComplianceChecker:
    def __init__(self, rules=None):
        self.rules = tuple(default_rules() if rules is None else rules)
        ids = set()
        compiled = []
        for rule in self.rules:
            if not isinstance(rule, ComplianceRule):
                raise TypeError('rules must contain ComplianceRule objects')
            if (not rule.rule_id or rule.rule_id in ids or rule.category not in CATEGORIES
                    or rule.severity not in {'error', 'warning', 'info'}
                    or not rule.explanation or not rule.recommended_action):
                raise ValueError('Invalid rule metadata or duplicate rule ID')
            ids.add(rule.rule_id)
            pattern = re.compile(rule.pattern, re.I)
            if pattern.search(''):
                raise ValueError('Rules must not match empty text')
            compiled.append((rule, pattern))
        self._compiled = tuple(compiled)

    def check_listing(self, text):
        if not isinstance(text, str):
            raise TypeError('Listing description must be a string')
        if not text.strip():
            raise ValueError('Listing description must not be blank')
        # One-character substitutions retain offsets, including curly apostrophes.
        normalized = text.translate(str.maketrans({'’': "'", '–': '-', '—': '-', '‑': '-'}))
        findings = []
        for rule, pattern in self._compiled:
            for match in pattern.finditer(normalized):
                start, end = match.span()
                before = normalized[:start]
                after = normalized[end:]
                # Narrow adjacent negation, not a document-wide allowlist. A later
                # independent exclusion is still checked, even in the same sentence.
                if re.search(r"\b(?:not|never)\s+(?:an?\s+)?$|\b(?:do not|don't)\s+(?:require|prefer)\s+$", before, re.I):
                    continue
                if re.match(r'\s+(?:allowed\s+)?(?:is|are)\s+(?:not\s+(?:our|a)\s+policy|prohibited|not\s+required)\b', after, re.I):
                    continue
                severity, explanation, action = rule.severity, rule.explanation, rule.recommended_action
                # Text claims are unverified: possible exceptions never auto-approve.
                if rule.category == 'familial_status' and severity == 'error' and re.search(
                        r'\b(?:55\+|62\+|senior housing|housing for older persons)', normalized, re.I):
                    severity = 'warning'
                    explanation = 'Possible older-person housing exception claimed; eligibility is unverified.'
                    action = 'Require documented review of HOPA eligibility and the proposed restriction.'
                findings.append(dict(category=rule.category, rule_id=rule.rule_id,
                    matched_text=text[start:end], start=start, end=end, severity=severity,
                    explanation=explanation, recommended_action=action))
        findings.sort(key=lambda f: (f['start'], f['end'], f['rule_id']))
        highest = max((f['severity'] for f in findings), key=SEVERITIES.get, default='none')
        status = 'blocked' if highest == 'error' else 'review_required' if highest == 'warning' else 'ready'
        return {'status': status, 'can_publish': status == 'ready',
                'requires_review': any(f['severity'] == 'warning' for f in findings),
                'highest_severity': highest, 'findings': findings}
