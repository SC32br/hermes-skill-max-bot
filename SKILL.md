---
name: max-messenger-integration
description: "MAX messenger (max.ru) API integration, debugging, and platform constraints. Covers long polling limits, callback answering, and legal entity shadowbanning."
tags: [max, max.ru, messenger, bot, api, shadowban]
---

# MAX Messenger API Integration & Debugging

**🚀 Out-of-the-Box Solution:** The battle-tested Hermes plugin for MAX (with media routing, local STT via `faster-whisper`, and role constraints) has been packaged into a public repository. For new setups, use this instead of building from scratch:
```bash
git clone https://github.com/SC32br/hermes-skill-max-bot.git
cd hermes-skill-max-bot && bash install.sh
```

This skill covers the hard constraints and undocumented quirks of the MAX messenger API (platform-api.max.ru), specifically for bot developers and OpenClaw plugin integrations.

**Architectural Equivalence:** The MAX and Telegram bots are identical interfaces to the unified Hermes core. All skills, roles (e.g. Owner for code, Admin for no-code), and subagents apply globally across both messengers. Do NOT treat MAX as a separate bot with separate plans, skills, or logic. The user can interact with either messenger interchangeably to execute any task.

## Core API Quirks & Formats

- **Hermes Gateway Buttons:** Read `references/gateway_approvals.md` for the exact requirements to implement interactive keyboards (e.g., `{"type": "callback"}`) and how to wire `send_exec_approval` to avoid silent text fallbacks.


1. **Long Polling Limits (`GET /updates`) vs Webhooks**
   - **CRITICAL UPDATE (May 2026):** MAX platform imposes severe restrictions on Long Polling (max 2 RPS, 30s timeout, max 100 events, 24h TTL).
   - **Mandate:** DO NOT use Long Polling for production. You MUST use Webhooks (`POST /subscriptions`).
   - **Webhook Registration:** To receive updates, the bot must register its webhook URL explicitly via `POST https://platform-api.max.ru/subscriptions` with payload `{"url": "https://YOUR_DOMAIN/max-webhook", "update_types": ["message_created", "message_callback"]}`.
   - **Caddy Pitfall:** If the server uses `basic_auth` (e.g., for Hermes Web UI), the `/max-webhook` endpoint MUST be explicitly excluded in the `Caddyfile` so MAX servers can post without a password:
     ```caddyfile
     handle /max-webhook* {
         reverse_proxy 127.0.0.1:8080
     }
     handle {
         basic_auth bcrypt { ... }
         reverse_proxy 127.0.0.1:9119
     }
     ```
   - **Verification:** See `references/webhook-caddy-verification.md` for a 3-step checklist to verify the webhook chain locally via logs, curl, and Caddyfile.

2. **Button Formatting (Inline Keyboard)**
   - The platform strictly requires the `type` field on *every* button object inside `attachments[].payload.buttons[row][btn]`.
   - Callbacks: `{"type": "callback", "text": "Label", "payload": "cb_data"}` (Unlike Telegram which uses `callback_data`).
   - Links: `{"type": "link", "text": "Label", "url": "https://..."}`.
   - Without the `type` field, the API immediately throws `400 {"code":"proto.payload","message":"Can't deserialize body"}`.

2. **Handling Callbacks (`message_callback`)**
   - When a user clicks an inline keyboard, MAX sends a `message_callback` event. The incoming webhook payload structure is: `{"update_type": "message_callback", "callback": {"callback_id": "...", "payload": "...", "user": {"user_id": "..."}}}`.
   - **CRITICAL:** You *must* acknowledge this by calling `POST /answers` with the `callback_id`. 
   - If left unanswered, the bot's event queue will hang permanently, and it will stop receiving all messages.

3. **Platform Shadowbanning (Legal Entity Requirement)**
   - **Symptom:** The bot authenticates perfectly (`GET /me` returns the bot profile). However, `GET /updates` remains completely empty even when real users send messages to the bot. Attempting to send an outbound message to a user ID yields `{"code":"chat.not.found","message":"Chat <ID> not found"}`.
   - **Root Cause:** MAX (owned by VK/Mail.ru) enforce a strict business verification policy. Bots not linked to a verified Russian legal entity (ИП, ООО) are effectively shadowbanned. They exist, they get tokens, but message routing is disabled at the platform level.
   - **Fix:** There is no code workaround. The account owner must verify their business status in the MAX developer portal.

4. **Sending Messages (`POST /messages`) & Authorization Headers**
   - **Symptom 1 ("Unknown Recipient"):** API returns `{"code":"proto.payload","message":"Unknown recipient"}` when trying to send a message.
     - **Root Cause:** Attempting to pass the recipient ID inside the JSON body (e.g., `{"recipient": {"id": "..."}}` or `{"chat_id": "..."}`). MAX API strictly requires the target ID to be passed as a URL query parameter.
     - **Fix:** Append `?user_id=<ID>` or `?chat_id=<ID>` to the URL. Example: `POST https://platform-api.max.ru/messages?user_id=7445093`, keeping the JSON body focused only on `text` and `attachments`.
   - **Symptom 2 ("No access token"):** API returns `{"code":"verify.token","message":"No access token"}` despite the token being valid.
     - **Root Cause:** Sending the token as `Authorization: Bearer <token>`. The MAX API strictly expects just the raw token string.
     - **Fix:** Pass the raw token directly in the header: `Authorization: <token>`.

5. **Inline Keyboards (`400 Can't deserialize body`)**
   - **Symptom:** Sending a message with `attachments` containing an `inline_keyboard` returns `400 {"code":"proto.payload","message":"Can't deserialize body"}`.
   - **Root Cause:** The API strictly requires the button object to explicitly include `"type": "callback"` (or other valid types like `"url"`). Omitting the `type` or using Telegram-style `callback_data` fails validation.
   - **Fix:** Ensure the button payload structure exactly matches:
     ```json
     "attachments": [{
         "type": "inline_keyboard",
         "payload": {
             "buttons": [[
                 {"type": "callback", "text": "Button Label", "payload": "callback_data_here"}
             ]]
         }
     }]
     ```

6. **Typing Indicators & Read Receipts (`/chats/{chat_id}/actions`)**
   - **Symptom:** Attempts to send typing indicators to `/actions` or `/messages/read` return 404 or 400.
   - **Fix:** Use the specific chat actions endpoint: `POST https://platform-api.max.ru/chats/{chat_id}/actions`.
   - **Payloads:** `{"action": "typing_on"}` (for typing indicator) and `{"action": "mark_seen"}` (to clear unread badges). Do not use `"typing"`, `"read"`, or nested objects.

- **Voice & Media Attachments (Images, Videos, Docs)**
   - **Upload Process:** See `references/max_upload_quirks.md` for the 3-step upload mechanism (`/uploads`, multipart, and token attachment).
   - **Inbound Format:** MAX sends attachments as an array inside the `message_created` event: `attachments: [{"type": "audio", "payload": {"url": "http..."}}]`
   - **Outbound Media & Files (Native Support):** The MAX platform adapter natively supports `media_paths` (via `MEDIA:<path>` in the chat tool, or directly via gateway). 
   - **Upload Mechanics & Quirks:** MAX uses a 3-step upload process (`POST /uploads?type=...` -> Multipart upload to signed URL -> Receive `token` -> Send in `attachments` payload). 
   - **The `attachment.not.ready` Pitfall:** MAX's processing is asynchronous. If you send the message immediately after uploading a file/video/image, the API often returns `400 {"code": "attachment.not.ready"}`. The Hermes adapter automatically intercepts this code, sleeps for 1-5 seconds, and retries the send up to 5 times. Do not be alarmed by temporary delay.
   - **Types Mapping:**
     - `audio` / `voice` -> `MessageType.VOICE`
     - `image` / `photo` / `picture` -> `MessageType.PHOTO`
     - `video` -> `MessageType.VIDEO`
     - `file` / `document` -> `MessageType.DOCUMENT`
   - **Integration (CRITICAL TYPO WARNING):** Hermes gateway expects local file paths for media. The adapter must intercept the URL, download the file locally (e.g., using `urllib.request`), and pass it to the event object.
     **CRITICAL:** Pass the local paths to the `media_urls` parameter, *not* `media_paths`. 
     Correct: `MessageEvent(message_type=MessageType.VOICE, media_urls=[local_path])`
     Incorrect: `MessageEvent(..., media_paths=[local_path])` (Will crash the gateway with `unexpected keyword argument`).
   - **Local STT Dependency (faster-whisper):** If you successfully pass the audio to the gateway, but the bot responds "I received a voice message but can't listen to it", the Hermes core might be missing the `faster-whisper` dependency in its virtual environment. Check `~/.hermes/logs/agent.log` for `STT provider 'local' configured but unavailable`. Fix: `~/.hermes/hermes-agent/venv/bin/pip install faster-whisper`.

6. **Chat Actions (Typing Indicators & Read Receipts)**
   - The MAX API for chat actions is undocumented. Do not try to use `/messages/read` or `/actions` directly.
   - **Typing Indicator:** `POST https://platform-api.max.ru/chats/<chat_id>/actions` with payload `{"action": "typing_on"}`.
   - **Mark as Read:** `POST https://platform-api.max.ru/chats/<chat_id>/actions` with payload `{"action": "mark_seen"}`.
   - **Gateway Integration:** To support Hermes' built-in typing indicators, implement `async def send_typing(self, chat_id: str, metadata=None) -> None` in your adapter. The Hermes core loops will automatically invoke it while the agent is processing.

## Environment & Gateway Configuration

- **Terminal Approval UI (Native Inline Keyboards):** The Hermes core relies on `send_exec_approval` and `send_slash_confirm` for terminal tool and slash command approvals. Because MAX Messenger requires strict types (`"type": "callback"`) and drops generic Telegram-style keyboards, you MUST override these two methods in your `MaxAdapter`. Provide MAX-compliant inline keyboards (e.g., `{"type": "callback", "text": "✅ Один раз", "payload": f"app:once:{approval_id}"}`). Then, in your `message_callback` handler, intercept `app:` and `sc:` payloads, retrieve the `session_key` from state, and explicitly unblock the agent using `from tools.approval import resolve_gateway_approval; resolve_gateway_approval(session_key, action)`.
  **Pitfall (UnboundLocalError):** Do not write `import asyncio` or `import requests` inline within your webhook handler block just for these callback dispatches. Doing so shadows the variables at compile time for the entire function, causing `UnboundLocalError: cannot access local variable 'asyncio'` when `asyncio.create_task` is called elsewhere in the same function. Always put `import asyncio` at the top of `adapter.py`.
  **Pitfall (Gateway Core Null `_status_adapter`):** When intercepting interactive button callbacks, be aware of session state drops. If the gateway attempts to trigger an approval (which invokes `_status_adapter.pause_typing_for_chat()`) but the session has split or reconnected, `_status_adapter` might be `None`, causing `AttributeError: 'NoneType' object has no attribute 'pause_typing_for_chat'` in `gateway/run.py`. Always ensure the core gateway checks `if _status_adapter:` before invoking UI state methods.
- **Identity Mapping & Cross-Platform Symmetry:** When running MAX alongside Telegram, explicitly define who is who in `~/.hermes/.env` (e.g., `OWNER_TG_ID`, `OWNER_MAX_ID`, `DASHA_TG_ID`, `DASHA_MAX_ID`). This prevents role confusion (e.g., Owner vs Admin) across platforms. See `references/id-mapping-gotchas.md` for the exact required structure.
- **Webhooks vs Reverse Proxies:** If Hermes runs behind a reverse proxy with Basic Auth (e.g., Caddy), MAX webhooks will silently fail because MAX's servers cannot pass the Basic Auth challenge. In such setups, the platform adapter must be written to use Long Polling (`GET /updates`) to completely bypass inbound proxy restrictions.
- **Config Stripping & Environment Variables (The "No token configured" Pitfall):** The core Hermes gateway (`gateway/config.py`) strips non-standard keys from the top-level platform block in `config.yaml`. If your `config.yaml` has `max:\n  token: ${MAX_TOKEN}`, the gateway will discard it because `max` is a third-party plugin, not a built-in. Therefore, `config.get("token")` inside your plugin's `__init__` will be `None`. 
  **Fix:** Your plugin MUST explicitly read the environment variable as a fallback: `self.token = options.get("token") or conf_dict.get("token") or os.environ.get("MAX_TOKEN")`.
  **Double-Check:** If running as a systemd service, verify that `EnvironmentFile=/root/.hermes/.env` is present in the `[Service]` section of `hermes-gateway.service`, otherwise `os.environ.get("MAX_TOKEN")` will also fail silently in production.

## Gateway Plugin Troubleshooting & Lifecycle Constraints

- **Silent Message Drops (Unauthorized User):**
  - **Symptom:** Webhooks arrive successfully, but the bot ignores messages. `gateway.log` shows `WARNING gateway.run: Unauthorized user: <ID> on max`.
  - **Root Cause:** The Hermes gateway security model safely defaults to denying all inbound messages if a platform doesn't explicitly declare its allowlist environment variables.
  - **Fix:** In the plugin's `register(ctx)` function, explicitly provide the auth kwargs: `ctx.register_platform("max", "MAX Messenger", MaxAdapter, lambda config=None: True, allowed_users_env="MAX_ALLOWED_USERS", allow_all_env="MAX_ALLOW_ALL_USERS")`. Ensure the variables are actually set in `~/.hermes/.env`.
- **Platform Enum Initialization (`AttributeError: 'str' object has no attribute 'value'`):**
  - **Symptom:** Webhook receives updates (200 OK), but messages never reach the agent. `errors.log` shows `AttributeError: 'str' object has no attribute 'value'` inside `_process_update_async` or `build_session_key`.
  - **Root Cause:** In the adapter's `__init__`, calling `super().__init__(config, "max")` with a raw string causes the gateway's session router (`build_session_key`) to crash when it attempts to read `source.platform.value`.
  - **Fix:** You MUST pass an Enum object, not a string, to the base class. Define a custom Enum in the adapter:
    ```python
    from enum import Enum
    class MaxPlatform(Enum):
        MAX = "max"

    class MaxAdapter(BasePlatformAdapter):
        def __init__(self, config):
            super().__init__(config, MaxPlatform.MAX)
    ```
- **PlatformConfig Initialization (`AttributeError`):** In recent Hermes versions, the `config` parameter passed to an adapter's `__init__(self, config)` is a Pydantic `PlatformConfig` object, not a standard dictionary. Calling `config.get("token")` will crash the gateway during startup with `AttributeError: 'PlatformConfig' object has no attribute 'get'`. Update custom plugins to safely extract values using `isinstance(config, dict)` to toggle logic, or dump Pydantic objects first: `conf_dict = config if isinstance(config, dict) else (config.model_dump() if hasattr(config, "model_dump") else (config.dict() if hasattr(config, "dict") else vars(config)))`.
- **Silent Failures / Missing Updates:** If the bot can send messages via `curl` but receives nothing in the gateway, check `journalctl -u hermes-gateway`.
- **Abstract Method Errors:** The Hermes `BasePlatformAdapter` interface requires strict implementations for its abstract methods (`async def connect`, `async def disconnect`, `async def send`, `async def get_chat_info`). If a custom plugin (like `max_messenger/adapter.py`) misses an implementation entirely or uses a synchronous `def`, the gateway will fail to instantiate the adapter with a `TypeError: Can't instantiate abstract class`, dropping all incoming platform messages.
- **Plugin Discovery & Structure Constraints (NO BLIND WORKAROUNDS):** If a custom platform plugin (like `max_messenger`) is placed in `~/.hermes/plugins/` but the gateway ignores it, **DO NOT copy files to other directories (e.g. `/home/hermes-agent/`) as a blind workaround.** The Hermes plugin engine strictly requires the manifest to be named exactly `plugin.yaml` (lowercase, `PLUGIN.yaml` is silently ignored) and requires an `__init__.py` file. Fix the directory structure to resolve the root cause. Debug plugin discovery drops with: `python3 -c "import logging; logging.basicConfig(level=logging.DEBUG); from gateway.config import load_gateway_config; print('Connected:', [p.value for p in load_gateway_config().get_connected_platforms()])"`
- **Gateway Plugin Compatibility (v2 Events):** The `MessageEvent` structure now requires a nested `SessionSource` object instead of flat properties like `user_id` and `display_name`.
  ```python
  from gateway.platforms.base import SessionSource, MessageEvent, MessageType
  source = SessionSource(platform=self.platform, chat_id=user_id, user_id=user_id, user_name=username, chat_name=display_name)
  event = MessageEvent(text=text, source=source, message_id=msg_id, message_type=MessageType.TEXT)
  await self.handle_message(event) # MUST be awaited
  ```
- **Abstract Method Compliance:** Base classes require specific signatures. Example: `async def send(self, chat_id: str, text: str, **kwargs) -> SendResult:`, not `send_message`. All incoming/outgoing handlers must use non-blocking IO (e.g., `await asyncio.to_thread(requests.post, ...)`).
- **Plugin Discovery Failures (Silent Fallbacks):** The Hermes plugin loader strictly requires `plugin.yaml` (lowercase) and an `__init__.py` exposing `register(ctx)`. If you name it `PLUGIN.yaml` or forget `__init__.py`, the loader silently ignores the `/root/.hermes/plugins/<name>/` directory. If an older version exists in the bundled dir (`/home/hermes-agent/plugins/`), the gateway will load that instead, leading to confusing "missing method" errors despite recent edits in your user dir.
- **USER PREFERENCE - Root Cause over Band-Aids:** When a plugin fails to load or an old version runs, *do not* blindly copy files between directories (e.g., copying from `~/.hermes/` to `/home/hermes-agent/`) to force it to work. The user explicitly hates careless "write-then-copy-then-rewrite" band-aids. Stop, enable debug logging for plugin discovery (`python3 -c "import logging; logging.basicConfig(level=logging.DEBUG); from gateway.config import load_gateway_config; load_gateway_config().get_connected_platforms()"`), find the real root cause (e.g., missing init, bad manifest name), and fix it properly.
- **CRITICAL WORKFLOW PITFALL (No Blind Restarts / Offline Testing Required):** When debugging gateway plugins, *never* blindly restart the gateway process to test if a code patch works. Do NOT execute commands like `kill $(pgrep ...)`, `systemctl restart hermes-gateway`, or `pm2 restart` without explicit permission. A restart instantly kills the active Telegram session you are using to communicate with the user. Furthermore, users hate "testing in production" loops where you ask for a restart, it crashes again, and you have to repeat the process. 
  **Mandatory Workflow:** 
  1. Generate a mock harness using the provided template (e.g., `templates/test_plugin_harness.py`).
  2. Use `unittest.mock` (e.g., `patch`, `MagicMock`, `AsyncMock`) to isolate network calls.
  3. Instantiate the modified plugin class with mock configs.
  4. Manually trigger the patched methods (`_process_update_async`, `send`, etc) to prove state parsing and async logic works.
  5. Run the script locally to prove the exception is resolved and edge cases are handled.
  6. **Verify the Production Deployment Context:** Ensure the target `systemd` service unit actually provides the environment the code needs (e.g., `EnvironmentFile=/root/.hermes/.env`). Do not confidently celebrate passing mock tests if you haven't verified the integration layer. Perfect mock-tested code will still fail in production if the systemd unit doesn't load the required tokens.
  7. Only after the script runs cleanly AND the systemd environment is verified, ask the user for explicit restart approval as the absolute final step.

## ❌ Anti-Patterns (Как делать НЕ НАДО)
*Explicitly recorded to prevent recurrent API/Gateway crashes:*
1. **DO NOT** send a message immediately after uploading an attachment. MAX processes files asynchronously. Immediate sending causes `400 attachment.not.ready`. **Must:** Implement a retry loop (e.g., 5 attempts with sleep).
2. **DO NOT** use `media_paths` in the gateway `MessageEvent` when passing local files. It crashes the gateway (`unexpected keyword argument`). **Must:** Pass local file paths to `media_urls` instead.
3. **DO NOT** omit `{"type": "callback"}` in inline button payloads. Telegram-style generic dictionaries trigger `400 Can't deserialize body` and drop the message.
4. **DO NOT** place `chat_id` or `user_id` inside the JSON body of a `POST /messages` request. **Must:** Pass the recipient ID exclusively as a URL query parameter (`?user_id=...`).
5. **DO NOT** perform blind `systemctl restart hermes-gateway` commands to test plugin fixes. It kills active chat sessions. **Must:** Test via mock scripts (`unittest.mock`) locally first.