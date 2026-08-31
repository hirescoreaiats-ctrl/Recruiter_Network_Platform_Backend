# Database schema

## Identity and tenancy

- `users`: authentication identity and immutable role.
- `companies`, `company_members`: client tenant and membership.
- `sourcing_partner_profiles`: market, technology, role, location, employment, and authorization expertise.
- `candidate_profiles`, `resume_files`: direct or partner-owned candidate identity and protected local documents.

## Requirements and distribution

- `requirements`: country-aware role and hiring details.
- `requirement_submission_schemas`: versioned required candidate fields.
- `requirement_commercial_terms`: immutable payout/payment/replacement versions.
- `requirement_partners`: partner match, work state, and accepted terms version.

## Candidate decision state

- `candidate_availability`: freshness and confirmation source/date.
- `candidate_interests`: role-specific interest.
- `applications`: source/provenance, pipeline state, submission data, and readiness.
- `candidate_eligibility`: market/eligibility result independent from fit.
- `candidate_evaluations`: versioned structured evaluation contract.
- `candidate_ownership`: partner ownership and optional future expiry.
- `duplicate_attempts`: rejected duplicate audit trail and match signal.

## Fulfillment and collaboration

- `placements`: vendor/candidate/partner claims and aggregate verification.
- `payouts`: fixed commercial snapshot and status tracking.
- `conversations`, `messages`: contextual human client-partner chat.
- `audit_logs`: actor, action, entity, details, and timestamp.

Readiness is derived only when fit is strong, availability is current, interest is confirmed, eligibility is compatible, and all required submission data is complete.
