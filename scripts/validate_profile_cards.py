"""Reject incomplete/error output before the workflow publishes any cards."""

from pathlib import Path
import xml.etree.ElementTree as ET

CARD_DIRECTORY = Path("profile-summary-card-output/github_dark")
CARD_NAMES = (
    "0-profile-details.svg",
    "1-repos-per-language.svg",
    "3-stats.svg",
)


def validate_cards(directory=CARD_DIRECTORY):
    for name in CARD_NAMES:
        path = directory / name
        root = ET.parse(path).getroot()
        if root.tag != "{http://www.w3.org/2000/svg}svg":
            raise ValueError(f"Not an SVG card: {path}")
        labels = " ".join(
            "".join(node.itertext())
            for node in root.iter("{http://www.w3.org/2000/svg}text")
        ).lower()
        if not labels.strip():
            raise ValueError(f"Card contains no text: {path}")
        error_labels = ("rate limit", "something went wrong", "bad credentials",
                        "maximum retries", "failed to", "error", "not found")
        if any(message in labels for message in error_labels):
            raise ValueError(f"Card contains an error message: {path}")
    print("All three profile cards validated; safe to publish.")


if __name__ == "__main__":
    validate_cards()
