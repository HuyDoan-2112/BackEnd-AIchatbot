# Streaming Chat Fix - Thinking Field Support

## Problem Identified

Your React frontend hook was receiving **blank responses** because it was looking for a `thinking` or `reasoning` field in the streaming chunks, but the backend was sending status messages as regular `content` with markdown formatting.

### What Was Happening:

1. **Frontend expected**: `delta.thinking` or `delta.reasoning` or `delta.content`
2. **Backend sent**: Only `delta.content` with status messages like `"_[Processing your request...]_"`
3. **Result**: The frontend's parsing logic didn't match the backend format, causing blank responses

## Solution Applied

### Changes Made:

#### 1. **Schema Enhancement** (`app/schemas/chat_response.py`)
Added `thinking` and `reasoning` fields to `ChatCompletionChunkDelta`:

```python
class ChatCompletionChunkDelta(BaseModel):
    """Delta in streaming chunk"""
    role: Optional[ChatRole] = None
    content: Optional[str] = None
    thinking: Optional[str] = None  # For thinking/reasoning status messages
    reasoning: Optional[str] = None  # Alias for thinking (OpenAI o1 compatibility)
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
```

#### 2. **Service Update** (`app/services/chat_service.py`)
Modified `_send_status_chunk` to use the `thinking` field:

```python
async def _send_status_chunk(self, request_id: str, model: str, status_message: str):
    """Create a status/thinking chunk to show progress."""
    return ChatCompletionChunk(
        id=request_id,
        created=int(time.time()),
        model=model,
        choices=[
            ChatCompletionChunkChoice(
                index=0,
                delta=ChatCompletionChunkDelta(
                    role=ChatRole.ASSISTANT,
                    thinking=status_message  # ✅ Now uses thinking field
                ),
                finish_reason=None
            )
        ]
    )
```

## How It Works Now

### Backend Streaming Behavior:

When `STREAM_SHOW_THINKING=true` (from `.env`), the backend sends:

1. **Thinking Phase** (3 status chunks):
   - `delta.thinking = "Processing your request..."`
   - `delta.thinking = "Building context from history..."`
   - `delta.thinking = "Generating response..."`

2. **Content Phase** (multiple chunks):
   - `delta.content = "Python"` 
   - `delta.content = " is"`
   - `delta.content = " a programming"`
   - etc.

3. **Completion**:
   - `finish_reason = "stop"`
   - `data: [DONE]`

### Frontend Hook Compatibility:

Your existing frontend hook now works correctly:

```typescript
// This now receives data correctly!
const delta = chunk.choices?.[0]?.delta;

if (delta) {
  // Thinking chunks
  const thinkingDelta = delta.thinking || delta.reasoning;
  if (thinkingDelta) {
    thinkingAccumulated += thinkingDelta;
    onThinkingUpdate?.(thinkingAccumulated);
  }

  // Content chunks
  if (delta.content) {
    contentAccumulated += delta.content;
    onContentUpdate?.(contentAccumulated);
  }
}
```

## Testing

### Run the Test Script:

```bash
# Make sure your server is running
python test_streaming_fix.py
```

Expected output:
```
Starting streaming test...

🤔 Thinking: Processing your request...
🤔 Thinking: Building context from history...
🤔 Thinking: Generating response...
💬 Content: Python is a high-level...

==================================================
Summary:
  Thinking chunks: 3
  Content chunks: 45
  Total thinking: Processing your request... | Building context from history... | Generating response...
  Total content length: 234 chars
==================================================
```

### Manual Test with cURL:

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-20b",
    "messages": [
      {"role": "user", "content": "Hello"}
    ],
    "stream": true
  }' --no-buffer
```

Look for chunks like:
```
data: {"id":"...","object":"chat.completion.chunk","created":...,"model":"...","choices":[{"index":0,"delta":{"role":"assistant","thinking":"Processing your request..."},"finish_reason":null}]}

data: {"id":"...","object":"chat.completion.chunk","created":...,"model":"...","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}
```

## Configuration

Control thinking messages via environment variable:

```env
# .env file
STREAM_SHOW_THINKING=true   # Show thinking status (recommended for UX)
STREAM_SHOW_THINKING=false  # Skip thinking messages (faster, but less feedback)
```

## Benefits

✅ **Proper separation** of thinking vs content  
✅ **OpenAI o1 compatibility** (supports both `thinking` and `reasoning`)  
✅ **Better UX** - frontend can show "thinking" indicators  
✅ **Backward compatible** - still sends content normally  
✅ **No breaking changes** - works with existing non-streaming endpoints  

## Alternative Solution (If You Don't Want Thinking)

If you prefer a simpler approach without thinking messages, update your frontend hook:

```typescript
// Simplified - ignore thinking completely
const delta = chunk.choices?.[0]?.delta;
if (delta?.content) {
  contentAccumulated += delta.content;
  onContentUpdate?.(contentAccumulated);
}
```

And set in `.env`:
```env
STREAM_SHOW_THINKING=false
```
