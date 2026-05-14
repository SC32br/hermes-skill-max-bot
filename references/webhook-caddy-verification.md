# Verifying MAX Webhooks with Caddy

When debugging MAX messenger webhook integration on a server using Caddy as a reverse proxy, follow this chain to verify the local environment before testing with real platform messages:

1. **Verify Gateway Logs:**
   Ensure the Hermes gateway successfully connected and registered the webhook.
   `grep -i "max" ~/.hermes/logs/gateway.log`
   Look for: `[MAX] Webhook successfully registered via API: https://your-domain/max-webhook`
   And: `[MAX] Connected. Webhook server starting on port 8080.`

2. **Verify Local Webhook Listener (aiohttp):**
   Test the internal port to confirm the webhook listener is active.
   `curl -s -I -X POST http://127.0.0.1:8080/max-webhook`
   *Expected:* HTTP 400 Bad Request. (This is successful! It means the Python `aiohttp` server received the request but rejected it because the payload was empty/invalid).

3. **Verify Reverse Proxy (Caddyfile):**
   Confirm that the external traffic is routed to the internal port without getting caught in basic auth.
   `cat /etc/caddy/Caddyfile`
   *Expected snippet:*
   ```caddyfile
   handle /max-webhook* {
       reverse_proxy 127.0.0.1:8080
   }
   ```
   (Note: `/max-webhook*` allows query params to pass through).

If all three layers confirm, the gateway is fully ready to receive external messages.