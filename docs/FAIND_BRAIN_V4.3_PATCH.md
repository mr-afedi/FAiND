# FAiND System Brain — Version 4.3 PATCH
## Applies on top of V4.1 and V4.2

This patch supersedes any conflicting logic in V4.1 and V4.2.
Read this patch in full before implementing any feature or fix
related to lost item reporting, found item reporting, or any
of the three verification paths.

---

## ⚠️ CHANGELOG — V4.3

### Summary of Changes

1. Private description removed from lost item form entirely
2. Hidden questions and answers moved to lost item form
3. Path B completely redesigned — finder answers owner's hidden questions
4. Path C now identical to Path A — owner answers finder's hidden questions
5. Path B scoring formula updated
6. Attempt limit changed to 3 with escalating penalties
7. Admin review attempt counter pause rule added
8. UI guidance added for hidden question quality
9. Notification content rules tightened for Path B

---

# 6. Lost Item Reporting — UPDATED V4.3

When a registered user reports a lost item, they must provide:
- **Category** (fixed list: Electronics, Bag, ID/Card, Keys, Clothing,
  Books/Notes, Wallet, Jewellery, Other)
- **Public description** — visible to all users
- **Campus location** — dropdown storing location_label + lat/lng
- **Date and time lost**
- **Optional images** — maximum 2, Cloudinary
- **2–3 hidden verification questions with answers** — AES-256-GCM
  encrypted; never returned in any API response; immutable after
  submission

## ⚠️ REMOVED IN V4.3
Private description is permanently removed from the lost item form.
It served no scoring purpose after the Path B redesign.
Do not implement a private description field on lost item posting.
Remove it from the database model, migration, and all API responses.

## 6.1 Hidden Questions on Lost Items
The owner sets questions that only someone who physically has the item
can answer. These are used in Path B verification — the finder answers
them to prove they have the item.

**UI guidance shown to the owner during form filling:**
"Ask questions about details not visible in your description or photos.
Example: What is written inside? What is in the front pocket?
What color is the lining? Avoid asking obvious things like color or brand."

**Good questions:**
- What is written inside the cover?
- What was in the front pocket?
- What color is the inside lining?
- Describe any damage or scratch on it
- What sticker or personalisation is on it?

**Bad questions (backend should warn but not block):**
If the owner's answer is too similar to their public description,
show a warning: "This answer might be too obvious. Consider asking
something more specific." Do not block submission — just warn.

## 6.2 Hidden Answer Rules
- Stored AES-256-GCM encrypted at rest
- Never returned in any API response to any user including the owner
- Immutable after submission
- Decrypted in memory only during Path B verification scoring

## 6.3 Initial Status: OPEN

---

# 7. Found Item Reporting — UPDATED V4.3

When a registered user reports a found item, they must provide:
- **Category** (same fixed list)
- **Short description** of the item as found
- **Campus location** — same dropdown, stores label + lat/lng
- **Date and time found**
- **At least one image** — required, maximum 2, Cloudinary
- **2–3 hidden verification questions with answers** — AES-256-GCM
  encrypted; never returned in any API response; immutable after
  submission

## 7.1 Why the Finder Sets Questions on Found Items
The finder physically has the item. They can ask specific questions
about physical details that only the real owner would know from memory
— details the finder can verify by looking at the item in hand.

**UI guidance shown to the finder during form filling:**
"Ask questions that only the real owner would know from memory.
Example: What color is the inside lining? What is written inside?
What was in the front pocket? Avoid asking things visible in your photo."

## 7.2 Hidden Answer Rules
Same rules as lost item hidden answers — encrypted, immutable,
never returned in API responses.

## 7.3 Initial Status: FOUND
## 7.4 Trust Reward: +2 points on successful submission

---

# 8. The Three Paths to Chat — UPDATED V4.3

---

## Path A — AI Match Flow — UNCHANGED FROM V4.2

1. New item posted → AI matching runs
2. Match score ≥ 0.60 → PotentialMatch created
3. Both users notified
4. Lost item status → POTENTIAL_MATCH
5. Lost item owner clicks "Verify Ownership"
6. Owner is shown the FINDER'S hidden questions from the found item
7. Owner answers the finder's questions
8. AI scores owner's answers against finder's encrypted answers
9. Score > 0.75 → chat unlocks
10. Score 0.50–0.75 → admin review
11. Score < 0.50 → rejected

---

## Path B — "I Have This Item" Flow — COMPLETELY REDESIGNED IN V4.3

**Condition:** A finder physically has a lost item, sees the lost post,
and wants to contact the owner.

**⚠️ COMPLETE REDESIGN FROM V4.2:**
Path B no longer uses private description matching.
The finder now answers the OWNER'S hidden questions to prove
they physically have the item.

**Steps:**
1. Logged-in user (not the item owner) views a lost item post
2. Clicks "I Have This Item"
3. Fills out a form:
   - The owner's hidden questions are displayed (questions only,
     not answers — finder must answer from physical inspection)
   - Finder answers each question by looking at the item they have
   - Where they found it (campus location dropdown)
   - Photo of the item (optional but recommended)
4. Creates an IHaveThisItemClaim record
5. AI scores the finder's answers against the owner's encrypted answers
   using the Path B scoring formula (see Section 12)
6. Score > 0.75 → chat unlocks
7. Score 0.50–0.75 → admin review
8. Score < 0.50 → rejected
9. After successful return: prompt finder to post as resolved found
   item for trust recognition (optional, incentivized)

**Why this is more secure:**
- The owner set questions about specific private details of their item
- The finder must physically inspect the item to answer correctly
- A fraudster who has never seen the item cannot answer specific
  questions like "What color is the inside lining?" correctly

**Abuse prevention:**
- 3 attempts per user per item (see Section 12.6)
- Escalating penalties on failed attempts
- All claims visible to admins
- Admin sees all attempts side by side to detect gradual improvement fraud

**Notification to owner when Path B claim is submitted:**
Show ONLY: "Someone claims to have found your item. We are verifying
their claim." Do NOT reveal the finder's identity, submitted answers,
or photo before verification passes.

---

## Path C — "This Might Be Mine" Flow — UPDATED V4.3

**Condition:** An owner sees a found item post but has not posted a
lost item yet.

**⚠️ CHANGE FROM V4.2:** Path C now uses identical verification logic
to Path A. The owner answers the FINDER'S hidden questions.
The preliminary description-only check from V4.2 is removed.

**Steps:**
1. Logged-in user (not the found item poster) views a found item post
2. Clicks "This Might Be Mine"
3. The finder's hidden questions are displayed immediately
   (questions only — not answers)
4. Owner answers the finder's questions from memory
5. Owner also provides:
   - Where they lost it (campus location dropdown)
   - When they lost it (date picker)
6. AI scores owner's answers against finder's encrypted answers
   using the Path A/C scoring formula (see Section 12)
7. Score > 0.75 → chat unlocks
8. Score 0.50–0.75 → admin review
9. Score < 0.50 → rejected
10. After successful return: prompt owner to post resolved lost item
    for record completion (optional, incentivized)

**Why Path C = Path A:**
Both involve the owner proving ownership by answering the finder's
hidden questions. The only difference is how they arrived at the
verification step — AI matched them (Path A) vs owner found the
post manually (Path C). The verification mechanism is identical.

---

# 12. Ownership Verification Logic — UPDATED V4.3

## 12.1 Entry Points
- Path A: "Verify Ownership" on matched found item
- Path B: "I Have This Item" form on lost item
- Path C: "This Might Be Mine" form on found item

## 12.2 Who Sets Questions, Who Answers

| Path | Questions set by | Questions answered by |
|---|---|---|
| Path A | Finder (on found item) | Owner |
| Path B | Owner (on lost item) | Finder |
| Path C | Finder (on found item) | Owner |

## 12.3 Path A and Path C Scoring Formula — UNCHANGED FROM V4.2

| Factor | Weight | Notes |
|---|---|---|
| Hidden answer similarity | 0.70 | Owner answers finder's questions |
| Description similarity | 0.30 | Owner's description vs found item public description |

Auto-approve threshold: score > 0.70 (lowered from 0.75 in V4.2 fix)
Admin review: score 0.50–0.70
Rejected: score < 0.50

## 12.4 Path B Scoring Formula — NEW IN V4.3

| Factor | Weight | Notes |
|---|---|---|
| Hidden answer similarity | 0.70 | Finder answers owner's questions — primary signal |
| Image similarity | 0.15 | Finder's photo vs owner's photo (if both exist) |
| Location proximity | 0.15 | Where finder found it vs where owner lost it |

**Special weight redistribution rules:**
- If owner has no photo → image weight (0.15) adds to hidden answers
  making it 0.85 hidden answers + 0.15 location
- If finder provides no photo → image score = 0.0, weight redistributes
  proportionally to hidden answers and location

**Auto-approve override rules:**
- If hidden answer score alone > 0.80 → auto-approve regardless of
  image and location scores
- If hidden answer score < 0.40 → auto-reject regardless of other scores

**Thresholds:**
- Score > 0.75 → auto-approved, chat unlocks
- Score 0.50–0.75 → admin review
- Score < 0.50 → rejected

## 12.5 Semantic Comparison Method — UNCHANGED
sentence-transformers (all-MiniLM-L6-v2). Cosine similarity.
Handles synonyms and paraphrasing.

## 12.6 Attempt Limits and Penalties — UPDATED V4.3

**Maximum 3 attempts per user per item.**

| Attempt | Penalty on failure |
|---|---|
| 1st failed attempt | No penalty — notification only |
| 2nd failed attempt | Trust score -3 |
| 3rd failed attempt | Trust score -5, fraud risk +20, admin alerted |
| 4th attempt | Blocked — system message: "You have reached the maximum number of attempts for this item" |

**Admin review pause rule:**
If the finder is on their last attempt (3rd) and it lands in admin
review, the attempt counter pauses until admin makes a decision.
The finder is not locked out while waiting for admin review of a
potentially legitimate claim.

## 12.7 Multiple Claimants — UNCHANGED
Each claim scored independently. If two exceed threshold → dispute opened.

## 12.8 False Claim Penalty — UNCHANGED
Score < 0.30 or admin-confirmed: -10 trust points

## 12.9 Gradual Improvement Fraud Detection
If a user submits multiple attempts and each attempt scores
progressively higher than the last, flag this as a potential
fraud signal. Add +10 to their fraud risk score and show all
attempts side by side in the admin review panel.
This pattern suggests the user is learning from failures rather
than genuinely knowing the answers.

---

# Implementation Notes for Agent

When implementing V4.3 changes:

**Database:**
- Remove private_description column from items table (lost items)
- Add hidden_questions and hidden_answers to lost items table
  (they already exist on found items from V4.2)
- Create and run Alembic migration for these changes
- Add attempt_scores array to IHaveThisItemClaim for fraud detection

**Backend:**
- Remove private description from lost item creation endpoint
- Add hidden question storage to lost item creation endpoint
- Update Path B verification service completely:
  - Fetch owner's hidden questions from lost item
  - Display questions to finder (questions only, never answers)
  - Score finder's answers against owner's encrypted answers
  - Apply new scoring formula with weight redistribution rules
  - Apply auto-approve override rules
  - Apply escalating penalties
  - Implement attempt counter pause on admin review
  - Store all attempt scores for fraud detection
- Update Path C verification service:
  - Remove preliminary description check
  - Show finder's hidden questions directly
  - Score using Path A/C formula
- Path A verification service: no changes needed

**Frontend:**
- Remove private description field from lost item reporting form
- Add hidden question fields to lost item reporting form
  (2-3 questions with answers, same UI as found item form)
- Add UI guidance text explaining what makes a good question
- Update Path B form:
  - Show owner's hidden questions to finder
  - Finder answers each question
  - Location dropdown
  - Optional photo upload
- Update Path C form:
  - Show finder's hidden questions directly (remove description step)
  - Owner answers each question
  - Location and date fields
- Add warning when owner's answer is too similar to public description

**Do not change:**
- Path A verification flow
- AI matching engine
- Trust system
- Fraud detection base logic
- All other features
