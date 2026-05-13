---
name: qrypticrox-admin-approval
description: Design spec for QRypticRx registration/identity hardening — admin-approval workflow to prevent unauthorized doctor/pharmacist self-registration
metadata:
  type: project
---

# QRypticRx: Registration / Identity Hardening — Admin Approval Workflow

**Date:** 2026-05-13
**Sub-project:** #1 of 5
**Status:** Approved design, ready for implementation planning

## Background

Currently any visitor can self-register as a doctor or pharmacist without any verification.
A malicious user could create a doctor account to issue fraudulent prescriptions or a pharmacist account to mark prescriptions as dispensed. This spec introduces a mandatory admin-approval gate for all new registrations.

## Goals

- No doctor or pharmacist can log in until an admin explicitly approves their application.
- A single seeded admin account (created via env vars on first boot) is the gatekeeper.
- The registration flow collects enough plausible evidence (license number, affiliation, optional note) for a demo audience to understand the trust model.
- Existing approved users are not affected by the migration.

## Out of Scope

- Real medical-board / government registry integration.
- Email notifications on approval/rejection (deferred to sub-project #2).
- File uploads (license scans, ID documents).
- Account reactivation / re-application after rejection.
- Frontend test coverage (deferred to sub-project #3).
- UI/UX polish (deferred to sub-project #4).

---

## Section 1 — Data Model

### Role extension

The `role` CHECK constraint is extended to include `'admin'`:

```sql
CHECK (role IN ('doctor', 'pharmacist', 'admin'))
```

### New columns on `users`

| Column | Type | Nullable | Purpose |
|---|---|---|---|
| `status` | `VARCHAR(20) NOT NULL DEFAULT 'pending'` | No | `pending` / `approved` / `rejected` |
| `license_number` | `VARCHAR(100)` | Yes | Self-reported; required for doctor and pharmacist roles |
| `affiliation` | `VARCHAR(255)` | Yes | Clinic/hospital name (required for doctors; pharmacists use `pharmacy_name`) |
| `applicant_note` | `TEXT` | Yes | Free-text justification from applicant |
| `rejection_reason` | `TEXT` | Yes | Admin-supplied reason when rejecting |
| `reviewed_by` | `UUID REFERENCES users(id)` | Yes | Which admin approved/rejected; NULL while pending |
| `reviewed_at` | `TIMESTAMPTZ` | Yes | Timestamp of admin decision |

`pharmacy_name` (existing) is retained for pharmacists. Doctors use `affiliation` instead.

### `audit_logs` change

`prescription_id` becomes nullable so non-prescription admin actions (user approvals/rejections) can be recorded.

```sql
ALTER TABLE audit_logs ALTER COLUMN prescription_id DROP NOT NULL;
```

### Migration file

`backend/db/migrations/001_admin_approval.sql` (run against Supabase before deploy).
`backend/db/schema.sql` updated to match for clean installs.

Existing rows are backfilled: `UPDATE users SET status = 'approved' WHERE status = 'pending'`.

### Index

```sql
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
```

---

## Section 2 — Auth Flow & API Changes

### `POST /api/auth/register`

**Request body additions:**
- `license_number` (string, required for `doctor` and `pharmacist`)
- `affiliation` (string, required when `role === 'doctor'`)
- `applicant_note` (string, optional)

**Validation changes:**
- `role === 'admin'` in request body → 400 immediately. Belt-and-suspenders: insert path also hardcodes rejection of admin role.
- Missing `license_number` → 400.
- Doctor missing `affiliation` → 400.
- Pharmacist missing `pharmacy_name` → 400 (existing check retained).

**Behaviour change:**
- Inserts user with `status = 'pending'`.
- Does **not** return a JWT.
- Returns `202 Accepted` with `{ message: "Application submitted. You'll be able to log in once an admin approves your account." }`.
- RSA keypair generation for doctors is **removed from registration** and moved to approval time.

### `POST /api/auth/login`

After password verification succeeds, branch on `status`:

| `status` | Response | Body |
|---|---|---|
| `pending` | 403 | `{ error: "Your account is awaiting admin approval.", status: "pending" }` |
| `rejected` | 403 | `{ error: "Your application was denied.", status: "rejected", reason: "<rejection_reason>" }` |
| `approved` | 200 | Existing JWT flow unchanged |

**Enumeration protection:** On wrong password, the server returns 401 without revealing `status`. The status check only runs after password verification passes.

### New admin endpoints

All require `requireRole('admin')` middleware.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/admin/applications` | List applications. Query param `?status=pending\|approved\|rejected`. Defaults to `pending`. |
| `GET` | `/api/admin/applications/:id` | Full detail of one application. |
| `POST` | `/api/admin/applications/:id/approve` | Approve applicant. Generates RSA keypair for doctors. Sets `status='approved'`, `reviewed_by`, `reviewed_at`. Inserts `audit_logs` row with `action='approved_user'`. Returns 409 if already approved. |
| `POST` | `/api/admin/applications/:id/reject` | Reject applicant. Body: `{ reason: string }` (required — 400 if missing). Sets `status='rejected'`, `rejection_reason`, `reviewed_by`, `reviewed_at`. Inserts `audit_logs` row with `action='rejected_user'`. |

**New files:**
- `backend/routes/admin.js`
- `backend/controllers/adminController.js`

`server.js` mounts: `app.use('/api/admin', adminRoutes)`.

---

## Section 3 — Frontend Changes

### New routes (`App.jsx`)

| Route | Access | Component |
|---|---|---|
| `/register` | Public (updated) | `RegisterPage` |
| `/register/submitted` | Public (new) | `RegisterSubmittedPage` |
| `/login` | Public (updated) | `LoginPage` |
| `/admin` | Admin only | `AdminDashboard` |
| `/admin/applications/:id` | Admin only | `ApplicationDetail` |

### Component changes

**`RegisterPage.jsx`**
- New fields: `license_number` (always), `affiliation` (doctors), `applicant_note` (both). `pharmacy_name` kept for pharmacists.
- On success: `navigate('/register/submitted')`. Do NOT call `login()`.

**`RegisterSubmittedPage.jsx`** (new, ~30 lines)
- Confirmation card: "Application submitted. You'll receive access once an admin reviews it."
- Link back to `/login`.

**`LoginPage.jsx`**
- Parse `status` from 403 responses.
  - `pending`: "Your account is awaiting admin approval."
  - `rejected`: "Your application was denied." + show `reason` if present.

**`AdminDashboard.jsx`** (new)
- Fetches applications (default `pending`).
- Three filterable tabs: Pending / Approved / Rejected.
- Click row → navigate to `ApplicationDetail`.

**`ApplicationDetail.jsx`** (new)
- Displays all submitted fields: name, email, role, license number, affiliation/pharmacy, applicant note.
- Approve button.
- Reject button → opens inline textarea for reason → confirms → submits.
- Shows current status and reviewer info if already decided.

**`ProtectedRoute.jsx`**
- Existing `role` prop mechanism is used; add `<ProtectedRoute role="admin">` wrapping admin routes.

**`AuthContext.jsx`**
- Login redirect extended: `admin` → `/admin`, `doctor` → `/doctor`, `pharmacist` → `/pharmacist`.

### API layer

**`src/api/auth.js`**
- `register()` no longer expects `{ token, user }` — returns `{ message }`.

**`src/api/admin.js`** (new)
- `listApplications(status)`, `getApplication(id)`, `approveApplication(id)`, `rejectApplication(id, reason)`.

### Styling

No new design system. All new pages use existing CSS classes (`card`, `btn`, `badge`, `form-group`, etc.) from `index.css`. Visual polish deferred to sub-project #4.

---

## Section 4 — Env Vars, Config, Deployment

### New backend env vars

| Variable | Required | Purpose |
|---|---|---|
| `ADMIN_EMAIL` | Yes — fail-loud | Email for seeded admin account |
| `ADMIN_PASSWORD` | Yes — fail-loud | Plain password for first-boot seed; bcrypt-hashed in memory before INSERT |

Server refuses to start (same `process.exit(1)` pattern as `FRONTEND_URL`) if either is missing.

### Bootstrap logic (runs before `app.listen`)

1. `SELECT id FROM users WHERE role='admin' LIMIT 1`.
2. If no row: bcrypt-hash `ADMIN_PASSWORD` (cost 12), insert `{ name:'Administrator', email:ADMIN_EMAIL, role:'admin', status:'approved', ... }`. Log `Admin account seeded: <email>`.
3. If row exists: log `Admin account exists: <id>`. Do not overwrite.

### App/server split

`server.js` is split into:
- `app.js` — builds and exports the Express app (required for tests).
- `server.js` — imports `app.js`, calls `listen`, runs bootstrap. Entry point unchanged for Railway.

### Migration & deploy order

1. Run `backend/db/migrations/001_admin_approval.sql` against Supabase.
2. Set `ADMIN_EMAIL` + `ADMIN_PASSWORD` on Railway.
3. Deploy backend. Bootstrap seeds the admin row.
4. Deploy frontend (`npm run deploy --prefix frontend`).
5. Smoke test: log in as admin → admin dashboard loads → register a test doctor → admin approves → doctor logs in.

---

## Section 5 — Testing

Full test framework setup deferred to sub-project #3. This sub-project introduces the minimum needed to cover the security-critical paths.

### Stack

- **Backend only.** Frontend tests deferred to sub-project #3.
- `jest` + `supertest` as dev dependencies.
- Real PostgreSQL via `TEST_DATABASE_URL` env var (same Supabase instance, separate schema or separate DB).
- No mocks. Each test file truncates relevant tables in `beforeEach`.

### Test cases

**Registration**
- Doctor: 202, `status='pending'`, no JWT, keypair NOT generated.
- Pharmacist: 202, `status='pending'`, no JWT.
- `role='admin'` in body → 400.
- Missing `license_number` → 400.
- Doctor missing `affiliation` → 400.
- Pharmacist missing `pharmacy_name` → 400.
- Duplicate email → 409.

**Login gating**
- Pending user correct password → 403, `status: pending`.
- Rejected user correct password → 403, `status: rejected`, reason in body.
- Approved user correct password → 200, JWT.
- Any user wrong password → 401 (no status field — enumeration protection).

**Admin endpoints**
- Non-admin JWT on any `/api/admin/*` → 403.
- No JWT → 401.
- List pending: returns only pending applications.
- Approve doctor: `status='approved'`, `public_key` populated, `reviewed_by`/`reviewed_at` set, audit log inserted.
- Approve pharmacist: same minus `public_key`.
- Approve already-approved → 409.
- Reject without reason → 400.
- Reject with reason: `status='rejected'`, `rejection_reason` set, audit log inserted.

**Bootstrap**
- `seedAdmin()` unit test: no admin row → inserts one; existing admin row → no-op.

### npm scripts

```json
"test":       "jest",
"test:watch": "jest --watch"
```

New dev dependencies: `jest`, `supertest`.

---

## Queued Sub-Projects

| # | Sub-project |
|---|---|
| 2 | Email QR to patient (SMTP/email provider, patient email field on prescriptions) |
| 3 | Full test coverage + CI harness |
| 4 | UI/UX polish |
| 5 | Prescription form redesign: structured X+X+X dosage (morning/afternoon/night), liquid/tablet toggle, counter inputs for each time slot, unit field (drops/mL) for liquids, notes section |
