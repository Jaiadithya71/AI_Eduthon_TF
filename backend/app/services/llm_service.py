import json
from typing import List, Dict, Any

from groq import Groq

from app.core.config import settings
from app.models.schemas import (
    PresentationRequest,
    SlideContent,
    SlideType,
    AudienceLevel,
    PresentationStyle,
    Language,
)


class LLMService:
    """
    Service for interacting with Groq to generate
    high-quality, structured slide content.
    """

    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        print(">>> USING GROQ MODEL:", settings.GROQ_MODEL)

    # ---------------------------
    # PUBLIC: main entry point
    # ---------------------------
    def generate_slide_content(
        self, request: PresentationRequest
    ) -> List[SlideContent]:
        prompt = self._build_generation_prompt(request)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert teacher and presentation designer. "
                            "You create clear, structured, engaging slide decks for students."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.6,
                max_tokens=3500,
            )

            raw_text = response.choices[0].message.content
            slides_dict = self._extract_and_parse_json(raw_text)

            if not slides_dict:
                return self._generate_template_slides(request)

            return self._parse_slides(slides_dict, request)

        except Exception as e:
            print(f"Error in generate_slide_content: {e}")
            return self._generate_template_slides(request)

    # ---------------------------
    # NEW IMPROVED PROMPT
    # ---------------------------
    def _build_generation_prompt(self, request: PresentationRequest) -> str:

        audience_map = {
            AudienceLevel.ELEMENTARY: "children studying in grades 1–5",
            AudienceLevel.MIDDLE: "students in grades 6–8",
            AudienceLevel.HIGH: "class 9–12 students",
            AudienceLevel.COLLEGE: "undergraduate learners",
            AudienceLevel.PROFESSIONAL: "industry professionals",
        }

        style_map = {
            PresentationStyle.ACADEMIC: "structured, clear, textbook-oriented",
            PresentationStyle.STORYTELLING: "narrative with relatable scenarios and examples",
            PresentationStyle.INTERACTIVE: "engaging, question-based, activity-driven",
            PresentationStyle.TECHNICAL: "precise, systematic, process-focused",
            PresentationStyle.VISUAL: "minimal text, diagram-friendly, visual-oriented",
        }

        audience_desc = audience_map.get(request.audience_level, "students")
        style_desc = style_map.get(request.presentation_style, "clear and structured")

        language = request.language.value
        num_slides = request.num_slides
        include_quiz = request.include_quiz

        prompt = f"""
You are an expert educator who designs high-quality presentation slides.

TASK:
Generate EXACTLY {num_slides} slides about: "{request.topic}"

REQUIREMENTS:
- Write all content in {language}.
- Each slide must have **4–6 rich bullet points** (not short phrases).
- Bullets must be explanatory, clear, and teaching-oriented.
- Every slide must include one relevant short English "image_query".
- Speaker notes must be 2–3 sentences if requested.

SLIDE STRUCTURE:
1. TITLE slide  
2. Overview / introduction  
3. Core concept slides  
4. Real-world examples / applications  
5. {"Quiz slide" if include_quiz else "Optional quiz slide only if meaningful"}  
6. Summary slide

ALLOWED SLIDE TYPES:
"title", "content", "summary", "quiz", "image_heavy"

FORMAT (VERY IMPORTANT):
Return ONLY this JSON (no markdown fences):

{{
  "slides": [
    {{
      "type": "content",
      "title": "...",
      "subtitle": null,
      "content": ["bullet 1", "bullet 2", "bullet 3", "bullet 4"],
      "image_query": "educational photo of ...",
      "speaker_notes": "2–3 sentence explanation."
    }}
  ]
}}

Make the content deeply informative, well-structured, and age-appropriate for {audience_desc}.
"""
        return prompt.strip()

    # ---------------------------
    # JSON HANDLING
    # ---------------------------
    def _extract_and_parse_json(self, text: str) -> Dict[str, Any] | None:
        if not text:
            return None

        if "```" in text:
            parts = text.split("```")
            candidate = None
            for part in parts:
                if "{" in part:
                    candidate = part
                    break
            text = candidate or text

        text = text.strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end <= start:
            return None

        json_str = text[start: end + 1]

        try:
            return json.loads(json_str)
        except Exception as e:
            print(f"JSON parse error: {e}")
            print("RAW TEXT:", text[:400])
            return None

    # ---------------------------
    # SLIDE PARSING
    # ---------------------------
    def _parse_slides(
        self, slides_data: Dict[str, Any], request: PresentationRequest
    ) -> List[SlideContent]:

        raw_slides = slides_data.get("slides", [])
        slides: List[SlideContent] = []

        if not isinstance(raw_slides, list):
            return self._generate_template_slides(request)

        for slide_data in raw_slides:

            slide_type_str = str(slide_data.get("type", "content")).lower()
            try:
                slide_type = SlideType(slide_type_str)
            except:
                slide_type = SlideType.CONTENT

            content_list = []
            content = slide_data.get("content", [])

            if isinstance(content, str):
                content_list = [content]
            elif isinstance(content, list):
                content_list = [str(item) for item in content if item]

            notes = slide_data.get("speaker_notes")
            if not request.speaker_notes:
                notes = None

            slides.append(
                SlideContent(
                    type=slide_type,
                    title=str(slide_data.get("title", request.topic)),
                    subtitle=slide_data.get("subtitle"),
                    content=content_list,
                    image_query=slide_data.get("image_query") or request.topic,
                    image_url=None,
                    speaker_notes=notes,
                    layout="default",
                )
            )

        return slides

    # ---------------------------
    # SIMPLE TEMPLATE FALLBACK
    # ---------------------------
    def _generate_template_slides(self, request: PresentationRequest) -> List[SlideContent]:

        slides: List[SlideContent] = []

        slides.append(
            SlideContent(
                type=SlideType.TITLE,
                title=request.topic,
                subtitle=None,
                content=[],
                image_query=request.topic,
                image_url=None,
                speaker_notes=None,
                layout="default",
            )
        )

        for i in range(1, request.num_slides):
            slides.append(
                SlideContent(
                    type=SlideType.CONTENT,
                    title=f"{request.topic} – Key Idea {i}",
                    subtitle=None,
                    content=[
                        f"Important concept {i}",
                        f"Explanation {i}",
                        f"Example {i}",
                    ],
                    image_query=request.topic,
                    image_url=None,
                    speaker_notes=None,
                    layout="default",
                )
            )

        return slides


llm_service = LLMService()
