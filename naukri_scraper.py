import requests
import os
import time

# --- CONFIGURATION ---
WEBHOOK_URL = os.getenv("NAUKRI_DISCORD_WEBHOOK")
HISTORY_FILE = "processed_naukri_jobs.txt"

LOCATIONS = ["pune", "mumbai"]

BASE_SEARCH_URL = (
    "https://www.naukri.com/jobapi/v3/search"
    "?noOfResults=20"
    "&urlType=search_by_keyword"
    "&searchType=adv"
    "&keyword=devops+engineer"
    "&location={location}"
    "&experience=0"
    "&pageNo={page}"
    "&k=devops+engineer"
    "&l={location}"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.naukri.com/",
    "appid": "109",
    "systemid": "Naukri",
    "gid": "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
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

# ❌ Exclude senior roles
EXCLUDE_KEYWORDS = [
    "senior", "lead", "staff", "principal", "architect"
]

MAX_NEW_JOBS = 5
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
        print("❌ NAUKRI_DISCORD_WEBHOOK environment variable not set")
        return

    processed_jobs = load_history()
    sent_count = 0

    print(f"🚀 Looking for {MAX_NEW_JOBS} NEW DevOps jobs on Naukri in Pune & Mumbai...")
    print(f"📁 Already processed: {len(processed_jobs)}")

    try:
        for location in LOCATIONS:
            if sent_count >= MAX_NEW_JOBS:
                break

            print(f"\n📍 Searching in {location.capitalize()}...")
            page = 1

            while sent_count < MAX_NEW_JOBS:
                search_url = BASE_SEARCH_URL.format(location=location, page=page)
                print(f"🔍 Fetching page {page}")

                response = requests.get(search_url, headers=HEADERS, timeout=10)
                if response.status_code != 200:
                    print(f"❌ Failed to fetch page {page}: HTTP {response.status_code}")
                    break

                data = response.json()
                job_details = data.get("jobDetails", [])

                if not job_details:
                    print(f"❌ No more jobs available in {location.capitalize()}")
                    break

                for job in job_details:
                    if sent_count >= MAX_NEW_JOBS:
                        break

                    job_id = str(job.get("jobId", ""))
                    if not job_id or job_id in processed_jobs:
                        continue

                    title = job.get("title", "").strip()
                    company = job.get("companyName", "Unknown Company").strip()
                    job_location = job.get("placeholders", [{}])[0].get("label", location.capitalize())
                    link = job.get("jdURL", "")

                    if not title or not link:
                        continue

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
                        "content": "🚀 **New DevOps Job Found on Naukri!**",
                        "embeds": [
                            {
                                "title": title,
                                "url": link,
                                "description": (
                                    f"🏢 **Company:** {company}\n"
                                    f"📍 **Location:** {job_location}\n"
                                    f"🆔 **ID:** {job_id}"
                                ),
                                "color": 15844367,
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

                page += 1

        if sent_count == 0:
            print("ℹ️ No new DevOps jobs found on Naukri this run")

    except Exception as e:
        print(f"⚠️ Error: {e}")


if __name__ == "__main__":
    run()
