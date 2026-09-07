"""
customer_view.py
Builds the HTML page a customer sees after scanning the QR code on
the jasmine packaging. Pure Python string templating -- no extra
dependencies (no Jinja2 needed), so nothing new to install.
"""

from typing import List, Dict, Any
from datetime import datetime

# Friendly labels + emoji-free icons (using simple unicode symbols only)
EVENT_LABELS = {
    "CULTIVATION":       "Cultivation",
    "DISEASE_DETECTION": "Disease Detection (AI)",
    "TREATMENT":         "Treatment Applied",
    "HARVEST":           "Harvest",
    "COLLECTION":        "Collected by Distributor",
    "TRANSPORTATION":    "Transportation",
    "SALE":              "Sold to Retailer/Customer",
}

ROLE_LABELS = {
    "farmer": "Farmer",
    "ai_system": "AI System",
    "expert": "Agricultural Expert",
    "distributor": "Distributor",
    "seller": "Seller",
}


def _format_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%d %b %Y, %I:%M %p")


def _render_details(details: Dict[str, Any]) -> str:
    """Turn the off-chain record dict into a readable list of rows."""
    if not details:
        return "<p class='muted'>No additional details recorded.</p>"
    rows = []
    for key, value in details.items():
        if key == "_id":
            continue
        label = key.replace("_", " ").title()
        rows.append(f"<div class='detail-row'><span class='detail-label'>{label}</span>"
                     f"<span class='detail-value'>{value}</span></div>")
    return "".join(rows)


def render_batch_page(batch_id: str, timeline: List[Dict[str, Any]], is_valid: bool) -> str:
    """
    Builds the full standalone HTML page for a batch's public
    traceability view. This is what loads when someone scans the QR
    code printed on the jasmine packaging.
    """
    if not timeline:
        return f"""
        <html><body style="font-family:sans-serif;text-align:center;margin-top:100px;">
        <h2>Batch '{batch_id}' not found</h2>
        <p>This QR code does not correspond to a valid jasmine batch record.</p>
        </body></html>
        """

    integrity_badge = (
        "<span class='badge badge-ok'>&#10003; Verified &ndash; No Tampering Detected</span>"
        if is_valid else
        "<span class='badge badge-bad'>&#9888; Warning &ndash; Data Integrity Issue Detected</span>"
    )

    timeline_html = ""
    for i, event in enumerate(timeline):
        label = EVENT_LABELS.get(event["event_type"], event["event_type"])
        role_label = ROLE_LABELS.get(event["role"], event["role"])
        timestamp = _format_timestamp(event["timestamp"])
        details_html = _render_details(event["details"])
        is_last = (i == len(timeline) - 1)
        connector = "" if is_last else "<div class='connector'></div>"

        timeline_html += f"""
        <div class="timeline-item">
            <div class="timeline-marker">
                <div class="dot"></div>
                {connector}
            </div>
            <div class="timeline-content">
                <div class="event-header">
                    <span class="event-title">{label}</span>
                    <span class="event-time">{timestamp}</span>
                </div>
                <div class="event-role">Recorded by: {role_label} — {event.get('actor_name', event['actor_id'])} ({event['actor_id']})</div>
                <div class="event-details">{details_html}</div>
                <div class="event-hash">Block hash: {event['block_hash'][:16]}...</div>
            </div>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Jasmine Batch {batch_id} — Traceability</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                font-family: -apple-system, 'Segoe UI', Roboto, sans-serif;
                background: #f7f5f0;
                color: #2c2c2a;
                padding: 24px 16px 60px;
            }}
            .container {{ max-width: 640px; margin: 0 auto; }}
            .header {{
                background: linear-gradient(135deg, #6b8e5a, #4a6b3a);
                color: white;
                border-radius: 16px;
                padding: 24px;
                margin-bottom: 20px;
            }}
            .header h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
            .header .batch-id {{ font-size: 14px; opacity: 0.9; font-family: monospace; }}
            .badge {{
                display: inline-block;
                margin-top: 12px;
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            .badge-ok {{ background: #d4edda; color: #1e5a2b; }}
            .badge-bad {{ background: #f8d7da; color: #7a1f28; }}
            .timeline-item {{ display: flex; margin-bottom: 4px; }}
            .timeline-marker {{
                display: flex;
                flex-direction: column;
                align-items: center;
                margin-right: 16px;
            }}
            .dot {{
                width: 14px; height: 14px;
                background: #4a6b3a;
                border-radius: 50%;
                border: 3px solid #d9e5d0;
                flex-shrink: 0;
                margin-top: 6px;
            }}
            .connector {{
                width: 2px;
                flex-grow: 1;
                background: #d9d5c9;
                margin-top: 4px;
                min-height: 40px;
            }}
            .timeline-content {{
                background: white;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 20px;
                flex: 1;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            }}
            .event-header {{
                display: flex;
                justify-content: space-between;
                align-items: baseline;
                flex-wrap: wrap;
                gap: 6px;
                margin-bottom: 6px;
            }}
            .event-title {{ font-size: 16px; font-weight: 600; color: #2c2c2a; }}
            .event-time {{ font-size: 12px; color: #888780; }}
            .event-role {{ font-size: 13px; color: #5f5e5a; margin-bottom: 10px; }}
            .event-details {{ border-top: 1px solid #f0eee6; padding-top: 10px; }}
            .detail-row {{
                display: flex;
                justify-content: space-between;
                font-size: 13px;
                padding: 3px 0;
                gap: 12px;
            }}
            .detail-label {{ color: #888780; }}
            .detail-value {{ color: #2c2c2a; font-weight: 500; text-align: right; }}
            .event-hash {{
                font-size: 11px;
                color: #b4b2a9;
                font-family: monospace;
                margin-top: 10px;
                border-top: 1px solid #f0eee6;
                padding-top: 8px;
            }}
            .muted {{ color: #b4b2a9; font-size: 13px; }}
            .footer-note {{
                text-align: center;
                font-size: 12px;
                color: #888780;
                margin-top: 20px;
                padding: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Jasmine Traceability Record</h1>
                <div class="batch-id">Batch ID: {batch_id}</div>
                {integrity_badge}
            </div>
            {timeline_html}
            <div class="footer-note">
                This record is secured with blockchain-based hash-chaining.
                Every event above is cryptographically linked and tamper-evident.
            </div>
        </div>
    </body>
    </html>
    """
