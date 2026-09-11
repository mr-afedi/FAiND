# FAiND System Brain — Version 4.2
## Authoritative Master Reference for the FAiND Project

This document supersedes ALL previous versions including V4.1.

---

## ⚠️ CHANGELOG — V4.2 (Read This First)

### What Changed and Why

**CRITICAL LOGIC CHANGE — Ownership Verification Questions**

In V4.1, hidden verification questions were set by the LOST ITEM OWNER
when posting a lost item. This was logically flawed because the owner
was answering questions they themselves had set — making it trivially
easy and not a true proof of ownership.

**The new logic (V4.2):**
- Hidden verification questions are set by the FINDER when posting a
  FOUND ITEM — because the finder physically has the item and can ask
  specific questions only the real owner would know the answers to
- The OWNER answers the finder's hidden questions during verification
- The AI compares the owner's answers against the finder's stored answers
- If matched above threshold → chat unlocks

**Sections changed:**
- Section 6: Lost Item Reporting — hidden questions REMOVED
- Section 7: Found Item Reporting — hidden questions ADDED
- Section 8: Path A — verification flow updated
- Section 8: Path B — unchanged (description matching only)
- Section 8: Path C — verification flow updated (same as Path A)
- Section 12: Ownership Verification — score formula updated

**What the agent must do:**
- Remove hidden question fields from the lost item reporting form (frontend)
- Remove hidden question storage from the lost item backend model and API
- Add hidden question fields to the found item reporting form (frontend)
- Add hidden question storage to the found item backend model and API
- Update Path A verification: owner answers finder's questions
- Update Path C verification: owner answers finder's questions (same logic)
- Path B remains unchanged — description matching only, no questions
- Update all related database migrations
- Update all related API endpoints
- Update all related frontend forms and verification screens

---

# 6. Lost Item Reporting — UPDATED V4.2

When a registered user reports a lost item, they must provide:
- **Category** (fixed list: Electronics, Bag, ID/Card, Keys, Clothing,
  Books/Notes, Wallet, Jewellery, Other)
- **Short public description** — visible to all users
- **Detailed private description** — AES-256-GCM encrypted; used only
  in Path B verification; never shown publicly
- **Campus location** — dropdown storing location_label + lat/lng
- **Date and time lost**
- **Optional images** — maximum 2, Cloudinary

## ⚠️ REMOVED IN V4.2
Hidden verification questions and answers are NO LONGER part of the
lost item reporting form. They have been moved to the found item
reporting form. Do not implement hidden questions on lost item posting.

---

# 7. Found Item Reporting — UPDATED V4.2

When a registered user reports a found item, they must provide:
- **Category** (same fixed list)
- **Short description** of the item as found
- **Campus location** — same dropdown, stores label + lat/lng
- **Date and time found**
- **At least one image** — required, maximum 2, Cloudinary
- **2–3 hidden verification questions with answers** — AES-256-GCM
  encrypted; never returned in any API response; immutable after
  submission

## 7.1 Why the Finder Sets the Questions
The finder physically has the item in their possession. They are in
the best position to ask specific, detailed questions about the item's
physical characteristics that only the real owner would know.

Examples of good finder questions:
- "What color is the inside lining of the bag?"
- "Is there a scratch or damage anywhere? Describe it."
- "What was inside the front pocket?"
- "Is there a name or marking written anywhere inside?"
- "Describe any sticker or personalisation on the item."

Examples of bad questions (too guessable):
- "What color is it?" — visible in the photo
- "What brand is it?" — visible in the photo

## 7.2 Hidden Answer Rules
- Stored AES-256-GCM encrypted at rest
- Never returned in any API response to any user including the finder
- Immutable after submission — cannot be edited
- Decrypted in memory only during verification scoring — never logged

## 7.3 Initial Status: FOUND
## 7.4 Trust Reward: +2 points on successful submission

---

# 8. The Three Paths to Chat — UPDATED V4.2

---

## Path A — AI Match Flow — UPDATED V4.2

**Condition:** Both a lost item and found item exist. AI finds a match.

1. New item posted → AI matching runs as BackgroundTask
2. Match score ≥ 0.60 → PotentialMatch record created
3. Both users notified
4. Lost item status → POTENTIAL_MATCH
5. Lost item owner clicks "Verify Ownership"
6. Owner is shown the FINDER'S hidden questions (questions only —
   not answers)
7. Owner types their answers to the finder's questions
8. AI scores owner's answers against finder's encrypted answers
9. Score > 0.75 → chat unlocks immediately
10. Score 0.50–0.75 → admin review queue
11. Score < 0.50 → rejected, penalty may apply

## ⚠️ KEY CHANGE FROM V4.1
The owner no longer answers questions they set themselves.
The owner answers questions the FINDER set about the physical item.
This proves the owner genuinely knows their own item's private details
without having seen it recently — details a fraudster could not guess.

---

## Path B — "I Have This Item" Flow — UNCHANGED IN V4.2

Path B remains exactly as defined in V4.1.
No hidden questions are involved in Path B.
Verification is description-based only — the finder's submitted
description is compared against the lost item's private description.

---

## Path C — "This Might Be Mine" Flow — UPDATED V4.2

**Condition:** An owner sees a found item post but has not posted a
lost item yet.

**⚠️ CHANGE FROM V4.1:** Path C now uses the same verification logic
as Path A — the owner answers the FINDER'S hidden questions.

Steps:
1. Logged-in user (not the found item poster) views a found item post
2. Clicks "This Might Be Mine"
3. Fills out form:
   - Description of the item as they remember it
   - Where they lost it (campus location dropdown)
   - When they lost it (date picker)
4. AI runs a preliminary description similarity check against the
   found item's public description and photo
5. If preliminary score > 0.40 → proceed to verification step
6. Owner is shown the FINDER'S hidden questions
7. Owner answers the finder's questions
8. AI scores answers against finder's encrypted answers
9. Score > 0.75 → chat unlocks
10. Score 0.50–0.75 → admin review
11. Score < 0.50 → rejected

## ⚠️ KEY CHANGE FROM V4.1
Path C no longer uses description matching only.
It now uses the finder's hidden questions — same as Path A.
The preliminary description check (step 4) is just a pre-filter to
avoid showing questions to obviously wrong claimants.

---

# 12. Ownership Verification Logic — UPDATED V4.2

## 12.1 Entry Points
- Path A: "Verify Ownership" button on matched found item
- Path B: Automatic after "I Have This Item" submission
- Path C: "This Might Be Mine" form → preliminary check → question step

Button must always say "Verify Ownership" — never "Claim" or "Take".

## 12.2 Who Sets Questions, Who Answers
- **Questions set by:** FINDER (when posting found item)
- **Questions answered by:** OWNER (during verification)
- **AI compares:** owner's answers vs finder's encrypted answers

## 12.3 Path A and C Ownership Score Formula — UPDATED V4.2

| Factor | Weight | Notes |
|---|---|---|
| Hidden answer similarity | 0.70 | Primary signal — owner answers finder's questions |
| Description similarity | 0.30 | Owner's description vs found item public description |

⚠️ Image similarity removed from Path A and C formula in V4.2.
The finder's questions are now the dominant verification signal.
Image similarity is used only in AI item matching (Section 10),
not in ownership verification scoring.

## 12.4 Path B Ownership Score Formula — UNCHANGED

| Factor | Weight | Notes |
|---|---|---|
| Description similarity | 0.70 | Finder's description vs lost item private description |
| Image similarity | 0.30 | Only if finder provides a photo |

## 12.5 Decision Thresholds — UNCHANGED
- Score > 0.75 → Auto-approved — chat unlocks immediately
- Score 0.50–0.75 → Admin review — both users notified
- Score < 0.50 → Rejected — claimant notified

## 12.6 Anti-Abuse Rules — UNCHANGED
- Max 3 attempts per user per item per 24 hours
- 2nd and 3rd failed attempts: -3 trust points each
- 3 failed attempts: fraud risk +20, admin alerted

## 12.7 False Claim Penalty — UNCHANGED
Score < 0.30 or admin-confirmed: -10 trust points

---

# Implementation Notes for Agent

When implementing this change, the agent must:

1. **Database:**
   - Remove hidden_questions and hidden_answers from lost items table/model
   - Add hidden_questions and hidden_answers to found items table/model
   - Create and run Alembic migration for these changes

2. **Backend:**
   - Remove hidden question endpoints from lost item API
   - Add hidden question storage to found item creation endpoint
   - Update verification service to fetch questions from found item
     instead of lost item
   - Update Path A verification: compare owner answers vs found item
     encrypted answers
   - Update Path C verification: show finder's questions, compare answers
   - Path B verification service: no changes needed

3. **Frontend:**
   - Remove hidden question fields from lost item reporting form
   - Add hidden question fields to found item reporting form
     (minimum 2, maximum 3, with question + answer inputs)
   - Update verification form to show finder's questions to the owner
   - Update Path C form to include question answering step after
     preliminary description check

4. **Do not change:**
   - AI matching engine (Section 10) — unchanged
   - Path B flow — unchanged
   - Trust system — unchanged
   - Fraud detection — unchanged
   - All other features — unchanged
