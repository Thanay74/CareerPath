# Recommendation Evidence and Scoring

## Student-facing meaning

CareerPath recommendations are exploratory academic guidance. They are not admissions decisions, success probabilities, or professionally validated psychometric results. A numeric personalized compatibility estimate is shown only when at least **two distinct assessment areas** contribute and at least **two actual student-provided inputs** are used. This is a project-level guardrail, not a validated statistical threshold.

If this threshold is not met, a recommendation is labelled a **provisional pathway suggestion**. Personalized score and model-family score fields are null in a newly generated response. Existing API field names remain present for compatibility. Evidence coverage lists each dimension as assessed, missing, or not applicable, and summarizes which inputs were used.

## Evidence dimensions

For career records after Class 10, the scorer can use:

- Self-reported subject-rating fit (subject ratings matching career-record subjects). Self-reported academic performance is a separate dimension; academic history is not substituted for either.
- Scored aptitude domains matching the career record.
- Interest ratings matching the career record.
- Technical and employability skill ratings matching the career record. Only applicable, assessed skill values contribute; explicit Not Applicable entries are excluded from scoring and shown separately.
- Career and research preferences supplied by the student.

For Class 10 pathway comparisons, evidence dimensions are self-reported subject ratings, aptitude, interests, and stated preferences. The selected stream/pathway is contextual and is not a strength score.

Missing values remain unknown. They are not converted to zero. An explicit numeric zero remains an assessed input. Education stage, stream suitability, and degree-route alignment are returned as separate pathway context and are not part of personalized compatibility. Eligibility is evaluated and displayed separately from personal strengths.

## Scoring

Within the personalized evidence dimensions, existing component weights are renormalized across only dimensions with usable evidence. The final estimate uses 90% of this compatibility estimate and 10% of the experimental model-family signal when that signal is available and evidence coverage meets the threshold. Below the evidence threshold, no numeric estimate is published and the model signal is suppressed. Class 10 pathways use their own subject, aptitude, interest, and preference weights with the same minimum evidence rule.

The model-family signal uses existing synthetic-data-trained artifacts. It is labelled experimental and is never a probability of career success or admission. The model artifacts are not retrained or modified by this change.

## Eligibility and limitations

Education stage, stream, and degree are not proof that a student has studied a subject or meets a program's admission rules. CareerPath displays catalog route context and eligibility status separately. Unverified program rules remain unverified. Skill-gap messages report insufficient data when relevant skill ratings are unavailable; unassessed skills are not treated as zero.

The evidence threshold is a pragmatic product safeguard for an MCA academic project, not an empirically validated confidence guarantee. The career catalog and existing model family labels remain limited, and production readiness is not asserted.
