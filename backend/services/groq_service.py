from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

SYSTEM_PROMPT = """You are a senior market intelligence analyst. Analyze the provided web data and return structured, data-backed insights.

The context message specifies which DATA SOURCES were available. Only reference those exact source names in the "source" field.

Return using EXACTLY these section markers — no markdown, no text outside sections:

###PAIN_POINTS###
[{"text": "verbatim or closely paraphrased user complaint from the data — name the specific broken feature or workflow", "frequency": 12, "source": "Hacker News"}]

###COMPETITOR_GAPS###
[{"competitor": "ExactProductName", "gap": "specific missing feature users complained about — quote or paraphrase the data", "opportunity": "concrete differentiation with a specific feature name"}]

###PRICING_SIGNALS###
{"competitor_range": "$X-$Y/month", "willingness_to_pay": "$X-$Y/month", "insights": ["Name specific product + its price from the data, e.g. Acuity charges $16/month for basic calendar sync", "Another specific pricing observation from the data with product name or dollar amount"]}

###HOT_COMMUNITIES###
[{"name": "r/freelance", "members": "140K", "activity": "high"}]

###AI_SUMMARY###
2-3 sentences. Must include: (1) a specific dollar amount or percentage from the data, (2) at least one named competitor or product, (3) one concrete action for a founder.

STRICT RULES — each violation breaks the app:
1. PAIN_POINTS: Be specific. BAD: "difficulty finding a scheduling app". GOOD: "Calendly blocks buffer time customization behind $16/mo plan — freelancers on free tier can't set recovery time between meetings".
2. COMPETITOR_GAPS: Only name competitors explicitly mentioned in the data. Never invent names.
3. PRICING_SIGNALS insights: Must reference actual product names and/or dollar amounts from the data. The word "key insight" is BANNED — if you write it the app crashes.
4. HOT_COMMUNITIES: ONLY exact r/subredditname format (lowercase, no spaces, no prefixes like "Reddit's") OR "Hacker News". Never invent community names.
5. SOURCE field in PAIN_POINTS: Only values from AVAILABLE DATA SOURCES in the context. Never write a source not in that list.
6. frequency = your best integer estimate of how many times this pain point appeared across all sources.
7. activity must be exactly: "high", "medium", or "low"
8. Maximum 5 items per list section.
9. Return ONLY valid JSON in each section — no trailing commas, no code fences, no comments.
"""


async def analyze_stream(niche: str, raw_data: str):
    """Stream Groq analysis as text chunks."""
    user_message = f"Niche to analyze: {niche}\n\nWeb data collected:\n{raw_data}"

    try:
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            stream=True,
            max_tokens=2048,
            temperature=0.3,
        )

        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    except Exception as e:
        yield f"\n###ERROR###\n{str(e)}"
