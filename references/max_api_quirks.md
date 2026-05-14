# MAX Messenger (max.ru) API Quirks & Workarounds

Documented requirements and idiosyncrasies discovered when integrating Hermes with the MAX API:

## Webhooks
- **HTTPS Enforcement**: MAX strictly requires a valid SSL certificate for webhooks. Local development/deployment requires a reverse proxy (e.g., Caddy) pointing a public domain to the local bot port (e.g., `127.0.0.1:8080`).
- **Explicit Subscriptions**: When registering a webhook endpoint via `POST /subscriptions`, you must explicitly declare the required events. If you need button support, you must pass `update_types: ["message_created", "message_callback"]`.

## UI & Keyboards
- **Inline Keyboards Structure**: Unlike Telegram, MAX requires strict type definitions for every button and nests them under `attachments`.
  ```json
  "attachments": [{
      "type": "inline_keyboard",
      "payload": {
          "buttons": [
              [
                  {"type": "link", "text": "URL", "url": "https..."},
                  {"type": "callback", "text": "Click Me", "payload": "callback_data"}
              ]
          ]
      }
  }]
  ```
- **Callback Payloads**: Incoming webhook updates for button clicks arrive with `update_type: "message_callback"`. The actual payload data is nested under `update["callback"]["callback_id"]` or `update["payload"]["callback_id"]`.

## Chat Actions (UX)
- **Typing Status**: To prevent the user from thinking the bot is unresponsive during LLM generation, explicitly send a typing status as soon as the request is received:
  `POST /chats/{chat_id}/actions` with JSON `{"action": "typing_on"}`.

## Inbound Files & Media Handling
- **File Extensions (.bin):** When a user sends a document (e.g., MS Word, PDF) to the bot via MAX Messenger, the OpenClaw/MAX gateway adapter often downloads and saves it locally with a generic `.bin` extension (e.g., `/tmp/max_media_fa00d79e...bin`). 
- **Agent Workflow:** When the system prompts that the user sent a document ending in `.bin`, do NOT assume it is a raw binary executable. Always use the `file` command (`file /tmp/max_media...bin`) to determine its actual MIME type first. If it is a Word document (`Microsoft Word 2007+`), parse it using the appropriate library (e.g., `python3 -c "import docx; print('\n'.join([p.text for p in docx.Document('/tmp/max_media...bin').paragraphs]))"`).