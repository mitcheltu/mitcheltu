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
    # This is a distribution of each repository's latest push, not commit history.
    today = datetime.strptime(updated, "%Y-%m-%d")
    month_index = today.year * 12 + today.month - 1
    months = [divmod(month_index - offset, 12) for offset in range(11, -1, -1)]
    month_keys = [f"{year:04d}-{month + 1:02d}" for year, month in months]
    latest = Counter(repo["pushed_at"][:7] for repo in owned
                     if repo["name"].lower() != USERNAME and repo["pushed_at"])
    values = [latest[key] for key in month_keys]
    peak = max(max(values), 1)
    body = text(22, 55, "Original public repositories by latest push month; profile excluded", 11, "#8b949e")
    left, top, bottom, chart_width = 48, 79, 187, 626
    for tick in sorted({0, peak // 2, peak}):
        y = bottom - (bottom - top) * tick / peak
        body += f'<path d="M {left} {y:.2f} H 674" stroke="#30363d"/>'
        body += text(25, y + 4, tick, 10, "#8b949e")
    for i, ((year, month), value) in enumerate(zip(months, values)):
        x = left + i * chart_width / 12 + 12
        height = (bottom - top) * value / peak
        body += (f'<rect x="{x:.2f}" y="{bottom-height:.2f}" width="27" '
                 f'height="{height:.2f}" rx="3" fill="#b1bac4">'
                 f'<title>{month_keys[i]}: {value} repositories</title></rect>')
        if value:
            body += text(x + 9, bottom - height - 6, value, 10, "#f0f6fc")
        label = datetime(year, month + 1, 1).strftime("%b")
        body += text(x + 3, 204, label, 10, "#8b949e")
    body += text(566, 232, f"{month_keys[0]} / {month_keys[-1]}", 9, "#8b949e")
    activity = card("Repository recency", 700, body, updated)

    metrics = [("Public repositories", len(repos)),
               ("Original repositories", len(owned)),
               ("Stars on original repos", sum(r["stargazers_count"] for r in owned)),
               ("Forks of original repos", sum(r["forks_count"] for r in owned)),
               ("Followers", profile["followers"])]
    body = text(22, 55, "Counts on a shared linear scale", 11, "#8b949e")
    maximum = max(1, max(value for _, value in metrics))
    for x in (180, 233, 286):
        body += f'<path d="M {x} 66 V 201" stroke="#21262d"/>'
    for i, (label, value) in enumerate(metrics):
        y = 82 + i * 27
        body += text(22, y, label, 11)
        body += (f'<rect x="180" y="{y-11}" width="{106*value/maximum:.2f}" '
                 f'height="14" rx="2" fill="#b1bac4"><title>{escape(label)}: {value}</title></rect>')
        body += text(297, y, f"{value:,}", 11, "#f0f6fc", "600")
    stats = card("Public snapshot", 340, body, updated)

    counts = Counter(repo["language"] for repo in owned if repo["language"])
    ranked = counts.most_common(4)
    if len(counts) > 4:
        ranked.append(("Other", sum(counts.values()) - sum(n for _, n in ranked)))
    body = text(22, 55, "Primary language of original public repositories", 10, "#8b949e")
    total = sum(counts.values())
    palette = ["#f0f6fc", "#b1bac4", "#8b949e", "#6e7681", "#484f58"]
    body += '<circle cx="89" cy="135" r="49" fill="none" stroke="#21262d" stroke-width="17"/>'
    offset = 0
    for i, (language, count) in enumerate(ranked):
        fraction = 100 * count / total
        color = palette[i]
        body += (f'<circle cx="89" cy="135" r="49" fill="none" stroke="{color}" '
                 f'stroke-width="17" pathLength="100" stroke-dasharray="{fraction:.5f} {100-fraction:.5f}" '
                 f'stroke-dashoffset="{-offset:.5f}" transform="rotate(-90 89 135)">'
                 f'<title>{escape(language)}: {count} repositories ({fraction:.1f}%)</title></circle>')
        offset += fraction
        y = 88 + i * 25
        body += f'<rect x="166" y="{y-8}" width="7" height="7" rx="1" fill="{color}"/>'
        label = language if len(language) <= 17 else language[:14] + "..."
        body += text(181, y, label, 11)
        body += text(308, y, count, 11, "#f0f6fc")
    body += f'<text x="89" y="138" text-anchor="middle" font-size="25" fill="#f0f6fc">{total}</text>'
    body += '<text x="89" y="155" text-anchor="middle" font-size="10" fill="#8b949e">repos</text>'
    if not ranked:
        body += text(164, 130, "No language data", 11, "#8b949e")
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
