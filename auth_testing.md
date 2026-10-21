# Auth testing playbook (CASA AI Academy)

1. MongoDB: `db.users.find({}, {email:1, roles:1, password_hash:1})`. Hashes start with `$2b$`. There is a unique index on users.email and an index on login_attempts.identifier.
2. API:
```
API=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2)/api
curl -s -X POST $API/auth/login -H "Content-Type: application/json" -d '{"email":"apprenant@casa-academy.ci","password":"Apprenant2026!"}'
curl -s $API/auth/me -H "Authorization: Bearer <access_token>"
```
3. Brute force protection: 5 failed logins for the same ip+email trigger a 15-minute lockout (HTTP 429).
4. Register validation: password of at least 8 characters, email must be valid, duplicate email returns 409.

## Roles consolidation 2026-10 (current model)
- Single admin: db.users.find({role:"admin"}) → exactly 1 (admin@casa-academy.com). Index `unique_single_admin` (partial unique on role=admin).
- JWT claims: sub, type, sv, exp. Rejected if sv != users.session_version, account inactive, or role not in {admin, learner}.
- Register always creates role=learner. Admin: 403 on learner writes; admin events not recorded; diagnostic not saved.
- Admin cannot be deactivated/reset via API; recovery: backend/scripts/admin_recover.py. Suite: backend/tests/test_roles_2026_10.py (-n 0).
