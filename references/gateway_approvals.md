# MAX Messenger: Gateway Approvals & Interactive Buttons

## API Requirement for Buttons
When implementing interactive inline keyboards in MAX Messenger (e.g., for `send_exec_approval` or `send_slash_confirm`), the MAX API strictly requires each button dictionary to explicitly define `"type": "callback"` (or `"type": "link"`). 
If this explicit typing is missing, the API will silently drop the keyboard and render the message without buttons.

```python
# Correct payload format for MAX buttons
max_row.append({"type": "callback", "text": "✅ Approve", "payload": "app:once:123456"})
```

## Hermes Gateway Architecture Quirk
To support Hermes system approval prompts on a new platform:
1. The adapter class MUST have the methods `send_exec_approval` and `send_slash_confirm` defined.
2. The Gateway (`run.py`) checks for their existence via `getattr(type(_status_adapter), "send_exec_approval", None)`. If they are missing from the adapter's class definition, the gateway silently falls back to sending a text-only representation of the prompt.
3. State (`approval_id` -> `session_key`) must be maintained locally in the adapter (e.g., in a dictionary like `self._approval_state`).
4. Incoming callbacks (starting with `app:once:`, `app:session:`, `sc:once:`, etc.) must be intercepted in the webhook update processor. The handler pops the `session_key` and resolves the hung command via `tools.approval.resolve_gateway_approval(session_key, action)`.