#!/usr/bin/env python3
"""
Daily Report Generator
Runs Kusto queries, sends results to Azure OpenAI for analysis,
and emails the report via Microsoft Graph API.

Usage:
  python daily_report.py                    # Run with default config
  python daily_report.py --config my.yaml   # Run with custom config
  python daily_report.py --dry-run          # Generate report without emailing
  python daily_report.py --output report.html  # Save to file

Schedule it:
  Windows Task Scheduler  -  see README for instructions
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
import requests
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).parent / "reports" / "daily-backup-report.yaml"


def load_config(path):
    p = Path(path) if path else DEFAULT_CONFIG
    if not p.exists():
        log.error(f"Config not found: {p}")
        sys.exit(1)
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


# -- Kusto ------------------------------------------------------------------

def get_kusto_token():
    try:
        cred = DefaultAzureCredential()
        return cred.get_token("https://kusto.kusto.windows.net/.default").token
    except Exception:
        log.info("DefaultAzureCredential failed, trying az CLI...")
        az = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
        if not Path(az).exists():
            az = "az"
        r = subprocess.run(
            [az, "account", "get-access-token", "--resource", "https://kusto.kusto.windows.net"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            log.error(f"az CLI failed: {r.stderr}")
            sys.exit(1)
        return json.loads(r.stdout)["accessToken"]


def run_query(cluster_url, database, query, token):
    kcsb = KustoConnectionStringBuilder.with_aad_application_token_authentication(
        cluster_url, application_token=token
    )
    client = KustoClient(kcsb)
    resp = client.execute(database, query)
    rows = []
    if resp.primary_results and resp.primary_results[0]:
        cols = [c.column_name for c in resp.primary_results[0].columns]
        for row in resp.primary_results[0]:
            rows.append({c: (str(row[c]) if row[c] is not None else None) for c in cols})
    return rows


# -- Azure OpenAI -----------------------------------------------------------

def analyze_with_llm(query_results, config):
    aoai = config["azure_openai"]
    endpoint = aoai["endpoint"]
    deployment = aoai["deployment"]
    api_ver = aoai.get("api_version", "2024-08-01-preview")
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_ver}"

    # Auth: try AAD, fallback to API key
    try:
        cred = DefaultAzureCredential()
        tok = cred.get_token("https://cognitiveservices.azure.com/.default")
        headers = {"Authorization": f"Bearer {tok.token}", "Content-Type": "application/json"}
    except Exception:
        key = aoai.get("api_key") or os.getenv("AZURE_OPENAI_API_KEY")
        if not key:
            return "<p>LLM analysis unavailable (no credentials).</p>"
        headers = {"api-key": key, "Content-Type": "application/json"}

    # Build data summary for LLM
    data_text = ""
    for name, res in query_results.items():
        data_text += f"\n### {name}\n{res.get('description','')}\nRows: {len(res['data'])}\n"
        if res["data"]:
            data_text += f"```json\n{json.dumps(res['data'][:50], indent=2, default=str)}\n```\n"

    prompt = config.get("analysis_prompt", "Analyze the data and provide key insights.")

    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a data analyst helping a PM. Provide a clear executive summary "
                    "with key metrics, trends, and actionable insights. Use bullet points. "
                    "Highlight concerns. Format as HTML for an email."
                ),
            },
            {
                "role": "user",
                "content": f"{prompt}\n\nDate: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n{data_text}",
            },
        ],
        "max_tokens": 2000,
        "temperature": 0.3,
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.error(f"LLM call failed: {e}")
        return f"<p>LLM analysis failed: {e}</p>"


# -- Email via Graph --------------------------------------------------------

def send_email(subject, html_body, config):
    try:
        cred = DefaultAzureCredential()
        tok = cred.get_token("https://graph.microsoft.com/.default").token
    except Exception:
        cred = InteractiveBrowserCredential()
        tok = cred.get_token("https://graph.microsoft.com/.default").token

    to_list = [{"emailAddress": {"address": r}} for r in config["email"]["to"]]
    cc_list = [{"emailAddress": {"address": r}} for r in config["email"].get("cc", []) if r]

    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": to_list,
            "ccRecipients": cc_list,
        },
        "saveToSentItems": "true",
    }

    r = requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        json=payload, timeout=30,
    )
    if r.status_code == 202:
        log.info(f"Email sent to {config['email']['to']}")
    else:
        log.error(f"Email failed ({r.status_code}): {r.text}")


# -- HTML builder -----------------------------------------------------------

def build_html(query_results, llm_analysis, config):
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    title = config.get("report_title", "Daily Report")

    tables_html = ""
    for name, res in query_results.items():
        if not res["data"]:
            continue
        cols = list(res["data"][0].keys())
        hdr = "".join(f"<th style='padding:8px;text-align:left;border-bottom:2px solid #0078d4;color:#0078d4'>{c}</th>" for c in cols)
        rows = ""
        for i, row in enumerate(res["data"][:25]):
            bg = "#f8f8f8" if i % 2 == 0 else "#fff"
            cells = "".join(f"<td style='padding:6px 8px;border-bottom:1px solid #eee'>{row.get(c,'')}</td>" for c in cols)
            rows += f"<tr style='background:{bg}'>{cells}</tr>"
        note = f"<p style='color:#888;font-size:12px'>Showing 25 of {len(res['data'])} rows</p>" if len(res["data"]) > 25 else ""
        tables_html += f"""
        <h3 style="color:#0078d4;margin-top:24px">{name}</h3>
        <p style="color:#666;font-size:13px">{res.get('description','')}</p>
        <table style="border-collapse:collapse;width:100%;font-size:13px"><tr>{hdr}</tr>{rows}</table>{note}"""

    return f"""<html><body style="font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:0 auto;padding:20px">
    <div style="background:#0078d4;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0">
        <h1 style="margin:0;font-size:22px">{title}</h1>
        <p style="margin:4px 0 0;opacity:0.9;font-size:14px">{date_str}</p>
    </div>
    <div style="background:#fff;padding:24px;border:1px solid #e0e0e0;border-top:none">
        <h2 style="color:#333;border-bottom:2px solid #0078d4;padding-bottom:8px">Executive Summary (AI Analysis)</h2>
        {llm_analysis}
        <h2 style="color:#333;border-bottom:2px solid #0078d4;padding-bottom:8px;margin-top:32px">Data Details</h2>
        {tables_html}
    </div>
    <div style="background:#f5f5f5;padding:12px 24px;border-radius:0 0 8px 8px;border:1px solid #e0e0e0;border-top:none">
        <p style="color:#888;font-size:11px;margin:0">Generated by <a href="https://github.com/vaibhav3301/kusto-ai-assistant">Kusto AI Assistant</a> | {date_str}</p>
    </div></body></html>"""


# -- Main -------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Kusto AI Daily Report")
    parser.add_argument("--config", help="Path to report YAML config")
    parser.add_argument("--dry-run", action="store_true", help="Generate without emailing")
    parser.add_argument("--output", help="Save HTML to file")
    args = parser.parse_args()

    config = load_config(args.config)
    log.info(f"Report: {config.get('report_title')}")

    # 1. Run queries
    log.info("Running Kusto queries...")
    token = get_kusto_token()
    results = {}
    for q in config["queries"]:
        log.info(f"  {q['name']}...")
        try:
            data = run_query(q["cluster"], q["database"], q["kql"], token)
            results[q["name"]] = {"data": data, "description": q.get("description", "")}
            log.info(f"    -> {len(data)} rows")
        except Exception as e:
            log.error(f"    -> Error: {e}")
            results[q["name"]] = {"data": [], "description": f"Error: {e}"}

    # 2. LLM analysis
    log.info("Running LLM analysis...")
    analysis = analyze_with_llm(results, config) if "azure_openai" in config else "<p>Skipped (no Azure OpenAI config).</p>"

    # 3. Build HTML
    html = build_html(results, analysis, config)

    # 4. Output
    if args.output:
        Path(args.output).write_text(html, encoding="utf-8")
        log.info(f"Saved: {args.output}")
    elif args.dry_run:
        out = Path(__file__).parent / "reports" / f"report-{datetime.now().strftime('%Y%m%d')}.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(html, encoding="utf-8")
        log.info(f"Saved: {out}")
    else:
        subject = f"{config.get('report_title', 'Daily Report')} - {datetime.now(timezone.utc).strftime('%b %d, %Y')}"
        send_email(subject, html, config)

    log.info("Done!")


if __name__ == "__main__":
    main()
