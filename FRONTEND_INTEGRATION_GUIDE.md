# Frontend Integration Guide

Complete guide for integrating streaming chat with your frontend.

## 🌐 CORS Configuration (Already Done!)

Your backend is already configured for streaming! The CORS settings in `app/main.py:124-140` allow:

```python
allow_origins=[
    "http://localhost:5173",      # Vite default
    "http://127.0.0.1:5173",
    "http://192.168.0.246:5173",  # Your local network
    "https://qwg237dx-5173.use.devtunnels.ms"  # Dev tunnel
]
```

**To add your frontend URL:**
```python
# In app/main.py, add your URL to allow_origins:
"http://yourdomain.com",
"https://yourdomain.com"
```

---

## 📡 Streaming from Frontend

Your streaming endpoint is ready to use! No special configuration needed.

### JavaScript/React Example

```javascript
async function streamChat(message) {
    const response = await fetch('http://localhost:8000/api/v1/chat/completions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            // Add auth token if needed:
            // 'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            model: 'openai/gpt-oss-20b',
            messages: [{ role: 'user', content: message }],
            stream: true  // Enable streaming
        })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
            if (!line.trim() || !line.startsWith('data: ')) continue;

            const data = line.slice(6);
            if (data === '[DONE]') break;

            try {
                const chunk = JSON.parse(data);
                const content = chunk.choices[0]?.delta?.content;
                if (content) {
                    // Display content in UI
                    updateChatUI(content);
                }
            } catch (e) {
                console.error('Parse error:', e);
            }
        }
    }
}
```

---

## ✅ Using Your Response Status Classes

You have a clean response system in `app/core/response_status.py`!

### Your Status Classes

```python
from app.core.response_status import (
    OK,                  # 200
    Created,             # 201
    BadRequest,          # 400
    Unauthorized,        # 401
    Forbidden,           # 403
    NotFound,            # 404
    Conflict,            # 409
    InternalError,       # 500
    ServiceUnavailable,  # 503
    ValidationError,     # 400 with custom code
    # ... and more!
)
```

### Response Format

Your responses look like this:

```json
{
  "success": true,
  "message": "OK",
  "data": { /* your data here */ }
}
```

**For errors:**
```json
{
  "success": false,
  "message": "Unauthorized",
  "error_code": "4001"
}
```

### Example Usage in Routes

```python
from app.core.response_status import OK, Unauthorized, BadRequest

@router.post("/example")
async def example_endpoint(request: SomeRequest):
    # Success response
    return OK(
        message="Request processed successfully",
        data={"result": "some data"}
    ).send()

    # Error response
    return Unauthorized(
        message="Invalid credentials"
    ).send()

    # With custom data
    return OK(
        message="User created",
        data={
            "user_id": "123",
            "email": "user@example.com"
        },
        meta={
            "timestamp": "2025-01-15T10:30:00Z"
        }
    ).send()
```

---

## 🔐 Adding Authentication to Streaming

If you need authentication for streaming:

```javascript
async function streamChatWithAuth(message, token) {
    const response = await fetch('http://localhost:8000/api/v1/chat/completions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`  // Add auth token
        },
        body: JSON.stringify({
            model: 'openai/gpt-oss-20b',
            messages: [{ role: 'user', content: message }],
            stream: true
        })
    });

    // ... rest of streaming code
}
```

**In your route:**
```python
from app.core.dependencies import get_current_user
from app.core.response_status import Unauthorized

@router.post("/chat/completions")
async def chat(
    request: ChatCompletionRequest,
    current_user: User = Depends(get_current_user)  # Validate token
):
    if not current_user:
        return Unauthorized(message="Invalid or expired token").send()

    # Process chat request
    if request.stream:
        return StreamingResponse(...)
    else:
        return OK(message="Chat completed", data=response).send()
```

---

## 🎨 Frontend Response Handling

### Handling Your Response Format

```typescript
interface ApiResponse<T = any> {
    success: boolean;
    message: string;
    data?: T;
    error_code?: string;
    meta?: Record<string, any>;
}

async function makeRequest<T>(
    endpoint: string,
    method: 'GET' | 'POST' = 'GET',
    body?: any
): Promise<ApiResponse<T>> {
    const response = await fetch(`http://localhost:8000/api/v1${endpoint}`, {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: body ? JSON.stringify(body) : undefined
    });

    const data: ApiResponse<T> = await response.json();

    if (!data.success) {
        // Handle error with your UI
        showError(data.message, data.error_code);
        throw new Error(data.message);
    }

    return data;
}

// Usage
try {
    const result = await makeRequest<{ user_id: string }>('/auth/login', 'POST', {
        email: 'user@example.com',
        password: 'password123'
    });

    console.log('Success:', result.message);
    console.log('User ID:', result.data?.user_id);
} catch (error) {
    console.error('Request failed:', error);
}
```

---

## 📊 Status Code Reference

Your backend returns these readable status messages:

| HTTP Code | Status Message | Your Class | Error Code |
|-----------|---------------|------------|------------|
| 200 | OK | `OK()` | - |
| 201 | Created | `Created()` | - |
| 400 | Bad Request | `BadRequest()` | 4000 |
| 401 | Unauthorized | `Unauthorized()` | 4001 |
| 403 | Forbidden | `Forbidden()` | 4003 |
| 404 | Not Found | `NotFound()` | 4004 |
| 409 | Conflict | `Conflict()` | 4009 |
| 422 | Unprocessable Entity | `UnprocessableEntity()` | 4022 |
| 429 | Too Many Requests | `TooManyRequests()` | 4029 |
| 500 | Internal Server Error | `InternalError()` | 5000 |
| 503 | Service Unavailable | `ServiceUnavailable()` | 5003 |

**Custom Error Codes:**
- `4001` - Invalid Credentials
- `4011` - Token Expired
- `4012` - Token Invalid
- `5001` - Database Error

---

## 🚀 Complete React Hook Example

```typescript
import { useState } from 'react';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

export function useChatStream() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const sendMessage = async (content: string, token?: string) => {
        setError(null);
        setIsStreaming(true);

        // Add user message
        setMessages(prev => [...prev, { role: 'user', content }]);

        try {
            const response = await fetch('http://localhost:8000/api/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token && { 'Authorization': `Bearer ${token}` })
                },
                body: JSON.stringify({
                    model: 'openai/gpt-oss-20b',
                    messages: [...messages, { role: 'user', content }],
                    stream: true
                })
            });

            // Check for errors
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `HTTP ${response.status}`);
            }

            const reader = response.body!.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let assistantMessage = '';

            // Add empty assistant message
            setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop()!;

                for (const line of lines) {
                    if (!line.trim() || !line.startsWith('data: ')) continue;

                    const data = line.slice(6);
                    if (data === '[DONE]') break;

                    try {
                        const chunk = JSON.parse(data);
                        const content = chunk.choices[0]?.delta?.content;

                        if (content) {
                            assistantMessage += content;
                            setMessages(prev => {
                                const updated = [...prev];
                                updated[updated.length - 1].content = assistantMessage;
                                return updated;
                            });
                        }
                    } catch (e) {
                        console.warn('Failed to parse chunk:', e);
                    }
                }
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Unknown error';
            setError(errorMessage);
            setMessages(prev => [
                ...prev,
                { role: 'assistant', content: `Error: ${errorMessage}` }
            ]);
        } finally {
            setIsStreaming(false);
        }
    };

    return {
        messages,
        isStreaming,
        error,
        sendMessage
    };
}

// Usage in component
function ChatComponent() {
    const { messages, isStreaming, error, sendMessage } = useChatStream();
    const [input, setInput] = useState('');

    const handleSend = () => {
        if (input.trim() && !isStreaming) {
            sendMessage(input);
            setInput('');
        }
    };

    return (
        <div className="chat-container">
            <div className="messages">
                {messages.map((msg, i) => (
                    <div key={i} className={`message ${msg.role}`}>
                        {msg.content}
                    </div>
                ))}
            </div>

            {error && (
                <div className="error-banner">
                    {error}
                </div>
            )}

            <div className="input-area">
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                    disabled={isStreaming}
                    placeholder="Type your message..."
                />
                <button onClick={handleSend} disabled={isStreaming}>
                    {isStreaming ? 'Sending...' : 'Send'}
                </button>
            </div>
        </div>
    );
}
```

---

## 🎯 Summary

### What's Already Set Up:
✅ **CORS** - Your frontend can access the API
✅ **Streaming** - Real-time responses work out of the box
✅ **Clean Status Responses** - Readable error messages (not just numbers)
✅ **Response Format** - Consistent `{success, message, data}` structure

### What You Need to Do:
1. **Add your frontend URL** to CORS if not already there
2. **Use the streaming example** from this guide
3. **Handle responses** with your existing format:
   ```javascript
   if (!response.success) {
       showError(response.message, response.error_code);
   }
   ```

### Response Examples:

**Success:**
```json
{
  "success": true,
  "message": "OK",
  "data": { "result": "..." }
}
```

**Error:**
```json
{
  "success": false,
  "message": "Unauthorized",
  "error_code": "4001"
}
```

Your backend is production-ready! Just use the examples above to integrate streaming into your frontend. 🚀
