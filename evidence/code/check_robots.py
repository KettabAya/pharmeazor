
import requests
import json
import logging
import sys
import re

from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from logging.handlers import RotatingFileHandler

# Import websites and authority information
from source_authority import get_all_sources


# ==========================================
# CONFIGURATION
# ==========================================

USER_AGENT = "PharmeazorStudentBot"

BASE_DIR = Path(__file__).resolve().parents[1]

OUTPUT_FILE = BASE_DIR / "data/metadata/robots_audit.json"
LOG_FILE = BASE_DIR / "logs/robots_checker.log"


# ==========================================
# LOGGING CONFIGURATION
# ==========================================

def setup_logger():

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("Pharmeazor")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console logging
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)

    # File logging with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8"
    )

    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()


# ==========================================
# EXTRACT ALLOWED / DISALLOWED PATHS
# ==========================================

def extract_robots_rules(content, user_agent):
    """
    Extract Allow and Disallow paths applicable
    to the configured User-Agent.

    Prefer specific User-Agent groups over *.
    Empty Disallow directives are ignored.
    """

    groups = []
    agents = []
    rules = []
    seen_directive = False

    for raw_line in content.splitlines():

        # Remove comments
        line = raw_line.split("#", 1)[0].strip()

        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        key = key.strip().lower()
        value = value.strip()

        if key == "user-agent":

            # A new group begins after directives
            if seen_directive and agents:
                groups.append((agents, rules))
                agents = []
                rules = []
                seen_directive = False

            agents.append(value.lower())

        elif agents:

            seen_directive = True

            if key in ("allow", "disallow"):
                rules.append((key, value))

    if agents:
        groups.append((agents, rules))

    # Select the most specific matching group(s)
    matching_groups = []

    for group_agents, group_rules in groups:

        specificity = max(
            (
                0 if agent == "*" else len(agent)
                for agent in group_agents
                if agent == "*"
                or agent in user_agent.lower()
            ),
            default=-1
        )

        if specificity >= 0:
            matching_groups.append(
                (specificity, group_rules)
            )

    if not matching_groups:
        return [], [], []

    best_specificity = max(
        score for score, _ in matching_groups
    )

    applicable_rules = [
        rule
        for score, group_rules in matching_groups
        if score == best_specificity
        for rule in group_rules
    ]

    allowed = list(dict.fromkeys(
        path
        for directive, path in applicable_rules
        if directive == "allow" and path
    ))

    disallowed = list(dict.fromkeys(
        path
        for directive, path in applicable_rules
        if directive == "disallow" and path
    ))

    return allowed, disallowed, applicable_rules


# ==========================================
# CHECK WHETHER A URL IS ALLOWED
# ==========================================

def rule_match_length(pattern, path):
    """
    Check a robots path rule.

    Supports * wildcards and $ end anchors.
    Returns -1 when the rule does not match.
    """

    if not pattern:
        return -1

    end_anchor = pattern.endswith("$")

    if end_anchor:
        pattern = pattern[:-1]

    regex_pattern = (
        "^"
        + re.escape(pattern).replace(r"\*", ".*")
        + ("$" if end_anchor else "")
    )

    if re.match(regex_pattern, path):
        return len(pattern.replace("*", ""))

    return -1


def is_url_allowed(url, rules):
    """
    Evaluate matching Allow/Disallow rules.

    The longest matching rule wins.
    Allow wins when rules have equal specificity.
    """

    parsed = urlsplit(url)

    path = parsed.path or "/"

    if parsed.query:
        path += "?" + parsed.query

    matches = []

    for directive, pattern in rules:

        match_length = rule_match_length(pattern, path)

        if match_length >= 0:
            matches.append(
                (match_length, directive == "allow")
            )

    # No matching restriction: allowed by robots
    if not matches:
        return True

    return max(matches)[1]


# ==========================================
# CHECK ROBOTS.TXT
# ==========================================

def check_robots(source):

    name = source["source_name"]
    url = source["url"]

    logger.info("Checking website: %s", name)
    logger.info("Website URL: %s", url)

    result = {
        "website_name": name,
        "website_url": url,
        "authority_level": source["authority_level"],
        "authority_type": source["authority_type"],
        "country": source["country"],
        "sub_urls": source.get("sub_urls", {}),
        "robots_url": None,
        "status": "unknown",

        # NEW: Path lists
        "allowed": [],
        "disallowed": [],

        # NEW: URL evaluation
        "url_allowed": None,
        "default_allowed": True,

        "crawl_delay": None,
        "request_rate": None,

        "checked_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    parsed = urlsplit(url)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:

        logger.error("Invalid website URL: %s", url)

        result["status"] = "invalid_url"
        result["default_allowed"] = None

        return result

    robots_url = urlunsplit((
        parsed.scheme,
        parsed.netloc,
        "/robots.txt",
        "",
        ""
    ))

    result["robots_url"] = robots_url

    logger.debug("Robots URL: %s", robots_url)

    try:

        response = requests.get(
            robots_url,
            headers={"User-Agent": USER_AGENT},
            timeout=15
        )

        status_code = response.status_code

        logger.debug(
            "HTTP response: %s | Status: %s",
            name,
            status_code
        )

        logger.debug(
            "Final response URL: %s",
            response.url
        )

        if status_code == 200:

            content = response.text

            logger.debug(
                "Robots content length: %d characters",
                len(content)
            )

            is_html = content.lstrip().lower().startswith(
                ("<!doctype html", "<html")
            )

            has_user_agent = any(
                re.match(
                    r"^\s*user-agent\s*:",
                    line,
                    flags=re.IGNORECASE
                )
                for line in content.splitlines()
            )

            if is_html or not has_user_agent:

                result["status"] = "invalid_robots_content"
                result["default_allowed"] = None

                logger.warning(
                    "Cannot reliably parse robots.txt: %s",
                    name
                )

                return result

            # ---------------------------------
            # Extract paths from robots.txt
            # ---------------------------------

            allowed_paths, disallowed_paths, rules = (
                extract_robots_rules(
                    content,
                    USER_AGENT
                )
            )

            result["allowed"] = allowed_paths
            result["disallowed"] = disallowed_paths

            # Evaluate the actual website URL
            result["url_allowed"] = is_url_allowed(
                url,
                rules
            )

            result["status"] = "robots_found"

            # ---------------------------------
            # Read crawl-delay and request-rate
            # ---------------------------------

            parser = RobotFileParser()

            parser.set_url(robots_url)
            parser.parse(content.splitlines())

            result["crawl_delay"] = parser.crawl_delay(
                USER_AGENT
            )

            rate = parser.request_rate(USER_AGENT)

            if rate is not None:
                result["request_rate"] = {
                    "requests": rate.requests,
                    "seconds": rate.seconds
                }

            # ---------------------------------
            # Logging
            # ---------------------------------

            logger.info(
                "ALLOWED PATHS | %s | %s",
                name,
                allowed_paths
            )

            logger.info(
                "DISALLOWED PATHS | %s | %s",
                name,
                disallowed_paths
            )

            if result["url_allowed"]:

                logger.info(
                    "ROBOTS ALLOWED URL: %s",
                    url
                )

            else:

                logger.warning(
                    "ROBOTS DISALLOWED URL: %s",
                    url
                )

            logger.debug(
                "Crawl delay: %s",
                result["crawl_delay"]
            )

            logger.debug(
                "Request rate: %s",
                result["request_rate"]
            )

        elif status_code in (404, 410):

            result["status"] = "robots_not_found"
            result["url_allowed"] = True

            logger.warning(
                "No robots.txt found: %s",
                name
            )

        elif status_code in (401, 403):

            result["status"] = "access_denied"
            result["url_allowed"] = False
            result["default_allowed"] = None

            logger.warning(
                "Access denied: %s",
                name
            )

        else:

            result["status"] = f"http_error_{status_code}"
            result["default_allowed"] = None

            logger.error(
                "HTTP error %s: %s",
                status_code,
                name
            )

    except requests.Timeout:

        result["status"] = "timeout"
        result["default_allowed"] = None

        logger.error(
            "Connection timeout: %s",
            name
        )

    except requests.RequestException as error:

        result["status"] = "connection_error"
        result["default_allowed"] = None
        result["error"] = str(error)

        logger.error(
            "Connection failed: %s | %s",
            name,
            error
        )

    return result


# ==========================================
# SAVE JSON RESULTS
# ==========================================

def save_results(results):

    try:

        OUTPUT_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                results,
                file,
                indent=4,
                ensure_ascii=False
            )

        logger.info(
            "Results saved: %s",
            OUTPUT_FILE
        )

    except OSError:

        logger.critical(
            "Could not save audit results",
            exc_info=True
        )

        raise


# ==========================================
# MAIN PROGRAM
# ==========================================

def main():

    logger.info("=" * 60)
    logger.info("PHARMEAZOR - SOURCE AUDIT STARTED")
    logger.info("=" * 60)

    websites = get_all_sources()

    if not websites:

        logger.critical("No websites configured")
        return

    results = []

    for website in websites:

        logger.info("-" * 60)

        result = check_robots(website)
        results.append(result)

        logger.info(
            "RESULT | Name: %s | URL: %s | "
            "Authority: %s | Robots: %s | "
            "URL Allowed: %s",
            result["website_name"],
            result["website_url"],
            result["authority_level"],
            result["robots_url"],
            result["url_allowed"]
        )

    save_results(results)

    allowed = sum(
        r["url_allowed"] is True
        for r in results
    )

    denied = sum(
        r["url_allowed"] is False
        for r in results
    )

    unknown = sum(
        r["url_allowed"] is None
        for r in results
    )

    logger.info("=" * 60)
    logger.info("AUDIT SUMMARY")
    logger.info("=" * 60)

    logger.info("Total websites: %d", len(results))
    logger.info("Robots allowed: %d", allowed)
    logger.info("Robots denied: %d", denied)
    logger.info("Unknown status: %d", unknown)

    logger.warning(
        "Review website terms of use before collection."
    )

    logger.info("Audit completed successfully")


if __name__ == "__main__":
    main()
