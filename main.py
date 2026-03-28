import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlencode

import feedparser
import requests
import yaml


CONFIG_PATH = Path("config.yml")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("config.yml not found.")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_date_clause(days_back: int) -> str:
    now = datetime.now(timezone.utc)
    start_dt = now - timedelta(days=days_back)

    start_str = start_dt.strftime("%Y%m%d%H%M")
    end_str = now.strftime("%Y%m%d%H%M")

    return f"submittedDate:[{start_str} TO {end_str}]"


def build_keyword_clause(keyword: str) -> str:
    keyword = keyword.strip()

    if " " in keyword:
        return f'(ti:"{keyword}" OR abs:"{keyword}")'

    return f"(ti:{keyword} OR abs:{keyword})"


def build_category_clause(categories: list[str]) -> str | None:
    if not categories:
        return None

    if len(categories) == 1:
        return f"cat:{categories[0]}"

    joined = " OR ".join(f"cat:{category}" for category in categories)
    return f"({joined})"


def build_search_query(config: dict) -> str:
    query_config = config.get("query", {})
    search_config = config.get("search", {})

    include_keywords = query_config.get("include_keywords", [])
    exclude_keywords = query_config.get("exclude_keywords", [])
    categories = query_config.get("categories", [])
    days_back = int(search_config.get("days_back", 7))

    positive_parts = []

    category_clause = build_category_clause(categories)
    if category_clause:
        positive_parts.append(category_clause)

    if include_keywords:
        include_clause = " OR ".join(
            build_keyword_clause(keyword) for keyword in include_keywords
        )
        positive_parts.append(f"({include_clause})")

    positive_parts.append(build_date_clause(days_back))

    if not include_keywords and not categories:
        raise ValueError("At least one include_keyword or category is required.")

    query = " AND ".join(positive_parts)

    if exclude_keywords:
        exclude_clause = " OR ".join(
            build_keyword_clause(keyword) for keyword in exclude_keywords
        )
        query = f"{query} ANDNOT ({exclude_clause})"

    return query


def fetch_arxiv_entries(search_query: str, max_results: int):
    base_url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    response = requests.get(base_url, params=params, timeout=30)
    response.raise_for_status()

    print("Search query:", search_query)
    print("Request URL:", f"{base_url}?{urlencode(params)}")

    feed = feedparser.parse(response.text)
    return feed.entries


def format_authors(entry) -> str:
    authors = getattr(entry, "authors", [])
    if not authors:
        return "Unknown"

    names = []
    for author in authors:
        name = getattr(author, "name", "").strip()
        if name:
            names.append(name)

    return ", ".join(names) if names else "Unknown"


def format_published(published: str) -> str:
    if not published:
        return "Unknown"

    try:
        dt = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return published


def build_digest(entries) -> str:
    lines = []
    lines.append("-" * 80)

    for index, entry in enumerate(entries, start=1):
        title = (getattr(entry, "title", "") or "").replace("\n", " ").strip()
        summary = (getattr(entry, "summary", "") or "").replace("\n", " ").strip()
        link = getattr(entry, "link", "") or ""
        published = format_published(getattr(entry, "published", "") or "")
        authors = format_authors(entry)

        lines.append(f"Published: {published}")
        lines.append(f"Title: {title}")
        lines.append(f"Authors: {authors}")
        lines.append(f"Link: {link}")
        lines.append("")
        lines.append("Abstract:")
        lines.append(summary)
        lines.append("")
        lines.append("-" * 80)

    return "\n".join(lines)


def send_email(subject: str, body: str) -> None:
    sender_email = os.environ["SENDER_EMAIL"]
    receiver_email = os.environ["RECEIVER_EMAIL"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender_email, app_password)
        smtp.send_message(msg)


def main() -> None:
    config = load_config()
    search_config = config.get("search", {})
    max_results = int(search_config.get("max_results", 10))

    search_query = build_search_query(config)
    entries = fetch_arxiv_entries(search_query, max_results)

    print(f"Fetched entries: {len(entries)}")

    if not entries:
        print("No matching papers found.")
        return

    digest = build_digest(entries)
    subject = f"Latest arXiv Matches ({len(entries)} papers)"
    send_email(subject, digest)

    print("Email sent.")


if __name__ == "__main__":
    main()