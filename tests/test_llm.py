"""
Script to test Google Gemini 1.5 Flash API integration using google-generativeai
and python-dotenv.

Loads GOOGLE_API_KEY from .env file without hardcoding keys in source code.
"""

import os
import sys
from google import genai
from dotenv import load_dotenv

def main():
    # Load environment variables from .env
    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key or api_key == "your_key_here":
        print("Error: GOOGLE_API_KEY is missing or set to placeholder in .env file.")
        print("Please add your valid Gemini API key to .env file.")
        sys.exit(1)

    # Configure google-genai client
    client = genai.Client(api_key=api_key)

    print("Sending prompt 'say hello' to Gemini 1.5 Flash...")
    response = client.models.generate_content(model="gemini-1.5-flash", contents="say hello")

    print("\nGemini Response:")
    print(response.text)


if __name__ == "__main__":
    main()
