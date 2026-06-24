"""
Shared slide generation for wiki video overview.

This module contains the common slide rendering logic used by both
the moviepy and PIL/ffmpeg video generators. Each generator only
implements its video-encoding backend.

Usage:
    from video.slides import SlideRenderer

    renderer = SlideRenderer()
    title_slide = renderer.create_title_slide()  # Returns PIL Image
    section_slide = renderer.create_section_slide("Title", ["Item 1", "Item 2"])
"""

from PIL import Image, ImageDraw, ImageFont


class SlideRenderer:
    """Renders slide images for the wiki video overview."""

    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height

        # Colors
        self.bg_color = (15, 23, 42)  # Dark blue-gray
        self.text_color = (255, 255, 255)  # White
        self.accent_color = (59, 130, 246)  # Blue
        self.secondary_color = (148, 163, 184)  # Gray

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Load a font with fallback to default."""
        try:
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
        except (OSError, IOError):
            return ImageFont.load_default()

    def create_title_slide(self) -> Image.Image:
        """Create the title slide."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)

        title_font = self._load_font(72)
        subtitle_font = self._load_font(36)

        title = "Social AI Reply / RedditFlow"
        subtitle = "Wiki Documentation Overview"
        branding = "360 Flatmates"

        # Center title
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (self.width - title_width) // 2
        title_y = self.height // 2 - 100
        draw.text((title_x, title_y), title, fill=self.text_color, font=title_font)

        # Center subtitle
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = (self.width - subtitle_width) // 2
        subtitle_y = title_y + 100
        draw.text((subtitle_x, subtitle_y), subtitle, fill=self.secondary_color, font=subtitle_font)

        # Center branding
        branding_bbox = draw.textbbox((0, 0), branding, font=subtitle_font)
        branding_width = branding_bbox[2] - branding_bbox[0]
        branding_x = (self.width - branding_width) // 2
        branding_y = self.height - 100
        draw.text((branding_x, branding_y), branding, fill=self.accent_color, font=subtitle_font)

        return img

    def create_section_slide(self, title: str, items: list[str]) -> Image.Image:
        """Create a section slide with title and bullet points."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)

        title_font = self._load_font(48)
        item_font = self._load_font(28)

        draw.text((100, 100), title, fill=self.accent_color, font=title_font)

        y_offset = 200
        for item in items[:8]:
            draw.text((150, y_offset), f"\u2022 {item}", fill=self.text_color, font=item_font)
            y_offset += 50

        return img

    def create_architecture_slide(self) -> Image.Image:
        """Create an architecture overview slide."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)

        title_font = self._load_font(48)
        box_font = self._load_font(24)

        draw.text((100, 50), "Architecture Overview", fill=self.accent_color, font=title_font)

        boxes = [
            {"title": "Frontend", "items": ["Next.js 16", "React 19", "Tailwind CSS"], "x": 100, "y": 200},
            {"title": "Backend", "items": ["FastAPI", "Python 3.11", "Supabase"], "x": 700, "y": 200},
            {"title": "Agents", "items": ["10 Specialized", "Multi-agent", "System"], "x": 1300, "y": 200},
            {"title": "Database", "items": ["Supabase Postgres", "Redis Cache", "File Storage"], "x": 100, "y": 600},
            {"title": "LLM", "items": ["Gemini", "OpenAI", "Claude"], "x": 700, "y": 600},
            {"title": "External", "items": ["Reddit API", "HN API", "Web Scraping"], "x": 1300, "y": 600},
        ]

        for box in boxes:
            draw.rectangle(
                [box["x"], box["y"], box["x"] + 400, box["y"] + 200],
                fill=(30, 41, 59),
                outline=self.accent_color,
                width=2,
            )
            draw.text((box["x"] + 20, box["y"] + 20), box["title"], fill=self.text_color, font=box_font)

            y_offset = box["y"] + 60
            for item in box["items"]:
                draw.text((box["x"] + 40, y_offset), f"\u2022 {item}", fill=self.secondary_color, font=box_font)
                y_offset += 30

        return img

    def create_agents_slide(self) -> Image.Image:
        """Create a slide showing all 10 agents."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)

        title_font = self._load_font(48)
        agent_font = self._load_font(24)

        draw.text((100, 50), "10 Specialized Agents", fill=self.accent_color, font=title_font)

        agents = [
            "Brand Brain - Website analysis",
            "Reddit Agent - Post discovery",
            "Hacker News Agent - Tech discussions",
            "SEO Agent - Website audit",
            "GEO Agent - AI search visibility",
            "Articles Agent - Content briefs",
            "X Agent - Twitter ideas",
            "LinkedIn Agent - Professional posts",
            "UGC Agent - Video briefs",
            "Technical SEO Agent - Code audit",
        ]

        y_offset = 150
        for i, agent in enumerate(agents):
            x_offset = 100 if i < 5 else 900
            if i == 5:
                y_offset = 150
            draw.text((x_offset, y_offset), f"{i+1}. {agent}", fill=self.text_color, font=agent_font)
            y_offset += 60

        return img

    def get_all_slides(self) -> list[tuple[Image.Image, float]]:
        """Return all slides with their durations (seconds).

        Returns:
            List of (image, duration_seconds) tuples.
        """
        return [
            (self.create_title_slide(), 4.0),
            (self.create_section_slide(
                "Core Features",
                [
                    "Multi-agent AI marketing platform",
                    "Transparent relevance scoring",
                    "Manual posting (no auto-posting)",
                    "Free/open-source-first approach",
                    "10 specialized marketing agents",
                    "LLM provider flexibility",
                ],
            ), 4.0),
            (self.create_architecture_slide(), 8.0),
            (self.create_agents_slide(), 8.0),
            (self.create_section_slide(
                "Technical Stack",
                [
                    "Backend: FastAPI + Python 3.11",
                    "Frontend: Next.js 16 + React 19",
                    "Database: Supabase Postgres",
                    "Auth: Supabase Auth with JWT",
                    "Embeddings: TF-IDF + sentence-transformers",
                    "LLM: Gemini, OpenAI, Claude, Perplexity",
                ],
            ), 4.0),
            (self.create_section_slide(
                "Deployment",
                [
                    "Backend: Railway",
                    "Frontend: Netlify",
                    "Database: Supabase (managed)",
                    "CI/CD: GitHub Actions",
                    "Automatic wiki publishing",
                ],
            ), 4.0),
        ]
