from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

LOG_PATH = Path("data/logs.jsonl")


def _percentile(values: list[int | float], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def compute_dashboard_metrics() -> dict:
    if not LOG_PATH.exists():
        return {
            "traffic": 0,
            "latency_p50": 0.0,
            "latency_p95": 0.0,
            "latency_p99": 0.0,
            "ttft_p95": 0.0,
            "error_rate_pct": 0.0,
            "tool_success_rate_pct": 100.0,
            "error_breakdown": {},
            "total_cost_usd": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "quality_avg": 0.0,
            "history": [],
        }

    records: list[dict] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    req_received = [r for r in records if r.get("event") == "request_received"]
    req_sent = [r for r in records if r.get("event") == "response_sent"]
    req_failed = [r for r in records if r.get("event") == "request_failed"]

    latencies = [int(r["latency_ms"]) for r in req_sent if "latency_ms" in r]
    ttfts = [int(r["ttft_ms"]) for r in req_sent if "ttft_ms" in r]
    costs = [float(r["cost_usd"]) for r in req_sent if "cost_usd" in r]
    tokens_in = [int(r["tokens_in"]) for r in req_sent if "tokens_in" in r]
    tokens_out = [int(r["tokens_out"]) for r in req_sent if "tokens_out" in r]
    qualities = [float(r["quality_score"]) for r in req_sent if "quality_score" in r]

    tool_successes = [
        r["tool_success"]
        for r in records
        if "tool_success" in r and r.get("tool_name") == "retrieval" and r.get("tool_success") is not None
    ]
    tool_success_rate = (
        round((sum(1 for s in tool_successes if s is True) / len(tool_successes)) * 100, 1)
        if tool_successes
        else 100.0
    )

    error_breakdown: dict[str, int] = {}
    for r in req_failed:
        err = r.get("error_type", "UnknownError")
        error_breakdown[err] = error_breakdown.get(err, 0) + 1

    total_reqs = len(req_received)
    failed_reqs = len(req_failed)
    error_rate = round((failed_reqs / total_reqs * 100), 2) if total_reqs > 0 else 0.0

    history = []
    for idx, r in enumerate(req_sent):
        history.append({
            "idx": idx + 1,
            "ts": r.get("ts", "")[-12:-4],
            "correlation_id": r.get("correlation_id", ""),
            "latency_ms": r.get("latency_ms", 0),
            "ttft_ms": r.get("ttft_ms", 0),
            "cost_usd": r.get("cost_usd", 0.0),
            "quality_score": r.get("quality_score", 0.0),
            "tokens_in": r.get("tokens_in", 0),
            "tokens_out": r.get("tokens_out", 0),
        })

    return {
        "traffic": total_reqs,
        "latency_p50": _percentile(latencies, 50),
        "latency_p95": _percentile(latencies, 95),
        "latency_p99": _percentile(latencies, 99),
        "ttft_p95": _percentile(ttfts, 95),
        "error_rate_pct": error_rate,
        "tool_success_rate_pct": tool_success_rate,
        "error_breakdown": error_breakdown,
        "total_cost_usd": round(sum(costs), 4),
        "tokens_in": sum(tokens_in),
        "tokens_out": sum(tokens_out),
        "quality_avg": round(mean(qualities), 2) if qualities else 0.0,
        "history": history,
    }


def render_dashboard_html() -> str:
    data = compute_dashboard_metrics()
    history_json = json.dumps(data["history"])
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>K4-L3B Day 13 Monitoring & LLMOps Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-green: #4ade80;
            --accent-red: #f87171;
            --accent-amber: #fbbf24;
            --accent-purple: #c084fc;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            padding: 24px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .header h1 {{ font-size: 24px; color: var(--accent-blue); }}
        .header .meta {{ font-size: 14px; color: var(--text-secondary); text-align: right; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }}
        .panel {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 16px;
            display: flex;
            flex-direction: column;
        }}
        .panel-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 12px;
        }}
        .panel-title {{ font-size: 16px; font-weight: 600; color: var(--text-primary); }}
        .panel-badge {{
            font-size: 11px;
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-blue);
            padding: 2px 8px;
            border-radius: 12px;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 12px;
        }}
        .stat-box {{
            background: rgba(15, 23, 42, 0.6);
            border-radius: 6px;
            padding: 10px;
            text-align: center;
        }}
        .stat-val {{ font-size: 20px; font-weight: 700; color: var(--text-primary); }}
        .stat-label {{ font-size: 11px; color: var(--text-secondary); text-transform: uppercase; margin-top: 2px; }}
        .threshold-banner {{
            font-size: 12px;
            padding: 6px 10px;
            border-radius: 4px;
            background: rgba(51, 65, 85, 0.5);
            color: var(--text-secondary);
            margin-top: auto;
            border-left: 3px solid var(--accent-blue);
        }}
        .chart-box {{ height: 160px; margin-top: 10px; }}
        @media (max-width: 1024px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>K4-L3B Monitoring & LLMOps Dashboard</h1>
            <p style="color: var(--text-secondary); font-size: 13px; margin-top: 4px;">Source: <code>data/logs.jsonl</code> | Auto-refresh: 30s</p>
        </div>
        <div class="meta">
            <div>Học viên: <strong>Phạm Đình Hải</strong> | MSSV: <strong>2A202602482</strong></div>
            <div>Time window: <strong>Last 60 minutes</strong></div>
        </div>
    </div>

    <div class="grid">
        <!-- Panel 1: Latency -->
        <div class="panel" id="panel-latency">
            <div class="panel-header">
                <span class="panel-title">1. Latency percentiles & TTFT</span>
                <span class="panel-badge">Unit: ms</span>
            </div>
            <div class="stat-grid">
                <div class="stat-box"><div class="stat-val">{data['latency_p50']}</div><div class="stat-label">P50</div></div>
                <div class="stat-box"><div class="stat-val" style="color: { 'var(--accent-green)' if data['latency_p95'] <= 3000 else 'var(--accent-red)' }">{data['latency_p95']}</div><div class="stat-label">P95</div></div>
                <div class="stat-box"><div class="stat-val">{data['latency_p99']}</div><div class="stat-label">P99</div></div>
                <div class="stat-box"><div class="stat-val">{data['ttft_p95']}</div><div class="stat-label">TTFT P95</div></div>
            </div>
            <div class="chart-box"><canvas id="chartLatency"></canvas></div>
            <div class="threshold-banner">Threshold: P95 &le; 3000 ms (Current: {data['latency_p95']} ms)</div>
        </div>

        <!-- Panel 2: Traffic -->
        <div class="panel" id="panel-traffic">
            <div class="panel-header">
                <span class="panel-title">2. Request Traffic</span>
                <span class="panel-badge">Unit: reqs/min</span>
            </div>
            <div class="stat-grid">
                <div class="stat-box"><div class="stat-val">{data['traffic']}</div><div class="stat-label">Total Requests</div></div>
                <div class="stat-box"><div class="stat-val">{round(data['traffic'] / max(1, len(data['history'])), 1)}</div><div class="stat-label">Rate / Min</div></div>
            </div>
            <div class="chart-box"><canvas id="chartTraffic"></canvas></div>
            <div class="threshold-banner">Threshold: Rate &ge; 1 req/min (Total: {data['traffic']} requests)</div>
        </div>

        <!-- Panel 3: Errors -->
        <div class="panel" id="panel-errors">
            <div class="panel-header">
                <span class="panel-title">3. Error Rate & Retrieval</span>
                <span class="panel-badge">Unit: percent</span>
            </div>
            <div class="stat-grid">
                <div class="stat-box"><div class="stat-val" style="color: { 'var(--accent-green)' if data['error_rate_pct'] <= 2.0 else 'var(--accent-red)' }">{data['error_rate_pct']}%</div><div class="stat-label">Error Rate</div></div>
                <div class="stat-box"><div class="stat-val" style="color: { 'var(--accent-green)' if data['tool_success_rate_pct'] >= 90.0 else 'var(--accent-red)' }">{data['tool_success_rate_pct']}%</div><div class="stat-label">Retrieval Success</div></div>
            </div>
            <div class="chart-box"><canvas id="chartErrors"></canvas></div>
            <div class="threshold-banner">Threshold: Error rate &le; 2% | Retrieval success &ge; 90%</div>
        </div>

        <!-- Panel 4: Cost -->
        <div class="panel" id="panel-cost">
            <div class="panel-header">
                <span class="panel-title">4. Cost Over Time</span>
                <span class="panel-badge">Unit: USD</span>
            </div>
            <div class="stat-grid">
                <div class="stat-box"><div class="stat-val">${data['total_cost_usd']}</div><div class="stat-label">Total Cost</div></div>
                <div class="stat-box"><div class="stat-val">${round(data['total_cost_usd'] / max(1, len(data['history'])), 4)}</div><div class="stat-label">Avg / Request</div></div>
            </div>
            <div class="chart-box"><canvas id="chartCost"></canvas></div>
            <div class="threshold-banner">Threshold: Total &le; $2.50 USD (Current: ${data['total_cost_usd']})</div>
        </div>

        <!-- Panel 5: Tokens -->
        <div class="panel" id="panel-tokens">
            <div class="panel-header">
                <span class="panel-title">5. Input & Output Tokens</span>
                <span class="panel-badge">Unit: tokens</span>
            </div>
            <div class="stat-grid">
                <div class="stat-box"><div class="stat-val">{data['tokens_in']}</div><div class="stat-label">Tokens In</div></div>
                <div class="stat-box"><div class="stat-val">{data['tokens_out']}</div><div class="stat-label">Tokens Out</div></div>
            </div>
            <div class="chart-box"><canvas id="chartTokens"></canvas></div>
            <div class="threshold-banner">Threshold: Total &le; 50,000 tokens (Sum: {data['tokens_in'] + data['tokens_out']})</div>
        </div>

        <!-- Panel 6: Quality -->
        <div class="panel" id="panel-quality">
            <div class="panel-header">
                <span class="panel-title">6. Quality Proxy</span>
                <span class="panel-badge">Unit: 0.0 - 1.0</span>
            </div>
            <div class="stat-grid">
                <div class="stat-box"><div class="stat-val" style="color: { 'var(--accent-green)' if data['quality_avg'] >= 0.75 else 'var(--accent-red)' }">{data['quality_avg']}</div><div class="stat-label">Mean Quality</div></div>
                <div class="stat-box"><div class="stat-val">&ge; 0.75</div><div class="stat-label">Target Score</div></div>
            </div>
            <div class="chart-box"><canvas id="chartQuality"></canvas></div>
            <div class="threshold-banner">Threshold: Mean Quality &ge; 0.75 (Current: {data['quality_avg']})</div>
        </div>
    </div>

    <script>
        const history = {history_json};
        const labels = history.map(h => '#' + h.idx);

        // Chart 1: Latency
        new Chart(document.getElementById('chartLatency'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'Latency (ms)', data: history.map(h => h.latency_ms), borderColor: '#38bdf8', tension: 0.2 }},
                    {{ label: 'TTFT (ms)', data: history.map(h => h.ttft_ms), borderColor: '#a855f7', tension: 0.2 }}
                ]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }}, scales: {{ y: {{ ticks: {{ color: '#94a3b8' }} }}, x: {{ ticks: {{ color: '#94a3b8' }} }} }} }}
        }});

        // Chart 2: Traffic
        new Chart(document.getElementById('chartTraffic'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{ label: 'Requests', data: history.map(() => 1), backgroundColor: '#38bdf8' }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ ticks: {{ color: '#94a3b8' }} }}, x: {{ ticks: {{ color: '#94a3b8' }} }} }} }}
        }});

        // Chart 3: Errors
        new Chart(document.getElementById('chartErrors'), {{
            type: 'doughnut',
            data: {{
                labels: ['Success', 'Errors'],
                datasets: [{{ data: [{data['traffic'] - int(data['traffic'] * data['error_rate_pct'] / 100)}, {int(data['traffic'] * data['error_rate_pct'] / 100)}], backgroundColor: ['#4ade80', '#f87171'] }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }} }}
        }});

        // Chart 4: Cost
        let cumCost = 0;
        const cumCosts = history.map(h => {{ cumCost += h.cost_usd; return parseFloat(cumCost.toFixed(4)); }});
        new Chart(document.getElementById('chartCost'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{ label: 'Cumulative USD', data: cumCosts, borderColor: '#fbbf24', fill: true, backgroundColor: 'rgba(251, 191, 36, 0.1)', tension: 0.2 }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }}, scales: {{ y: {{ ticks: {{ color: '#94a3b8' }} }}, x: {{ ticks: {{ color: '#94a3b8' }} }} }} }}
        }});

        // Chart 5: Tokens
        new Chart(document.getElementById('chartTokens'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'Tokens In', data: history.map(h => h.tokens_in), backgroundColor: '#38bdf8' }},
                    {{ label: 'Tokens Out', data: history.map(h => h.tokens_out), backgroundColor: '#c084fc' }}
                ]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }}, scales: {{ y: {{ ticks: {{ color: '#94a3b8' }} }}, x: {{ ticks: {{ color: '#94a3b8' }} }} }} }}
        }});

        // Chart 6: Quality
        new Chart(document.getElementById('chartQuality'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{ label: 'Quality Score', data: history.map(h => h.quality_score), borderColor: '#4ade80', tension: 0.2 }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }}, scales: {{ y: {{ min: 0, max: 1, ticks: {{ color: '#94a3b8' }} }}, x: {{ ticks: {{ color: '#94a3b8' }} }} }} }}
        }});
    </script>
</body>
</html>
"""
