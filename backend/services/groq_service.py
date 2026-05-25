from groq import Groq
import os
import logging
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior market intelligence analyst. Extract insights from the web data provided and return them in the exact JSON format shown below.

════════════════════════════════
EXAMPLE OF CORRECT OUTPUT
(This is a template — replace every value with real data from the context)
════════════════════════════════

###PAIN_POINTS###
[
  {"text": "Calendly locks buffer time between meetings behind the $16/mo Essentials plan — users on free tier report back-to-back bookings with no recovery gap", "frequency": 14, "source": "Tavily"},
  {"text": "Acuity Scheduling charges $20/month minimum — solo freelancers on Reddit say it's overpriced for 1-person operations", "frequency": 9, "source": "Exa"},
  {"text": "Setmore's free tier limits users to 1 staff calendar — teams of 2+ must pay $12/user/month", "frequency": 6, "source": "Hacker News"}
]

###COMPETITOR_GAPS###
[
  {"competitor": "Calendly", "gap": "No client intake forms on free tier — upgrading to $16/mo just to ask booking questions", "opportunity": "Include custom intake forms in the free tier as default"},
  {"competitor": "Acuity Scheduling", "gap": "No AI-suggested time slots — users manually browse availability", "opportunity": "Add AI scheduling assistant that proposes optimal slots based on past patterns"}
]

###PRICING_SIGNALS###
{"competitor_range": "$0-$40/month", "willingness_to_pay": "$8-$20/month", "insights": ["Calendly Essentials costs $16/month per user — the most-cited price in user complaints", "Cal.com open-source free tier converts users to paid $15/month Pro plan"]}

###HOT_COMMUNITIES###
[
  {"name": "r/freelance", "members": "150K", "activity": "high"},
  {"name": "r/solopreneur", "members": "45K", "activity": "high"},
  {"name": "r/productivity", "members": "900K", "activity": "high"},
  {"name": "Hacker News", "members": "400K+", "activity": "high"}
]

###AI_SUMMARY###
Freelance scheduling is a $400M+ market with Calendly ($16/mo) and Acuity ($20/mo) dominating but leaving gaps in affordability and AI features. Users consistently pay $8-20/month and want buffer time control and client intake forms without a paywall. A founder should launch with those two features free and monetize on team collaboration.

════════════════════════════════
YOUR TASK
════════════════════════════════

Now do the same for the actual niche and web data in the user message.

RULES (failure to follow = broken output):
1. PAIN_POINTS: Each item must name the specific product AND the specific broken feature. Never write generic phrases like "complex scheduling" or "high costs" without a product name. If data is sparse, write 2 good items rather than 5 vague ones.

2. COMPETITOR_GAPS: Only name competitors mentioned in the data. Never invent names.

3. PRICING_SIGNALS insights: Each insight needs a product name AND a dollar amount. Never write "Pricing varies by plan" — that phrase is banned.

4. HOT_COMMUNITIES: Use the SUGGESTED COMMUNITIES list provided in the context. Pick the most relevant ones and use the exact format shown: r/subredditname or "Hacker News". Always return 3-5 items.

5. SOURCE in PAIN_POINTS: Only values listed in AVAILABLE DATA SOURCES. Never invent a source name.

6. frequency = integer estimate of how often this pain appeared across all sources.

7. activity = exactly "high", "medium", or "low".

8. Maximum 5 items per list section.

9. Pure JSON only — no markdown code fences (no ```), no trailing commas, no comments.
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
            max_tokens=3000,
            temperature=0.3,
        )

        full_text = []
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_text.append(content)
                yield content

        # Log full AI output so we can debug quality issues
        logger.info("=== RAW GROQ OUTPUT ===\n%s\n======================", "".join(full_text))

    except Exception as e:
        yield f"\n###ERROR###\n{str(e)}"
