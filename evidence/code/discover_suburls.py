import json
import logging
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data/metadata/robots_audit.json"
OUTPUT_FILE = BASE_DIR / "data/metadata/discovered_suburls.json"

USER_AGENT = "PharmeazorStudentBot"

KEYWORDS = [
    "medicament", "médicament",
    "medicine", "drug", "product",
    "notice", "leaflet", "rcp",
    "sm pc", "sm pc", "monographie",
    "pdf", "pharmaceutical",
    "nomenclature", "interaction",
    "thesaurus"
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("Pharmeazor.SubURLs")

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def load_sources():
    with open(INPUT_FILE, encoding="utf-8") as file:
        return json.load(file)


def get_robots_parser(url):
    parsed = urlsplit(url)
    robots_url = (
        f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    )

    try:
        response = session.get(
            robots_url,
            timeout=15,
            allow_redirects=False
        )

        if response.status_code != 200:
            logger.warning(
                "Cannot verify robots rules: %s",
                robots_url
            )
            return None

        parser = RobotFileParser()
        parser.parse(response.text.splitlines())

        return parser

    except requests.RequestException as error:
        logger.error("Robots error: %s", error)
        return None


def discover_suburls(source):

    website_url = source["website_url"]

    logger.info("Checking %s", website_url)

    if not (
        source.get("terms_reviewed") is True
        and source.get("collection_approved") is True
    ):
        logger.warning(
            "Source not approved for automation: %s",
            website_url
        )
        return []

    robots = get_robots_parser(website_url)

    if robots is None:
        return []

    if not robots.can_fetch(USER_AGENT, website_url):
        logger.warning(
            "Homepage disallowed: %s",
            website_url
        )
        return []

    try:
        response = session.get(
            website_url,
            timeout=20,
            allow_redirects=False
        )

        if response.status_code != 200:
            logger.warning(
                "HTTP %s: %s",
                response.status_code,
                website_url
            )
            return []

        if "text/html" not in response.headers.get(
            "Content-Type", ""
        ).lower():
            return []

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        discovered = []
        seen = set()

        for tag in soup.find_all("a", href=True):

            link = urljoin(
                website_url,
                tag["href"]
            )

            parsed = urlsplit(link)

            # Keep only same-host HTTP(S) links
            if parsed.scheme not in ("http", "https"):
                continue

            if parsed.netloc != urlsplit(website_url).netloc:
                continue

            link = parsed._replace(fragment="").geturl()

            link_text = tag.get_text(
                " ", strip=True
            ).lower()

            searchable = (
                parsed.path + " " + link_text
            ).lower()

            if not any(
                keyword in searchable
                for keyword in KEYWORDS
            ):
                continue

            if not robots.can_fetch(USER_AGENT, link):
                logger.warning(
                    "Disallowed candidate: %s",
                    link
                )
                continue

            if link in seen:
                continue

            seen.add(link)

            discovered.append({
                "url": link,
                "link_text": link_text,"status": "NEEDS_REVIEW"
            })

            logger.info("Discovered: %s", link)

        return discovered

    except requests.RequestException as error:
        logger.error(
            "Discovery failed: %s",
            error
        )
        return []


def main():

    sources = load_sources()
    results = []

    for source in sources:

        suburls = discover_suburls(source)

        results.append({
            "website_name": source["website_name"],
            "website_url": source["website_url"],
            "sub_urls": suburls
        })

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            results,
            indent=4,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    logger.info(
        "Discovery results saved: %s",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()