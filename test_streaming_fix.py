"""
Test script to verify streaming with thinking field works correctly
"""
import asyncio
import httpx

async def test_streaming():
    """Test the streaming endpoint with thinking field"""
    url = "http://localhost:8000/api/v1/chat/completions"
    
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is Python?"}
        ],
        "stream": True,
        "temperature": 0.7
    }
    
    print("Starting streaming test...\n")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            if response.status_code != 200:
                print(f"Error: HTTP {response.status_code}")
                print(await response.aread())
                return
            
            thinking_chunks = []
            content_chunks = []
            
            async for line in response.aiter_lines():
                if not line.strip() or not line.startswith('data: '):
                    continue
                
                data = line[6:]  # Remove 'data: ' prefix
                if data == '[DONE]':
                    print("\n✅ Stream completed with [DONE]")
                    break
                
                try:
                    import json
                    chunk = json.loads(data)
                    
                    # Check for thinking field
                    delta = chunk.get('choices', [{}])[0].get('delta', {})
                    
                    if 'thinking' in delta and delta['thinking']:
                        thinking_chunks.append(delta['thinking'])
                        print(f"🤔 Thinking: {delta['thinking']}")
                    
                    if 'reasoning' in delta and delta['reasoning']:
                        thinking_chunks.append(delta['reasoning'])
                        print(f"💭 Reasoning: {delta['reasoning']}")
                    
                    if 'content' in delta and delta['content']:
                        content_chunks.append(delta['content'])
                        print(f"💬 Content: {delta['content']}", end='', flush=True)
                
                except Exception as e:
                    print(f"\n⚠️  Parse error: {e}")
                    print(f"   Data: {data[:100]}...")
            
            print("\n\n" + "="*50)
            print(f"Summary:")
            print(f"  Thinking chunks: {len(thinking_chunks)}")
            print(f"  Content chunks: {len(content_chunks)}")
            print(f"  Total thinking: {' | '.join(thinking_chunks)}")
            print(f"  Total content length: {len(''.join(content_chunks))} chars")
            print("="*50)

if __name__ == "__main__":
    asyncio.run(test_streaming())
