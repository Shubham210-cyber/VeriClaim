"""Recommendation precedence (docs/DECISIONS.md). Deterministic; AI never touches this."""
from dataclasses import dataclass

from app.enums import Category, Recommendation, RuleResult
from app.rules.engine import RuleOutcome

_OPEN = (RuleResult.FAIL, RuleResult.INDETERMINATE)


@dataclass
class Aggregate:
    recommendation: Recommendation
    reason_codes: list[str]
    missing_evidence: list[dict]
    summary: str


def _of(outcomes, *cats):
    return [o for o in outcomes if o.category in cats and o.result in _OPEN]


def _codes(os_):
    return sorted({o.reason_code for o in os_ if o.reason_code})


def aggregate(outcomes: list[RuleOutcome]) -> Aggregate:
    missing: list[dict] = []
    for o in _of(outcomes, Category.MISSING, Category.CLARIFY):
        if o.request and o.request not in missing:
            missing.append(o.request)

    conflicts = _of(outcomes, Category.CONFLICT, Category.AMBIGUOUS)
    rejections = _of(outcomes, Category.REJECTION_CANDIDATE)
    needs_info = _of(outcomes, Category.MISSING, Category.CLARIFY)

    if conflicts:
        rec = Recommendation.HUMAN_REVIEW_REQUIRED
        why, used = "Material conflict or ambiguity needs human judgment: ", conflicts
    elif rejections:
        # A rejection candidate that is independent of any conflict outranks plain missing evidence.
        rec = Recommendation.RECOMMENDED_REJECTION
        why, used = "Reliable evidence establishes a hard eligibility failure: ", rejections
    elif needs_info:
        rec = Recommendation.MORE_INFORMATION_REQUIRED
        why, used = "Required evidence is missing or could not be verified: ", needs_info
    else:
        rec = Recommendation.RECOMMENDED_APPROVAL
        why, used = "Required evidence is present, policy checks pass and no blocking conflict exists.", []
    detail = "; ".join(o.title for o in used)
    return Aggregate(rec, _codes(used), missing, why + detail + ("." if detail else ""))


def processing_failed(code: str) -> Aggregate:
    return Aggregate(Recommendation.PROCESSING_FAILED, [code], [],
                     "A technical error prevented a reliable evaluation. This is not a claim outcome.")
