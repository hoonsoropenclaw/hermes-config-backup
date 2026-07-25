# arXiv 2508.08220 — User Preference Learning for Image Generation

## Source
- **Paper**: Learning User Preferences for Image Generation Models
- **arXiv**: 2508.08220v1
- **Framework**: MLLM-based Contrastive Preference Learning
- **Key finding**: Outperforms Claude-3.5-Sonnet and human experts on preference prediction

## Core Insight
Negative feedback (disliked images) provides **equally valuable** signal as positive feedback.
Ignoring disliked images loses ~50% of the information available from user feedback.

## Key Numbers
| Setup | Top-1 Accuracy |
|-------|---------------|
| Without negative signal | 35.72% |
| With contrastive negative loss | **37.47%** |
| Human experts | 57.60% |
| Our model (with P_v tokens) | **61.68%** |

> The +1.75% gain from adding negative signals is achieved with no additional model capacity — just better use of existing feedback.

## What This Means for skill-usage-tracker
Current `skill-usage-tracker` only records `combo_rating` (liked direction) but does NOT have a field for `liked: false` with structured negative feedback.

**Minimum viable fix**: Add `liked: bool` field to every JSONL entry.
- `liked: true` + rating 4-5 → positive signal
- `liked: false` + rating 1-2 → negative signal
- Rating 3 without explicit liked → neutral, should NOT be treated as strong positive

## Schema Upgrade (Minimal)
```json
{
  "ts": "...",
  "session_id": "...",
  "task_summary": "...",
  "actual_skills": [...],
  "combo_rating": 4,
  "liked": true,
  "negative_signal_reason": null,
  "individual_ratings": {...},
  "comment": "..."
}
```

## Why This Matters for Hermes
- Current analyze.py has `parse_weak_reward()` but only converts text → number
- It does NOT distinguish "I gave it 3 stars but didn't like it" from "I gave it 3 stars and liked it"
- With `liked` field: `rating + liked` gives 4-state signal instead of 5-state
- 4-state: {liked+high, liked+low, disliked+high, disliked+low} is more informative than 5-state {1,2,3,4,5}

## Implementation Priority
**Low** (architecture already works, just add two fields)
**Value**: Prevents preference model from being biased toward avoiding negative reactions rather than maximizing positive ones
