# Cross-Platform Identity Mapping

When integrating Hermes with MAX Messenger alongside a primary gateway (like Telegram), you must explicitly map user identities in `~/.hermes/.env` to avoid cross-platform permission confusion.

Hermes treats each platform as a separate origin by default. If a user is an Owner in Telegram but interacts via MAX, the bot will not inherently know they are the same person unless their IDs are cleanly managed.

## Required .env Structure

To enforce identity symmetry and maintain clear roles (e.g., Owner for code execution, Admin for no-code tasks), define explicit mapping variables in your `.env`:

```env
# --- USER IDENTIFIERS ---

# Owner (Full access, code execution)
OWNER_TG_ID=1472473612
OWNER_MAX_ID=7445093
_OWNER_MAX_ID=7445093

# Admin (Non-code tasks, e.g., Dasha)
DASHA_TG_ID=755196422
DASHA_MAX_ID=15963859
_ADMIN_MAX_ID=15963859
_ADMIN_MAX_ROLE=admin

# Gateway Allowlist (Must contain all allowed MAX IDs)
MAX_ALLOWED_USERS=7445093,15963859
```

## Why this is critical

1. **Role Enforcement:** The Hermes prompt injects strict rules (e.g., "Dasha cannot request code changes"). By mapping `DASHA_TG_ID` and `DASHA_MAX_ID` explicitly in `.env`, the agent has a source of truth for who is talking, regardless of platform.
2. **Access Control:** The gateway will silently drop MAX messages if the `MAX_ALLOWED_USERS` list does not contain the exact ID.
3. **Debugging:** When looking at `gateway.log`, you will see numeric IDs. Having them mapped cleanly in `.env` makes it immediately obvious who triggered an error.