#!/usr/bin/env python3
"""
Simple Wiki Video Generator for Social AI Reply / RedditFlow

This script generates a video overview of the wiki documentation using PIL and ffmpeg.
It can be run independently and the code is kept for future editing.

Usage:
    python video/generate_wiki_video_simple.py

Output:
    video/overview.mp4 - Video overview of the wiki
"""

import subprocess
import tempfile
from pathlib import Path

from video.slides import SlideRenderer


class SimpleWikiVideoGenerator:
    """Generates a video overview of the wiki documentation using PIL and ffmpeg."""

    def __init__(self, wiki_dir: str = "wiki", output_dir: str = "video"):
        self.wiki_dir = Path(wiki_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.fps = 30
        self.renderer = SlideRenderer()

    def save_slide(self, slide, slide_number: int, temp_dir: Path) -> Path:
        """Save a slide as an image file."""
        slide_path = temp_dir / f"slide_{slide_number:03d}.png"
        slide.save(slide_path, "PNG")
        return slide_path

    def generate_video(self) -> str:
        """Generate the complete video."""
        print("Generating wiki video overview...")

        slides_with_duration = self.renderer.get_all_slides()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "input.txt"

            with open(input_file, "w") as f:
                for i, (slide, duration) in enumerate(slides_with_duration):
                    slide_path = self.save_slide(slide, i, temp_path)
                    f.write(f"file '{slide_path}'\n")
                    f.write(f"duration {duration}\n")
                    print(f"Created slide {i+1}/{len(slides_with_duration)}")
                # Add last slide again for ffmpeg concat
                f.write(f"file '{self.save_slide(slides_with_duration[-1][0], len(slides_with_duration), temp_path)}'\n")

            output_path = self.output_dir / "overview.mp4"
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(input_file),
                "-vf", f"fps={self.fps}",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                str(output_path),
            ]

            subprocess.run(cmd, check=True, capture_output=True)

            print(f"Video generated: {output_path}")
            return str(output_path)


def main():
    """Main entry point."""
    generator = SimpleWikiVideoGenerator()
    output_path = generator.generate_video()
    print(f"Video saved to: {output_path}")


if __name__ == "__main__":
    main()
