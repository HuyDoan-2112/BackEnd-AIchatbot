import asyncio

import httpx

async def make_request(endpoint, param=None):
    url = f"http://localhost:8000/{endpoint}"
    async with httpx.AsyncClient(timeout = 20) as client:
        if param:
            response = await client.post(url, param=param)
        else:
            response = await client.get(url)
        
        if response.status_code == 200:
            print(f"Response from {endpoint}: {response.json()}")
        else:
            print(f"Error from {endpoint}: {response.status_code}")
            print(f"Response content: {response.text}")


async def main():
    chat_params = {"msg": "Hello, how are you?"}
    tasks =[make_request("get-all-ids/"), make_request("chat/", param=chat_params)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    for _ in range(3):  # Run the main function 3 times
        asyncio.run(main())