import requests
from bs4 import BeautifulSoup
import os
import time

# --- CONFIGURATION ---
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
HISTORY_FILE = "processed_jobs.txt"

LOCATIONS = [
    "Pune%2C%20Maharashtra%2C%20India",
    "Mumbai%2C%20Maharashtra%2C%20India",
]

BASE_SEARCH_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    "?keywords=DevOps%20Engineer"
    "&location={location}"
    "&f_E=2%2C3"
    "&f_TPR=r604800"
    "&sortBy=DD"
    "&start={start}"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ✅ DevOps Keywords
INCLUDE_KEYWORDS = [
    "devops", "devops engineer", "site reliability engineer", "sre",
    "cloud engineer", "platform engineer", "infrastructure engineer",
    "aws", "azure", "gcp",
    "ci/cd", "jenkins", "github actions", "gitlab ci",
    "docker", "kubernetes",
    "terraform", "infrastructure as code",
    "ansible",
    "prometheus", "grafana", "monitoring",
    "linux", "bash", "python",
    "devsecops", "iam"
]

# ❌ Exclude senior roles (customize if needed)
EXCLUDE_KEYWORDS = [
    "senior", "lead", "staff", "principal", "architect"
]

MAX_NEW_JOBS = 5
PAGE_SIZE = 25
REQUEST_DELAY = 2


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def save_history(job_id):
    with open(HISTORY_FILE, "a") as f:
        f.write(job_id + "\n")


def run():
    if not WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK environment variable not set")
        return

    processed_jobs = load_history()
    sent_count = 0

    print(f"🚀 Looking for {MAX_NEW_JOBS} NEW DevOps jobs in Pune & Mumbai...")
    print(f"📁 Already processed: {len(processed_jobs)}")

    try:
        for location in LOCATIONS:
            if sent_count >= MAX_NEW_JOBS:
                break

            location_name = location.split("%2C")[0].replace("%20", " ")
            print(f"\n📍 Searching in {location_name}...")
            start = 0

            while sent_count < MAX_NEW_JOBS:
                search_url = BASE_SEARCH_URL.format(location=location, start=start)
                print(f"🔍 Fetching page start={start}")

                response = requests.get(search_url, headers=HEADERS, timeout=10)
                soup = BeautifulSoup(response.text, "html.parser")
                job_cards = soup.find_all("li")

                if not job_cards:
                    print(f"❌ No more jobs available in {location_name}")
                    break

                for job in job_cards:
                    if sent_count >= MAX_NEW_JOBS:
                        break

                    base_card = job.find("div", class_="base-card")
                    if not base_card or not base_card.has_attr("data-entity-urn"):
                        continue

                    job_id = base_card["data-entity-urn"].split(":")[-1]
                    if job_id in processed_jobs:
                        continue

                    title_tag = job.find("h3", class_="base-search-card__title")
                    company_tag = job.find("h4", class_="base-search-card__subtitle")
                    link_tag = job.find("a", class_="base-card__full-link")

                    if not title_tag or not link_tag:
                        continue

                    title = title_tag.text.strip()
                    company = company_tag.text.strip() if company_tag else "Unknown Company"
                    link = link_tag["href"].split("?")[0]
                    title_lower = title.lower()

                    # ✅ Include DevOps roles only
                    if not any(word in title_lower for word in INCLUDE_KEYWORDS):
                        print(f"⏩ Skipped (not DevOps): {title}")
                        continue

                    # ❌ Skip senior roles
                    if any(word in title_lower for word in EXCLUDE_KEYWORDS):
                        print(f"⏩ Skipped (senior role): {title}")
                        continue

                    payload = {
                        "content": "🚀 **New DevOps Job Found!**",
                        "embeds": [
                            {
                                "title": title,
                                "url": link,
                                "description": (
                                    f"🏢 **Company:** {company}\n"
                                    f"📍 **Location:** {location_name}\n"
                                    f"🆔 **ID:** {job_id}"
                                ),
                                "color": 5763719,
                            }
                        ],
                    }

                    resp = requests.post(WEBHOOK_URL, json=payload)
                    if resp.status_code == 204:
                        save_history(job_id)
                        processed_jobs.add(job_id)
                        sent_count += 1
                        print(f"✅ Sent ({sent_count}/{MAX_NEW_JOBS}): {title}")
                        time.sleep(REQUEST_DELAY)

                start += PAGE_SIZE

        if sent_count == 0:
            print("ℹ️ No new DevOps jobs found this run")

    except Exception as e:
        print(f"⚠️ Error: {e}")


if __name__ == "__main__":
    run()
