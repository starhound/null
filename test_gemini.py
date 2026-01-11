import asyncio
import os

from google.genai import Client


async def test():
    api_key = os.environ.get("GOOGLE_API_KEY", "fake_key")
    print(f"Testing with key: {api_key[:4]}...")

    try:
        client = Client(api_key=api_key)
        print("Client initialized (no http_options)")

        print("Attempting generate_content...")
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash", contents="Hi"
        )
        print("Response received")
        print(response.text)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test())
