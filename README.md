# Agente de vagas — frontend

Página estática (GitHub Pages) que mostra a curadoria de vagas do Tiago
consumindo a API do **backend** ao vivo:

- **Site:** https://dhiegopimenta.github.io/Agente-vagas/
- **Backend/API:** https://agente-vagas-backend.onrender.com
  ([repo](https://github.com/DhiegoPimenta/Agente-vagas-backend))

Tudo mora em [`site/index.html`](site/index.html) — HTML + CSS + JS puro, sem build.
`GET /api/jobs` para a lista, `POST /api/chat` para o chat por vaga.

O pipeline (coleta em RemoteOK/Arbeitnow, score heurístico, análise "Saber mais"
por LLM) vive **só no repo do backend**. Este repo não tem mais Python.

## Deploy

`.github/workflows/curadoria.yml` publica `site/` no GitHub Pages a cada push que
toca `site/**`. Nada de servidor.

## Mexer no frontend

Edita `site/index.html`. Para trocar o backend, muda a constante `BACKEND` no
topo do `<script>`. `git push` → o Actions publica.
