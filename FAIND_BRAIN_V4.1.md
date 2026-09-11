**FAiND System Brain — Version 4.1**  
**Authoritative Master Reference for the FAiND Project**  
This document is the single source of truth for the FAiND project.  
   
 It supersedes ALL previous versions: FAIND_BRAIN.md, FAIND_BRAIN_V2.md,  
   
 FAIND_BRAIN_V3.md, and FAIND_BRAIN_V4.md.  
Claude must read this document IN FULL before implementing any feature,  
   
 generating any code, editing any file, or making any architectural decision.  
Claude must not deviate from the architecture, logic, UI philosophy,  
   
 workflows, platform scope, visibility rules, or technology stack defined  
   
 here unless explicitly instructed by the project owner.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSNBCUpfDq4wwIAABiywEZJWQZeZ2ao9AAD+4liruzq/ngAA8Nr1ABweBgdur/QFAAAAAElFTkSuQmCC)  
**What Changed in V4.1 (from V4)**  
Three targeted fixes. No structural changes.  
1. **Typo fix — Section 3.3:** ThisMightBeMineClams corrected to  
   
 ThisMightBeMineClaims. Prevents a wrongly named database table  
   
 during implementation.  
2. **Feature build order fix — Section 33:** Trust System moved from  
   
 Feature N to Feature E (immediately after Found Item Reporting).  
   
 Features D, M, and any other feature that awards or deducts trust  
   
 points must have TrustService available at build time. The old order  
   
 would have caused broken trust logic or required rewrites.  
3. **Rate limiting library added — Section 31.2:** slowapi added to  
   
 the backend stack. Section 30.5 defines rate limits but V4 had no  
   
 library specified to enforce them. Without this, Claude implementing  
   
 the rate limiting section would either skip it or pick an arbitrary  
   
 library inconsistent with FastAPI.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSNBACPykMH4NpGACyywEZJWQZeZ2aszAAD+4l6rrTo+jgAA8N71AL/CBEiG5xPoAAAAAElFTkSuQmCC)  
**What Changed in V4 (from V3)**  
The following critical issues were identified in V3 and are fully fixed here:  
1. Path C circular verification removed — hidden questions cannot self-verify  
2. POTENTIAL_MATCH timeout added — 14-day expiry back to OPEN  
3. Owner self-claim blocked — backend + frontend enforcement  
4. Suspended user behavior fully defined — items, chats, notifications  
5. Report/Flag workflow fully specified — report types, admin queue, auto-escalation  
6. JWT refresh interceptor explicitly specified for frontend Axios  
7. Tip-before-dispute scenario handled — freeze, admin notified, resolution rules  
8. UNDER_DISPUTE now pauses all other pending matches on same item  
9. Push notification permission timing fixed — contextual, not on login  
10. User reporting added — from public profiles and inside chat  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OQQmAABRAsSfYxKK/kJXEkyE8WcGbCFuCLTOzVXsAAPzFsVZ3dX4cAQDgvesB/vEF9H9odtUAAAAASUVORK5CYII=)  
**Implementation Rules**  
- Do not introduce technologies outside the defined stack  
- Do not rewrite already-working systems unless necessary  
- Do not implement unrelated features when asked for a specific one  
- Build in modular, testable steps  
- All UI must work smoothly on iOS Safari, Android Chrome, and desktop browsers  
- Follow secure-by-default practices throughout every feature  
- Every button, form, and clickable element must follow the interaction  
   
 map in Section 27  
- Business logic lives in services, not route handlers  
- All DB access via SQLAlchemy ORM — no raw SQL, no exceptions  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OQQmAUBBAwSfIb+HdmNvAkgaxgjcRZhLMNjNHdQUAwF/ce7Wq8+sJAACvrQctewNKtdojwQAAAABJRU5ErkJggg==)  
**1. Project Overview**  
**Project Name:** FAiND  
FAiND is an **AI-powered lost and found web application** built for  
   
 university campuses. It helps students and staff report, match, verify,  
   
 and safely return lost items.  
**Initial deployment:** Ghana Communication Technology University (GCTU)  
**Future expansion:** Other universities can be added by the Root Admin.  
   
 Each university is logically isolated from others.  
FAiND is not a listing website. It is a **trust-based digital recovery**  
 **  
 platform** that combines:  
- Structured lost and found reporting with encrypted private details  
- AI-powered semantic matching (description + image + location + date + category)  
- Three verified paths to chat (Path A: AI Match, Path B: I Have This Item,  
   
 Path C: This Might Be Mine)  
- Ownership verification using hidden questions and semantic AI scoring  
- Fraud detection, risk scoring, and admin alerting  
- Trust and reputation system with tier-based public display  
- Secure real-time chat with seen receipts and a full messages inbox  
- Returned item lifecycle: tipping window, dispute window, resolution record  
- Optional Paystack tipping after successful return  
- Three-tier admin governance with 2FA-protected Root Admin access  
- Post lifecycle management with APScheduler background jobs  
- Opt-in civic notifications and Web Push Notifications (phone/desktop tray)  
- Progressive Web App: installable on Android, iOS, and desktop  
- User and post reporting system with admin review queue  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAM0lEQVR4nO3OUQmAABBAsaeI2MKqV8RyJrGCfyJsCbbMzFldAQDwF/dWrdXx9QQAgNf2B/NkAzRb7P0YAAAAAElFTkSuQmCC)  
**2. Project Purpose**  
FAiND replaces broken traditional lost and found systems which are:  
- Manual and disorganized  
- Impossible to search effectively  
- Impossible to verify ownership  
- Easy to abuse or manipulate  
- Dependent on noisy WhatsApp groups and physical notice boards  
FAiND gives every campus a secure, intelligent recovery platform where:  
- Lost item owners can post with private verification details  
- Finders can post found items with required photos  
- AI automatically matches lost and found items semantically  
- Finders with items can contact owners without posting first (Path B)  
- Owners can contact finders without having posted yet (Path C)  
- Ownership is verified before any chat is possible  
- Returns are confirmed by both parties or via QR scan  
- Trust is earned through honest behavior, not gaming  
- Admins govern the platform with clear authority and logged actions  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsSfYxZo/jkUsYQLPJrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA4rDBc72meO5AAAAAElFTkSuQmCC)  
**3. Scope and Multi-University Architecture**  
**3.1 Current Scope**  
Scoped to **GCTU** at launch. All users, items, and activity belong to GCTU.  
**3.2 Future Expansion**  
- Root Admin adds universities via the admin dashboard  
- Each university gets its own namespace  
- Users, items, claims, trust scores, and disputes are scoped per university  
- University Admins manage their own campus only  
**3.3 Data Isolation Rule**  
Every major database entity must carry a university_id:  
   
 Users, Items, Claims, PotentialMatches, IHaveThisItemClaims,  
   
 ThisMightBeMineClaims, Disputes, Notifications, Conversations,  
   
 Messages, TrustEvents, FraudEvents, Reports, AdminLogs, CampusZones.  
Cross-university queries are never permitted except for Root Admin  
   
 platform-wide analytics endpoints.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OQQmAABRAsaeILbwZ9Fewo0Gs4E2ELcGWmTmqKwAA/uLeqr06v54AAPDa+gAthwNEfGhnhAAAAABJRU5ErkJggg==)  
**4. User Roles and Permissions**  
**4.1 Guest Users**  
Unauthenticated visitors.  
**Can:**  
- Browse homepage, /lost, /found pages  
- View item detail pages (public fields only)  
- View "Why Choose FAiND" and safety warnings  
**Cannot:**  
- Post items, use any claim flow, access chat or messages  
- Access dashboard, profile, settings, or any admin feature  
Attempting a restricted action → login/signup prompt.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsSeYxZw/lieLGMACBrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA6fGBdgoVMwYAAAAAElFTkSuQmCC)  
**4.2 Registered Users**  
Users with verified university email accounts.  
**Can:**  
- Post lost items (with encrypted hidden questions)  
- Post found items (with required photo)  
- Use Path B and Path C claim flows (on items they did NOT post)  
- Attempt ownership verification (max 3 per item per 24h)  
- Access Messages inbox and active conversations  
- Chat after verification passes  
- See message seen/delivered receipts  
- Confirm returns (dual confirm or QR)  
- Dispute a return within the 7-day dispute window  
- Send optional tips within the 7-day tipping window  
- View own dashboard: items, returns, trust score, tip count  
- Receive in-app notifications and Web Push (if permission granted)  
- Toggle civic lost-item alerts and push notifications in settings  
- Extend own posts (max 2 extensions per post)  
- Soft-delete own posts  
- Report posts and report users  
**Cannot:**  
- Use Path B or Path C on their own items (enforced backend + frontend)  
- Set item status directly  
- Access admin features  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNhwgJe0PYTKpnRgQU2QtIq6DIze3UGAMBf3Gu1VcfXEwAAXrseaIEEMYtKmi4AAAAASUVORK5CYII=)  
**4.3 Admin Hierarchy**  
**Tier 1 — Root Admin**  
- Exactly **one** Root Admin exists on the platform at all times  
- Created via seed_admin.py before deployment — never through signup  
- Accesses admin via a secret route (returns 404 to all others)  
- Protected by password + TOTP 2FA  
**Root Admin exclusive powers:**  
- Promote/demote Assistant Root Admins (max 2 enforced)  
- Assign/remove University Admins (future)  
- Add universities (future)  
- View all admin activity logs  
- View full platform analytics  
- Access Root Admin-only audit tools  
- Final authority on all disputes  
**Shared admin powers (Root + Assistants):**  
- Suspend/unsuspend users  
- Review and resolve claims in the 0.50–0.75 range  
- Review and act on fraud alerts  
- Remove item posts  
- Force-close items  
- Resolve disputes  
- Review user and post reports  
- View platform analytics  
**Tier 2 — Assistant Root Admins**  
- Maximum **2** — hard backend constraint enforced on every promotion attempt  
- Assigned by Root Admin only  
**Cannot:**  
- Promote or demote any admin  
- Access Root Admin-only audit tools  
- Override Root Admin decisions  
**Tier 3 — University Admins (Future)**  
- Scoped to assigned university only  
- Same shared admin powers but within their university only  
- Cannot promote any admin or access cross-university data  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OQQmAABRAsSd4NIGJjPWxpgGsYQVvImwJtszMXp0BAPAX91pt1fH1BACA164HhZwEOFrXVOsAAAAASUVORK5CYII=)  
**4.4 Administrative Activity Logging**  
All significant admin actions written to admin_logs table.  
Logged: promoting/demoting, suspending/unsuspending, removing posts,  
   
 approving/rejecting claims, force-closing, opening/closing disputes,  
   
 resolving disputes, acting on reports, adding universities.  
Root Admin sees full log. Assistants see own actions only.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsSeYxZw/lieLGMACBrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA6fGBdgoVMwYAAAAAElFTkSuQmCC)  
**4.5 Admin Bootstrapping**  
python seed_admin.py  
   
Reads from environment variables:  
- ROOT_ADMIN_EMAIL  
- ROOT_ADMIN_PASSWORD  
- ROOT_ADMIN_TOTP_SECRET (pre-generated; used to configure authenticator app)  
Script is idempotent — never creates a second root admin.  
   
 Delete or disable the script after first successful run.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAM0lEQVR4nO3OMQ0AIAwAwZIgBKm1gjSMNCwYYCIkd9OP3zJzRMQMAAB+sfqJeroBAMCN2pTWBSSZVtjzAAAAAElFTkSuQmCC)  
**4.6 Root Admin 2FA**  
**Step 1:** Email + password on standard login page.  
   
 **Step 2:** If credentials match a Root Admin account, a second screen  
   
 requests the 6-digit TOTP code from Google Authenticator or Authy.  
   
 Backend validates via pyotp. Access denied without the correct code.  
**Secret admin route:** Not linked anywhere in the UI.  
   
 Returns **404** (not 403) for any request without a valid Root Admin JWT.  
   
 404 prevents route discovery by unauthorized users.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OQQmAABRAsSd4NIGBzPXBmAawhhW8ibAl2DIze3UGAMBf3Gu1VcfXEwAAXrsehaQEN+8fLHEAAAAASUVORK5CYII=)  
**4.7 Suspended User Behavior**  
When a user is suspended by an admin:  
**Immediate effects:**  
- Their active item posts are hidden from the public feed and matching pool  
   
 (not deleted — status gains a hidden_by_suspension flag)  
- Their open chat conversations are frozen — messages can be read but  
   
 no new messages can be sent by the suspended user  
- Their pending verification attempts are paused  
- Their push subscriptions are deactivated temporarily  
**Notifications:**  
- Suspended user receives: *"Your account has been suspended pending*  
 *  
 review. Contact support if you believe this is an error."*  
- Other parties in active conversations receive: *"This conversation*  
 *  
 has been paused pending a platform review."*  
**On unsuspension:**  
- Items are restored to their previous status in the feed and matching pool  
- Chat conversations are unfrozen  
- Push subscriptions reactivated  
- User receives: *"Your account suspension has been lifted."*  
**Trust score during suspension:** frozen — no changes applied until  
   
 suspension is resolved.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AUBBAsUfyNTCi9VwgEA3sWGAjJK2CbjNzVGcAAPzFtapV7V9PAAB47X4AEW4ELQDBN+AAAAAASUVORK5CYII=)  
**5. Authentication and Signup**  
**5.1 Signup Fields**  
- **Full name** (required)  
- **Username** (required, unique, used for public display)  
- **University email** (required — backend validates domain: @live.gctu.edu.gh)  
- **Student ID** (optional — stored, not validated in v1; future validation planned)  
- **Password** (required, min 8 characters)  
- **Confirm password** (required, must match)  
- **"I agree to FAiND's community guidelines"** checkbox (required)  
On submit: account created as UNVERIFIED, 6-digit code emailed,  
   
 user redirected to verification screen.  
**5.2 Email Verification**  
- 6-digit code input + Verify button  
- Resend Code button (active after 60-second cooldown)  
- Code expires in 15 minutes  
- Max 5 failed attempts before lockout  
- On success: account → ACTIVE, user logged in automatically  
**5.3 Login**  
- Email + password + Login button  
- Forgot Password link / Sign Up link  
- On success: JWT access token (15min, stored in memory) +  
   
 refresh token (7 days, httpOnly cookie)  
- Root Admin login: after credentials pass, TOTP screen appears  
**5.4 JWT Refresh — Axios Interceptor (REQUIRED)**  
The frontend must implement an **Axios response interceptor** that:  
1. Catches any 401 Unauthorized response  
2. Automatically calls POST /auth/refresh using the httpOnly  
   
 refresh token cookie  
3. Receives a new access token  
4. Retries the original failed request with the new token  
5. If refresh also fails (expired or revoked) → clears local auth state  
   
 and redirects to login  
This must be implemented in Feature A and applied globally to the Axios  
   
 instance. Without it, users will experience silent broken states when  
   
 their 15-minute access token expires mid-session.  
**5.5 Forgot Password**  
1. Enter email → 6-digit reset code sent (expires 10 minutes)  
2. Enter code → enter new password  
3. All existing sessions invalidated  
4. Redirect to login  
**5.6 Student ID Behavior**  
**v1 (now):**  
- Optional at signup  
- Stored if provided  
- Not validated  
- Shows "Student ID Provided" only on own profile — not visible to others  
**v2+ (future):**  
- Validated against GCTU database/API when access is provided  
- Verified users get "Verified Student" badge on public profile  
- Unverified users prompted to add/confirm ID  
**Why collect now:** higher compliance at signup, immediately usable  
   
 when validation is added, signals good faith.  
**5.7 University Email Enforcement**  
- Backend validates domain on signup  
- Only @live.gctu.edu.gh accepted in v1  
- New universities add their domain to the universities table  
- Frontend error: *"Please use your GCTU student email to register."*  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAALUlEQVR4nO3OQQ0AIAwEsAMlSJ0UrOFkGngRklZBR1WtJDsAAPzizNcDAADuNcKwAyU+nb+5AAAAAElFTkSuQmCC)  
**6. Lost Item Reporting**  
Required fields:  
- **Category** — Electronics, Bag, ID/Card, Keys, Clothing, Books/Notes,  
   
 Wallet, Jewellery, Other  
- **Public description** — visible to everyone  
- **Private description** — AES-256-GCM encrypted; used only in  
   
 ownership verification; never returned in any API response  
- **Campus location** — dropdown (stores location_label + lat/lng)  
- **Date and time lost**  
- **Images** — optional, max 2, Cloudinary  
- **2–3 hidden verification questions + answers** — AES-256-GCM encrypted;  
   
 never returned in any API response; immutable after submission  
**6.1 Good vs Bad Verification Questions**  
**Good:** What was inside the front pocket? / What sticker was on the back? /  
   
 Describe any damage or marks? / What was your phone wallpaper?  
**Bad (too guessable):** What color is it? / What brand is it?  
**6.2 Hidden Answer Rules**  
- Encrypted at rest, decrypted in memory only during scoring  
- Never logged, never returned in API, never shown to anyone including owner  
- Cannot be edited after submission  
**6.3 Initial Status: **OPEN  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSPBCj7fFRYQwYwEZiywEZJWQZeZ2ao9AAD+4lyruzq+ngAA8Nr1AMTJBeJDClAyAAAAAElFTkSuQmCC)  
**7. Found Item Reporting**  
Required fields:  
- **Category** (same list)  
- **Description** of item as found  
- **Campus location** (same dropdown — stores label + lat/lng)  
- **Date and time found**  
- **At least one image** — mandatory, max 2, Cloudinary  
Submission is blocked without at least one photo. No hidden questions  
   
 on found items — verification always flows from the lost item side.  
**7.1 Initial Status: **FOUND  
**7.2 Trust Reward: +2 points on successful submission**  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAM0lEQVR4nO3OUQmAQBBAwSdcjsu6HYxoDsEK/okwk2COmdnVGQAAf3GtalX76wkAAK/dDxFWBDkFf6+SAAAAAElFTkSuQmCC)  
**8. The Three Paths to Chat**  
Exactly three ways for chat to unlock. All enforce verification.  
   
 None allow open messaging between arbitrary users.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNhwgJuUPYDMpnRgQU2QtIq6DIze3UGAMBf3Gu1VcfXEwAAXrseaHEEM+cJoFcAAAAASUVORK5CYII=)  
**Path A — AI Match Flow**  
**Condition:** Both a lost and found item exist. AI finds a match.  
1. New item posted → AI matching runs as BackgroundTask  
2. Match score ≥ 0.60 → PotentialMatch record created  
3. Both users notified  
4. Lost item status → POTENTIAL_MATCH  
5. Lost item owner clicks **"Verify Ownership"**  
6. Owner answers their hidden questions  
7. AI scores answers against encrypted originals  
8. Score > 0.75 → chat unlocks immediately  
9. Score 0.50–0.75 → admin review queue  
10. Score < 0.50 → rejected, penalty may apply  
**POTENTIAL_MATCH Timeout:**  
   
 If an item remains in POTENTIAL_MATCH for **14 days** with no  
   
 verification attempt by the owner, APScheduler reverts it to OPEN.  
   
 The PotentialMatch record is marked EXPIRED. Owner notified:  
   
 *"Your potential match has expired. Your item is back in the active pool."*  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNBCUpfD6ZYGZDAgAU2QtIq6DIzW7UHAMBfHGt1V+fXEwAAXrseHCoGAe/SKtAAAAAASUVORK5CYII=)  
**Path B — "I Have This Item" Flow**  
**Condition:** A finder has an item, sees the lost post, has not posted  
   
 a found item yet.  
**Self-claim prevention:** The backend must verify the user attempting  
   
 Path B is NOT the owner of the target lost item. If they are, return 403.  
   
 The frontend hides the button for the item owner but backend enforcement  
   
 is mandatory.  
1. Logged-in user (not the item owner) views a lost item post  
2. Clicks **"I Have This Item"**  
3. Submits lightweight form:  
- Description of item as found  
- Campus location (dropdown)  
- Optional photo  
4. Creates IHaveThisItem claim record  
5. AI scores finder's description against the lost item's **private**  
 **  
 description and hidden answers**  
6. Score > 0.75 → chat unlocks  
7. Score 0.50–0.75 → admin review  
8. Score < 0.50 → rejected  
9. After successful return: prompt to post as resolved found item  
   
 for trust recognition (optional, incentivized)  
**Abuse prevention:**  
- 3 attempts per user per item per 24 hours  
- Failed attempts: trust penalty -3 per failed attempt after first  
- Suspicious patterns increase fraud risk score  
- All claims visible to admins  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSNBCkLfFDZwwIgHRiywEZJWQZeZ2ao9AAD+4lyruzq+ngAA8Nr1AOH0BedHjjlfAAAAAElFTkSuQmCC)  
**Path C — "This Might Be Mine" Flow**  
**Condition:** An owner sees a found item post but has not posted a  
   
 lost item yet.  
**Self-claim prevention:** Backend verifies user is NOT the poster of  
   
 the target found item. If they are, return 403. Frontend hides button  
   
 for item owner.  
**CRITICAL FIX from V3:** Path C does NOT use hidden verification  
   
 questions. The person has not previously set any questions — there are  
   
 no stored encrypted answers to compare against. Self-set-and-self-answer  
   
 questions would always score 1.0 and prove nothing.  
**Path C verification is description-based only:**  
1. Logged-in user (not the found item poster) views a found item post  
2. Clicks **"This Might Be Mine"**  
3. Submits structured form:  
- Description of item as they remember it  
- Where they lost it (campus location dropdown)  
- When they lost it (date picker)  
4. AI compares their description against the found item's public  
   
 description AND image using semantic similarity + image hashing  
5. Score > 0.75 → chat unlocks between owner and finder  
6. Score 0.50–0.75 → admin review (admin sees both descriptions + image)  
7. Score < 0.50 → rejected  
8. After successful return: prompt owner to post a resolved lost item  
   
 for record completion (optional, incentivized)  
**Why this is still secure:**  
- The claimant must accurately describe specific details of the item  
   
 without seeing the found item's full details  
- The found item photo acts as additional ground truth for admin review  
   
 in the 0.50–0.75 range  
- 3-attempt limit and trust penalties still apply  
- Admins can see both descriptions side-by-side for manual judgment  
**Abuse prevention:**  
- 3 attempts per user per item per 24 hours  
- Failed attempts penalize trust  
- Fraud risk score increases with suspicious patterns  
- All claims visible to admins  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAM0lEQVR4nO3OMQ0AIAwAwZIgBKm1gjSMNCwYYCIkd9OP3zJzRMQMAAB+sfqJeroBAMCN2pTWBSSZVtjzAAAAAElFTkSuQmCC)  
**9. Campus Location System**  
**9.1 Approach**  
Predefined campus zone dropdown in v1. No map UI required.  
   
 User selects a zone → system stores known lat/lng automatically.  
**9.2 GCTU Seed Zones**  
Pre-loaded at deployment:  
- Main Library  
- Block A Lecture Hall  
- Block B Lecture Hall  
- Cafeteria / Canteen  
- Administration Block  
- ICT Lab  
- Student Services Centre  
- Car Park  
- Sports Ground  
- Main Gate / Entrance  
Each zone: name, latitude, longitude, university_id  
   
 Admins can add more zones via the admin dashboard.  
**9.3 Distance Calculation**  
geopy.distance.geodesic calculates metres between two items'  
   
 coordinates. Feeds into AI match scoring (Section 10).  
**9.4 Future Enhancement**  
Leaflet.js pin-drop map replaces dropdown in v2. Schema already  
   
 supports it — only a frontend change needed.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNBCUrfD6LYGNDAgAU2QtIq6DIzW7UHAMBfHGt1V+fXEwAAXrseHDAF/orRG+cAAAAASUVORK5CYII=)  
**10. AI Matching Logic**  
Runs as a BackgroundTask every time a lost or found item is posted.  
   
 Compares new item against all active opposing items in the same university.  
**10.1 Match Score Formula**  
| | | |  
|-|-|-|  
| **Factor** | **Weight** | **Method** |   
| Description similarity | 0.40 | sentence-transformers cosine similarity |   
| Image similarity | 0.15 | imagehash perceptual hashing (phash) |   
| Location proximity | 0.15 | geopy geodesic distance |   
| Date proximity | 0.15 | Days between lost and found dates |   
| Category match | 0.15 | Exact match = 1.0, mismatch = 0.0 |   
   
If either item has no image: image score = 0.0, weight redistributes  
   
 proportionally across the remaining four factors.  
**10.2 Description Similarity**  
sentence-transformers model all-MiniLM-L6-v2 (~80MB).  
   
 Public descriptions only — private descriptions never used here.  
**10.3 Image Similarity**  
imagehash.phash(). Hamming distance normalized to 0.0–1.0.  
**10.4 Location Proximity Score**  
- 0–100m → 1.0  
- 100–300m → 0.75  
- 300–600m → 0.50  
- 600m–1km → 0.25  
- Over 1km → 0.0  
**10.5 Date Proximity Score**  
- 0–1 days → 1.0  
- 2–3 days → 0.75  
- 4–7 days → 0.50  
- 8–14 days → 0.25  
- Over 14 days → 0.0  
**10.6 Category Match**  
Same → 1.0 / Different → 0.0  
**10.7 Match Threshold**  
- ≥ 0.60 → create PotentialMatch, notify both users  
- < 0.60 → no match, item stays in pool  
**10.8 Matching Pool**  
Only OPEN, FOUND, POTENTIAL_MATCH items included.  
   
 EXPIRED, ARCHIVED, RETURNED, CLOSED, UNDER_DISPUTE excluded.  
**10.9 Multiple Matches**  
One item may match multiple candidates. All records created.  
   
 User sees them ranked by score descending.  
**10.10 POTENTIAL_MATCH + UNDER_DISPUTE Interaction**  
When an item enters UNDER_DISPUTE, ALL other pending PotentialMatch  
   
 records for that item are paused (status = PAUSED). No other  
   
 verification can proceed until the dispute is resolved.  
On dispute resolution, paused matches resume their previous state and  
   
 the owner is notified they can proceed with pending matches.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsSfYxZo/jzlMYQLPJrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA4q7Bc870TqdAAAAAElFTkSuQmCC)  
**11. Notification Logic**  
Targeted and meaningful. No global broadcasts.  
**11.1 Notification Triggers**  
| | |  
|-|-|  
| **Event** | **Who is notified** |   
| AI match found | Lost item owner + found item poster |   
| "I Have This Item" claim received | Lost item owner |   
| "This Might Be Mine" claim received | Found item poster |   
| Verification passed (any path) | Both parties |   
| Verification failed | Claimant only |   
| Verification sent to admin review | Claimant only |   
| POTENTIAL_MATCH expired (14-day timeout) | Lost item owner |   
| Paused matches resumed after dispute | Lost item owner |   
| New chat message | Recipient only |   
| Conversation paused (sender suspended) | Other party in conversation |   
| Item successfully returned | Both parties |   
| Return disputed | Both parties |   
| Dispute resolved | Both parties |   
| Tip received | Finder only |   
| Post expiring in 3 days | Item owner only |   
| Post extended | Item owner only |   
| Account suspended | Suspended user only |   
| Account unsuspended | User only |   
| Post removed by admin | Post owner only |   
| Report acted on | Reporter only (outcome summary) |   
| New lost item posted (civic opt-in) | Opted-in users only |   
   
**11.2 Civic Lost Item Alerts (Opt-In)**  
Toggle in settings: **"Notify me about lost items so I can help"**  
   
 Default: OFF.  
Notification shows: category, general location, help prompt, link.  
   
 Never shows: owner identity, contact details, private description.  
**11.3 Web Push Notifications**  
Real phone/desktop tray notifications via the Web Push API.  
**How it works:**  
- Device registered with push subscription stored in backend  
- Backend sends messages via pywebpush on notification events  
- Appears in tray even when browser is closed  
**Platform support:**  
- Android Chrome: full support  
- iOS Safari 16.4+ (PWA must be installed first on iOS)  
- Desktop Chrome/Edge: full support  
**Permission timing — FIXED from V3:**  
   
 Do NOT request push permission on login. Instead, request it  
   
 **contextually** — the first time a notification-worthy event occurs  
   
 for that user (e.g. a match is found), show an **in-app prompt first**:  
   
 *"Turn on push notifications to get alerts like this on your phone?"*  
   
 with Accept / Not Now buttons.  
Only if the user clicks Accept does the browser's native permission  
   
 dialog appear. This dramatically increases opt-in rates and avoids  
   
 being flagged as aggressive by browsers.  
Users can also toggle push notifications manually in Settings at any time.  
**Push content:**  
- Title: "FAiND"  
- Body: event description (e.g. "A potential match was found for your lost item!")  
- Icon: FAiND app icon  
- Click action: deep-links to the relevant page in the app  
**11.4 Notification Delivery Layers**  
1. In-app notification (stored in notifications table, bell icon)  
2. Toast message (when user is actively in the app)  
3. Web Push (phone/desktop tray via pywebpush)  
4. Email (future — SMTP toggle in settings)  
**11.5 Notification Read State**  
Each notification has read boolean. Unread count = badge on bell icon.  
   
 Clicking marks read and navigates to relevant page.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsSfYxZo/jzlMYQLPJrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA4q7Bc870TqdAAAAAElFTkSuQmCC)  
**12. Ownership Verification Logic**  
The security gate preventing wrong users from claiming items.  
   
 Applies to all three paths.  
**12.1 Entry Points**  
- Path A: "Verify Ownership" button on matched found item  
- Path B: Automatic after "I Have This Item" submission  
- Path C: Automatic after "This Might Be Mine" submission  
Button label must always be **"Verify Ownership"** — never "Claim" or "Take".  
**12.2 Semantic Comparison Method**  
sentence-transformers (all-MiniLM-L6-v2). Encode submitted text and  
   
 stored text (decrypted in memory only — never logged). Compute cosine  
   
 similarity. Handles synonyms and paraphrasing naturally.  
**12.3 Path A + B Ownership Score Formula**  
| | | |  
|-|-|-|  
| **Factor** | **Weight** | **Notes** |   
| Hidden answer similarity | 0.55 | Primary signal |   
| Description similarity | 0.25 | Claimant description vs item public description |   
| Image similarity | 0.20 | Only if claimant provides an image |   
   
Trust score and fraud risk are NOT in this formula. They are  
   
 admin-visible signals only and never block a legitimate new user.  
**12.4 Path C Ownership Score Formula**  
| | | |  
|-|-|-|  
| **Factor** | **Weight** | **Notes** |   
| Description similarity | 0.70 | Claimant's description vs found item description |   
| Image similarity | 0.30 | Claimant's description vs found item photo (imagehash) |   
   
Path C has no hidden answers to compare (they don't exist yet).  
   
 Description accuracy is the primary ownership signal.  
   
 Admin review range is wider for Path C — admins see both descriptions  
   
 and the found item photo side-by-side.  
**12.5 Decision Thresholds**  
- Score > 0.75 → **Auto-approved** — chat unlocks immediately  
- Score 0.50–0.75 → **Admin review** — both users notified, awaiting admin  
- Score < 0.50 → **Rejected** — claimant notified  
**12.6 Anti-Abuse Rules**  
- Max 3 attempts per user per item per 24 hours  
- 2nd and 3rd failed attempts: -3 trust points each  
- 3 failed attempts: fraud risk +20, admin alerted  
- Item never locked for other legitimate claimants  
**12.7 Multiple Claimants**  
Each claim scored independently. If two or more both exceed 0.75 →  
   
 dispute opened automatically. Never auto-award by timing.  
**12.8 False Claim Penalty**  
Score < 0.30 or admin-confirmed: **-10 trust points**  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OYQ1AABSAwY9JoICqL4Z8Ikiggn9mu0twy8wc1RkAAH9xbdVa7V9PAAB47X4A9CgEJQFjJ/EAAAAASUVORK5CYII=)  
**13. Post and User Reporting**  
**13.1 Reporting a Post**  
Any logged-in user can report an item post they did not create.  
**Report reasons (dropdown):**  
- Fake or misleading item  
- Suspicious behavior  
- Inappropriate content  
- Spam  
- Other (free text, max 200 chars)  
**What happens:**  
- A PostReport record is created with: reporter ID, item ID,  
   
 reason, timestamp  
- The report appears as a flag on the item in the admin Posts section  
- Three or more reports from different users on the same item  
 **auto-escalates** to the admin review queue with a priority flag  
- Admin reviews and decides: dismiss, remove post, warn user,  
   
 or suspend user  
**Outcome notification:** Reporter receives a brief notification  
   
 when the admin acts on their report (e.g. "Thank you — your report  
   
 has been reviewed."). The specific outcome is not disclosed.  
**13.2 Reporting a User**  
Any logged-in user can report another user.  
**Entry points:**  
- "Report User" button on any public profile page  
- Flag icon in the chat conversation header (reports the other party)  
**Report reasons (dropdown):**  
- Threatening or abusive behavior  
- Suspected fraud or scam attempt  
- Harassment  
- Impersonation  
- Other (free text, max 200 chars)  
**What happens:**  
- A UserReport record is created with: reporter ID, reported user ID,  
   
 reason, optional context (e.g. conversation ID if from chat), timestamp  
- Appears in admin Users section as a flag on the reported user's profile  
- Three or more reports against the same user from different users  
 **auto-escalates** to admin review queue with priority flag  
- This feeds directly into the fraud monitoring system  
- Fraud risk score: +15 per user report received (after first)  
**Outcome notification:** Reporter notified when admin acts.  
**13.3 Report Abuse Prevention**  
- A user cannot report the same post or user more than once  
- Reports from suspended users are deprioritized in the queue  
- Admins can mark a reporter as a bad-faith reporter, which suppresses  
   
 future reports from them pending review  
**13.4 Admin Report Queue**  
Both PostReports and UserReports appear in the admin dashboard under  
   
 a unified "Reports" section. Each report shows:  
- Reporter's display name and trust tier  
- Target (post or user)  
- Reason and optional context  
- Timestamp  
- Auto-escalation flag if threshold reached  
- Action buttons: Dismiss / Remove Post / Warn User / Suspend User  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSNBCUpfDq4wwIAABiywEZJWQZeZ2ao9AAD+4liruzq/ngAA8Nr1ABweBgdur/QFAAAAAElFTkSuQmCC)  
**14. Messages Inbox and Real-Time Chat**  
**14.1 Chat Unlock Conditions**  
Chat unlocks ONLY when:  
- Verification score > 0.75 (auto-approved), OR  
- Admin manually approves a claim in the 0.50–0.75 range  
No messages possible before one of these conditions is met.  
**14.2 Messages Page (**/messages **)**  
Accessible from nav bar with unread badge.  
**Conversations list (left panel / full screen on mobile):**  
- Each row: avatar, display name, item name, last message preview,  
   
 timestamp, unread count badge  
- Search bar to filter by name or item name  
**Inside a conversation (right panel / full screen on mobile):**  
- Other user's name + avatar at top → click → public profile  
- Item name link at top → click → item detail page  
- **"Report User" flag icon** in conversation header → report form  
- Safety warning banner (always visible, cannot be dismissed)  
- Message bubbles (own: right, theirs: left)  
- Timestamps on all messages  
- **Seen receipts:** ✓ = delivered, ✓✓ = seen (read)  
- Message input + Send button  
- Real-time via WebSockets — no page refresh  
**14.3 Seen Receipt Implementation**  
When a user opens a conversation, backend marks all unread messages  
   
 in that thread as read = true for that user. Sender's UI updates  
   
 via WebSocket to show the ✓✓ indicator.  
**14.4 Chat Safety Warning (Always Visible)**  
*"Keep your conversation focused on recovering your item safely.*  
 *  
 Do not share passwords, banking details, or sensitive personal*  
 *  
 information. FAiND is not responsible for off-platform exchanges."*  
**14.5 Message Preservation**  
Chat history is never deleted. Preserved even if item is removed by user.  
   
 Required for dispute resolution and fraud investigation.  
**14.6 Frozen Conversations (Suspended User)**  
If one party is suspended, the conversation is frozen:  
- Both parties can read existing messages  
- The suspended user cannot send new messages  
- A banner replaces the input: *"This conversation is currently paused*  
 *  
 pending a platform review."*  
- On unsuspension, the conversation unfreezes automatically  
**14.7 Real-Time Implementation**  
FastAPI WebSockets with in-memory connection manager (Python dict keyed  
   
 by conversation ID). Redis Pub/Sub deferred to v2.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OYQ1AABSAwc8mi5wvlAB6CKCAACr4Z7a7BLfMzFYdAQDwF+da3dX+9QQAgNeuB6fWBdZMUxZ2AAAAAElFTkSuQmCC)  
**15. Return Confirmation**  
**15.1 Method 1 — Dual Confirmation**  
1. Finder marks item as handed over  
2. Owner confirms receipt  
3. Status → RETURNED only after both  
If finder confirms but owner does not within 7 days → reminder sent.  
   
 If still unconfirmed after 14 days → admin review flag raised.  
**15.2 Method 2 — QR Code**  
1. System generates temporary single-use QR code  
2. Finder displays it on their device  
3. Owner scans it on their device  
4. Successful scan → immediate RETURNED status  
QR codes expire after 24 hours. Single-use only.  
**15.3 Return Result**  
- Finder: **+5 trust points**  
- Status → RETURNED  
- 7-day tipping window opens  
- 7-day dispute window opens  
- Both notified  
- Item appears in "Recently Returned" homepage section (anonymously, 7 days)  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSNhRAF6EPYDLhGADSywEZJWQZeZ2aszAAD+4l6rrTq+ngAA8Nr1AIWsBDYDm5cLAAAAAElFTkSuQmCC)  
**16. Returned Items Lifecycle**  
**16.1 Immediately After Return**  
- Removed from public browsing feed (/lost, /found, homepage columns)  
- Visible in "Recently Returned" section (anonymous — no names or images)  
- Visible on both parties' dashboards under "Returned" tab  
- Chat remains accessible (read-only unless further coordination needed)  
- Tipping window: 7 days for owner to tip finder  
- Dispute window: 7 days for either party to challenge the return  
**16.2 Returned Item Detail Page**  
Private — accessible only to the two parties involved.  
**Shows:**  
- Item name, category, public description  
- Dates: lost / found / returned  
- Location found  
- Item images (if any)  
- Return summary statement  
- Chat history (read-only, preserved)  
- Tipping section (within window, if not yet tipped)  
- Dispute section (within window)  
- "Resolved" badge  
**Never shows:** hidden answers, private description, raw trust scores,  
   
 fraud signals, or admin notes.  
**16.3 Tipping Window (7 Days)**  
Owner sees on returned item detail page:  
- **"Send Appreciation"** → tipping form → Paystack  
- **"Skip for Now"** → dismisses temporarily  
- Countdown: *"X days left to send appreciation"*  
After 7 days: section disappears. No guilt messaging if no tip sent.  
**16.4 Dispute Window (7 Days)**  
Either party can click **"Dispute This Return"** within 7 days.  
On dispute:  
- Status → UNDER_DISPUTE  
- Tipping paused if not yet completed (see Section 16.5)  
- Admin reviews all evidence  
- Outcome: stays RETURNED or reopened  
After 7 days: dispute option removed, return is final.  
**16.5 Tip Sent Before Dispute Filed**  
If the owner already sent a tip before filing a dispute:  
- The tip is **frozen** — not automatically refunded  
- Admin is notified that a tip exists for this disputed return  
- If dispute resolves as *legitimate return*: tip stands, released normally  
- If dispute resolves as *fraudulent/false return*: admin contacts  
   
 Paystack manually to initiate refund. This is documented in admin logs.  
**16.6 "Recently Returned" Homepage Section**  
Shows resolved items from the past 7 days, anonymously:  
- Item category  
- "Successfully returned" badge  
- Date returned  
- University  
Never shows: names, images, identifying details.  
   
 Builds community trust in the platform.  
**16.7 After 7 Days**  
- Status → ARCHIVED  
- Removed from all public views  
- Visible only on both parties' dashboards  
- Preserved for 60 days, then eligible for deletion  
**16.8 Dashboard — Returned Tab**  
**Owner sees:** item name, category, date returned, finder's display name  
   
 and trust tier, whether tip was sent, "View Details" button.  
**Finder sees:** item name, category, date returned, whether appreciated  
   
 (count — not amount), "View Details" button.  
**16.9 Public Profile — Return Count**  
"X items successfully returned" — count only. No identifying details.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsScYxpg/h5VMYARvRrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA224BcUMk6pDAAAAAElFTkSuQmCC)  
**17. Trust and Reputation System**  
All trust changes routed through canonical **TrustService**.  
   
 All changes logged in TrustEvent table.  
**17.1 Trust Events**  
| | |  
|-|-|  
| **Event** | **Change** |   
| Post a found item | +2 |   
| Successful return (finder) | +5 |   
| 2nd failed verification attempt | -3 |   
| 3rd failed verification attempt | -3 |   
| Confirmed false claim (< 0.30 or admin-confirmed) | -10 |   
| Admin-confirmed fraud | -20 |   
| User report received (after first) | -5 per report |   
| Account suspended | Score frozen until unsuspended |   
   
**17.2 Trust Display**  
**Own dashboard:** Raw number (e.g. "Trust Score: 47")  
**Other users / public profile:** Tier label only:  
- 0–20: New Member  
- 21–50: Trusted Member  
- 51–100: Reliable Member  
- 100+: Community Champion  
Raw scores never shown to others. Tier labels communicate credibility  
   
 without exposing numbers or triggering comparison.  
**17.3 Trust and Verification**  
Trust score is NOT in the ownership confidence formula.  
   
 Admin-visible signal only. Never blocks a legitimate new user.  
**17.4 Trust and Tipping**  
Receiving a tip does NOT increase trust. Trust is earned through  
   
 honest behavior, not money.  
**17.5 TrustEvent Log**  
Every change: user_id, delta, reason (enum), reference_id,  
   
 created_at, applied_by (system or admin ID).  
Root Admin can view full trust history for any user.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAMUlEQVR4nO3WAQkAIBAEsBPMYs4PZhMDWMAA5njYUmxU1UqyAwBAF2cmeZE4AIBO7gentgXapSWpbgAAAABJRU5ErkJggg==)  
**18. Fraud Detection**  
**18.1 Fraud Risk Signals**  
| | |  
|-|-|  
| **Signal** | **Effect** |   
| 2 failed verifications in 24h | Risk +10 |   
| 3 failed verifications in 24h | Risk +20, admin alerted |   
| Repeated low-score claims across multiple items | Risk +15 |   
| Multiple failed Path B or C claims | Risk +10 each |   
| Unusual claim volume (5+ in 24h) | Risk +25, admin alerted |   
| User report received | Risk +15 per report |   
| Admin confirms fraud | Risk +50 |   
   
**18.2 Fraud Risk Thresholds**  
- 0–30: Normal  
- 31–60: Elevated — admin sees flag on user profile  
- 61–100: High — admin auto-alerted  
- 100+: Admin review required before further verifications allowed  
**18.3 Visibility**  
Internal only. Never shown to regular users.  
   
 Admins see in user profiles and fraud monitoring dashboard.  
**18.4 FraudEvent Log**  
Every suspicious event written to FraudEvent table for admin review.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OQQmAABRAsSd4NIGhrOTvaQBrWMGbCFuCLTOzV2cAAPzFvVZbdXw9AQDgtesBhYQEO+64Y8AAAAAASUVORK5CYII=)  
**19. Dispute Resolution**  
**19.1 Dispute Triggers**  
- Verification score 0.50–0.75 (admin review range)  
- Two or more users both exceed 0.75 on same item  
- User reports suspicious claim behavior  
- Return challenged within 7-day dispute window  
- Admin manually opens dispute  
**19.2 Dispute State**  
- Item → UNDER_DISPUTE  
- All pending PotentialMatch records for this item → PAUSED  
- Permanent deletion blocked  
- Tipping paused if not yet completed  
- All evidence preserved  
**19.3 Evidence Available to Admins**  
- Item public details; private description (not decrypted — similarity score shown)  
- Path B or C submission content  
- Hidden answer similarity scores (not raw answers)  
- Description similarity scores  
- Image similarity scores  
- Trust scores and full trust history  
- Fraud risk scores and full fraud event history  
- Claim attempt history with timestamps  
- Full chat history  
- Return confirmation state and QR scan logs  
- All report history for both parties  
**19.4 Dispute Outcomes**  
1. Claim Approved → chat unlocks or return confirmed  
2. Claim Rejected → trust penalty may apply  
3. Request More Information → admin asks parties for evidence  
4. User Flagged → fraud monitoring increased  
5. Item Locked → no further claims until resolved  
6. Escalated to Root Admin → final authority  
**19.5 Resolution Authority**  
- Root Admin: final authority on all disputes  
- Assistant Root Admins: can resolve, subject to Root Admin override  
- University Admins (future): resolve within their university  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsScYxpg/h5VMYARvRrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA224BcUMk6pDAAAAAElFTkSuQmCC)  
**20. Tipping System**  
**20.1 Rules**  
- Entirely optional  
- 7-day window after return  
- Paystack test mode for project demo  
- Does NOT affect trust score or any platform feature  
- Paused if dispute is opened; resolved per Section 16.5  
**20.2 Visibility — Strictly Enforced**  
| | |  
|-|-|  
| **Context** | **What is shown** |   
| Public profile | "Tips Received: 3" — count only |   
| Returned item page | "The owner expressed appreciation to the finder." |   
| Sender's transaction history | Amount (private to sender only) |   
| Receiver's transaction history | Amount (private to receiver only) |   
| Any public API response | Amount NEVER exposed |   
| Admin dashboard | Amount visible to Root Admin only |   
   
Tip amounts stored AES-256-GCM encrypted.  
   
 Backend enforces this — it is not a frontend-only rule.  
**20.3 Paystack Integration**  
- Ghana payment gateway  
- Test mode for demo  
- Webhook verification required before updating tip records  
- Never trust client-side payment confirmation  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OUQmAABBAsSeIWMICprwEpjSIFfwTYUuwZWaO6goAgL+412qrzq8nAAC8tj8tdQNNdXaCdAAAAABJRU5ErkJggg==)  
**21. Post Lifecycle, Expiry, and Deletion**  
**21.1 Lost Item Lifecycle**  
- Active: 45 days from posting  
- Reminder notification: 3 days before expiry  
- Extensions: max 2, +30 days each (max total: 105 days)  
- On expiry: status → EXPIRED, removed from feed and matching pool  
**21.2 Found Item Lifecycle**  
- Active: 21 days  
- Reminder: 3 days before expiry  
- Extensions: max 2, +30 days each (max total: 81 days)  
**21.3 POTENTIAL_MATCH Timeout**  
If no verification attempt within 14 days of match creation:  
- Status reverts to OPEN  
- PotentialMatch record → EXPIRED  
- Owner notified  
**21.4 Returned Item**  
- RETURNED status for 7 days (tipping + dispute window)  
- After 7 days → ARCHIVED  
- Visible on both dashboards throughout  
**21.5 User-Removed Posts**  
- Status → ARCHIVED (soft delete — never immediately destroyed)  
- Hidden from feed and matching pool  
- Preserved 60 days internally  
**21.6 Permanent Deletion Eligibility**  
All three must be true:  
- ARCHIVED or EXPIRED for 60+ days, AND  
- NOT UNDER_DISPUTE, AND  
- NOT admin_locked = true or under fraud investigation  
**21.7 Scheduled Jobs (APScheduler)**  
- **Every hour:** expire items past deadline; revert stale POTENTIAL_MATCHes  
- **Daily midnight:** send 3-day expiry reminders  
- **Daily midnight:** close expired tipping windows  
- **Daily midnight:** close expired dispute windows on returned items  
- **Daily midnight:** move eligible archived items to deletion queue  
- **Daily midnight:** resume paused matches on resolved disputes  
APScheduler is required. FastAPI BackgroundTasks cannot handle  
   
 time-scheduled jobs — it only runs when a request is received.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsSfYxZo/jzlMYQLPJrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA4q7Bc870TqdAAAAAElFTkSuQmCC)  
**22. Item Status Reference**  
| | |  
|-|-|  
| **Status** | **Meaning** |   
| OPEN | Lost item active, in matching pool |   
| FOUND | Found item active, in matching pool |   
| POTENTIAL_MATCH | AI-identified candidate match exists |   
| UNDER_VERIFICATION | Verification in progress |   
| UNDER_DISPUTE | In admin review or contested |   
| RETURNED | Successfully returned; windows open |   
| EXPIRED | Passed active period without return |   
| ARCHIVED | Soft-deleted or resolved past visible window |   
| CLOSED | Force-closed by admin |   
   
Status transitions enforced on the backend only.  
   
 No client can directly set item status.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OMQ0AIAwAwZIgBKnVgjN8dGDBABMhuZt+/JaZIyJmAADwi9VP1NMNAABu1AaU3AUhiyfJeAAAAABJRU5ErkJggg==)  
**23. Public Profile — Visibility Rules**  
**23.1 What Other Users See**  
| | | |  
|-|-|-|  
| **Field** | **Visible** | **Notes** |   
| Display name / username | ✅ | Never full real name by default |   
| Profile photo | ✅ | Optional |   
| Trust tier label | ✅ | Label only — not raw score |   
| Items successfully returned (count) | ✅ | "3 items returned" |   
| Tips received (count) | ✅ | "Appreciated 2 times" — no amounts |   
| Member since (month/year) | ✅ | Not exact date |   
| University | ✅ | "GCTU" |   
| Verified Student badge | ✅ future | When validation implemented |   
| "Report User" button | ✅ | Any logged-in user can report |   
| Email address | ❌ | Private |   
| Phone number | ❌ | Private |   
| Raw trust score | ❌ | Tier label only |   
| Fraud risk score | ❌ | Admin only |   
| Transaction history | ❌ | Private |   
| Hidden answers | ❌ | System only |   
| Student ID number | ❌ | Private |   
   
**23.2 Where Users See Others' Info**  
- Item post cards: display name, avatar, trust tier, return count  
- Public profile page (click their name/avatar)  
- Chat conversation header: name and avatar  
**23.3 Own Dashboard vs Public**  
Own dashboard additionally shows: raw trust score, full transaction  
   
 history, student ID field, email, all own posts (active/returned/archived).  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSNBCkJfFEIwwIgHRiywEZJWQZeZ2ao9AAD+4lyruzq+ngAA8Nr1AOHsBegrsOrIAAAAAElFTkSuQmCC)  
**24. Homepage and Browse Pages**  
**24.1 Homepage Layout (Top to Bottom)**  
**Nav bar** (always visible, sticky)  
**Hero section:**  
- Background: high-quality Unsplash image of diverse campus students,  
   
 slightly blurred with semi-transparent overlay for readability  
- Headline + subheadline  
- Two CTA buttons: "Report Lost Item" / "Report Found Item"  
   
 (login prompt for guests)  
**Two-column section:**  
- Left: 5 latest lost items → "See All Lost Items →" → /lost  
- Right: 5 latest found items → "See All Found Items →" → /found  
- Columns update via polling on new posts  
**Recently Returned section:**  
- Anonymous resolved items from past 7 days  
- Builds community trust  
**"Why Choose FAiND" section**  
**Safety warning banner**  
**FAB (Floating Action Button):**  
- Fixed bottom-right, always visible  
- Expands: Report Lost Item / Report Found Item  
- Login prompt for guests  
**24.2 Browse Pages (**/lost ** and **/found **)**  
Full dedicated pages — not popups.  
**Layout:**  
- Search bar at top  
- Collapsible filter panel (mobile-friendly):  
- Category (multi-select checkboxes)  
- Campus location zone (dropdown)  
- Date range picker  
- Status (Open / Potential Match)  
- Sort: Newest / Oldest / Most Recent Activity  
- 20-item card grid  
- Load More button  
**Each card:**  
- Photo (or category icon if none)  
- Category badge  
- Public description preview  
- Location label  
- "X days ago" timestamp  
- Poster's trust tier badge + display name (→ public profile)  
**24.3 Theme Toggle**  
🌙 / ☀️ in nav bar. System preference on first visit.  
   
 Manual preference saved to localStorage.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNhYMMAKlD4OzrxgQU2QtIq6DIzR3UFAMBf3Gu1VefXEwAAXtsfSqADWz4G/HUAAAAASUVORK5CYII=)  
**25. User Dashboard (**/dashboard **)**  
**25.1 Overview Cards**  
- Raw trust score (own view only)  
- Total items posted  
- Total items returned  
- Tips received count (amounts private)  
**25.2 Tabs**  
- **Active Lost Items** — View / Edit / Extend / Remove / Verify buttons  
- **Active Found Items** — View / Edit / Extend / Remove buttons  
- **Returned Items** — View Details button per item  
- **Pending** — active matches and verifications awaiting action  
**25.3 Settings (**/settings **)**  
- Edit display name  
- Edit profile photo  
- Change password  
- Student ID (add/edit, optional)  
- 🔔 Civic lost-item alerts toggle  
- 🔔 Push notifications toggle  
- 🔔 Email notifications toggle (future)  
- Save Changes button  
- Delete Account button (confirmation dialog required)  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OUQmAABBAsSdYxKYXx1gmEBOIFfwTYUuwZWa2ag8AgL841uquzq8nAAC8dj05WgYLQTzjnAAAAABJRU5ErkJggg==)  
**26. Admin Dashboard (**/admin/[secret-path] **)**  
**26.1 Access**  
Secret route → 404 for all unauthorized users.  
   
 JWT role check + 2FA enforced on backend.  
**26.2 Sidebar Navigation**  
- Overview (analytics)  
- Users (management)  
- Claims Review (0.50–0.75 queue)  
- Disputes (open queue)  
- Reports (post + user reports)  
- Fraud Alerts (flagged users)  
- Posts (moderation)  
- Admin Logs (Root Admin only)  
- Universities (Root Admin only, future)  
**26.3 Platform Analytics (Root Admin)**  
Total lost/found/returned items, return rate, avg time to return,  
   
 claims attempted, disputes opened/resolved, trust distribution,  
   
 fraud frequency, active users (daily/weekly/monthly).  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsSfYxZo/jVEMYQLPJrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA4rLBc059ysnAAAAAElFTkSuQmCC)  
**27. Complete Interaction Map**  
Every clickable element and its behavior.  
**27.1 Navigation Bar — Guest**  
- Logo → homepage  
- Lost Items → /lost  
- Found Items → /found  
- Login → /login  
- Sign Up → /signup  
- 🌙/☀️ → theme toggle  
**27.2 Navigation Bar — Logged In**  
- Logo → homepage  
- Lost Items → /lost  
- Found Items → /found  
- 🔔 bell (badge) → notification dropdown  
- 💬 messages (badge) → /messages  
- 👤 avatar → dropdown: My Profile / Dashboard / Settings / Logout  
- 🌙/☀️ → theme toggle  
**27.3 Homepage**  
- Hero CTA buttons → forms (login prompt if guest)  
- Item cards → item detail page  
- Poster name/avatar → public profile  
- "See All Lost/Found" → /lost or /found  
- FAB → expands: Report Lost / Report Found  
- Recently Returned cards → anonymous summary only (no navigation)  
**27.4 Browse Pages**  
- Category checkboxes → live filter  
- Location dropdown → live filter  
- Date range inputs → live filter  
- Clear filters → reset all  
- Sort dropdown → reorder  
- Item cards → item detail page  
- Poster name/avatar → public profile  
- Load More → next 20 items  
**27.5 Item Detail Page**  
**All users:**  
- Back/breadcrumb → browse page  
- Poster name/avatar → public profile  
- Category badge → browse page filtered by category  
- Images → fullscreen lightbox  
**Logged-in (not owner):**  
- "I Have This Item" (lost items only) → Path B form  
- "This Might Be Mine" (found items only) → Path C form  
- "Flag / Report Post" → report reason dropdown → submit  
**Owner only:**  
- "Edit" → edit form (limited fields, hidden answers immutable)  
- "Extend Post" → extends expiry (shown if extensions remain)  
- "Remove Post" → confirmation dialog → soft delete  
- "Mark as Returned" → return confirmation flow  
- "View Match" (when match exists) → match detail card  
- "Verify Ownership" (when match exists) → verification form  
**27.6 Lost Item Form**  
Category dropdown, public description, private description, location  
   
 dropdown, date/time pickers, optional image upload (max 2, preview),  
   
 add/remove question rows (2–3), question + answer inputs, Submit, Cancel.  
**27.7 Found Item Form**  
Category dropdown, description, location dropdown, date/time pickers,  
   
 required image upload (max 2, preview — cannot submit without one),  
   
 Submit, Cancel.  
**27.8 Verification Form (Path A)**  
Read-only questions display, answer input fields, Submit Verification.  
   
 Result screen: Passed → "Open Chat" button / Admin Review → info message /  
   
 Rejected → error + attempts remaining. Cancel.  
**27.9 "I Have This Item" Form (Path B)**  
Description field, location dropdown, optional image upload, Submit.  
   
 Same result states as Path A verification. Cancel.  
**27.10 "This Might Be Mine" Form (Path C)**  
Description field, location dropdown, date lost picker, Submit.  
   
 Result: Passed → "Open Chat" / Admin Review → info message /  
   
 Rejected → error + attempts remaining. Cancel.  
**27.11 Messages Page**  
- Conversation rows → open conversation  
- Search input → filter list  
- Inside conversation:  
- Back (mobile) → list  
- Other user name/avatar → public profile  
- Item name link → item detail page  
- 🚩 flag icon in header → report user form  
- Message input + Send  
- Seen receipts auto-update via WebSocket  
- Frozen banner (if conversation paused)  
**27.12 Notification Dropdown**  
- "Mark all as read" → clears badges  
- Each row → navigates to relevant page  
- "See all" → /notifications  
**27.13 Returned Item Detail Page**  
- "Send Appreciation" (owner, within window) → Paystack tipping  
- "Skip for Now" (owner, within window, untipped) → temporary dismiss  
- "Dispute This Return" (both, within window) → dispute form  
- "View Chat History" (both) → read-only chat  
- Back → dashboard  
**27.14 Return Confirmation**  
- "I Have Returned This Item" (finder) → marks finder side  
- "I Have Received This Item" (owner) → marks owner side → triggers RETURNED  
- "Generate QR Code" (finder) → displays QR  
- "Scan QR Code" (owner) → opens camera → confirms return  
**27.15 Auth Pages**  
- Login: email, password, Login, Forgot Password link, Sign Up link  
- Signup: all fields, Create Account, Login link  
- Email verification: 6-digit input, Verify, Resend Code (after 60s)  
- Forgot password: email → code input → new password → Reset  
**27.16 Public Profile Page**  
- Poster's items cards → item detail page  
- "Report User" button → report reason dropdown → submit  
**27.17 Dashboard**  
- Tab buttons → sections  
- Item cards: View / Edit / Extend / Remove / Verify buttons  
- Overview cards: display only  
**27.18 Settings**  
- All fields: inline edit + Save Changes  
- Toggles: on/off switches  
- Delete Account → confirmation dialog  
**27.19 Admin Dashboard**  
- Sidebar nav → sections  
- View → detail panels  
- Approve / Reject → claims and disputes  
- Suspend User → confirmation dialog  
- Unsuspend User → confirmation dialog  
- Remove Post → confirmation  
- Force Close → confirmation  
- Dismiss Report → confirmation  
- Promote to Assistant Admin (Root Admin only) → confirmation  
- Demote (Root Admin only) → confirmation  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSNBACPq8MH2NpGACyywEZJWQZeZ2aszAAD+4l6rrTq+ngAA8Nr1AL/KBEe6dElaAAAAAElFTkSuQmCC)  
**28. UI Philosophy and Design**  
**28.1 Design Style**  
- Modern, clean, premium, **mobile-first**  
- **Liquid glass / glassmorphism:**  
- backdrop-filter: blur(20px) on cards  
- Semi-transparent backgrounds  
- Subtle white/light gradient borders  
- Soft diffused shadows  
- Slight inner glow on hover/press for interactive elements  
- iOS-inspired: rounded corners, smooth transitions, gentle depth  
- Subtle gradient accents — not loud or heavy  
- Breathing room in spacing — minimal but not sparse  
**28.2 Background**  
- Homepage **hero section only**: high-quality Unsplash image of diverse  
   
 students on a campus, slightly blurred, semi-transparent overlay  
   
 for text readability  
- Below hero: clean solid color or very subtle gradient matching theme  
- Rest of app: clean backgrounds — no image behind content pages  
- Glassmorphism cards float over backgrounds for visual depth  
**28.3 Theme**  
- Light and dark mode  
- 🌙 / ☀️ toggle in nav bar  
- System preference on first visit  
- Saved to localStorage  
**28.4 Responsive Breakpoints**  
- Mobile: 360px–480px  
- Tablet: 768px–1024px  
- Desktop: 1280px+  
**28.5 Cross-Platform Testing Priority**  
1. iOS Safari (PWA install + WebSocket behavior)  
2. Android Chrome  
3. Desktop Chrome / Firefox / Edge  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsSfYxZo/kC1sYQLPJrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA4qzBdC53Vr8AAAAAElFTkSuQmCC)  
**29. PWA Requirements**  
**29.1 Purpose**  
FAiND installs on mobile and desktop like a native app.  
**Mobile:** Android Chrome + iOS Safari 16.4+ (PWA must be installed  
   
 for push notifications on iOS).  
**Desktop:** Chrome/Edge install icon in address bar. Creates standalone  
   
 window with taskbar icon. Push notifications work on desktop too.  
**29.2 Requirements**  
- Web app manifest: name, short_name, icons (512px + 192px),  
   
 theme_color, background_color, display: standalone  
- Service worker via vite-plugin-pwa  
- Cache-first strategy for static assets  
- Offline fallback page: cached UI + "You are offline" for dynamic content  
- Push permission requested contextually (see Section 11.3)  
**29.3 Service Worker Scope**  
Caches static assets only. Dynamic data (items, chat) requires  
   
 live connection. Offline fallback shown for dynamic content.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNhQAQ60PcrIhnxgQU2QtIq6DIze3UGAMBf3Gu1VcfXEwAAXrseS14EKxPCORkAAAAASUVORK5CYII=)  
**30. Security Requirements**  
**30.1 Authentication**  
- JWT access tokens: 15-minute lifetime, stored in memory only  
- Refresh tokens: 7-day lifetime, httpOnly cookie  
- Frontend Axios interceptor handles silent refresh (Section 5.4)  
- All non-public routes require valid JWT (verified on backend)  
- Admin routes: valid JWT + correct role  
- Root Admin routes: valid JWT + root_admin role + 2FA TOTP  
**30.2 IDOR Prevention**  
For every resource: verify authenticated user is owner or has explicit  
   
 permission. Scope all queries by object ID + owner/role/university.  
   
 A user can never access another user's resources by ID manipulation.  
**30.3 Input Validation**  
- All request bodies: Pydantic schemas  
- All DB access: SQLAlchemy ORM — no raw SQL ever  
- File type + size: validated server-side (not just frontend)  
**30.4 Sensitive Data**  
- Passwords: bcrypt via passlib  
- Hidden answers: AES-256-GCM encrypted at rest  
- Tip amounts: AES-256-GCM encrypted at rest  
- Decryption: in memory only, never logged  
- No sensitive field in any public API response  
**30.5 Rate Limiting**  
- Login: 5 attempts/minute/IP  
- Email verification: 5 attempts before lockout  
- Verification attempts: 3/user/item/24h (enforced in DB)  
- Path B and C submissions: 3/user/item/24h  
- Item posting: 10/user/day  
- Reports: 1 per user per target (cannot report same post/user twice)  
**30.6 File Upload Safety**  
- Accept only: JPEG, PNG, WEBP  
- Max 5MB per image, enforced backend  
- Cloudinary only — no raw files on application server  
- MIME type validated server-side (not just extension)  
**30.7 API Design**  
- Public and protected routes clearly separated  
- Return 404 instead of 403 when resource existence must not be revealed  
- Never expose stack traces or internal error details in responses  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsScYxpg/i2XMYARvRrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA22YBcnkstSpAAAAAElFTkSuQmCC)  
**31. Technology Stack**  
Fixed. Do not introduce technologies outside this list.  
**31.1 Frontend**  
| | |  
|-|-|  
| **Technology** | **Purpose** |   
| React | UI framework |   
| Vite | Build tool and dev server |   
| Tailwind CSS | Styling |   
| React Router | Client-side routing |   
| TanStack Query | Server state, caching, background refetch |   
| Axios | HTTP client (with refresh interceptor) |   
| vite-plugin-pwa | PWA manifest and service worker |   
| React Hot Toast | Toast notifications |   
   
**31.2 Backend**  
| | |  
|-|-|  
| **Technology** | **Purpose** |   
| FastAPI | API framework |   
| Uvicorn | ASGI server |   
| PostgreSQL | Primary database |   
| SQLAlchemy | ORM — all DB access, no raw SQL |   
| Alembic | Database migrations |   
| Pydantic | Request/response validation |   
| APScheduler | Scheduled background jobs |   
| python-jose | JWT creation and verification |   
| passlib (bcrypt) | Password hashing |   
| pyotp | Root Admin TOTP 2FA |   
| pywebpush | Web Push Notifications |   
| httpx | Async HTTP client |   
| qrcode | QR code generation |   
| cryptography | AES-256-GCM encryption |   
| geopy | Geodesic distance calculation |   
| slowapi | Route-level rate limiting (login, posting, verification, reports) |   
   
**31.3 AI / ML**  
| | |  
|-|-|  
| **Technology** | **Purpose** |   
| sentence-transformers | Semantic embeddings (all-MiniLM-L6-v2) |   
| numpy | Vector math |   
| scikit-learn | Cosine similarity |   
| imagehash | Perceptual image hashing |   
| Pillow | Image processing |   
   
**31.4 Real-Time**  
| | |  
|-|-|  
| **Technology** | **Purpose** |   
| FastAPI WebSockets | Chat, seen receipts, live notifications |   
   
Redis deferred to v2. In-memory management sufficient for v1 at GCTU scale.  
**31.5 Payments**  
| | |  
|-|-|  
| **Technology** | **Purpose** |   
| Paystack | Optional tipping (Ghana, test mode for demo) |   
   
**31.6 Storage**  
| | |  
|-|-|  
| **Technology** | **Purpose** |   
| Cloudinary | Image upload and delivery |   
   
**31.7 Utilities**  
| | |  
|-|-|  
| **Technology** | **Purpose** |   
| FastAPI BackgroundTasks | Trigger matching + notifications on item post |   
| SMTP / fastapi-mail | Email notifications (future) |   
| Docker | Containerization |   
| Git | Version control |   
   
**31.8 Deployment**  
| | |  
|-|-|  
| **Service** | **Purpose** |   
| Vercel | Frontend (free tier) |   
| Render | Backend (free tier) |   
| Supabase | Hosted PostgreSQL (free tier) |   
| Cloudinary | Image hosting (free tier) |   
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNhwgJWEPcbJpnRgQU2QtIq6DIze3UGAMBf3Gu1VcfXEwAAXrseaIkEMIPgIvAAAAAASUVORK5CYII=)  
**32. Code Architecture**  
**32.1 Backend**  
backend/  
   app/  
     api/          # Route handlers by feature module  
     models/       # SQLAlchemy ORM models  
     schemas/      # Pydantic request/response schemas  
     services/     # Business logic (TrustService, MatchingService,  
                   #   NotificationService, ReportService, etc.)  
     utils/        # Encryption, hashing, push, QR, email  
     core/         # Config, DB session, security, APScheduler setup  
   alembic/        # Database migrations  
   seed_admin.py   # One-time root admin seeding — delete after use  
   
**32.2 Frontend**  
frontend/  
   src/  
     components/   # Reusable UI components  
    pages/        # Route-level page components  
     hooks/        # Custom React Query hooks  
     services/     # Axios API functions (includes refresh interceptor)  
     context/      # AuthContext, NotificationContext  
     utils/        # Helpers, formatters  
   
**32.3 Standards**  
- Business logic in services only — route handlers handle request/response  
- All DB: SQLAlchemy ORM, no exceptions  
- All requests: Pydantic schemas  
- No sensitive data in logs  
- Admin-only fields stripped from non-admin responses at schema level  
- Every resource endpoint: IDOR check before any data access  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAM0lEQVR4nO3OUQmAQBBAwSdcjsu6HYxoDsEK/okwk2COmdnVGQAAf3GtalX76wkAAK/dDxFWBDkFf6+SAAAAAElFTkSuQmCC)  
**33. Feature Build Order**  
| | | |  
|-|-|-|  
| **#** | **Feature** | **Key Deliverable** |   
| A | Project Setup + Auth | Register, login, JWT, Axios interceptor, email verification, university + campus zone seed |   
| B | User Profile + Dashboard | Profile page, dashboard shell, settings, theme toggle |   
| C | Lost Item Reporting | Full form, encrypted answers, location dropdown, Cloudinary |   
| D | Found Item Reporting | Full form, required image, Cloudinary |   
| E | Trust System | TrustService, TrustEvent log, tier display, +2 on found post wired — required before any feature that awards or deducts trust points |   
| F | Homepage + Browse Pages | Hero + campus image, two columns, /lost /found pages, filters, FAB |   
| G | AI Matching | Semantic + image + location + date + category scoring, PotentialMatch records, BackgroundTask |   
| H | Notifications + Web Push | In-app bell, pywebpush, contextual permission prompt, civic alerts |   
| I | Ownership Verification (Path A) | Hidden question scoring, thresholds, result screens, 14-day match timeout |   
| J | Path B — I Have This Item | Lightweight form, reverse verification, self-claim prevention |   
| K | Path C — This Might Be Mine | Description-only verification, separate score formula, self-claim prevention |   
| L | Messages Inbox + Chat | WebSocket chat, seen receipts, message inbox, frozen conversation support |   
| M | Return Confirmation | Dual confirm + QR flow, both methods working, trust +5 on return wired |   
| N | Returned Items | Detail page, recently returned section, tipping window, dispute window, tip-freeze logic |   
| O | Fraud Detection | FraudEvent log, risk score, admin alerts, all fraud signals wired |   
| P | Post + User Reporting | Report forms, PostReport + UserReport tables, auto-escalation, admin queue |   
| Q | Tipping | Paystack test mode, webhook verification, visibility rules enforced |   
| R | Admin Dashboard | 2FA login, secret route, all queues, user management, analytics, report queue |   
| S | Post Lifecycle + APScheduler | All scheduled jobs: expiry, reminders, timeouts, tipping/dispute window close, deletion queue |   
| T | Suspension System | Suspend/unsuspend user: item hiding, chat freezing, notifications, restoration |   
| U | PWA Setup | Manifest, service worker, offline fallback, contextual push permission |   
| V | Polish + Deploy | Liquid glass UI, campus hero image, full responsive QA, Render + Vercel + Supabase |   
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OQQmAABRAsSdYxKa/i8WMIR7ECt5E2BJsmZmt2gMA4C+Otbqr8+sJAACvXQ85PAYartXEogAAAABJRU5ErkJggg==)  
**34. Prompting Rule for All Implementation Sessions**  
Every prompt to Claude for implementation must begin with:  
*"Read and follow FAIND_BRAIN_V4.1.md as the single source of truth for*  
 *  
 this project. Implement only the feature requested. Do not modify*  
 *  
 working systems unless instructed. Follow all security, IDOR, trust,*  
 *  
 fraud, verification, lifecycle, interaction map, and role rules*  
 *  
 defined in the document."*  
Claude Opus or Claude Sonnet should be used for implementation.  
   
 This document replaces all previous BRAIN versions entirely.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsScYxpg/h5VMYARvRrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA224BcUMk6pDAAAAAElFTkSuQmCC)  
**35. Final Summary**  
FAiND is a trust-based AI-powered lost and found recovery platform for  
   
 university campuses, initially deployed at GCTU.  
**Core capabilities:**  
- Three verified chat paths (AI Match / I Have This Item / This Might Be Mine)  
- AI matching: semantic text + perceptual image + location + date + category  
- Ownership verification: hidden answers + description + image similarity  
- Path C: description-only verification (no self-answering circular logic)  
- Real-time chat with seen receipts and full messages inbox  
- Returned item lifecycle: tipping window, dispute window, tip-freeze on dispute  
- All pending matches paused when item enters UNDER_DISPUTE  
- POTENTIAL_MATCH expires after 14 days of inactivity  
- Users cannot claim their own items (backend enforced)  
- Suspended users: items hidden, chats frozen, restored on unsuspension  
- Post and user reporting with auto-escalation and admin review queue  
- Web Push Notifications with contextual permission prompting  
- JWT refresh handled silently via Axios interceptor  
- Root Admin: 2FA protected, secret route, 404 for all unauthorized access  
- Trust system with tier-based public display and full audit log  
- Fraud detection with risk scoring, event logging, admin alerting  
- APScheduler for all time-based lifecycle jobs  
- PWA: installable on Android, iOS, desktop  
- Liquid glass / glassmorphism UI, dark/light mode, campus hero image  
- Stack: React + FastAPI + PostgreSQL + sentence-transformers + imagehash + slowapi  
- Deployment: Vercel + Render + Supabase + Cloudinary (all free tiers)  
This document is complete, consistent, and ready for implementation.  
   
 Nothing here should be omitted. When in doubt, re-read before writing code.  
