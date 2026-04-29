"""
Quick Post — One command, post everywhere!
==========================================
Run this script, type your message, and it goes to ALL social media platforms.

Usage:
    python quick_post.py                          # Interactive — ask for text
    python quick_post.py "Hello from AI Employee!"  # Direct text
    python quick_post.py "Hello!" --image photo.jpg  # Text + image
    python quick_post.py --file my_post.md          # From file
    python quick_post.py "Hello!" --platforms linkedin,twitter  # Specific platforms only
"""

import sys
from pathlib import Path

VAULT = Path(__file__).parent.resolve()
sys.path.insert(0, str(VAULT))

from post_everywhere import main as post_main


def run():
    # If no arguments given, ask interactively
    if len(sys.argv) == 1:
        print()
        print("=" * 55)
        print("  QUICK POST — Post to ALL Social Media at once!")
        print("=" * 55)
        print()
        print("Platforms: LinkedIn, Facebook, Instagram, Twitter/X, WhatsApp")
        print()

        text = input("Type your post message:\n> ").strip()
        if not text:
            print("No text entered. Exiting.")
            sys.exit(1)

        image = input("\nImage path (press Enter to skip): ").strip()

        platforms_input = input(
            "\nPlatforms (press Enter for ALL, or type e.g. linkedin,twitter): "
        ).strip()

        # Build sys.argv for post_everywhere
        sys.argv = ["post_everywhere", "--text", text]
        if image:
            sys.argv += ["--image", image]
        if platforms_input:
            sys.argv += ["--platforms", platforms_input]

        print()
        print("-" * 55)
        print(f"  Posting: {text[:70]}{'...' if len(text) > 70 else ''}")
        print(f"  Image:   {image or '(none)'}")
        print(f"  To:      {platforms_input or 'ALL platforms'}")
        print("-" * 55)
        print()

        confirm = input("Confirm? (y/n): ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            sys.exit(0)

        print()
        post_main()

    else:
        # CLI mode — pass first positional arg as --text
        args = sys.argv[1:]

        # If first arg doesn't start with --, treat it as the text
        if args and not args[0].startswith("--"):
            text = args.pop(0)
            sys.argv = ["post_everywhere", "--text", text] + args
        else:
            sys.argv = ["post_everywhere"] + args

        post_main()


if __name__ == "__main__":
    run()
