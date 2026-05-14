# Deployment & Operational Notes

- **Gateway Service:** The MAX webhook integration runs via the standard Hermes gateway (`python -m hermes_cli.main gateway run --replace`). For production, this must be managed via a `systemd` service (e.g., `hermes-gateway.service`) for automatic restarts on failure.
- **Restarting & Pitfalls:** Do NOT restart the `hermes-gateway` service blindly to apply patches or test code. Doing so drops the active Telegram session polling, disconnecting the agent from the user mid-dialogue. 
- **User Preference (Restarts):** If a restart is absolutely required after code changes, inform the Owner (Sergey) and wait for his signal. He prefers to restart the entire server manually to ensure dialogue consistency isn't broken unexpectedly.
- **Post-Integration Cleanup:** After testing webhooks, APIs, or integrations, aggressively find and remove temporary mock/test scripts (e.g., `test_max*.py`, `patch_*.py`) from `/root/` to keep the environment perfectly clean.