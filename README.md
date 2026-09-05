# Agente de curadoria de vagas — Tiago

Roda periodicamente, busca vagas em fontes com API pública, faz o *match* com o
perfil do Tiago e gera um **relatório HTML** (opcionalmente enviado por e‑mail)
com as vagas ranqueadas.

> **Esta versão roda em modo "só curadoria".** Não aplica em vaga nenhuma
> automaticamente. Isso é proposital — a spec original manda rodar 1–2 semanas só
> observando antes de considerar auto‑apply.

---

## O que ele faz

1. **Coleta** vagas das últimas 48h em: RemoteOK, Arbeitnow e (opcional) Adzuna.
2. **Deduplica** por empresa + título + local.
3. **Dá um score de 0 a 100** para cada vaga nova, comparando com o perfil:
   - por heurística (padrão, não precisa de nada), ou
   - por LLM (se você instalar `anthropic` e setar `ANTHROPIC_API_KEY`).
4. **Roteia**: `score >= 55` → *Recomendadas*; abaixo → *Descartadas*.
5. **Gera** `output/vagas-AAAAMMDD-HHMMSS.html` e, se `email.enabled: true`, envia.
6. **Guarda** tudo num SQLite (`data/jobagent.sqlite3`) pra nunca repetir vaga.

**LinkedIn e Indeed nunca são acessados** — os Termos de Uso proíbem automação.
Se o Tiago quiser vagas de lá, ele usa os alertas nativos do LinkedIn e aplica na mão.

---

## Instalação (Windows / PowerShell)

```bash
cd C:\Users\dhieg\agente-vagas
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuração

```bash
python run.py --init
```

Isso cria `config.yaml`. Abra e ajuste:

- `candidate.*` — dados do Tiago. O essencial já vem preenchido (Angular, React,
  Java, C#, Python; pleno/sênior; remoto/híbrido). Falta:
  - `faixa_salarial_min` (deixe `0` pra não filtrar por salário)
  - `email_destino`
  - `resumo_curriculo` — preencha quando o currículo dele chegar (só o score por LLM usa)
- `sources.adzuna` — deixe `enabled: false` por enquanto. Pra ligar: crie uma
  chave grátis em https://developer.adzuna.com e ponha `app_id`/`app_key` (ou use
  as variáveis `ADZUNA_APP_ID` / `ADZUNA_APP_KEY`).
- `email` — deixe `enabled: false` pra só gerar o arquivo. Pra enviar de verdade,
  veja "E‑mail" abaixo.

`config.yaml` está no `.gitignore` — não versione, ele tem dados pessoais.

## Rodar

```bash
python run.py --dry-run   # testa tudo sem gravar nada
python run.py             # roda de verdade: grava no banco + gera relatório
```

O relatório fica em `output/`. Abra o `.html` mais recente no navegador.

---

## E‑mail (opcional)

No `config.yaml`, seção `email`: `enabled: true`, preencha `smtp_host`,
`smtp_port`, `smtp_user`, `from_addr`, `to_addr`.

A **senha nunca vai no arquivo** — vem de uma variável de ambiente
(`smtp_password_env`, por padrão `JOBAGENT_SMTP_PASSWORD`).

Gmail: use uma **Senha de app** (Conta Google → Segurança → Verificação em duas
etapas → Senhas de app), não a senha normal.

```powershell
$env:JOBAGENT_SMTP_PASSWORD = "a-senha-de-app"
python run.py
```

---

## Publicação automática no GitHub Pages (sem backend)

O arquivo [`.github/workflows/curadoria.yml`](.github/workflows/curadoria.yml) faz tudo
dentro do GitHub — **não precisa de servidor**:

1. Roda todo dia às **07:00 (horário de Brasília)** — ou na hora que você quiser
   (edite o `cron`; ele usa UTC). Também dá pra rodar na mão em **Actions →
   Curadoria de vagas → Run workflow**.
2. Executa `python run.py`, que gera `docs/index.html`.
3. Publica essa pasta no **GitHub Pages**.

Link do Tiago depois do primeiro run: `https://<seu-usuario>.github.io/<repo>/`

### Passo único que você precisa fazer: a chave da Anthropic

O workflow lê a chave de um **secret** do repositório. **Adicione você mesmo**
(nunca comite a chave):

1. No GitHub, vá em **Settings → Secrets and variables → Actions → New repository secret**
2. Name: `ANTHROPIC_API_KEY`
3. Secret: cole a chave (`sk-ant-...`)
4. Salve e rode o workflow de novo (**Actions → Run workflow**)

Sem esse secret o site ainda funciona, só que o score usa a **heurística** em vez do LLM.

> Se você já colou essa chave em algum chat/lugar, **gere uma nova** em
> https://console.anthropic.com/settings/keys e use a nova só aqui no secret.

### Rodar localmente todo dia (opcional, alternativa ao GitHub)

`run-diario.ps1`:

```powershell
Set-Location $PSScriptRoot
.\.venv\Scripts\python.exe run.py
```

```powershell
schtasks /Create /SC DAILY /ST 07:00 /TN "AgenteVagasTiago" `
  /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\dhieg\agente-vagas\run-diario.ps1"
```

---

## Score por LLM

`anthropic` já vem em `requirements.txt`. Para usar o LLM **localmente**:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python run.py
```

No GitHub, a chave vem do secret `ANTHROPIC_API_KEY` (ver seção acima).

Com `scoring.mode: auto` (padrão), ele usa o LLM se a chave existir e cai na
heurística se der qualquer erro ou se a chave não estiver setada. O modelo
default é `claude-sonnet-5` (configurável em `scoring.llm_model`).

---

## Estrutura

```
run.py                  entrypoint (--init / --dry-run / normal)
config.example.yaml     modelo de configuração
jobagent/
  pipeline.py           orquestra tudo
  sources/              remoteok.py, arbeitnow.py, adzuna.py (+ base, registry)
  scoring.py            heurística + score por LLM
  forms.py              classificação de formulário (sempre "complexo" nesta versão)
  routing.py            recomendada / descartada / auto_apply
  store.py              SQLite (dedupe entre execuções)
  report.py             gera o HTML
  emailer.py            envio SMTP opcional
```

---

## Salvaguardas (já embutidas)

- `linkedin` / `indeed` bloqueados no código — nem dá pra habilitar.
- Auto‑apply desligado **e não implementado** nesta versão.
- Formulário sempre tratado como "complexo" (fail‑safe da spec).
- Nada é reenviado: cada vaga entra no SQLite na primeira vez que aparece.
- `config.yaml` e `data/` fora do controle de versão.

## Próximos passos

1. Preencher `resumo_curriculo` e `curriculo_arquivo` quando o CV do Tiago chegar.
2. Rodar 1–2 semanas em curadoria e ajustar `min_score_recommend` conforme o que
   o Tiago acha das recomendações.
3. Só depois disso discutir auto‑apply — e apenas para ATS com submissão
   programática oficial (ex.: Greenhouse/Lever com endpoint público), nunca
   automação de navegador em site que proíba.
