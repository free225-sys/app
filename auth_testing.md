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
