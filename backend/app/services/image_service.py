import hashlib
from typing import Optional, List, Set

import requests
from app.core.config import settings

# OpenAI is optional – hybrid mode works even if it's missing
try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None


class ImageService:
    """
    Hybrid Image Engine

    - Uses OpenAI for clean educational diagrams when helpful.
    - Uses Pexels for realistic photos.
    - Filters out people / classroom / ADHD stock images.
    - Avoids repeating the same URL across slides.
    """

    def __init__(self) -> None:
        # Pexels
        self.api_key = getattr(settings, "PEXELS_API_KEY", None)
        self.base_url = "https://api.pexels.com/v1"

        # OpenAI (optional)
        self.openai_api_key = getattr(settings, "OPENAI_API_KEY", None)
        self.openai_image_model = getattr(
            settings, "OPENAI_IMAGE_MODEL", "gpt-image-1"
        )
        self.image_strategy = getattr(
            settings, "IMAGE_STRATEGY", "hybrid"
        ).lower()  # "hybrid" / "pexels" / "openai"

        self._openai_client = None
        if OpenAI is not None and self.openai_api_key:
            try:
                self._openai_client = OpenAI(api_key=self.openai_api_key)
            except Exception as e:
                print(f"[OpenAI] Failed to init image client: {e}")
                self._openai_client = None

    # ------------------------------------------------------------------
    # PUBLIC HYBRID ENTRY
    # ------------------------------------------------------------------
    def get_hybrid_image_for_slide(
        self,
        topic: str,
        slide,
        slide_index: int,
        language,
        presentation_style,
        used_urls: Set[str],
    ) -> Optional[str]:
        """
        Decide the best image provider for this slide and return a URL.
        """

        topic_text = (topic or "").strip()
        style_val = getattr(presentation_style, "value", str(presentation_style)).lower()
        lang_val = getattr(language, "value", str(language)).lower()
        title = (slide.title or "").strip()

        needs_diagram = self._needs_diagram(topic_text, title, style_val)

        # Helper to avoid repetition
        def remember(url: Optional[str]) -> Optional[str]:
            if url and url not in used_urls:
                used_urls.add(url)
            return url

        # Strategy 1: OpenAI diagrams when needed & available
        if self._openai_client and self.image_strategy in {"hybrid", "openai"}:
            if needs_diagram:
                ai_url = self._generate_openai_diagram(
                    topic=topic_text,
                    slide_title=title,
                    slide_type=getattr(slide, "type", None),
                    language=lang_val,
                )
                if ai_url and ai_url not in used_urls:
                    return remember(ai_url)

        # Strategy 2: Pexels (primary in most cases)
        if self.image_strategy in {"hybrid", "pexels"}:
            pexels_url = self._search_pexels_for_slide(
                topic=topic_text,
                slide=slide,
                slide_index=slide_index,
                used_urls=used_urls,
            )
            if pexels_url:
                return remember(pexels_url)

        # Strategy 3: Fallback to OpenAI if we didn't use it yet
        if (
            self._openai_client
            and self.image_strategy in {"hybrid", "openai"}
            and not needs_diagram
        ):
            ai_url = self._generate_openai_diagram(
                topic=topic_text,
                slide_title=title,
                slide_type=getattr(slide, "type", None),
                language=lang_val,
            )
            if ai_url:
                return remember(ai_url)

        # Final fallback: placeholder
        return self._get_placeholder_image(topic_text or title or "education")

    # ------------------------------------------------------------------
    # DECISION: does this slide really need a diagram?
    # ------------------------------------------------------------------
    def _needs_diagram(self, topic: str, title: str, style_val: str) -> bool:
        text = f"{topic} {title}".lower()

        # Obvious STEM / diagram-heavy topics
        diagram_keywords = [
            "regression",
            "linear regression",
            "logistic regression",
            "machine learning",
            "neural network",
            "algorithm",
            "data structure",
            "statistics",
            "probability",
            "graph theory",
            "function",
            "equation",
            "calculus",
            "derivative",
            "integral",
            "matrix",
            "vector",
            "physics",
            "chemistry",
            "digestive",
            "stomach",
            "intestine",
            "esophagus",
            "heart",
            "circulatory",
            "respiratory",
            "lungs",
            "brain",
            "nervous system",
            "kidney",
            "liver",
            "orbit",
            "solar system",
            "circuit",
            "transistor",
            "os",
            "operating system",
            "computer architecture",
        ]

        if any(k in text for k in diagram_keywords):
            return True

        # Strong technical styles also benefit from diagrams
        if any(tag in style_val for tag in ["technical", "deep_dive", "technical_deep_dive"]):
            return True

        return False

    # ------------------------------------------------------------------
    # OPENAI IMAGE GENERATION
    # ------------------------------------------------------------------
    def _generate_openai_diagram(
        self,
        topic: str,
        slide_title: str,
        slide_type,
        language: str,
    ) -> Optional[str]:
        """
        Generate a simple educational diagram via OpenAI images.
        Returns an image URL if successful.
        """
        if not self._openai_client:
            return None

        base = topic or slide_title or "educational concept"
        base = base.strip()

        # Hint based on slide type
        slide_type_name = getattr(slide_type, "value", str(slide_type) or "").lower()
        type_hint = ""
        if "title" in slide_type_name:
            type_hint = "overview concept illustration"
        elif "summary" in slide_type_name:
            type_hint = "summary infographic with simple visual metaphor"
        elif "quiz" in slide_type_name:
            type_hint = "clean quiz iconography without text"
        else:
            type_hint = "process or relationship diagram"

        prompt = (
            f"Flat, clean educational diagram about '{base}'. "
            f"Show the key idea visually, with arrows or simple shapes. "
            f"No human faces, no classroom photos. "
            f"White or light background, high contrast, suitable for a PowerPoint slide. "
            f"Style: minimal, vector-like illustration. {type_hint}."
        )

        try:
            result = self._openai_client.images.generate(
                model=self.openai_image_model,
                prompt=prompt,
                size="1024x1024",
                n=1,
            )
            data = getattr(result, "data", None) or []
            if not data:
                return None

            item = data[0]
            # Newer OpenAI clients expose 'url'
            url = getattr(item, "url", None)
            if not url:
                # some clients use dict-like objects
                url = getattr(item, "get", lambda *_a, **_k: None)("url")
            return url
        except Exception as e:
            print(f"[OpenAI] Image generation failed: {e}")
            return None

    # ------------------------------------------------------------------
    # PEXELS SEARCH + RANKING
    # ------------------------------------------------------------------
    def _search_pexels_for_slide(
        self,
        topic: str,
        slide,
        slide_index: int,
        used_urls: Set[str],
    ) -> Optional[str]:
        """
        Search Pexels with a smart query, rank images, avoid bad ones and repeats.
        """
        query = self._build_pexels_query(topic, slide)

        if not self.api_key or self.api_key == "your_pexels_api_key_here":
            # No key – fallback to placeholder
            return self._get_placeholder_image(query or topic)

        try:
            url = f"{self.base_url}/search"
            params = {
                "query": query,
                "orientation": "landscape",
                "per_page": 20,
            }
            headers = {"Authorization": self.api_key}

            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            photos: List[dict] = data.get("photos") or []
            if not photos:
                return None

            primary_hint = self._extract_primary_keyword(query or topic)
            return self._pick_best_photo(
                photos=photos,
                primary_hint=primary_hint,
                avoid_urls=used_urls,
                slide_index=slide_index,
            )

        except Exception as e:
            print(f"[Pexels] Error for query '{query}': {e}")
            return None

    def _build_pexels_query(self, topic: str, slide) -> str:
        topic = (topic or "").strip()
        title = (slide.title or "").strip()
        base_query = getattr(slide, "image_query", "") or ""
        base_query = base_query.strip()

        pieces: List[str] = []

        if topic:
            pieces.append(topic)

        if title and title.lower() not in topic.lower():
            pieces.append(title)

        if base_query and base_query.lower() not in topic.lower():
            pieces.append(base_query)

        text = f"{topic} {title}".lower()

        # Domain hints
        if any(k in text for k in ["regression", "statistics", "machine learning"]):
            pieces.append("regression line data chart scatter plot")
        elif any(k in text for k in ["digestive", "stomach", "intestine", "esophagus", "pancreas", "liver"]):
            pieces.append("digestive system anatomy medical illustration")
        elif any(k in text for k in ["heart", "circulatory", "cardio"]):
            pieces.append("heart anatomy circulatory system medical diagram")
        elif any(k in text for k in ["brain", "nervous system"]):
            pieces.append("brain anatomy neuron diagram")
        else:
            pieces.append("education diagram illustration")

        return " ".join(pieces).strip()

    def _pick_best_photo(
        self,
        photos: List[dict],
        primary_hint: Optional[str],
        avoid_urls: Set[str],
        slide_index: int,
    ) -> Optional[str]:
        """
        Score and pick the best Pexels photo:

        - Prefer diagrams / charts / anatomy.
        - Avoid people / classroom / ADHD / mental health images.
        - Avoid URLs already used in this deck.
        - Use slide_index to vary choice across slides.
        """

        if not photos:
            return None

        person_words = [
            "person",
            "people",
            "man",
            "woman",
            "boy",
            "girl",
            "child",
            "children",
            "students",
            "student",
            "teacher",
            "portrait",
            "face",
            "selfie",
            "classroom",
            "class room",
            "meeting",
            "team",
            "group of people",
            "adhd",
            "mental",
            "psychology",
            "therapy",
            "counseling",
        ]

        diagram_keywords = [
            "diagram",
            "graph",
            "chart",
            "plot",
            "equation",
            "formula",
            "data",
            "analytics",
            "statistics",
            "regression",
            "anatomy",
            "organ",
            "medical",
            "biology",
            "microscope",
            "infographic",
            "illustration",
            "concept map",
            "x-ray",
        ]

        def is_persony(alt: str) -> bool:
            return any(w in alt for w in person_words)

        def has_diagram_word(alt: str) -> bool:
            return any(w in alt for w in diagram_keywords)

        def has_primary_hint(alt: str) -> bool:
            return bool(primary_hint) and primary_hint in alt

        def photo_url(photo: dict) -> Optional[str]:
            src = photo.get("src") or {}
            return src.get("large") or src.get("medium") or src.get("original")

        scored = []
        for p in photos:
            url = photo_url(p)
            if not url:
                continue

            alt = str(p.get("alt", "")).lower()

            score = 0
            if has_diagram_word(alt):
                score += 4
            if has_primary_hint(alt):
                score += 3
            if is_persony(alt):
                score -= 4

            # Small bonus for landscape-ish dimensions if available
            width = p.get("width") or 0
            height = p.get("height") or 0
            if width and height and width > height:
                score += 1

            scored.append((score, url))

        if not scored:
            return None

        # Sort by score (best first)
        scored.sort(key=lambda t: t[0], reverse=True)

        # Filter out already used URLs if possible
        fresh = [(s, u) for (s, u) in scored if u not in avoid_urls]
        if fresh:
            scored = fresh

        # Deterministic choice based on slide_index
        idx = slide_index % len(scored)
        _, chosen_url = scored[idx]
        return chosen_url

    # ------------------------------------------------------------------
    # PRIMARY KEYWORD EXTRACTION
    # ------------------------------------------------------------------
    def _extract_primary_keyword(self, text: str) -> Optional[str]:
        text = (text or "").lower()
        tokens = [t for t in text.replace("/", " ").split() if t.isalpha()]

        stop = {
            "the",
            "and",
            "of",
            "for",
            "in",
            "to",
            "a",
            "an",
            "on",
            "with",
            "introduction",
            "overview",
            "diagram",
            "illustration",
            "education",
            "system",
            "process",
        }

        filtered = [t for t in tokens if t not in stop]
        if not filtered:
            return None

        filtered.sort(key=len, reverse=True)
        return filtered[0]

    # ------------------------------------------------------------------
    # MULTI-IMAGE FETCH (still available if needed)
    # ------------------------------------------------------------------
    def get_multiple_images(
        self,
        queries: List[str],
        orientation: str = "landscape",
    ) -> List[Optional[str]]:
        results: List[Optional[str]] = []
        for q in queries:
            # Use Pexels search here; hybrid is mainly per-slide
            url = self.search_image(q, orientation=orientation, per_page=10)
            results.append(url)
        return results

    # Simple direct search if you still need it elsewhere
    def search_image(
        self,
        query: str,
        orientation: str = "landscape",
        per_page: int = 1,
    ) -> Optional[str]:
        return self._search_pexels_for_slide(
            topic=query,
            slide=type("DummySlide", (), {"title": query, "image_query": ""})(),
            slide_index=0,
            used_urls=set(),
        )

    # ------------------------------------------------------------------
    # PLACEHOLDER / FALLBACK
    # ------------------------------------------------------------------
    def _get_placeholder_image(self, query: str) -> str:
        """
        Deterministic but varied placeholder image using a hash of the query.
        """
        base = (query or "lesson").strip().lower()
        digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:8]
        seed = f"{base}-{digest}"
        return f"https://picsum.photos/seed/{seed}/1600/900"

    # ------------------------------------------------------------------
    # EDUCATIONAL IMAGE HELPER
    # ------------------------------------------------------------------
    def get_educational_image(
        self,
        topic: str,
        subject: Optional[str] = None,
    ) -> str:
        topic = (topic or "").strip()
        if subject:
            base = f"{subject} {topic}".strip()
        else:
            base = topic

        enriched = f"{base} educational diagram illustration"
        url = self._search_pexels_for_slide(
            topic=enriched,
            slide=type("DummySlide", (), {"title": base, "image_query": ""})(),
            slide_index=0,
            used_urls=set(),
        )

        if not url:
            url = self._get_placeholder_image(topic or "education")

        return url


# Singleton instance
image_service = ImageService()
