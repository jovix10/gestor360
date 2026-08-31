# Auth Testing Playbook — Gestor360

## Backend endpoints
- POST /api/auth/register  { name, email, password } → { user, token }
- POST /api/auth/login     { email, password }       → { user, token }
- POST /api/auth/session   { session_id }            → sets session_token cookie
- GET  /api/auth/me                                  → user data
- POST /api/auth/logout                              → clears cookies

## Curl test
```
API=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2)
curl -s "$API/api/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"netozincaovendas@gmail.com","password":"Gestor360!"}'
```

## Emergent Google flow
1. Click "Continuar com Google" → redirects to auth.emergentagent.com
2. After Google auth returns to `/dashboard#session_id=XXX`
3. `AppRouter` detects `session_id` in `useLocation().hash` and renders `AuthCallback`
4. `AuthCallback` POSTs to `/api/auth/session`, backend fetches session-data, stores session_token cookie
5. Redirects to `/dashboard`

## Cookies
- `session_token` (Emergent OAuth) — httpOnly, secure, samesite=none
- `jwt_token` (email/password) — httpOnly, secure, samesite=none
- Frontend also stores JWT in `localStorage.g360_token` and sends as `Authorization: Bearer`
