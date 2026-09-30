from __future__ import annotations

import time

from .incidents import STATE
from .tracing import get_langfuse_client, observe

CORPUS = {
    "refund": ["Refunds are available within 7 days with proof of purchase."],
    "monitoring": ["Metrics detect incidents, logs identify affected requests, traces localize the root cause."],
    "policy": ["Do not expose PII in logs. Use sanitized summaries only."],
}


@observe(name="retrieval", as_type="retriever", capture_input=False, capture_output=False)
def retrieve(message: str) -> list[str]:
    client = get_langfuse_client()
    if STATE["tool_fail"]:
        if hasattr(client, "update_current_span"):
            try:
                client.update_current_span(
                    level="ERROR",
                    status_message="Vector store timeout",
                )
            except Exception:
                pass
        raise RuntimeError("Vector store timeout")
    if STATE["rag_slow"]:
        time.sleep(2.5)
    lowered = message.lower()
    for key, docs in CORPUS.items():
        if key in lowered:
            if hasattr(client, "update_current_span"):
                try:
                    client.update_current_span(
                        metadata={"matched_key": key, "doc_count": len(docs)}
                    )
                except Exception:
                    pass
            return docs
    fallback = ["No domain document matched. Use general fallback answer."]
    if hasattr(client, "update_current_span"):
        try:
            client.update_current_span(
                metadata={"matched_key": "fallback", "doc_count": len(fallback)}
            )
        except Exception:
            pass
    return fallback
