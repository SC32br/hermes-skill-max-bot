import sys
import logging
import asyncio
from unittest.mock import patch, MagicMock

# Setup environment
logging.basicConfig(level=logging.ERROR)
sys.path.append("/home/hermes-agent")

from gateway.platforms.base import BasePlatformAdapter, MessageType
from gateway.config import PlatformConfig

# Dynamically load the plugin to avoid pathing issues
import importlib.util
spec = importlib.util.spec_from_file_location("adapter", "/root/.hermes/plugins/max_messenger/adapter.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
MaxAdapter = getattr(module, "MaxAdapter")

class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)

async def test_init_and_parsing():
    adapter = MaxAdapter(PlatformConfig(enabled=True, token="test_token"))
    adapter.handle_message = AsyncMock()

    payload = {
        "update_type": "message_created",
        "message": {
            "body": {"text": "Hello"},
            "sender": {"user_id": "123", "username": "testuser"},
            "recipient": {"chat_id": "456", "chat_type": "dialog"}
        }
    }
    
    await adapter._process_update_async(payload)
    
    # Verify core behavior
    assert adapter.handle_message.call_count == 1
    call_args = adapter.handle_message.call_args[0][0]
    assert call_args.text == "Hello"
    assert call_args.source.user_id == "123"
    print("Parsing Test: PASS")

async def test_network_send():
    adapter = MaxAdapter(PlatformConfig(enabled=True, token="test_token"))
    
    # Mock requests to isolate network
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"body": {"mid": "final_mid"}}}
        mock_post.return_value = mock_response
        
        result = await adapter.send("chat1", "text")
        
        assert result.success is True
        assert result.message_id == "final_mid"
        print("Network Send Test: PASS")

async def test_media_download():
    adapter = MaxAdapter(PlatformConfig(enabled=True, token="test_token"))
    adapter.handle_message = AsyncMock()
    
    payload = {
        "update_type": "message_created",
        "message": {
            "body": {
                "text": "",
                "attachments": [
                    {"type": "audio", "payload": {"url": "http://fake.url/audio.ogg"}}
                ]
            },
            "sender": {"user_id": "123", "username": "testuser"},
            "recipient": {"chat_id": "456", "chat_type": "dialog"}
        }
    }
    
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"fake audio data"
    mock_resp.info.return_value = {"Content-Type": "audio/ogg"}
    
    with patch('urllib.request.urlopen', return_value=mock_resp):
        await adapter._process_update_async(payload)
        
    assert adapter.handle_message.call_count == 1
    call_args = adapter.handle_message.call_args[0][0]
    assert call_args.message_type == MessageType.VOICE
    assert len(call_args.media_urls) == 1
    assert call_args.media_urls[0].endswith(".ogg")
    print("Media Download Test: PASS")

if __name__ == "__main__":
    asyncio.run(test_init_and_parsing())
    asyncio.run(test_network_send())
    asyncio.run(test_media_download())