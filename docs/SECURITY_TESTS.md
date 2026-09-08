# Authentication and account-isolation tests

The security workflow runs on every push and pull request. It installs the
isolated backend dependencies and uploads a JUnit report, without repository
secrets, an external database, or paid API calls.

## Run locally (Python 3.12)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-security.txt
python -m pytest tests -q
```

The tests assemble the **production auth and settings routers** in a small
FastAPI application. They replace only the database dependency with a fresh
SQLite database for each test. Authentication, password hashing, JWT validation,
HTTP validation, SQLAlchemy queries, and persistence remain real. All identities
and passwords in the suite are fictional. Test configuration overrides any local
database URL and key before application imports.

## Covered behavior

- Register and log in, verify password hashing, and return only public user fields.
- Reject absent/malformed credentials, bad signatures, unsupported signing
  algorithms, expired tokens, and tokens missing expiry or subject claims.
- Enforce the configured issuer and audience.
- Issue tokens with the default 30-minute lifetime or an explicit lifetime.
- Reject deleted users, and prevent inactive users from logging in or using
  previously issued tokens.
- Read and update settings using the token's owner; another user's settings
  remain unchanged in both the database and API response.
- Reject `user_id` injected in PUT/PATCH bodies, reject unauthenticated settings
  access, and return 422 for invalid input instead of a server error.

## Configuration and compatibility

Set `SECRET_KEY` to a fresh, randomly generated secret of at least 32 characters.
There is no fallback signing key. Generate one locally with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set `ACCESS_TOKEN_EXPIRE_MINUTES` to a positive integer (default: `30`).
`JWT_ISS` and `JWT_AUD` default to `jip-api` and `jip-clients`.
The API refuses to initialize with a missing/short key or nonpositive lifetime.
Existing permanent tokens are intentionally rejected: users must log in again.
There is no refresh-token flow; sign in again after expiry. The frontend has not
been changed by this security update.

## Scope

This is focused regression coverage, not a claim that the whole application is
production-ready. It does not start `app.main` (which initializes external
providers), exercise every content/history route, audit all authorization paths,
validate PostgreSQL-specific behavior, or cover browser/session UX. The original
hosted service remains inactive. Review the remaining routes and integrations
before publishing a multiuser deployment.
