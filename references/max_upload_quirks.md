# MAX Messenger API: Media Upload Process

The MAX platform does not natively support sending raw files or `multipart/form-data` directly via `POST /messages`. Instead, it uses an asynchronous 3-step process.

## Step 1: Get Upload URL
Send a POST request to `/uploads` specifying the type of media:
`POST https://platform-api.max.ru/uploads?type=file` (or `image`, `video`, `audio`)
*Note: The `photo` type is deprecated; use `image` instead.*
*Response:* Returns a JSON with an `url` and sometimes a `token` (for some media types).

## Step 2: Upload File
Send the file using `multipart/form-data` to the `url` returned in Step 1.
*Response:* Returns a JSON containing a `token` (if not already provided in Step 1, or updated).

## Step 3: Attach to Message
Use the `token` in the `attachments` array of the `POST /messages` endpoint:
```json
{
    "text": "Here is the file",
    "attachments": [
        {
            "type": "file",
            "payload": {
                "token": "<the_token_from_step_1_or_2>"
            }
        }
    ]
}
```

## The `attachment.not.ready` Pitfall (CRITICAL)
MAX processes files asynchronously on their CDN. If you immediately execute Step 3 after Step 2, the API will frequently return:
`400 Bad Request` with `{"code": "attachment.not.ready"}`.

**Mitigation:** The Hermes gateway adapter must catch this specific error code and apply exponential backoff (e.g., waiting 1s, then 2s) up to 5 times before failing. Do not treat `attachment.not.ready` as a terminal failure.