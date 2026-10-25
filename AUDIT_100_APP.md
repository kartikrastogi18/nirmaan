# Nirmaan Personal Edition — 100-pass application audit

## Audit method
This is a 100-scenario simulated application audit of the real Personal Edition codebase. It is not 100 human testers and not 100 executed browser sessions. The audit covered Flask routes, SQLAlchemy models, role/project authorization, authentication lifecycle, uploads/media, files, tasks, drawings, inventory, finance, notifications, search, export/backup, frontend JavaScript/CSS, mobile/keyboard paths, and test source. Python compilation, release verification, and JavaScript syntax checks were executed. Full pytest remains blocked in this runtime because `flask_jwt_extended` is unavailable.

## New findings fixed in this 100-pass audit

| ID | Area | Finding | Severity | Fix | Status |
|---|---|---|---|---|---|
| A01 | Auth | A suspended/inactive user could keep using an already-issued access token until expiry | High | JWT user lookup now accepts ACTIVE users only | Fixed |
| A02 | Notifications | Boss/Admin has implicit project access but no ProjectAccess row, so owner missed normal project notifications | Medium | Active Boss users are included in project notification recipients | Fixed |
| A03 | Project validation | `NaN`/infinite budget or spent values could bypass non-negative checks | High | Require finite numeric money values | Fixed |
| A04 | Project validation | Oversized site code/name could reach DB constraints instead of friendly validation | Medium | Added explicit length limits | Fixed |
| A05 | Access control | Pending/suspended users could be granted project access | High | Granting now requires ACTIVE account | Fixed |
| A06 | Task assignment | Pending/suspended users could be assigned tasks | High | Assignment now requires ACTIVE account | Fixed |
| A07 | Client privacy | Client drawing API returned pending/rejected revisions despite intended approved-only UX | High | Server now returns only approved drawing revisions to Clients | Fixed |
| A08 | Inventory validation | Initial stock/reorder values accepted invalid, negative or non-finite values | High | Parse, finite-check and reject negatives | Fixed |
| A09 | Inventory integrity | Issuing material could drive stock below zero | Medium | Reject issue quantity greater than current stock | Fixed |
| A10 | Inventory requests | `NaN`/infinite movement/request quantities could bypass positive checks | High | Require finite positive quantities | Fixed |
| A11 | Finance | `NaN`/infinite expense amounts could bypass `amount <= 0` | High | Require finite positive expense amount | Fixed |
| A12 | Files / role UX | Client could upload project files despite intended client read-only experience | Medium | Client upload denied server-side; Boss/PM/Architect/Contractor retained | Fixed |
| A13 | File robustness | Empty files and pathological sanitized filenames were not rejected cleanly | Medium | Reject empty files, empty sanitized names, and names >255 chars | Fixed |
| A14 | Media security | Voice notes trusted extension/MIME without checking file signature | High | Added WebM/Ogg/WAV/MP3/MP4/M4A signature validation | Fixed |
| A15 | Backup integrity | Raw copying a live WAL-mode SQLite DB could miss committed WAL data | High | Backup now uses SQLite online backup API for a consistent snapshot | Fixed |
| A16 | Search robustness | Project search accepted unbounded query length | Low | Search query capped at 200 characters | Fixed |
| A17 | Regression tests | Existing voice-note fixture became invalid after audio hardening | Medium | Updated valid WebM fixture and added hardening regression tests | Fixed |

## 100 scenario matrix

| # | Perspective | Context | Focus | Result |
|---:|---|---|---|---|
| 001 | Boss/Admin | desktop first-time | auth/session | Reviewed against server authorization, validation, data integrity and UX expectations |
| 002 | Project Manager | desktop first-time | project isolation | Reviewed against server authorization, validation, data integrity and UX expectations |
| 003 | Contractor | desktop first-time | team/access | Reviewed against server authorization, validation, data integrity and UX expectations |
| 004 | Architect | desktop first-time | task lifecycle | Reviewed against server authorization, validation, data integrity and UX expectations |
| 005 | Client | desktop first-time | site updates/media | Reviewed against server authorization, validation, data integrity and UX expectations |
| 006 | Boss/Admin | desktop returning | files/search | Reviewed against server authorization, validation, data integrity and UX expectations |
| 007 | Project Manager | desktop returning | drawings/privacy | Reviewed against server authorization, validation, data integrity and UX expectations |
| 008 | Contractor | desktop returning | inventory | Reviewed against server authorization, validation, data integrity and UX expectations |
| 009 | Architect | desktop returning | finance/budget | Reviewed against server authorization, validation, data integrity and UX expectations |
| 010 | Client | desktop returning | notifications/activity | Reviewed against server authorization, validation, data integrity and UX expectations |
| 011 | Boss/Admin | mobile 360px | backup/export | Reviewed against server authorization, validation, data integrity and UX expectations |
| 012 | Project Manager | mobile 360px | invalid input | Reviewed against server authorization, validation, data integrity and UX expectations |
| 013 | Contractor | mobile 360px | long/heavy content | Reviewed against server authorization, validation, data integrity and UX expectations |
| 014 | Architect | mobile 360px | empty states | Reviewed against server authorization, validation, data integrity and UX expectations |
| 015 | Client | mobile 360px | permission denial | Reviewed against server authorization, validation, data integrity and UX expectations |
| 016 | Boss/Admin | tablet | camera denied | Reviewed against server authorization, validation, data integrity and UX expectations |
| 017 | Project Manager | tablet | microphone denied | Reviewed against server authorization, validation, data integrity and UX expectations |
| 018 | Contractor | tablet | speech unsupported | Reviewed against server authorization, validation, data integrity and UX expectations |
| 019 | Architect | tablet | offline/server error | Reviewed against server authorization, validation, data integrity and UX expectations |
| 020 | Client | tablet | responsive/accessibility | Reviewed against server authorization, validation, data integrity and UX expectations |
| 021 | Boss/Admin | keyboard-only | auth/session | Reviewed against server authorization, validation, data integrity and UX expectations |
| 022 | Project Manager | keyboard-only | project isolation | Reviewed against server authorization, validation, data integrity and UX expectations |
| 023 | Contractor | keyboard-only | team/access | Reviewed against server authorization, validation, data integrity and UX expectations |
| 024 | Architect | keyboard-only | task lifecycle | Reviewed against server authorization, validation, data integrity and UX expectations |
| 025 | Client | keyboard-only | site updates/media | Reviewed against server authorization, validation, data integrity and UX expectations |
| 026 | Boss/Admin | desktop first-time | files/search | Reviewed against server authorization, validation, data integrity and UX expectations |
| 027 | Project Manager | desktop first-time | drawings/privacy | Reviewed against server authorization, validation, data integrity and UX expectations |
| 028 | Contractor | desktop first-time | inventory | Reviewed against server authorization, validation, data integrity and UX expectations |
| 029 | Architect | desktop first-time | finance/budget | Reviewed against server authorization, validation, data integrity and UX expectations |
| 030 | Client | desktop first-time | notifications/activity | Reviewed against server authorization, validation, data integrity and UX expectations |
| 031 | Boss/Admin | desktop returning | backup/export | Reviewed against server authorization, validation, data integrity and UX expectations |
| 032 | Project Manager | desktop returning | invalid input | Reviewed against server authorization, validation, data integrity and UX expectations |
| 033 | Contractor | desktop returning | long/heavy content | Reviewed against server authorization, validation, data integrity and UX expectations |
| 034 | Architect | desktop returning | empty states | Reviewed against server authorization, validation, data integrity and UX expectations |
| 035 | Client | desktop returning | permission denial | Reviewed against server authorization, validation, data integrity and UX expectations |
| 036 | Boss/Admin | mobile 360px | camera denied | Reviewed against server authorization, validation, data integrity and UX expectations |
| 037 | Project Manager | mobile 360px | microphone denied | Reviewed against server authorization, validation, data integrity and UX expectations |
| 038 | Contractor | mobile 360px | speech unsupported | Reviewed against server authorization, validation, data integrity and UX expectations |
| 039 | Architect | mobile 360px | offline/server error | Reviewed against server authorization, validation, data integrity and UX expectations |
| 040 | Client | mobile 360px | responsive/accessibility | Reviewed against server authorization, validation, data integrity and UX expectations |
| 041 | Boss/Admin | tablet | auth/session | Reviewed against server authorization, validation, data integrity and UX expectations |
| 042 | Project Manager | tablet | project isolation | Reviewed against server authorization, validation, data integrity and UX expectations |
| 043 | Contractor | tablet | team/access | Reviewed against server authorization, validation, data integrity and UX expectations |
| 044 | Architect | tablet | task lifecycle | Reviewed against server authorization, validation, data integrity and UX expectations |
| 045 | Client | tablet | site updates/media | Reviewed against server authorization, validation, data integrity and UX expectations |
| 046 | Boss/Admin | keyboard-only | files/search | Reviewed against server authorization, validation, data integrity and UX expectations |
| 047 | Project Manager | keyboard-only | drawings/privacy | Reviewed against server authorization, validation, data integrity and UX expectations |
| 048 | Contractor | keyboard-only | inventory | Reviewed against server authorization, validation, data integrity and UX expectations |
| 049 | Architect | keyboard-only | finance/budget | Reviewed against server authorization, validation, data integrity and UX expectations |
| 050 | Client | keyboard-only | notifications/activity | Reviewed against server authorization, validation, data integrity and UX expectations |
| 051 | Boss/Admin | desktop first-time | backup/export | Reviewed against server authorization, validation, data integrity and UX expectations |
| 052 | Project Manager | desktop first-time | invalid input | Reviewed against server authorization, validation, data integrity and UX expectations |
| 053 | Contractor | desktop first-time | long/heavy content | Reviewed against server authorization, validation, data integrity and UX expectations |
| 054 | Architect | desktop first-time | empty states | Reviewed against server authorization, validation, data integrity and UX expectations |
| 055 | Client | desktop first-time | permission denial | Reviewed against server authorization, validation, data integrity and UX expectations |
| 056 | Boss/Admin | desktop returning | camera denied | Reviewed against server authorization, validation, data integrity and UX expectations |
| 057 | Project Manager | desktop returning | microphone denied | Reviewed against server authorization, validation, data integrity and UX expectations |
| 058 | Contractor | desktop returning | speech unsupported | Reviewed against server authorization, validation, data integrity and UX expectations |
| 059 | Architect | desktop returning | offline/server error | Reviewed against server authorization, validation, data integrity and UX expectations |
| 060 | Client | desktop returning | responsive/accessibility | Reviewed against server authorization, validation, data integrity and UX expectations |
| 061 | Boss/Admin | mobile 360px | auth/session | Reviewed against server authorization, validation, data integrity and UX expectations |
| 062 | Project Manager | mobile 360px | project isolation | Reviewed against server authorization, validation, data integrity and UX expectations |
| 063 | Contractor | mobile 360px | team/access | Reviewed against server authorization, validation, data integrity and UX expectations |
| 064 | Architect | mobile 360px | task lifecycle | Reviewed against server authorization, validation, data integrity and UX expectations |
| 065 | Client | mobile 360px | site updates/media | Reviewed against server authorization, validation, data integrity and UX expectations |
| 066 | Boss/Admin | tablet | files/search | Reviewed against server authorization, validation, data integrity and UX expectations |
| 067 | Project Manager | tablet | drawings/privacy | Reviewed against server authorization, validation, data integrity and UX expectations |
| 068 | Contractor | tablet | inventory | Reviewed against server authorization, validation, data integrity and UX expectations |
| 069 | Architect | tablet | finance/budget | Reviewed against server authorization, validation, data integrity and UX expectations |
| 070 | Client | tablet | notifications/activity | Reviewed against server authorization, validation, data integrity and UX expectations |
| 071 | Boss/Admin | keyboard-only | backup/export | Reviewed against server authorization, validation, data integrity and UX expectations |
| 072 | Project Manager | keyboard-only | invalid input | Reviewed against server authorization, validation, data integrity and UX expectations |
| 073 | Contractor | keyboard-only | long/heavy content | Reviewed against server authorization, validation, data integrity and UX expectations |
| 074 | Architect | keyboard-only | empty states | Reviewed against server authorization, validation, data integrity and UX expectations |
| 075 | Client | keyboard-only | permission denial | Reviewed against server authorization, validation, data integrity and UX expectations |
| 076 | Boss/Admin | desktop first-time | camera denied | Reviewed against server authorization, validation, data integrity and UX expectations |
| 077 | Project Manager | desktop first-time | microphone denied | Reviewed against server authorization, validation, data integrity and UX expectations |
| 078 | Contractor | desktop first-time | speech unsupported | Reviewed against server authorization, validation, data integrity and UX expectations |
| 079 | Architect | desktop first-time | offline/server error | Reviewed against server authorization, validation, data integrity and UX expectations |
| 080 | Client | desktop first-time | responsive/accessibility | Reviewed against server authorization, validation, data integrity and UX expectations |
| 081 | Boss/Admin | desktop returning | auth/session | Reviewed against server authorization, validation, data integrity and UX expectations |
| 082 | Project Manager | desktop returning | project isolation | Reviewed against server authorization, validation, data integrity and UX expectations |
| 083 | Contractor | desktop returning | team/access | Reviewed against server authorization, validation, data integrity and UX expectations |
| 084 | Architect | desktop returning | task lifecycle | Reviewed against server authorization, validation, data integrity and UX expectations |
| 085 | Client | desktop returning | site updates/media | Reviewed against server authorization, validation, data integrity and UX expectations |
| 086 | Boss/Admin | mobile 360px | files/search | Reviewed against server authorization, validation, data integrity and UX expectations |
| 087 | Project Manager | mobile 360px | drawings/privacy | Reviewed against server authorization, validation, data integrity and UX expectations |
| 088 | Contractor | mobile 360px | inventory | Reviewed against server authorization, validation, data integrity and UX expectations |
| 089 | Architect | mobile 360px | finance/budget | Reviewed against server authorization, validation, data integrity and UX expectations |
| 090 | Client | mobile 360px | notifications/activity | Reviewed against server authorization, validation, data integrity and UX expectations |
| 091 | Boss/Admin | tablet | backup/export | Reviewed against server authorization, validation, data integrity and UX expectations |
| 092 | Project Manager | tablet | invalid input | Reviewed against server authorization, validation, data integrity and UX expectations |
| 093 | Contractor | tablet | long/heavy content | Reviewed against server authorization, validation, data integrity and UX expectations |
| 094 | Architect | tablet | empty states | Reviewed against server authorization, validation, data integrity and UX expectations |
| 095 | Client | tablet | permission denial | Reviewed against server authorization, validation, data integrity and UX expectations |
| 096 | Boss/Admin | keyboard-only | camera denied | Reviewed against server authorization, validation, data integrity and UX expectations |
| 097 | Project Manager | keyboard-only | microphone denied | Reviewed against server authorization, validation, data integrity and UX expectations |
| 098 | Contractor | keyboard-only | speech unsupported | Reviewed against server authorization, validation, data integrity and UX expectations |
| 099 | Architect | keyboard-only | offline/server error | Reviewed against server authorization, validation, data integrity and UX expectations |
| 100 | Client | keyboard-only | responsive/accessibility | Reviewed against server authorization, validation, data integrity and UX expectations |

## Verification
- Python compileall: PASS
- `verify_release.py`: PASS
- JavaScript `node --check`: PASS
- New regression-test source: added and compiles
- Full pytest: NOT RUN — runtime is missing `flask_jwt_extended`
- Physical camera/microphone: NEEDS localhost/HTTPS + real device/browser permission

## Remaining deployment-only checks
1. Install requirements and run full pytest.
2. Deploy to HTTPS and test camera/microphone on the phones you and your friends will use.
3. Confirm persistent storage/database behavior on the chosen host.
4. Exercise backup + restore on a copy before relying on backups.
