#!/usr/bin/env python3
"""
Wiki Video Generator for Social AI Reply / RedditFlow

This script generates a video overview of the wiki documentation using moviepy.
It can be run independently and the code is kept for future editing.

Usage:
    python video/generate_wiki_video.py

Output:
    video/overview.mp4 - Video overview of the wiki
"""

import os
import sys
from pathlib import Path

import numpy as np
from moviepy import (
    ImageClip,
    concatenate_videoclips,
)

from video.slides import SlideRenderer


class WikiVideoGenerator:
    """Generates a video overview of the wiki documentation using moviepy."""

    def __init__(self, wiki_dir: str = "wiki", output_dir: str = "video"):
        self.wiki_dir = Path(wiki_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.fps = 30
        self.renderer = SlideRenderer()

    def generate_video(self) -> str:
        """Generate the complete video."""
        print("Generating wiki video overview...")

        slides_with_duration = self.renderer.get_all_slides()
        slides = [
            ImageClip(np.array(img)).with_duration(duration)
            for img, duration in slides_with_duration
        ]

        final_video = concatenate_videoclips(slides, method="compose")

        output_path = self.output_dir / "overview.mp4"
        final_video.write_videofile(
            str(output_path),
            fps=self.fps,
            codec="libx264",
            audio=False,
            logger=None,
        )

        print(f"Video generated: {output_path}")
        return str(output_path)


def main():
    """Main entry point."""
    generator = WikiVideoGenerator()
    output_path = generator.generate_video()
    print(f"Video saved to: {output_path}")


if __name__ == "__main__":
    main()
