"""Build saved profile cards from public GitHub REST data, using only Python."""

from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

from validate_profile_cards import CARD_DIRECTORY, validate_cards

USERNAME = "mitcheltu"


def github_json(path):
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "mitcheltu-profile-cards",
               "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request("https://api.github.com" + path, headers=headers), timeout=30) as response:
        return json.load(response)


def fetch_data():
    profile = github_json(f"/users/{USERNAME}")
    if profile.get("login", "").lower() != USERNAME:
        raise ValueError("Unexpected GitHub profile response")
    repos = []
    for page in range(1, 101):
        batch = github_json(f"/users/{USERNAME}/repos?type=owner&per_page=100&page={page}")
        if not isinstance(batch, list):
            raise ValueError("Unexpected repository response")
        for repo in batch:
            if repo.get("private") is not False:
                raise ValueError("Only public repositories may be displayed")
            for field in ("name", "fork", "stargazers_count", "forks_count", "language", "pushed_at"):
                if field not in repo:
                    raise ValueError(f"Missing repository field: {field}")
        repos.extend(batch)
        if len(batch) < 100:
            return profile, repos
    raise ValueError("Repository pagination exceeded safety limit; no cards updated")


def text(x, y, value, size=14, color="#c9d1d9", weight="400"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}">{escape(str(value))}</text>')


def card(title, width, body, updated):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="250" '
            f'viewBox="0 0 {width} 250" role="img" aria-labelledby="title desc">'
            f'<title id="title">{escape(title)}</title>'
            f'<desc id="desc">Public GitHub data for {USERNAME}. Updated {updated} UTC.</desc>'
            f'<rect x="0.5" y="0.5" width="{width-1}" height="249" rx="12" '
            'fill="#0d1117" stroke="#30363d"/>'
            '<g font-family="Arial,Helvetica,sans-serif">'
            + text(22, 34, title, 17, "#f0f6fc", "600")
            + body + text(22, 232, f"Updated {updated} UTC", 10, "#8b949e")
            + '</g></svg>')


def build_cards(profile, repos, updated):
    owned = [repo for repo in repos if not repo["fork"]]
    recent = sorted(
        (repo for repo in owned if repo["name"].lower() != USERNAME and repo["pushed_at"]),
        key=lambda repo: repo["pushed_at"], reverse=True,
    )[:4]
    body = text(22, 57, "Latest pushes to owned public repositories (excluding this profile)", 12, "#8b949e")
    for i, repo in enumerate(recent):
        y = 87 + i * 33
        name = repo["name"] if len(repo["name"]) <= 53 else repo["name"][:50] + "..."
        body += text(22, y, name)
        body += text(560, y, repo["pushed_at"][:10], 12, "#8b949e")
    if not recent:
        body += text(22, 110, "No public repository pushes available.")
    activity = card("Repository activity", 700, body, updated)

    metrics = [("Public repositories", len(repos)),
               ("Original repositories", len(owned)),
               ("Stars on original repos", sum(r["stargazers_count"] for r in owned)),
               ("Forks of original repos", sum(r["forks_count"] for r in owned)),
               ("Followers", profile["followers"])]
    body = ""
    for i, (label, value) in enumerate(metrics):
        y = 73 + i * 28
        body += text(22, y, label, 12)
        body += text(278, y, f"{value:,}", 14, "#f0f6fc", "600")
    stats = card("Public snapshot", 340, body, updated)

    counts = Counter(repo["language"] for repo in owned if repo["language"])
    ranked = counts.most_common(4)
    if len(counts) > 4:
        ranked.append(("Other", sum(counts.values()) - sum(n for _, n in ranked)))
    body = text(22, 55, "Primary language / original repository count", 11, "#8b949e")
    for i, (language, count) in enumerate(ranked):
        y = 80 + i * 27
        body += text(22, y, language[:25], 11)
        body += text(294, y, count, 11, "#f0f6fc")
        body += f'<rect x="22" y="{y+5}" width="290" height="4" rx="2" fill="#21262d"/>'
        body += (f'<rect x="22" y="{y+5}" width="{290*count/sum(counts.values()):.2f}" '
                 'height="4" rx="2" fill="#b1bac4"/>')
    if not ranked:
        body += text(22, 105, "No public language data available.", 12)
    languages = card("Languages", 340, body, updated)
    return {"0-profile-details.svg": activity, "1-repos-per-language.svg": languages,
            "3-stats.svg": stats}


def main():
    profile, repos = fetch_data()
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    generated = build_cards(profile, repos, updated)
    # A failed request or invalid render must leave every saved card untouched.
    with tempfile.TemporaryDirectory(prefix="profile-cards-") as temp:
        staged = Path(temp)
        for name, content in generated.items():
            (staged / name).write_text(content, encoding="utf-8")
        validate_cards(staged)
        CARD_DIRECTORY.mkdir(parents=True, exist_ok=True)
        for name, content in generated.items():
            (CARD_DIRECTORY / name).write_text(content, encoding="utf-8")
    print(f"Saved three cards from {len(repos)} public repositories.")


if __name__ == "__main__":
    main()
