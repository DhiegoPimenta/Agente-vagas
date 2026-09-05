from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Template

TEMPLATE = Template(
    """<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8">
<title>Vagas para {{ nome }} - {{ date }}</title></head>
<body style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:760px;margin:0 auto;padding:16px;color:#1a1a1a;background:#fff">
<h1 style="font-size:20px;margin-bottom:2px">Curadoria de vagas - {{ nome }}</h1>
<p style="color:#666;font-size:13px;margin-top:0">
  {{ date }} &middot; {{ collected }} vagas coletadas &middot; {{ new }} novas &middot;
  {{ total_recommended }} recomendadas{% if hidden_recommended %} (mostrando as {{ recommended|length }} melhores){% endif %} &middot; {{ discarded|length }} descartadas
</p>

<h2 style="font-size:16px;border-bottom:2px solid #eee;padding-bottom:4px">Aplicamos por voce</h2>
{% if applied %}
  {% for s in applied %}
  <div style="border:1px solid #cde;border-radius:8px;padding:12px;margin:10px 0">
    <a href="{{ s.job.url }}" style="font-weight:600;color:#0b5cff;text-decoration:none">{{ s.job.title }}</a>
    <div style="font-size:13px;color:#444">{{ s.job.company }} &middot; {{ s.job.location or '-' }}</div>
  </div>
  {% endfor %}
{% else %}
  <p style="color:#888;font-size:13px">Nada. O auto-apply esta <b>desligado</b> nesta versao (rodando so curadoria).</p>
{% endif %}

<h2 style="font-size:16px;border-bottom:2px solid #eee;padding-bottom:4px">Recomendadas pra voce aplicar</h2>
{% if recommended %}
  {% for s in recommended %}
  <div style="border:1px solid #e5e5e5;border-radius:8px;padding:12px;margin:10px 0">
    <div style="display:flex;justify-content:space-between;gap:8px;align-items:start">
      <a href="{{ s.job.url }}" style="font-weight:600;font-size:15px;color:#0b5cff;text-decoration:none">{{ s.job.title }}</a>
      <span style="background:#0b5cff;color:#fff;border-radius:12px;padding:2px 9px;font-size:12px;white-space:nowrap">{{ s.score }}</span>
    </div>
    <div style="color:#444;font-size:13px;margin:4px 0">
      {{ s.job.company or 'empresa nao informada' }} &middot; {{ s.job.location or '-' }} &middot; <i>{{ s.job.source }}</i>
    </div>
    {% if s.job.has_salary %}
    <div style="font-size:13px;color:#0a7a2f">Salario: {{ s.job.salary_min or '?' }} - {{ s.job.salary_max or '?' }} {{ s.job.salary_currency }}</div>
    {% endif %}
    <ul style="font-size:13px;color:#555;margin:6px 0 0 18px;padding:0">
      {% for r in s.reasons %}<li>{{ r }}</li>{% endfor %}
    </ul>
  </div>
  {% endfor %}
  {% if hidden_recommended %}
  <p style="color:#888;font-size:12px">+ {{ hidden_recommended }} outra(s) tambem acima do corte, com score menor, nao mostradas.</p>
  {% endif %}
{% else %}
  <p style="color:#888;font-size:13px">Nenhuma vaga nova acima do corte (score &gt;= {{ min_score }}) hoje.</p>
{% endif %}

<h2 style="font-size:16px;border-bottom:2px solid #eee;padding-bottom:4px">Descartadas</h2>
<p style="color:#888;font-size:13px">{{ discarded|length }} vagas abaixo do criterio minimo (score &lt; {{ min_score }}).</p>
{% if discarded %}
<details>
  <summary style="cursor:pointer;color:#666;font-size:13px">ver lista</summary>
  <ul style="font-size:12px;color:#999">
    {% for s in discarded %}<li>[{{ s.score }}] {{ s.job.title }} - {{ s.job.company }} ({{ s.job.source }})</li>{% endfor %}
  </ul>
</details>
{% endif %}

<p style="color:#bbb;font-size:11px;margin-top:24px">
  Gerado pelo agente-vagas &middot; fontes: {{ sources }}. LinkedIn e Indeed nao sao automatizados.
</p>
</body></html>
"""
)


def build_report(cfg, collected, new, recommended, discarded, applied=None):
    out_cfg = cfg.get("output", {})
    top = int(out_cfg.get("top_recommend", 0) or 0)
    shown = recommended[:top] if top else list(recommended)

    html = TEMPLATE.render(
        nome=cfg.get("candidate", {}).get("nome", "candidato"),
        date=datetime.now().strftime("%d/%m/%Y %H:%M"),
        collected=collected,
        new=new,
        recommended=shown,
        total_recommended=len(recommended),
        hidden_recommended=len(recommended) - len(shown),
        discarded=discarded,
        applied=applied or [],
        min_score=cfg.get("scoring", {}).get("min_score_recommend", 55),
        sources=", ".join(
            k for k, v in (cfg.get("sources") or {}).items() if isinstance(v, dict) and v.get("enabled")
        ),
    )
    out_dir = Path(out_cfg.get("dir", "output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"vagas-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    path.write_text(html, encoding="utf-8")

    # Copia para a pasta publicada pelo GitHub Pages, se configurada.
    pages_dir = out_cfg.get("pages_dir")
    if pages_dir:
        pd = Path(pages_dir)
        pd.mkdir(parents=True, exist_ok=True)
        (pd / "index.html").write_text(html, encoding="utf-8")

    return html, path
