"""
Text summarization logic
Integrated both Gemini API and fallback options
Went through several API changes
"""

import os
import re
import google.generativeai as genai
from newspaper import Article
import config

# Configure Gemini - had API key issues initially
genai.configure(api_key=config.GEMINI_API_KEY)
# model = genai.GenerativeModel('gemini-1.5-flash') : The first free model.
model = genai.GenerativeModel('gemini-2.0-flash-exp')


class SpiceSummarizer:
    """Main summarizer class - refactored 3 times"""

    def extract_text_from_url(self, url):
        """Extract article text from URL using newspaper4k"""
        try:
            article = Article(url)
            article.download()
            article.parse()
            return article.text
        except Exception as e:
            print(f"URL extraction failed: {e}")
            raise

    def is_text_too_long(self, text, max_words=5000):
        """Check if text exceeds word limit"""
        words = text.split()
        return len(words) > max_words

    def summarize(self, text, audience):
        """Main summarization function"""
        # Craft the prompt based on audience
        prompt = self._build_prompt(text, audience)

        try:
            response = model.generate_content(prompt)
            return self._parse_response(response.text)
        except Exception as e:
            print(f"API call failed: {e}")
            return self._get_fallback_response()

    def _build_prompt(self, text, audience):
        """Build the prompt for Gemini"""
        audience_instructions = {
            "kid": "Explain this like you're talking to a 10-year-old. Use simple words and fun examples.",
            "engineer": "Focus on technical details, specifications, and how things work.",
            "scientist": "Be precise and analytical. Highlight methods, data, and conclusions.",
            "busy worker": "Get straight to the point. Focus on key takeaways and action items.",
        }

        instruction = audience_instructions.get(audience, "Summarize this clearly:")

        return f"""
        {instruction}

        Please provide:
        1. A brief summary
        2. The overall sentiment (Positive/Negative/Neutral)
        3. 3-5 key points as bullet points

        Text to analyze:
        {text[:4000]}  # Truncate very long texts
        """

    def _parse_response(self, response_text):
        """Parse the API response - this parsing is kinda fragile"""
        lines = response_text.split('\n')
        summary = "Not available"
        sentiment = "Neutral"
        claims = []

        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if 'summary' in line.lower() or '1.' in line:
                current_section = 'summary'
                continue
            elif 'sentiment' in line.lower() or '2.' in line:
                current_section = 'sentiment'
                continue
            elif 'key' in line.lower() or '3.' in line or '•' in line or '-' in line:
                current_section = 'claims'
                continue

            if current_section == 'summary' and len(line) > 10:
                summary = line
            elif current_section == 'sentiment':
                for mood in ['Positive', 'Negative', 'Neutral']:
                    if mood in line:
                        sentiment = mood
                        break
            elif current_section == 'claims' and len(line) > 5:
                # Clean up bullet points
                clean_line = line.strip('•- ').strip()
                if clean_line and len(claims) < 5:
                    claims.append(clean_line)

        # Fallbacks if parsing didn't work well
        if not claims:
            claims = ["Key points not available"]

        return {
            'summary': summary,
            'sentiment': sentiment,
            'key_claims': claims[:4]  # Max 4 claims
        }

    def _get_fallback_response(self):
        """Return a fallback response when API fails"""
        return {
            'summary': "Sorry, I couldn't process that request right now.",
            'sentiment': "Neutral",
            'key_claims': ["Service temporarily unavailable"]
        }
