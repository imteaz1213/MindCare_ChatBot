from google import genai
from google.genai import types


class GenerativeEngine:

    SYSTEM_PROMPT = (
        "তুমি একজন সহানুভূতিশীল বাংলা মানসিক স্বাস্থ্য সহায়ক। "
        "তুমি থেরাপিস্ট নও এবং কোনো রোগ নির্ণয় বা ওষুধ পরামর্শ দাও না। "
        "ব্যবহারকারীর অনুভূতি বুঝে নিরাপদ, সহানুভূতিশীল ও "
        "অ-বিচারমূলক উত্তর দাও, প্রয়োজনে প্রফেশনাল সাহায্য নিতে উৎসাহিত করো।"
    )

    def __init__(
        self,
        gemini_api_key: str,
        gemini_model: str = "gemini-3.6-flash",
    ):
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model

        self.client = None

        if self.gemini_api_key:
            self.client = genai.Client(api_key=self.gemini_api_key)

    def generate(self, user_text: str) -> str:

       
        print("API Key Loaded :", "YES" if self.gemini_api_key else "NO")
       
      

        if self.client is None:
            print("Gemini client was not initialized.")
            return "Gemini API Key পাওয়া যায়নি।"

        try:
            print("Sending request to Gemini API...")

            response = self.client.models.generate_content(
                model=self.gemini_model,
                contents=user_text,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_PROMPT,
                    max_output_tokens=10000,
                ),
            )

           

            return response.text.strip()

        except Exception as e:
            print("\n===== GEMINI ERROR =====")
            print(type(e).__name__)
            print(str(e))
            print("========================\n")

            return (
                "দুঃখিত, এই মুহূর্তে আমি উত্তর তৈরি করতে পারছি না। "
                "অনুগ্রহ করে কিছুক্ষণ পরে আবার চেষ্টা করুন।"
            )