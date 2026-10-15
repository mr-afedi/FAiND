# FAiND System Brain — Version 5.0
## Authoritative Master Reference for the FAiND Project

This document COMPLETELY SUPERSEDES all previous versions:
FAIND_BRAIN.md, V2, V3, V4.1, V4.2_PATCH, V4.3_PATCH, V4.4_PATCH.

This is a ground-up redesign. The peer-to-peer chat/verification model
has been replaced with an institutional drop-point model involving
campus authorities (faculties and security posts).

Claude must read this document IN FULL before implementing any feature,
generating any code, editing any file, or making any architectural
decision. Do not reference or revive logic from prior versions unless
explicitly told to.

---

# 0. What Changed From V4.x — Read This First

## Removed Entirely
- Real-time chat (WebSockets, messages inbox, seen receipts)
- Trust score system (replaced by Token system)
- Tipping system (Paystack, appreciation, tip amounts)
- Path B ("I Have This Item" flow)
- Hidden verification questions (on both lost and found items)
- AI ownership-verification scoring / auto-approve thresholds
- Fraud detection system (fraud risk scores, fraud events)
- Assistant Root Admin role (replaced by Drop Point Supervisor)
- Mandatory login for finders

## Added
- Drop Point system (7 GCTU locations: 4 faculties + 3 security gates)
- Authority accounts (one per drop point, email OTP 2FA)
- Drop Point Supervisor role (oversees multiple drop points)
- Token reward system for finders
- Anonymous finder flow with post-dropoff optional registration
- Drop-off confirmation (dual confirm + QR, same mechanic as old Feature M)
- Claimant comparison dashboard for authorities
- Structured status-update messaging (replaces open chat)
- Item condition photo + digital sign-off at handover
- Token redemption via admin-generated codes
- 30-minute post-submission edit window for finders
- 48-hour drop-off deadline with escalation

## Modified
- Found item reporting — no login required, drop point selection added
- Lost item reporting — hidden questions removed
- AI matching engine — kept for discovery only, no longer gates chat
- Path A and Path C — simplified, authority does physical verification
- Notifications — restructured around drop-off and claim events
- Admin dashboard — restructured around drop points and claims
- Item status lifecycle — new statuses added

---

# 1. Project Overview

**Project Name:** FAiND

FAiND is an AI-assisted lost-and-found platform for university campuses
that routes found items through official campus drop points (faculties
and security posts) rather than relying on peer-to-peer exchange.
A finder reports an item and drops it off at a suggested nearby
location staffed by a campus authority. The owner is matched to the
item (by AI or manual browsing), goes to the drop point, and the
authority physically verifies and hands over the item.

**Initial deployment:** Ghana Communication Technology University (GCTU)
**Future expansion:** Additional universities, each with their own
drop point network, logically isolated.

---

# 2. Project Purpose

FAiND solves the same core problem as before — disorganised, unverifiable,
unsafe lost-and-found recovery on campus — but does so by involving
the institution itself instead of relying entirely on two strangers
trusting each other.

Benefits of the drop-point model:
- Finders are not burdened with holding onto items or meeting strangers
- Owners collect from a known, trusted institutional location
- Physical verification by a human authority eliminates AI-scoring
  ambiguity and fraud risk almost entirely
- No requirement for finders to create an account removes friction
  and encourages more people to report found items
- Institutional accountability (photo + sign-off at handover) protects
  everyone if a dispute arises

---

# 3. Scope and Multi-University Architecture

## 3.1 Current Scope
GCTU only at launch.

## 3.2 Data Isolation
Every major entity carries a `university_id`: Users, Authorities,
DropPoints, Items, Claims, Notifications, TokenLedger, AdminLogs.

## 3.3 Future Expansion
Root Admin can add new universities, each bringing their own set of
drop points (faculties + security posts) and authority accounts.

---

# 4. Drop Points

## 4.1 GCTU Drop Point Seed Data

| # | Name | Type |
|---|---|---|
| 1 | Faculty of Computing and Information Systems (FoCIS) | Faculty |
| 2 | Faculty of IT Business | Faculty |
| 3 | Faculty of Engineering | Faculty |
| 4 | School of Graduate Studies and Research | Faculty |
| 5 | Gate 1 | Security |
| 6 | Gate 2 | Security |
| 7 | Gate 3 | Security |

Each drop point stores: name, type (faculty/security), latitude,
longitude, university_id, operating_hours (set by its authority),
is_temporarily_closed (boolean + reason, settable by authority).

## 4.2 Drop Point Suggestion Logic
When a finder selects the campus zone where they found an item
(using the existing campus-zone lookup, retained here), the system
suggests the nearest drop point using geopy geodesic distance between
the campus zone coordinates and each drop point's coordinates. The
finder may override the suggestion and pick a different drop point.

## 4.3 Operating Hours
Each authority sets their own drop point's operating hours from their
dashboard. If an owner is directed to collect outside operating hours,
the app shows the closed message with hours. Authorities can also
toggle "Temporarily Closed" with a reason — all owners with pending
claims at that drop point are notified immediately.

---

# 5. User Roles

## 5.1 Guest / Anonymous Finder
- Can report a found item WITHOUT logging in (Section 7)
- Can browse lost and found listings
- Cannot claim a lost item (claiming requires login — Section 8)

## 5.2 Registered User (Student/Staff)
- Can report lost items
- Can claim items via Path A or Path C (requires login)
- Can later register to claim tokens if they were an anonymous finder
- Has a dashboard showing their lost item posts, claim status, and
  (if they've ever found something) their token balance

## 5.3 Authority
- Tied to exactly ONE drop point
- Cannot log in as the authority of a different drop point
- Logs in with email + password + Email OTP (2FA)
- Sees full details of items en route to or already at their drop point
- Confirms drop-off receipt, handles claimant verification and handover
- Logs in via /authority/login

## 5.4 Drop Point Supervisor
- Oversees a defined group of drop points (e.g. all 4 faculties, or
  all 3 security posts, or any custom group assigned by Root Admin)
- Can view all items/claims across their assigned drop points
- Can resolve disputes between drop points within their group
- Can manage (create/reset/deactivate) authority accounts within
  their assigned drop points
- Cannot access Root Admin-only tools (Admin Logs, Universities,
  platform-wide settings, token value configuration)

## 5.5 Root Admin
- Exactly one. Created via seed_admin.py. TOTP 2FA (unchanged from V4.x).
- Full platform authority: creates drop points, creates/assigns
  Supervisors and Authorities, sets token values, manages universities,
  resolves any dispute, views all analytics and logs.

---

# 6. Lost Item Reporting

Required fields (login required):
- Category — Electronics, Bag, ID/Card, Keys, Clothing, Books/Notes,
  Wallet, Jewellery, Other
- Public description
- Campus location lost — dropdown, stores label + lat/lng
- Date and time lost
- Optional images — max 2, Cloudinary

## No hidden questions on lost items in V5.0.
Verification is performed physically by the authority at the drop
point, not by AI answer-matching. The claim form (Section 8.2) is
what strengthens the authority's confidence — not a hidden Q&A system.

## 6.1 Initial Status: OPEN

---

# 7. Found Item Reporting — NO LOGIN REQUIRED

This is the most significant behavioural change in V5.0.

## 7.1 Form Fields
- Category (same fixed list)
- Description of the item as found
- Campus location found — dropdown, stores label + lat/lng
- Date and time found
- At least one image — required, max 2, Cloudinary
- Suggested drop point — auto-selected as nearest to the campus
  location chosen, finder may override via dropdown of all 7 drop points

## 7.2 No Hidden Questions
Hidden questions are removed entirely from found item reporting.
The authority verifies ownership in person.

## 7.3 Submission Flow
1. Finder fills the form (no login prompt at any point)
2. On submit, the item is created with status FOUND
3. The selected drop point's authority is immediately notified with
   full item details (description, photos, category, location found,
   timestamp)
4. Finder sees an on-screen instruction: "Please drop this item off at
   [Drop Point Name] within 48 hours. Thank you for helping a fellow
   student!"
5. Finder is shown a unique tracking reference for this item so they
   can return later and mark it as dropped off without needing an
   account — store this reference in the browser (localStorage) AND
   show it on screen for them to note down

## 7.4 30-Minute Edit Window
The finder can edit their item's description and photos within
30 minutes of posting, using their browser session or tracking
reference — but ONLY if the authority has not yet confirmed receipt.
Once 30 minutes pass OR the authority confirms receipt (whichever is
first), the item is locked from further edits.

## 7.5 48-Hour Drop-Off Deadline
- At posting: item status FOUND, drop-off pending
- At 24 hours with no drop-off confirmation: push/in-app reminder to
  finder (if they registered) or a banner shown when they revisit via
  tracking reference
- At 48 hours with no drop-off confirmation: status to OVERDUE.
  Authority notified. Any owner with a pending claim notified.
- At 72 hours with no drop-off confirmation: status to UNCONFIRMED,
  hidden from public browse and from the AI matching pool
- If the finder eventually drops it off late and the authority
  confirms receipt, the item reactivates to AT_DROPPOINT but the
  finder earns a reduced token amount (Section 12.1) as a soft
  late penalty

---

# 8. Verification Paths (A and C only — Path B removed)

There is no longer a "chat unlocks" outcome. The outcome of successful
verification is: the authority is told to expect this specific
claimant and hands the item over after an in-person check.

## 8.1 Path A — AI Match Flow

1. New lost or found item posted → AI matching runs (Section 10)
2. Match score >= 0.60 → PotentialMatch created
3. Only the lost item owner is notified ("Potential match found for
   your lost item") — the anonymous finder is not notified of matches
   since they may not have an account
4. Owner clicks the matched found item, prompted to log in if needed
5. Owner fills the Claim Form (Section 8.2)
6. System checks the found item's current status:
   - If FOUND or OVERDUE: owner is told it has not been dropped off
     yet and will be notified when it arrives
   - If AT_DROPPOINT: owner is told where to collect it and the
     operating hours, and to bring their student ID
7. The drop point's authority sees this claim in their dashboard
   immediately, with the owner's claim form details as supporting
   evidence, alongside the AI match confidence score (authority only)
8. Owner physically goes to the drop point. Authority interviews them
   in person and decides whether to hand over the item.
9. Authority marks the claim as Verified — Handed Over (Section 11)
   or Rejected in their dashboard.

## 8.2 The Claim Form (used identically in Path A and Path C)
- Optional photo of the item (as the owner remembers it)
- Date item was lost
- Time item was approximately lost
- Unique description of the item — free text, encouraged to include
  specific details only the owner would know (reference material for
  the authority, not scored by AI for auto-approval)

## 8.3 Path C — "This Might Be Mine" (Browse and Claim)

1. Owner (logged in) browses found items
2. Sees an item they believe is theirs — no AI match exists
3. Clicks "This Might Be Mine"
4. Fills the same Claim Form as Section 8.2, plus where they believe
   they lost it (campus location dropdown)
5. Same downstream flow as Path A from step 6 onward

## 8.4 AI Confidence Score — Authority-Only Evidence
For Path A claims, the AI match score (description, image, location,
date, category) is shown to the authority in their claim review panel
as a confidence indicator. It is NEVER shown to the owner and NEVER
used to auto-approve or auto-reject. It exists purely to help the
authority during their in-person interview.

For Path C claims (no AI match), no AI confidence score exists.

## 8.5 Multiple Claimants — Comparison Dashboard
If more than one person submits a claim on the same found item, the
authority's dashboard shows a side-by-side comparison panel:

For each claimant: submitted description, submitted photo (if any),
date/time they say they lost it, student ID (if on file), AI
confidence score (Path A claims only), and submission timestamp.

Authority actions per claimant:
- "Call to Collect" — notifies that claimant to come in
- Leave as Pending — no notification sent
- After in-person interview: mark ONE claimant as Verified Owner
  (triggers handover, Section 11) and the rest as Rejected (each
  rejected claimant is notified that another claimant was verified)

## 8.6 Item Condition Note
The owner's claim form is reference material only — never auto-scored
to grant or deny access. All decisions are made by a human authority.

---

# 9. Drop-Off Confirmation

Mirrors the dual-confirmation/QR mechanic previously used for returns,
now used for the finder-to-authority handoff.

## 9.1 Method 1 — Dual Confirmation
1. Finder taps "I Dropped This Off"
2. Authority taps "Received"
3. Status to AT_DROPPOINT only after BOTH confirmations

## 9.2 Method 2 — QR Code
1. System generates a single-use QR code tied to the item, shown on
   the finder's tracking-reference screen
2. Finder shows this QR code to the authority when dropping it off
3. Authority scans it for instant AT_DROPPOINT confirmation

## 9.3 Post-Confirmation — Optional Finder Registration
Immediately after AT_DROPPOINT is confirmed, if the finder is not
logged in, show a prompt that they earned tokens and can create a
free account to claim them and receive appreciation.

Three choices:
- "Claim my tokens" — quick signup, tokens credited immediately
- "Skip for now" — tokens held in a 7-day escrow keyed to a
  device/browser token in localStorage; if they register within
  7 days using the same browser/device, tokens transfer automatically;
  after 7 days, escrowed tokens are discarded by a daily APScheduler job
- "I don't want tokens" — tokens discarded immediately, no escrow

---

# 10. AI Matching Engine — Retained, Role Changed

The five-factor scoring engine from V4.x is RETAINED for discovery
purposes (weights, plus the V4.x false-positive fixes: category hard
block, minimum description similarity 0.35, and the "perfect location
+ perfect date + weak description" rule).

## 10.1 What Changed
- Matching still runs automatically when a lost or found item is posted
- A PotentialMatch >= 0.60 still notifies the lost item owner
- The match score is NO LONGER used to auto-unlock anything. It is
  shown only to the authority during claim review as a confidence
  indicator.
- Matching pool excludes items in status UNCONFIRMED, CLAIMED,
  RETURNED, EXPIRED, ARCHIVED, CLOSED, and OVERDUE items older
  than 72 hours (which become UNCONFIRMED)

All scoring formulas, weights, and false-positive fixes from V4.x
remain unchanged and must be preserved exactly.

---

# 11. Handover at the Drop Point

When the authority is ready to hand the item to a verified owner:

1. Authority taps "Verify and Hand Over" on the claim
2. App prompts the authority to capture, on their device:
   - A photo of the item's condition at handover
   - The claimant's name
   - The claimant's phone number
   - The claimant's student ID (if available)
   - A photo of the claimant (optional but recommended)
3. The owner is shown a digital sign-off prompt: "I confirm I
   received this item in the condition shown." and taps "I Confirm"
4. Once both the authority's capture and the owner's confirmation are
   recorded, item status to RETURNED
5. All captured data is stored permanently and is visible to Root
   Admin and the relevant Drop Point Supervisor for dispute
   resolution — never publicly exposed
6. Finder earns the "successfully claimed" token bonus if registered

If the owner cannot confirm digitally on the spot, the authority can
record the handover unilaterally with a note that the owner was
unable to confirm digitally, flagged distinctly for Root Admin
visibility.

---

# 12. Token System

## 12.1 Token Values (set by Root Admin, default seed values)

| Event | Tokens |
|---|---|
| Post a found item | 10 |
| Drop-off confirmed (on time, within 48h) | 40 |
| Drop-off confirmed (late, after 48h) | 20 |
| Item successfully claimed by verified owner | 10 |
| Total per on-time full recovery | 60 |

## 12.2 Token Ledger
Every token event is written to a TokenLedger table: user_id, delta,
reason (enum), reference_item_id, created_at.

## 12.3 Token Display
Registered users with a token balance see it on their dashboard.
Public profiles show nothing about tokens — private to the account
holder.

## 12.4 Token Redemption (v1 — manual)
1. User taps "Redeem Tokens" on their dashboard
2. Enters how many tokens to redeem
3. System generates a unique redemption code and deducts the tokens
   immediately from their balance
4. User shows this code to staff at a participating school-operated
   service
5. That staff member (or any Root Admin / Supervisor with redemption
   access) enters the code into a Redemption Lookup panel in the
   admin area, marking it REDEEMED — manual, non-automated for v1
6. Redemption codes expire after 30 days if unused; expired codes
   refund the tokens back to the user automatically via a daily
   APScheduler job

## 12.5 Future (v2)
Direct integration with school ID card / payment systems for
automatic redemption at point of sale. Not built in v1.

---

# 13. Structured Status Messaging (Replaces Open Chat)

No open chat exists in V5.0.

## 13.1 Item Status Visibility
Every claimed item shows a clear status to the owner at all times:
Posted to Dropped Off to Claimed/Verified to Returned (or Overdue /
Unconfirmed if the finder never drops it off). Owner can tap "Check
Status" on any item they have an active claim on.

## 13.2 Predefined Inquiry Messages
The owner may send exactly ONE of these predefined inquiries per
claim, selected from a dropdown — no free text:
- "Is this item still available for collection?"
- "I am on my way to collect"
- "I cannot collect today, can I come tomorrow?"

## 13.3 Authority Quick Replies
These appear in the authority's dashboard as structured items with
one-tap responses:
- "Yes, it is here"
- "Please come between [operating hours]"
- "This item has already been collected by someone else"
- "No response needed" to dismiss

This is intentionally NOT a freeform chat.

---

# 14. Notifications

## 14.1 Triggers

| Event | Who is notified |
|---|---|
| AI match found (Path A) | Lost item owner only |
| Item dropped off (finder confirms) | Selected drop point's authority |
| Drop-off confirmed by authority | Finder (if registered) |
| Item reaches 24h with no drop-off | Finder (if registered/has tracking) |
| Item reaches 48h, status to OVERDUE | Authority + any owner with pending claim |
| Item reaches 72h, status to UNCONFIRMED | Authority |
| Claim submitted (Path A or C) | The relevant drop point's authority |
| Item not yet at drop point (owner claims early) | Owner (told to wait) |
| Item arrives at drop point (owner had pending claim) | Owner (told to come collect) |
| Owner verified and item handed over | Owner + finder (if registered) |
| Claim rejected (another claimant verified) | Rejected claimant |
| Drop point temporarily closed | All owners with pending claims at that point |
| Predefined inquiry sent | Authority |
| Authority quick reply sent | Owner |
| Token escrow about to expire (day 6 of 7) | Anonymous finder, if recoverable |
| Redemption code expiring soon | User who generated it |
| Admin/Supervisor actions affecting a user | That user |

## 14.2 No Civic Lost-Item Alerts in V5.0
The old "opt-in lost item alert" feature is removed. Discovery now
happens through AI matching and normal browsing.

## 14.3 Web Push — Retained
Web Push Notifications (pywebpush) are retained exactly as in V4.x,
including the contextual permission-prompt strategy. Anonymous
finders without an account cannot receive push; they rely on the
in-app tracking-reference screen.

---

# 15. Admin Structure — Three Tiers

## 15.1 Root Admin
- Single account, TOTP 2FA, secret route (unchanged mechanics)
- Creates/edits drop points, sets token values, creates/removes
  Supervisors and Authorities directly or delegates to Supervisors
- Manages universities (future)
- Final authority on all disputes
- Views full platform analytics and full Admin Logs

## 15.2 Drop Point Supervisor (replaces Assistant Root Admin)
- Assigned a group of drop points by Root Admin
- Can view all items/claims across their assigned drop points
- Can resolve disputes within their assigned drop points
- Can manage Authority accounts within their assigned drop points
- Cannot set token values, manage universities, or view Admin Logs

## 15.3 Authority
- Tied to exactly one drop point, cannot cross over
- Email + password + Email OTP login
- Full dashboard scoped to their single drop point only

## 15.4 Admin Logging
All significant actions by Root Admin, Supervisors, and Authorities
are written to admin_logs. Root Admin sees everything. Supervisors
see logs only for their assigned drop points and their own actions.
Authorities do not have log access.

---

# 16. Authority Authentication

## 16.1 Account Creation
Authority accounts are created by Root Admin or by a Supervisor (for
drop points within that Supervisor's assigned group) — never via
public signup. Each account is permanently tied to one drop_point_id.

## 16.2 Login Flow
1. Authority goes to /authority/login
2. Enters email + password
3. System sends a 6-digit OTP to their registered institutional email
   (@gctu.edu.gh domain enforced for GCTU)
4. Authority enters the OTP (expires in 10 minutes)
5. On success, JWT issued with role: authority and drop_point_id
   embedded — every authority endpoint checks this drop_point_id
   matches the resource being accessed

## 16.3 Why Email OTP Instead of TOTP
Campus staff are not expected to be technical. Email OTP requires no
app installation and uses infrastructure they already have, while
still providing genuine two-factor security. TOTP remains reserved
for Root Admin only.

---

# 17. Authority Dashboard

## 17.1 Sections
- Incoming — items selected for this drop point, not yet confirmed
  received (full item details, finder's 48h deadline countdown)
- At Drop Point — items confirmed received, awaiting claim/collection
- Claims — all claims submitted against items at this drop point,
  with the comparison panel when multiple claimants exist
- Handover — in-progress handovers and completed handover history
- Settings — operating hours, temporarily-closed toggle + reason

## 17.2 Actions Available
- Confirm drop-off received (dual confirm or scan QR)
- View AI confidence score per claim (Path A only)
- Call a claimant to collect / leave pending / verify as owner / reject
- Complete handover (capture condition photo, claimant details, await
  or override owner digital sign-off)
- Send quick replies to predefined inquiries
- Toggle operating hours / temporary closure

---

# 18. Item Status Reference — V5.0

| Status | Meaning |
|---|---|
| OPEN | Lost item posted, active, in matching pool |
| FOUND | Found item posted, drop-off pending |
| OVERDUE | 48h passed, finder has not dropped off yet |
| UNCONFIRMED | 72h passed, hidden from browse/matching |
| AT_DROPPOINT | Authority confirmed receipt, awaiting claim |
| POTENTIAL_MATCH | AI matched a lost item to a found item (informational) |
| UNDER_CLAIM_REVIEW | One or more claims submitted, authority reviewing |
| RETURNED | Handover complete, item resolved |
| EXPIRED | Lost item passed its active period unclaimed |
| ARCHIVED | Soft-deleted or resolved past visible window |
| CLOSED | Force-closed by admin/supervisor |

Status transitions are enforced backend-only. No client can set status
directly.

---

# 19. Lost Item Lifecycle

- Active: 45 days from posting, reminder 3 days before expiry,
  max 2 extensions of +30 days each
- If expired with no successful claim: status to EXPIRED

Found items follow the drop-off-driven lifecycle in Section 7.5
instead of a fixed expiry — once AT_DROPPOINT, the item waits for a
verified claimant indefinitely, flagged for review after 60 days at
a drop point with no claimant.

---

# 20. Security Requirements

- JWT auth, 15-min access token, 7-day refresh token, httpOnly cookie,
  Axios silent-refresh interceptor — unchanged
- IDOR prevention on every resource, now also enforced for
  drop_point_id scoping on all Authority endpoints
- AES-256-GCM encryption now applies to claimant personal data
  captured at handover (phone number, student ID)
- Rate limiting (slowapi): found-item submission rate limited per
  IP/device since no login is required (e.g. 5 per IP per day)
- File upload safety unchanged (JPEG/PNG/WEBP, 5MB max, Cloudinary,
  server-side MIME validation)
- Root Admin: TOTP + secret route (unchanged)
- Authority: Email OTP + drop_point_id scoping (new)

---

# 21. Technology Stack — Changes From V4.x

## Removed
- Paystack (no tipping)
- FastAPI WebSockets (no chat)
- Any trust-score or fraud-score specific logic

## Retained Unchanged
- React + Vite + Tailwind + React Router + TanStack Query + Axios + vite-plugin-pwa
- FastAPI + Uvicorn + PostgreSQL + SQLAlchemy + Alembic + Pydantic
- APScheduler (now also handles 24h/48h/72h drop-off jobs, token
  escrow expiry, redemption code expiry)
- python-jose, passlib (bcrypt), pyotp (Root Admin only), pywebpush,
  httpx, qrcode, cryptography, geopy, slowapi
- sentence-transformers, numpy, scikit-learn, imagehash, Pillow
- Cloudinary, Vercel, Render, Supabase

## Added
- Email-sending capability for Authority OTP (fastapi-mail or
  smtplib, same EMAIL_CONSOLE_MODE pattern for local dev)

---

# 22. Code Architecture

Backend additions: drop_points.py, authority.py, claims.py, tokens.py
(api); DropPoint, Authority, Claim, TokenLedger, RedemptionCode,
Handover (models); drop_point_service.py, claim_service.py,
token_service.py, handover_service.py (services).

Backend removals: trust_service.py, fraud_service.py, chat/websocket
services, tip_service.py.

New seed file: seed_drop_points.py — seeds the 7 GCTU drop points.

Frontend additions: AuthorityLogin, AuthorityDashboard, ClaimForm,
TokenDashboard, RedeemTokens (pages); dropPointService.js,
claimService.js, tokenService.js, authorityService.js (services).

Frontend removals: MessagesPage, ConversationPage, TipModal pages;
chatService.js (websocket), tipService.js.

---

# 23. Feature Build Order — V5.0

Features already built are RETAINED where their underlying logic
still applies (auth, item browsing, AI matching engine, PWA, admin
dashboard skeleton). This list is the migration + new-feature roadmap.

| # | Feature | Key Deliverable |
|---|---|---|
| W1 | Removal Pass | Cleanly remove chat, trust, tipping, fraud, Path B, hidden questions, Assistant Admin role — delete dead code, routes, DB columns via migration |
| W2 | Drop Points | DropPoint model, seed_drop_points.py, nearest-drop-point suggestion logic |
| W3 | Found Item Reporting Rework | Remove login requirement, add drop point selection, tracking reference, 30-min edit window |
| W4 | Drop-Off Confirmation | Dual confirm + QR, 24h/48h/72h APScheduler jobs |
| W5 | Anonymous Finder + Token Escrow | Post-dropoff registration prompt, 7-day escrow, token crediting |
| W6 | Authority Auth | Authority model, Email OTP login, drop_point_id JWT scoping |
| W7 | Authority Dashboard | Incoming / At Drop Point / Claims / Handover / Settings |
| W8 | Claim Form + Path A/C Rework | Claim form, status-aware claim flow, removal of AI auto-approve logic from owner-facing flow |
| W9 | Claimant Comparison Dashboard | Multi-claimant side-by-side panel, Call to Collect / Verify / Reject |
| W10 | Handover Flow | Condition photo, claimant details capture, owner digital sign-off |
| W11 | Token System | TokenLedger, token values config (Root Admin), dashboard display |
| W12 | Redemption | Redemption code generation, manual redemption lookup panel, 30-day expiry job |
| W13 | Structured Messaging | Predefined inquiry dropdown, authority quick replies |
| W14 | Drop Point Supervisor Role | Supervisor model, assigned-drop-point scoping, permissions |
| W15 | Admin Dashboard Rework | Restructure around drop points, claims, supervisors, remove trust/fraud/tip tabs |
| W16 | Notifications Rework | New trigger table, remove civic-alert and chat-message triggers |
| W17 | Regression + Polish | Re-test AI matching, PWA, browse pages, lost item posting against the new flow end to end |

---

# 24. Prompting Rule

Every implementation prompt must begin with:

"Read and follow FAIND_BRAIN_V5.0.md as the single source of truth.
This supersedes all prior BRAIN versions and patches. Implement only
the requested feature. Follow all drop-point, authority, token, and
claim rules defined in this document."

---

# 25. Final Summary

FAiND V5.0 is an institutionally-mediated lost-and-found platform.
Finders report items with no login required and route them through
one of seven GCTU drop points (4 faculties + 3 security gates).
Authorities — staff accounts tied to a single drop point, protected
by Email OTP 2FA — physically verify owners and hand items over,
capturing condition photos and claimant details for accountability.
AI matching is retained purely as a discovery and confidence-scoring
tool; it no longer auto-approves anything. Finders are rewarded with
a token system redeemable for campus discounts instead of peer tips.
Drop Point Supervisors replace Assistant Root Admins, overseeing
groups of drop points on Root Admin's behalf. Chat, trust scores, and
fraud scoring are removed; structured status messaging and physical
verification replace them as the trust mechanism.
