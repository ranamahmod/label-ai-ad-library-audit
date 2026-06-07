# label-ai-ad-library-audit

An AI agent that audits Facebook Ad Library URLs and outputs a full HTML spy report with charts: format breakdown, messaging patterns, top ads, and creative velocity.

## What It Does

Point this agent at any Facebook Ad Library URL for a brand or advertiser. It scrapes available ad data, sends it to Groq AI (llama3-70b-8192), and generates a dark-themed HTML report with a pie chart of ad format breakdown, the top 5 ads with creative analysis, identified messaging themes, and a strategic summary.

## Who Buys This and at What Price

Marketing agencies, media buyers, and brand strategists who need fast competitive ad intelligence without manual research. Typical use cases: onboarding new clients, weekly competitor audits, pre-launch campaign research. Priced as a done-for-you deliverable at $150–$500 per audit report, or bundled into a monthly retainer.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and fill in your GROQ_API_KEY
```

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Your Groq API key from [console.groq.com](https://console.groq.com) |

## Usage

```bash
python agent1_ad_library_audit.py --url "https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=US&q=nike&search_type=keyword_unordered"
```

Replace the URL with any Facebook Ad Library search URL for your target brand.

## Output

The agent saves a timestamped HTML file in the current directory:

```
ad_library_report_20260601_143022.html
```

Open it in any browser to view:
- Ad format breakdown pie chart (Image / Video / Carousel percentages)
- Creative velocity estimate (posting frequency)
- Strategic summary of the brand's ad approach
- Top 5 ads with copy and "why it works" analysis
- Messaging themes identified by AI

## Notes

Facebook Ad Library uses JavaScript rendering for full ad display. When the static scrape is limited, the AI performs inference based on URL context and available metadata. Results are most accurate when the URL includes a brand name or advertiser query parameter.

---

Built by Rana Mahmod (Contact: mahmodrana24@gmail.com)
