# Security policy

Qalbu is an experimental portfolio project and does not currently publish a supported production release.

## Reporting

Do not open a public issue containing API keys, personal conversations, database credentials, exploit payloads, or private health information. Contact the repository owner privately through the GitHub profile until a dedicated security contact is published.

## Secret handling

- Keep real credentials only in untracked `.env` files or a deployment secret store.
- Never expose `SUPABASE_SECRET_KEY` or `SUPABASE_SERVICE_ROLE_KEY` to browser code.
- Rotate any credential pasted into chat, logs, screenshots, issues, or commits.
- Review staged changes for tokens before every push.

## Known non-production properties

- Rate limiting and caches are process-local.
- The development Compose file uses a bind mount and auto-reload.
- Corpus licenses and upstream redistribution permissions are not fully verified.
- The configured crisis contact is a release gate and must not be invented.
- The application is not a clinical or emergency-response system.
