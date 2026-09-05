from __future__ import annotations

import sys

from .config import load_config
from .emailer import send_email
from .forms import classify_form
from .models import Job, Scored
from .report import build_report
from .routing import route
from .scoring import score_all
from .sources import BLOCKED, build_sources
from .store import Store


def _dedupe(jobs: list[Job]) -> list[Job]:
    """Remove duplicatas por (empresa + titulo + local), mantendo a primeira ocorrencia."""
    seen: dict[str, Job] = {}
    for job in jobs:
        key = " | ".join(part.strip().lower() for part in (job.company, job.title, job.location))
        seen.setdefault(key, job)
    return list(seen.values())


def run(config_path: str, dry_run: bool = False) -> int:
    cfg = load_config(config_path)
    cand = cfg.get("candidate", {})
    coll = cfg.get("collection", {})
    lookback = int(coll.get("lookback_hours", 48))
    cap = int(coll.get("max_jobs_per_source", 200))

    print(f"[1] Coleta (ultimas {lookback}h)")
    collected: list[Job] = []
    for source in build_sources(cfg):
        try:
            got = source.fetch(lookback, cap)
            print(f"    {source.name}: {len(got)} vagas")
            collected.extend(got)
        except Exception as exc:  # uma fonte quebrada nao derruba o resto
            print(f"    {source.name}: ERRO - {exc}", file=sys.stderr)

    collected = [j for j in collected if j.source not in BLOCKED]
    deduped = _dedupe(collected)

    store = Store(cfg.get("output", {}).get("db_path", "data/jobagent.sqlite3"))
    already = store.known([j.uid for j in deduped])
    fresh = [j for j in deduped if j.uid not in already]
    print(f"[2] {len(collected)} coletadas - {len(deduped)} unicas - {len(fresh)} novas (nao vistas antes)")

    print("[3] Score + roteamento")
    scored: list[Scored] = score_all(fresh, cand, cfg)
    for s in scored:
        s.form_complexity = classify_form(s.job)
        route(s, cfg)
        if not dry_run:
            store.upsert(s)

    recommended = sorted((s for s in scored if s.route == "recomendada"), key=lambda s: s.score, reverse=True)
    discarded = sorted((s for s in scored if s.route == "descartada"), key=lambda s: s.score, reverse=True)
    applied = [s for s in scored if s.route == "auto_apply"]  # sempre vazio nesta versao

    html, path = build_report(cfg, len(deduped), len(fresh), recommended, discarded, applied)
    print(f"[4] Relatorio: {path}  ({len(recommended)} recomendadas, {len(discarded)} descartadas)")

    if dry_run:
        print("[5] dry-run: nada gravado no banco, e-mail nao enviado.")
        store.conn.close()
        return 0

    store.record_run(len(deduped), len(fresh), len(recommended), len(discarded))
    print(f"[5] {send_email(cfg, html)}")
    store.mark_emailed([s.job.uid for s in recommended])
    store.close()
    return 0
