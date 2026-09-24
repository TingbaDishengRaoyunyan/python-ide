# Multi-user security notes

- Passwords are stored as PBKDF2-SHA256 hashes, never plaintext.
- Sessions are signed and expire after seven days.
- Workspace paths are keyed by a SHA-256 identifier and validated against traversal.
- Each user's `.venv` and files are separate.
- The reserved administrator is `Yun_Yan+baili20130209`.
- Keep `ADMIN_USERNAME_AUTO_PROMOTE=false` in public deployments and bootstrap the administrator privately.

Admin API endpoints:

```text
GET    /api/admin/users
DELETE /api/admin/users/{username}
```

Send the session token in an `Authorization: Bearer <token>` header.
