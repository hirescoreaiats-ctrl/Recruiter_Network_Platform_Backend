from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class EvaluationAdapter(Protocol):
    provider: str
    version: str

    def evaluate(self, requirement: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class LocalHireScoreContractAdapter:
    """Deterministic development adapter shaped like the HireScoreAI result contract.

    It is intentionally conservative: profile claims are not described as resume evidence,
    confidence is capped, and the provider label makes clear that this is not production scoring.
    """

    provider: str = "hirescoreai_local_contract_mock"
    version: str = "1.0"

    def evaluate(self, requirement: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        required = [str(x).strip() for x in requirement.get("required_skills", []) if str(x).strip()]
        preferred = [str(x).strip() for x in requirement.get("preferred_skills", []) if str(x).strip()]
        claims = [str(x).strip() for x in candidate.get("skills", []) if str(x).strip()]
        claim_map = {x.casefold(): x for x in claims}
        matched = [skill for skill in required if skill.casefold() in claim_map]
        missing = [skill for skill in required if skill.casefold() not in claim_map]
        preferred_matched = [skill for skill in preferred if skill.casefold() in claim_map]

        skill_ratio = len(matched) / max(1, len(required))
        years = float(candidate.get("total_experience") or 0)
        minimum = float(requirement.get("min_experience") or 0)
        maximum = float(requirement.get("max_experience") or minimum or 60)
        experience_compatible = years >= minimum and (maximum <= 0 or years <= maximum + 3)
        experience_score = 20 if experience_compatible else max(0, 20 - abs(years - minimum) * 4)
        title_words = set(str(requirement.get("title") or "").casefold().split())
        candidate_title = set(str(candidate.get("current_title") or "").casefold().split())
        title_score = 10 if title_words & candidate_title else 4
        score = round(min(100, skill_ratio * 70 + experience_score + title_score), 1)
        fit_band = "strong" if score >= 80 and not missing else "moderate" if score >= 60 else "review"
        recommendation = "qualified" if fit_band == "strong" else "review"

        return {
            "final_score": score,
            "rank_score": score,
            "fit_band": fit_band,
            "recommendation": recommendation,
            "confidence_score": 60.0,
            "resume_quality_score": None,
            "mandatory_requirements": {"matched": len(matched), "total": len(required)},
            "matched_requirements": matched,
            "missing_requirements": missing,
            "preferred_skills_matched": preferred_matched,
            "skill_evidence": [
                {"skill": skill, "evidence_level": "candidate_profile_claim", "snippet": "Not verified against resume in local MVP"}
                for skill in matched
            ],
            "seniority_fit": "compatible" if experience_compatible else "needs_review",
            "domain_fit": "not_assessed",
            "relevant_projects": [],
            "risks": (["Missing mandatory profile claims: " + ", ".join(missing)] if missing else [])
            + ["Local development evaluation; production HireScoreAI service not connected."],
            "ranking_reason": f"{len(matched)}/{len(required)} mandatory skills are claimed in the candidate profile; experience is {'compatible' if experience_compatible else 'outside the target range'}.",
            "provider": self.provider,
            "provider_version": self.version,
        }


def get_evaluation_adapter() -> EvaluationAdapter:
    return LocalHireScoreContractAdapter()
