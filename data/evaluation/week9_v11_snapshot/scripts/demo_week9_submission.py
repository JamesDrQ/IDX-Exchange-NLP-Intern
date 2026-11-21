"""Pure submission gate. No database, network, or actual publication."""
import json
from scripts.compliance_checker import ComplianceChecker


def submit_listing(description, checker=None):
    """Return a decision; warnings stay queued until a separate reviewed resubmission.

    Call with the exact final text on every submission/edit. No boolean override
    can bypass errors or approve stale review decisions in this example.
    """
    result = (checker or ComplianceChecker()).check_listing(description)
    return {'publication_allowed': result['can_publish'], 'decision': result['status'],
            'compliance': result}


if __name__ == '__main__':
    for description in ['No children allowed.', 'Ideal for singles.',
                        'Step-free entrance and a sunny patio.']:
        print(json.dumps({'description': description, **submit_listing(description)}, indent=2))
