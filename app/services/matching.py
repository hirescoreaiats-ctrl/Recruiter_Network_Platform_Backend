from __future__ import annotations

import json


def _values(raw):
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw or "[]")
    except Exception:
        return []


def partner_requirement_match(partner, requirement) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    markets = {str(x).casefold() for x in _values(partner.hiring_markets)}
    skills = {str(x).casefold() for x in _values(partner.skill_areas)}
    roles = {str(x).casefold() for x in _values(partner.role_specializations)}
    locations = {str(x).casefold() for x in _values(partner.locations)}
    employment = {str(x).casefold() for x in _values(partner.employment_expertise)}
    required = {str(x).casefold() for x in _values(requirement.required_skills)}

    market_tokens = {requirement.country.casefold(), "us it" if requirement.country == "US" else "india it"}
    if partner.country == requirement.country or markets & market_tokens:
        score += 25
        reasons.append("market")
    overlap = skills & required
    if overlap:
        score += min(45, 15 * len(overlap))
        reasons.append("skills: " + ", ".join(sorted(overlap)))
    title = requirement.title.casefold()
    if any(role in title or title in role for role in roles):
        score += 15
        reasons.append("role specialization")
    if requirement.city.casefold() in locations or (requirement.state_region or "").casefold() in locations:
        score += 10
        reasons.append("location")
    if requirement.employment_type.casefold() in employment:
        score += 5
        reasons.append("employment type")
    return min(score, 100.0), reasons


def candidate_requirement_match(candidate, requirement) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    candidate_skills = {str(x).strip().casefold() for x in _values(candidate.skills) if str(x).strip()}
    required_skills = {str(x).strip().casefold() for x in _values(requirement.required_skills) if str(x).strip()}
    preferred_skills = {str(x).strip().casefold() for x in _values(requirement.preferred_skills) if str(x).strip()}

    required_overlap = candidate_skills & required_skills
    if required_skills:
        score += 55 * (len(required_overlap) / len(required_skills))
    if required_overlap:
        reasons.append("skills: " + ", ".join(sorted(required_overlap)))

    if requirement.min_experience <= candidate.total_experience <= requirement.max_experience:
        score += 20
        reasons.append("experience range")
    elif candidate.total_experience >= max(0, requirement.min_experience - 1):
        score += 8

    if candidate.country == requirement.country:
        score += 10
        reasons.append("country")

    candidate_title = {token for token in candidate.current_title.casefold().split() if len(token) > 2}
    requirement_title = {token for token in requirement.title.casefold().split() if len(token) > 2}
    if candidate_title & requirement_title:
        score += 10
        reasons.append("role title")

    preferred_overlap = candidate_skills & preferred_skills
    if preferred_overlap:
        score += min(5, 2.5 * len(preferred_overlap))
        reasons.append("preferred skills: " + ", ".join(sorted(preferred_overlap)))

    return round(min(score, 100.0), 1), reasons
