# FAiND System Brain — Version 4.4 PATCH
## Applies on top of V4.1, V4.2, and V4.3

This patch supersedes any conflicting logic in previous versions
regarding Path B and Path C verification forms and scoring.

---

## ⚠️ CHANGELOG — V4.4

### Summary of Changes

1. Path C form simplified — hidden answers only, no image or location
2. Path C scoring updated — hidden answers only (1.0 weight)
3. Path B form unchanged — questions + image + location
4. Path B scoring unchanged

---

# Path B — "I Have This Item" — UNCHANGED FROM V4.3

Path B form remains:
- Owner's hidden questions displayed (questions only, never answers)
- Finder answers each question
- Location dropdown (where they found it)
- Optional photo upload

Path B scoring remains (Section 12.4 of V4.3):
- Hidden answer similarity: 0.70
- Image similarity: 0.15
- Location proximity: 0.15
- With all weight redistribution rules from V4.3

**Why Path B keeps image and location:**
The finder physically has the item in their hands. Taking a photo
and saying where they found it is natural, easy, and adds real
supporting evidence. It costs them nothing extra and gives admins
visual evidence during review.

---

# Path C — "This Might Be Mine" — UPDATED V4.4

## Form — SIMPLIFIED

Path C form now contains ONLY:
- The finder's hidden questions displayed (questions only, never answers)
- Answer input fields for each question
- Submit button

**Remove from Path C form:**
- Location dropdown — owner may not remember exactly where they lost it
- Date picker — owner may not remember exact date
- Description field — not needed, adds friction

**Why Path C removes image and location:**
The owner does not have the item — they lost it. Asking them to
provide a photo makes no sense. Asking for location is unfair
because they may not remember exactly where they lost it.
The only thing they genuinely know is specific details about
their own item — which the hidden questions capture perfectly.

## Path C Scoring — UPDATED V4.4

| Factor | Weight | Notes |
|---|---|---|
| Hidden answer similarity | 1.0 | Only signal — pure proof of ownership |

**Thresholds (unchanged):**
- Score > 0.70 → auto-approved, chat unlocks
- Score 0.50–0.70 → admin review
- Score < 0.50 → rejected

**Auto-approve override:**
- Hidden answer score > 0.80 → auto-approve immediately

**Auto-reject override:**
- Hidden answer score < 0.40 → auto-reject immediately

**Attempt limits (unchanged from V4.3):**
- Maximum 3 attempts per user per found item
- 1st failed: no penalty
- 2nd failed: trust -3
- 3rd failed: trust -5, fraud risk +20, admin alerted
- 4th attempt: blocked
- 3rd attempt landing in admin review: counter pauses

---

# Implementation Notes for Agent

**Backend:**
- Update Path C verification service:
  - Remove location scoring completely
  - Remove date from claim model for Path C
  - Score using hidden answers only (1.0 weight)
  - Apply auto-approve override (> 0.80) and auto-reject override (< 0.40)
  - Keep all attempt limit logic from V4.3 unchanged

**Frontend:**
- Update Path C form:
  - Remove location dropdown
  - Remove date picker
  - Remove any description field
  - Show only finder's hidden questions and answer inputs
  - Submit button

**Do not change:**
- Path B form or scoring
- Path A verification
- AI matching engine
- Any other feature
