import os
import asyncio
import logging
from enum import Enum
from typing import Optional, Dict, Any
from aiohttp import web
import requests
import tempfile
import uuid

from gateway.platforms.base import BasePlatformAdapter, MessageEvent, MessageType, SendResult

from gateway.config import Platform

logger = logging.getLogger("gateway.max")

class MaxAdapter(BasePlatformAdapter):
    def __init__(self, config):
        super().__init__(config, Platform("max"))
        # Ensure config is treated as a dict for get() or use getattr safely
        conf_dict = config if isinstance(config, dict) else (config.model_dump() if hasattr(config, "model_dump") else (config.dict() if hasattr(config, "dict") else vars(config)))
        options = conf_dict.get("options", {}) or {}
        
        self.token = options.get("token") or conf_dict.get("token") or os.environ.get("MAX_TOKEN")
        self.secret = options.get("secret", "max_webhook_secret")
        self.base_url = "https://platform-api.max.ru"
        self.headers = {"Authorization": self.token, "Content-Type": "application/json"}
        
        # Webhook properties
        self._webhook_port = 8080
        self._app: Optional[web.Application] = None
        self._webhook_runner: Optional[web.AppRunner] = None
        self._webhook_site: Optional[web.TCPSite] = None
        self._slash_confirm_state = {}
        self._approval_state = {}
        
        # Get public domain from env or config
        self.public_url = "https://hermes-analyst.xn--b1amyej7e.xn--p1ai/max-webhook"

    async def connect(self) -> bool:
        if not self.token:
            logger.error("[MAX] No token configured.")
            return False
            
        # Register webhook with MAX API
        try:
            payload = {
                "url": self.public_url,
                "update_types": ["message_created", "message_callback"]
            }
            r = await asyncio.to_thread(
                requests.post, 
                f"{self.base_url}/subscriptions", 
                headers=self.headers, 
                json=payload, 
                timeout=10
            )
            if r.status_code == 200:
                logger.info(f"[MAX] Webhook successfully registered via API: {self.public_url}")
            else:
                logger.error(f"[MAX] Failed to register webhook: {r.status_code} {r.text}")
        except Exception as e:
            logger.error(f"[MAX] Exception during webhook registration: {e}")
            
        # Start webhook server in the background
        asyncio.create_task(self._start_webhook_server())
        
        logger.info(f"[MAX] Connected. Webhook server starting on port {self._webhook_port}.")
        return True

    async def _start_webhook_server(self):
        self._app = web.Application()
        self._app.router.add_post("/max-webhook", self._handle_webhook_request)
        
        self._webhook_runner = web.AppRunner(self._app)
        await self._webhook_runner.setup()
        self._webhook_site = web.TCPSite(self._webhook_runner, "127.0.0.1", self._webhook_port)
        await self._webhook_site.start()

    async def disconnect(self):
        if self._webhook_runner:
            asyncio.create_task(self._webhook_runner.cleanup())
        logger.info("[MAX] Disconnected.")

    async def _handle_webhook_request(self, request: web.Request) -> web.Response:
        try:
            raw_text = await request.text()
            logger.info(f"[MAX] Raw webhook payload: {raw_text}")
            update = await request.json()
            asyncio.create_task(self._process_update_async(update))
            return web.Response(status=200, text="OK")
        except Exception as e:
            logger.error(f"[MAX] Error parsing webhook: {e}")
            return web.Response(status=400, text="Bad Request")

    async def _process_update_async(self, update: dict):
        update_type = update.get("update_type", update.get("type"))
        
        # 1. Handle regular messages
        if update_type == "message_created":
            message = update.get("message", update.get("payload", {}).get("message", {}))
            sender = message.get("sender", {})
            user_id = str(sender.get("user_id", ""))
            
            recipient = message.get("recipient", {})
            chat_id = str(recipient.get("chat_id", ""))
            
            if chat_id:
                asyncio.create_task(self._mark_seen(chat_id))
            
            if sender.get("is_bot", False):
                return
                
            text = message.get("body", {}).get("text", "")
            msg_id = message.get("body", {}).get("mid", "")
            
            # Extract audio attachments
            attachments = message.get("body", {}).get("attachments", [])
            media_urls = []
            msg_type = MessageType.TEXT
            
            if attachments:
                for att in attachments:
                    att_type = att.get("type", "").lower()
                    url = att.get("payload", {}).get("url")
                    
                    if not url:
                        continue
                        
                    if att_type in ["audio", "voice"]:
                        media_urls.append(url)
                        msg_type = MessageType.VOICE
                    elif att_type in ["image", "photo", "picture"]:
                        media_urls.append(url)
                        msg_type = MessageType.PHOTO
                    elif att_type == "video":
                        media_urls.append(url)
                        msg_type = MessageType.VIDEO
                    elif att_type in ["file", "document"]:
                        media_urls.append(url)
                        msg_type = MessageType.DOCUMENT
                    else:
                        media_urls.append(url)
                        msg_type = MessageType.DOCUMENT
            
            from gateway.platforms.base import SessionSource
            source = SessionSource(
                platform=self.platform,
                chat_id=chat_id,
                user_id=user_id,
                user_name=sender.get("username", user_id),
                chat_name=sender.get("name", sender.get("first_name", ""))
            )
            
            media_paths = []
            if media_urls:
                for url in media_urls:
                    try:
                        import urllib.request
                        resp = await asyncio.to_thread(urllib.request.urlopen, url)
                        content_type = resp.info().get("Content-Type", "")
                        ext = ""
                        
                        if msg_type == MessageType.VOICE:
                            ext = ".ogg" if "ogg" in url or "ogg" in content_type else ".mp3"
                        elif msg_type == MessageType.PHOTO:
                            ext = ".jpg" if "jpeg" in content_type else ".png"
                        elif msg_type == MessageType.VIDEO:
                            ext = ".mp4"
                        else:
                            import mimetypes
                            ext = mimetypes.guess_extension(content_type) or ""
                            if not ext and "." in url.split("/")[-1]:
                                ext = "." + url.split("/")[-1].split(".")[-1].split("?")[0]
                        
                        tmp_path = os.path.join(tempfile.gettempdir(), f"max_media_{uuid.uuid4()}{ext}")
                        with open(tmp_path, "wb") as f_out:
                            f_out.write(resp.read())
                        media_paths.append(tmp_path)
                    except Exception as e:
                        logger.error(f"[MAX] Failed to download media: {e}")
                        
            event = MessageEvent(
                text=text,
                source=source,
                message_id=msg_id,
                message_type=msg_type,
                media_urls=media_paths if media_paths else []
            )
            await self.handle_message(event)

        # 2. Handle 'callback' type buttons
        elif update_type == "message_callback":
            callback = update.get("callback", update.get("payload", {}))
            callback_id = callback.get("callback_id", "")
            payload_text = callback.get("payload", "")
            
            
            
            if payload_text.startswith("app:"):
                parts = payload_text.split(":", 2)
                if len(parts) == 3:
                    action = parts[1]
                    approval_id = parts[2]
                    session_key = self._approval_state.pop(approval_id, None)
                    if session_key:
                        try:
                            from tools.approval import resolve_gateway_approval
                            resolve_gateway_approval(session_key, action)
                        except Exception as e:
                            import logging
                            logging.getLogger("gateway.max").error(f"[MAX] Error resolving exec approval: {e}")
                    
                    if callback_id:
                        ans_url = f"{self.base_url}/answers?callback_id={callback_id}"
                        try:
                            import requests
                            await asyncio.to_thread(requests.post, ans_url, headers=self.headers, json={}, timeout=5)
                        except: pass
                    
                    return # Handled
            if payload_text.startswith("sc:"):
                parts = payload_text.split(":", 2)
                if len(parts) == 3:
                    action = parts[1]
                    confirm_id = parts[2]
                    session_key = self._slash_confirm_state.pop(confirm_id, None)
                    if session_key:
                        try:
                            from tools.approval import resolve_gateway_approval
                            resolve_gateway_approval(confirm_id, action)
                        except Exception as e:
                            logger.error(f"[MAX] Error resolving slash confirmation: {e}")
                    
                    if callback_id:
                        ans_url = f"{self.base_url}/answers?callback_id={callback_id}"
                        try:
                            await asyncio.to_thread(requests.post, ans_url, headers=self.headers, json={}, timeout=5)
                        except: pass
                    
                    return # Handled
            user_info = callback.get("user", {})
            user_id = str(user_info.get("user_id", ""))
            
            # MUST acknowledge the callback so UI doesn't hang
            if callback_id:
                ans_url = f"{self.base_url}/answers?callback_id={callback_id}"
                try:
                    await asyncio.to_thread(requests.post, ans_url, headers=self.headers, json={}, timeout=5)
                except Exception as e:
                    logger.warning(f"[MAX] Failed to ack callback {callback_id}: {e}")
            
            message = update.get("message", {})
            recipient = message.get("recipient", {})
            real_chat_id = str(recipient.get("chat_id", user_id))
            
            from gateway.platforms.base import SessionSource
            source = SessionSource(
                platform=self.platform,
                chat_id=real_chat_id,
                user_id=user_id,
                user_name=user_id,
                chat_name=user_info.get("name", user_info.get("first_name", user_id))
            )
            event = MessageEvent(
                text=payload_text,
                source=source,
                message_id=callback_id,
                message_type=MessageType.TEXT
            )
            await self.handle_message(event)

    
    async def _mark_seen(self, chat_id: str):
        try:
            url = f"{self.base_url}/chats/{chat_id}/actions"
            await asyncio.to_thread(requests.post, url, headers=self.headers, json={"action": "mark_seen"}, timeout=5)
        except Exception as e:
            logger.debug(f"[MAX] Failed to mark seen for {chat_id}: {e}")

    async def send_typing(self, chat_id: str, metadata=None) -> None:
        try:
            url = f"{self.base_url}/chats/{chat_id}/actions"
            await asyncio.to_thread(requests.post, url, headers=self.headers, json={"action": "typing_on"}, timeout=5)
        except Exception as e:
            logger.debug(f"[MAX] Failed to send typing to {chat_id}: {e}")


    async def _upload_file(self, file_path: str):
        if not os.path.exists(file_path):
            logger.error(f"[MAX] File not found: {file_path}")
            return None
            
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or ""
        
        att_type = "file"
        if mime_type.startswith("image/"):
            att_type = "image"
        elif mime_type.startswith("video/"):
            att_type = "video"
        elif mime_type.startswith("audio/"):
            att_type = "audio"
            
        url_req = f"{self.base_url}/uploads?type={att_type}"
        try:
            r1 = await asyncio.to_thread(requests.post, url_req, headers=self.headers, timeout=10)
            if r1.status_code not in (200, 201):
                logger.error(f"[MAX] Failed to get upload URL: {r1.status_code} {r1.text}")
                return None
            
            data1 = r1.json()
            upload_url = data1.get("url")
            token = data1.get("token")
            
            if not upload_url:
                return None
                
            with open(file_path, "rb") as f:
                files = {"data": (os.path.basename(file_path), f, mime_type or "application/octet-stream")}
                r2 = await asyncio.to_thread(requests.post, upload_url, headers={"Authorization": self.token}, files=files, timeout=60)
                
            if r2.status_code not in (200, 201):
                logger.error(f"[MAX] Failed to upload file to {upload_url}: {r2.status_code} {r2.text}")
                return None
                
            data2 = r2.json()
            if att_type not in ["video", "audio"]:
                token = data2.get("token")
                
            if not token:
                logger.error(f"[MAX] No token received after upload: data1={data1}, data2={data2}")
                return None
                
            return {"type": att_type, "payload": {"token": token}}
            
        except Exception as e:
            logger.error(f"[MAX] Exception uploading {file_path}: {e}")
            return None

    async def send(self, chat_id: str, content: str, **kwargs) -> SendResult:
        payload = {"text": content, "format": "markdown"}
        media_paths = kwargs.get("media_paths", [])
        if media_paths:
            if "attachments" not in payload:
                payload["attachments"] = []
            for path in media_paths:
                att = await self._upload_file(path)
                if att:
                    payload["attachments"].append(att)

        
        inline_keyboard = kwargs.get("inline_keyboard")
        if inline_keyboard:
            # MAX requires explicit types for buttons
            max_buttons = []
            for row in inline_keyboard:
                max_row = []
                for btn in row:
                    if isinstance(btn, dict):
                        text = btn.get("text", "")
                        cb_data = btn.get("callback_data", btn.get("payload", ""))
                        if "url" in btn:
                            max_row.append({"type": "link", "text": text, "url": btn["url"]})
                        else:
                            max_row.append({"type": "callback", "text": text, "payload": cb_data})
                max_buttons.append(max_row)
                
            payload["attachments"] = [{
                "type": "inline_keyboard",
                "payload": {"buttons": max_buttons}
            }]
        
        url = f"{self.base_url}/messages?chat_id={chat_id}"
            
        try:
            r = await asyncio.to_thread(requests.post, url, headers=self.headers, json=payload, timeout=10)
            
            # Implementing retry for attachment.not.ready
            max_retries = 5
            for attempt in range(max_retries):
                if r.status_code not in (200, 201):
                    # Check if it's attachment.not.ready
                    try:
                        err_code = r.json().get("code")
                        if err_code == "attachment.not.ready":
                            logger.info(f"[MAX] Attachment not ready, waiting {attempt + 1}s before retry...")
                            await asyncio.sleep(1.0 + attempt)
                            r = await asyncio.to_thread(requests.post, url, headers=self.headers, json=payload, timeout=10)
                            continue
                    except:
                        pass
                        
                    fallback_param = "chat_id" if "user_id" in url else "user_id"
                    fallback_url = f"{self.base_url}/messages?{fallback_param}={chat_id}"
                    r = await asyncio.to_thread(requests.post, fallback_url, headers=self.headers, json=payload, timeout=10)
                    
                if r.status_code in (200, 201):
                    mid = r.json().get("message", {}).get("body", {}).get("mid", "")
                    return SendResult(success=True, message_id=mid)
                    
                break # if it failed and wasn't attachment.not.ready, break and log error
                
            logger.error(f"[MAX] Failed to send message to {chat_id}: {r.status_code} {r.text}")
        except Exception as e:
            logger.error(f"[MAX] Request failed: {e}")
            
        return SendResult(success=False)


    async def send_exec_approval(
        self,
        chat_id: str,
        command: str,
        session_key: str,
        description: str = "dangerous command",
        metadata=None,
    ) -> SendResult:
        import hashlib
        approval_id = str(hashlib.md5(f"{chat_id}:{command}:{session_key}".encode()).hexdigest())[:16]
        
        preview = f"⚠️ *Ожидает подтверждения: {description}*\n\n`{command[:500]}`"
        
        inline_keyboard = [
            [
                {"text": "✅ Один раз", "callback_data": f"app:once:{approval_id}"},
                {"text": "🔒 На сессию", "callback_data": f"app:session:{approval_id}"},
                {"text": "❌ Отменить", "callback_data": f"app:deny:{approval_id}"},
            ],
            [
                {"text": "🔑 Всегда", "callback_data": f"app:always:{approval_id}"},
            ],
        ]
        
        self._approval_state[approval_id] = session_key
        return await self.send(chat_id=chat_id, content=preview, inline_keyboard=inline_keyboard)

    async def send_slash_confirm(
        self,
        chat_id: str,
        title: str,
        message: str,
        session_key: str,
        confirm_id: str,
        metadata=None,
    ) -> SendResult:
        preview = message if len(message) <= 3800 else message[:3800] + "..."
        if title:
            preview = f"{title}\n\n{preview}"
            
        inline_keyboard = [
            [
                {"text": "✅ Approve Once", "callback_data": f"sc:once:{confirm_id}"},
                {"text": "🔒 Always Approve", "callback_data": f"sc:always:{confirm_id}"},
            ],
            [
                {"text": "❌ Cancel", "callback_data": f"sc:cancel:{confirm_id}"},
            ],
        ]
        
        self._slash_confirm_state[confirm_id] = session_key
        return await self.send(chat_id=chat_id, content=preview, inline_keyboard=inline_keyboard)
    async def get_chat_info(self, chat_id: str) -> dict:
        return {"id": chat_id, "name": f"MAX_{chat_id}", "type": "user"}

def register(ctx):
    ctx.register_platform("max", "MAX Messenger", MaxAdapter, lambda config=None: True, allowed_users_env="MAX_ALLOWED_USERS", allow_all_env="MAX_ALLOW_ALL_USERS")
