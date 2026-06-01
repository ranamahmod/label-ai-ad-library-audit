"""
Agent 1: Facebook Ad Library Audit
Scrapes a Facebook Ad Library URL, analyzes with Groq AI,
and outputs a professional HTML report with Chart.js visualizations.

Usage:
    python agent1_ad_library_audit.py --url "https://www.facebook.com/ads/library/..."
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-70b-8192"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Facebook Ad Library Audit Agent — powered by Groq AI"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Facebook Ad Library URL to audit (e.g. https://www.facebook.com/ads/library/?...)",
    )
    return parser.parse_args()


def scrape_ad_library(url: str) -> dict:
    """
    Attempt to scrape the Facebook Ad Library page.
    Returns a dict with raw HTML snippets and any parseable data.
    Since Meta heavily gates the Ad Library behind JS rendering,
    this function fetches the page and extracts whatever static data
    is available, then synthesizes structured mock-data for AI analysis
    when the page requires JavaScript to render fully.
    """
    print(f"[*] Fetching Ad Library URL: {url}")
    result = {
        "url": url,
        "page_title": "",
        "raw_text": "",
        "ads": [],
        "scrape_status": "partial",
    }

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        result["page_title"] = soup.title.string if soup.title else "Facebook Ad Library"

        # Extract all visible text blocks
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        raw_text = soup.get_text(separator="\n", strip=True)
        result["raw_text"] = raw_text[:8000]  # cap to avoid token overload

        # Try to find ad containers via common class patterns
        ad_containers = (
            soup.find_all("div", {"data-testid": re.compile(r"ad", re.I)})
            or soup.find_all("div", class_=re.compile(r"ad[_-]?card|sponsored", re.I))
            or soup.find_all("div", class_=re.compile(r"_4dki|_6m3b", re.I))
        )

        for container in ad_containers[:20]:
            text = container.get_text(separator=" ", strip=True)
            if len(text) > 30:
                result["ads"].append({"copy": text[:500], "format": "unknown"})

        if not result["ads"]:
            result["scrape_status"] = "js_rendered_page"
            print(
                "[!] Page appears to require JavaScript rendering. "
                "AI will analyze based on URL context and available metadata."
            )

        print(f"[+] Scraped {len(result['ads'])} ad containers from page.")
        return result

    except requests.exceptions.HTTPError as e:
        print(f"[!] HTTP error during scrape: {e}")
        result["scrape_status"] = "error"
        result["error"] = str(e)
        return result
    except Exception as e:
        print(f"[!] Scrape error: {e}")
        result["scrape_status"] = "error"
        result["error"] = str(e)
        return result


def extract_brand_from_url(url: str) -> str:
    """Extract advertiser/brand context from the URL query string."""
    match = re.search(r"[?&](?:q|advertiser_name)=([^&]+)", url)
    if match:
        return requests.utils.unquote(match.group(1)).replace("+", " ")
    match = re.search(r"facebook\.com/([^/?]+)", url)
    if match and match.group(1) not in ("ads", "library"):
        return match.group(1)
    return "the advertiser"


def analyze_with_groq(scrape_data: dict, brand: str) -> dict:
    """Send scraped data to Groq for AI analysis. Returns structured analysis."""
    if not GROQ_API_KEY:
        print("[!] GROQ_API_KEY not set. Skipping AI analysis.")
        return {
            "messaging_themes": ["(Set GROQ_API_KEY in .env to enable AI analysis)"],
            "top_ads": [],
            "format_breakdown": {"image": 40, "video": 35, "carousel": 25},
            "creative_velocity": "Unknown — API key required",
            "strategic_summary": "Set your GROQ_API_KEY in the .env file to enable full AI analysis.",
        }

    client = Groq(api_key=GROQ_API_KEY)

    context_text = scrape_data.get("raw_text", "") or ""
    ads_text = "\n".join(
        [f"Ad {i+1}: {a['copy']}" for i, a in enumerate(scrape_data.get("ads", []))]
    )
    full_context = f"Brand/Advertiser: {brand}\n\nPage Content:\n{context_text[:3000]}\n\nAd Copies Found:\n{ads_text[:2000]}"

    prompt = f"""You are an expert performance marketing analyst auditing a Facebook Ad Library page.

Based on the following data scraped from the Ad Library for "{brand}", provide a structured JSON analysis.

DATA:
{full_context}

Return ONLY valid JSON with this exact structure (no markdown, no extra text):
{{
  "messaging_themes": ["theme1", "theme2", "theme3", "theme4", "theme5"],
  "top_ads": [
    {{"rank": 1, "copy": "ad copy text", "format": "image|video|carousel", "angle": "why this works"}},
    {{"rank": 2, "copy": "ad copy text", "format": "image|video|carousel", "angle": "why this works"}},
    {{"rank": 3, "copy": "ad copy text", "format": "image|video|carousel", "angle": "why this works"}},
    {{"rank": 4, "copy": "ad copy text", "format": "image|video|carousel", "angle": "why this works"}},
    {{"rank": 5, "copy": "ad copy text", "format": "image|video|carousel", "angle": "why this works"}}
  ],
  "format_breakdown": {{"image": 40, "video": 35, "carousel": 25}},
  "creative_velocity": "e.g. 3-5 new ads per week, high testing cadence",
  "strategic_summary": "2-3 sentence strategic insight about this brand's ad strategy"
}}

If data is limited, make educated inferences based on the brand name and URL context.
Ensure format_breakdown values sum to 100."""

    print("[*] Sending data to Groq for AI analysis...")
    try:
        chat = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1500,
        )
        raw = chat.choices[0].message.content.strip()
        # Strip any markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        analysis = json.loads(raw)
        print("[+] Groq analysis complete.")
        return analysis
    except json.JSONDecodeError as e:
        print(f"[!] JSON parse error from Groq response: {e}")
        return {
            "messaging_themes": ["Could not parse AI response — check Groq API key"],
            "top_ads": [],
            "format_breakdown": {"image": 33, "video": 34, "carousel": 33},
            "creative_velocity": "Analysis unavailable",
            "strategic_summary": "AI response could not be parsed. Please verify your GROQ_API_KEY.",
        }
    except Exception as e:
        print(f"[!] Groq API error: {e}")
        return {
            "messaging_themes": [f"Groq error: {str(e)}"],
            "top_ads": [],
            "format_breakdown": {"image": 33, "video": 34, "carousel": 33},
            "creative_velocity": "Analysis unavailable",
            "strategic_summary": str(e),
        }


def build_html_report(brand: str, url: str, analysis: dict, scrape_status: str) -> str:
    """Build a professional dark-themed HTML report with Chart.js."""
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    fmt = analysis.get("format_breakdown", {"image": 33, "video": 34, "carousel": 33})
    themes = analysis.get("messaging_themes", [])
    top_ads = analysis.get("top_ads", [])
    velocity = analysis.get("creative_velocity", "N/A")
    summary = analysis.get("strategic_summary", "")

    themes_html = "".join(
        f'<div class="theme-pill">{t}</div>' for t in themes
    )

    top_ads_html = ""
    for ad in top_ads:
        top_ads_html += f"""
        <div class="ad-card">
            <div class="ad-rank">#{ad.get('rank', '?')}</div>
            <div class="ad-meta">
                <span class="ad-format-badge">{ad.get('format', 'unknown').upper()}</span>
            </div>
            <p class="ad-copy">"{ad.get('copy', 'N/A')}"</p>
            <p class="ad-angle"><strong>Why it works:</strong> {ad.get('angle', 'N/A')}</p>
        </div>"""

    if not top_ads_html:
        top_ads_html = '<p class="no-data">No individual ads extracted — AI analysis based on page-level data.</p>'

    status_badge = (
        '<span class="badge badge-warn">Partial Scrape (JS-rendered)</span>'
        if scrape_status in ("js_rendered_page", "partial")
        else '<span class="badge badge-ok">Full Scrape</span>'
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Ad Library Audit — {brand}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0f1117;
    --card: #1a1d27;
    --accent: #6c63ff;
    --accent2: #ff6584;
    --accent3: #43e97b;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --border: #2d3148;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; padding: 0; }}
  .header {{
    background: linear-gradient(135deg, #1a1d27 0%, #2d1b69 100%);
    border-bottom: 2px solid var(--accent);
    padding: 36px 48px;
  }}
  .header h1 {{ font-size: 2rem; font-weight: 700; color: #fff; }}
  .header .subtitle {{ color: var(--muted); margin-top: 8px; font-size: 0.95rem; }}
  .header .meta {{ display: flex; gap: 20px; margin-top: 16px; flex-wrap: wrap; align-items: center; }}
  .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }}
  .badge-ok {{ background: #1a3a2a; color: var(--accent3); border: 1px solid var(--accent3); }}
  .badge-warn {{ background: #3a2a1a; color: #fbbf24; border: 1px solid #fbbf24; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 24px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }}
  @media (max-width: 768px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 28px;
  }}
  .card h2 {{ font-size: 1.1rem; font-weight: 600; color: var(--accent); margin-bottom: 20px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .chart-wrap {{ position: relative; height: 280px; display: flex; align-items: center; justify-content: center; }}
  .theme-pill {{
    display: inline-block;
    background: #1e1b4b;
    border: 1px solid var(--accent);
    color: #c4b5fd;
    padding: 8px 16px;
    border-radius: 24px;
    font-size: 0.88rem;
    margin: 6px;
  }}
  .themes-wrap {{ display: flex; flex-wrap: wrap; gap: 4px; }}
  .summary-text {{ color: var(--text); line-height: 1.7; font-size: 0.95rem; }}
  .velocity-val {{ font-size: 1.4rem; font-weight: 700; color: var(--accent3); margin-top: 8px; }}
  .ad-card {{
    background: #12151f;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 16px;
    position: relative;
  }}
  .ad-rank {{ position: absolute; top: 16px; right: 16px; font-size: 1.5rem; font-weight: 800; color: var(--border); }}
  .ad-format-badge {{ background: #2d1b69; color: #a5b4fc; padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
  .ad-copy {{ color: var(--text); font-style: italic; margin: 12px 0; line-height: 1.6; font-size: 0.93rem; }}
  .ad-angle {{ color: var(--muted); font-size: 0.88rem; line-height: 1.5; }}
  .no-data {{ color: var(--muted); font-style: italic; }}
  .footer {{ text-align: center; padding: 32px; color: var(--muted); font-size: 0.82rem; border-top: 1px solid var(--border); margin-top: 40px; }}
  .url-link {{ color: var(--accent); word-break: break-all; font-size: 0.85rem; }}
</style>
</head>
<body>

<div class="header">
  <h1>Ad Library Audit Report</h1>
  <div class="subtitle">Brand: <strong>{brand}</strong></div>
  <div class="meta">
    <span>{status_badge}</span>
    <span style="color: var(--muted); font-size:0.85rem;">Generated: {timestamp}</span>
    <a class="url-link" href="{url}" target="_blank">{url[:80]}{'...' if len(url) > 80 else ''}</a>
  </div>
</div>

<div class="container">

  <!-- Row 1: Chart + Velocity + Summary -->
  <div class="grid-2">
    <div class="card">
      <h2>Ad Format Breakdown</h2>
      <div class="chart-wrap">
        <canvas id="fmtChart"></canvas>
      </div>
    </div>
    <div style="display:flex; flex-direction:column; gap:24px;">
      <div class="card" style="flex:1;">
        <h2>Creative Velocity</h2>
        <div class="velocity-val">{velocity}</div>
        <p style="color:var(--muted); font-size:0.85rem; margin-top:8px;">Estimated ad posting frequency</p>
      </div>
      <div class="card" style="flex:2;">
        <h2>Strategic Summary</h2>
        <p class="summary-text">{summary}</p>
      </div>
    </div>
  </div>

  <!-- Row 2: Messaging Themes -->
  <div class="card" style="margin-bottom:24px;">
    <h2>Messaging Themes Identified by AI</h2>
    <div class="themes-wrap">{themes_html}</div>
  </div>

  <!-- Row 3: Top 5 Ads -->
  <div class="card">
    <h2>Top 5 Ads — Copy & Creative Analysis</h2>
    {top_ads_html}
  </div>

</div>

<div class="footer">
  Generated by The Label AI Studios PH — Ad Library Audit Agent &nbsp;|&nbsp; Powered by Groq AI + llama3-70b-8192
</div>

<script>
const fmtData = {{
  labels: ['Image', 'Video', 'Carousel'],
  datasets: [{{
    data: [{fmt.get('image', 33)}, {fmt.get('video', 34)}, {fmt.get('carousel', 33)}],
    backgroundColor: ['#6c63ff', '#ff6584', '#43e97b'],
    borderColor: ['#0f1117'],
    borderWidth: 3,
    hoverOffset: 8
  }}]
}};
new Chart(document.getElementById('fmtChart'), {{
  type: 'pie',
  data: fmtData,
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{
        position: 'bottom',
        labels: {{ color: '#e2e8f0', font: {{ size: 13 }}, padding: 16 }}
      }},
      tooltip: {{
        callbacks: {{
          label: ctx => ` ${{ctx.label}}: ${{ctx.parsed}}%`
        }}
      }}
    }}
  }}
}});
</script>
</body>
</html>"""
    return html


def main():
    args = parse_args()
    url = args.url.strip()
    brand = extract_brand_from_url(url)
    print(f"[*] Starting Ad Library Audit for: {brand}")

    scrape_data = scrape_ad_library(url)
    analysis = analyze_with_groq(scrape_data, brand)

    html = build_html_report(brand, url, analysis, scrape_data.get("scrape_status", "unknown"))

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"ad_library_report_{timestamp_str}.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n[✓] Report saved: {output_file}")
    print(f"    Open in your browser to view the full audit.")


if __name__ == "__main__":
    main()
