# Score Rubric

## Active Metric Contract

The current evaluation system uses OmniEval metrics config v2 only.

Required judge metrics:

| Metric | Meaning | Scale | Direction |
| --- | --- | --- | --- |
| ACC | Factual and logical accuracy | 0-1 | Higher is better |
| COM | Completeness against required facts and constraints | 0-1 | Higher is better |
| NAC | Numeric accuracy for dates, amounts, codes, identifiers, and calculations | 0-1 | Higher is better |
| HAL_pass | Hallucination control pass score | 0-1 | Higher is better |

`HAL_rate` is a diagnostic display value calculated as `1 - HAL_pass`. It is not part of the score denominator.

## Overall Score

`overall_score = mean(ACC, COM, NAC, HAL_pass)`

The system stores and displays the 0-1 score directly. It does not convert scores to a larger total scale.

## Pass Policy

A row passes when:

`overall_score >= 0.60 and critical_fail is false`

Judge prompts must not return a separate pass/fail decision. The pipeline derives pass/fail from the normalized metrics and critical failure flag.

## Judge JSON Shape

```json
{
  "scores": {
    "acc": 0.0,
    "com": 0.0,
    "nac": 0.0,
    "hal_pass": 0.0
  },
  "overall_score": 0.0,
  "critical_fail": false,
  "error_type": "normal",
  "reason": "Concise Korean reasoning.",
  "confidence": 0.0,
  "evidence_notes": []
}
```
