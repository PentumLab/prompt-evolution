<div align="center">

<h1>Prompt Evolution</h1>

<p>Evolutionary optimization of prompts, agents, and workflows based on HyperAgents</p>

<p>
<a href="LICENSE.md">
  <img src="https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg?style=for-the-badge"
       alt="License: CC BY-NC-SA 4.0">
</a>
<a href="https://github.com/facebookresearch/HyperAgents">
  <img src="https://img.shields.io/badge/Based%20on-HyperAgents-555555.svg?style=for-the-badge"
       alt="Based on HyperAgents">
</a>
</p>

---

</div>

Prompt Evolution ist ein experimentelles Framework zur evolutionären Optimierung von Prompts und Agentensystemen.

Das Projekt basiert direkt auf [HyperAgents](https://github.com/facebookresearch/HyperAgents) und übernimmt dessen Grundidee eines Meta-Agenten, der nicht nur Antworten erzeugt, sondern die Implementierung des Agentensystems selbst untersuchen und verändern kann.

Der erste Referenz-Task ist die evolutionäre Verbesserung eines vorhandenen
System-Prompts für einen evidenzbasierten Fact-Checker von X-Posts.

## Grundprinzip

```text
Vorhandener Source Prompt
            |
            v
      Prompt Generator
            |
            v
     Candidate Prompt
            |
            v
        Evaluation
            |
            v
        Meta-Agent
            |
            v
   Prompt / Agent / Workflow
        wird angepasst
            |
            +------> nächste Generation
```

Der Task-Agent erzeugt zunächst aus einem vorhandenen Source Prompt einen
verbesserten Kandidaten-Prompt. Dieser wird bewertet. Anschließend erhält der
Meta-Agent die Evaluation und analysiert die aktuelle Implementierung.

Im eingeschränkten Modus optimiert er die Prompt-Generierungsstrategie. Im vollständigen Modus darf er zusätzlich relevante Teile des Agenten-Codes und des Workflows verändern.

Evaluationsdaten dürfen nicht verändert werden, um den Score künstlich zu verbessern.

## Aktuelles Beispiel: Fact Check

Die Prompt-Evolution-Domain befindet sich unter:

```text
domains/prompt_design/
```

Die Datei [`domains/prompt_design/prompt.md`](domains/prompt_design/prompt.md)
enthält den vorhandenen Source Prompt, der verbessert werden soll.

Die Datei [`domains/prompt_design/guidance.md`](domains/prompt_design/guidance.md)
enthält die Verbesserungsleitlinie. Sie beschreibt, dass der Prompt analysiert
und verbessert werden soll, ohne seinen Kern, seine Domäne, sein Ausgabeformat
oder seine Sicherheitsgrenzen zu verlieren.

Der Meta-Agent erhält die Bewertung einer Generation als Feedback für den
nächsten Evolutionsschritt und verbessert die Strategie, mit der der vorhandene
Prompt überarbeitet wird.

Generierte Candidate Prompts, Evaluationen und Reports werden unter `outputs/` abgelegt und nicht in Git gespeichert.

## Quickstart

### 1. Repository klonen

```bash
git clone https://github.com/PentumLab/prompt-evolution.git
cd prompt-evolution
```

### 2. Python-Umgebung vorbereiten

```bash
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

Die ursprüngliche HyperAgents-Dokumentation mit zusätzlicher Setup- und Docker-Infrastruktur befindet sich in [`README_HYPERAGENTS.md`](README_HYPERAGENTS.md).

### 3. Lokale Konfiguration anlegen

```bash
cp .env.example .env
cp hyperagent_config.example.json hyperagent_config.json
```

Für den aktuellen Meta-Agenten wird ein Anthropic API-Key benötigt:

```text
ANTHROPIC_API_KEY=...
```

Die mitgelieferte `.env.example` enthält außerdem einen lokalen OpenAI-kompatiblen vLLM-Endpunkt:

```text
HOSTED_VLLM_API_BASE=http://127.0.0.1:8000/v1
```

`hyperagent_config.json` ist die lokale, nicht eingecheckte Runtime-Konfiguration.
Dort werden Modelle, per-call Output-Limits, kumulative Token-Limits und der
Usage-Log-Pfad gesetzt. Das Repository enthält nur
`hyperagent_config.example.json` als sichere Vorlage.

Wichtige Felder:

```json
{
  "models": {
    "meta_agent": "anthropic/claude-haiku-4-5-20251001",
    "task_agent": "hosted_vllm/gemma-4",
    "prompt_design_task_agent": "hosted_vllm/gemma-4"
  },
  "defaults": {
    "max_output_tokens": 16384,
    "max_tool_calls": 40
  },
  "agent_max_output_tokens": {
    "meta_agent": 4000,
    "task_agent": "DEFAULT",
    "prompt_design_task_agent": 8000
  },
  "agent_max_tool_calls": {
    "meta_agent": 20
  },
  "usage": {
    "log_filename": "llm_usage.jsonl",
    "log_path": null
  },
  "model_token_limits": {
    "anthropic/claude-haiku-4-5-20251001": 150000,
    "hosted_vllm/gemma-4": "UNLIMITED"
  }
}
```

`agent_max_output_tokens` begrenzt die Output-Tokens pro LLM-Aufruf.
`agent_max_tool_calls` begrenzt die Tool-Aufrufe pro Agent-Lauf.
`model_token_limits` begrenzt den kumulierten Tokenverbrauch pro Modell anhand
des Usage-Logs.

Für `agent_max_output_tokens`, `model_max_output_tokens` und
`agent_max_tool_calls` gelten:

- Zahl: genau dieses Limit verwenden
- `"DEFAULT"` oder `null`: den passenden Wert aus `defaults` verwenden
- `"UNLIMITED"` oder `-1`: kein entsprechendes Limit setzen

### 4. Task-Agent-Modell bereitstellen

Der aktuelle Prompt-Generator verwendet:

```text
hosted_vllm/gemma-4
```

Vor dem ersten Evolutionslauf muss der dafür verwendete OpenAI-kompatible Modell-Endpunkt erreichbar sein.

### 5. Generation 0 erzeugen

Lege zuerst den vorhandenen Prompt in dieser Datei ab:

```text
domains/prompt_design/prompt.md
```

Optional kann die Verbesserungsleitlinie angepasst werden:

```text
domains/prompt_design/guidance.md
```

Dann erzeugst du den ersten Candidate Prompt:

```bash
PYTHONPATH=. python domains/prompt_design/harness.py --generation 0
```

Der erzeugte Prompt wird gespeichert unter:

```text
outputs/prompt_design/gen_000/candidate_prompt.txt
```

Damit entsteht die Ausgangsgeneration aus der eingecheckten, noch nicht
evolvierten Prompt-Verbesserungsstrategie.

Alternativ kann ein anderer Source Prompt übergeben werden:

```bash
PYTHONPATH=. python domains/prompt_design/harness.py \
  --generation 0 \
  --source-prompt /path/to/source_prompt.md
```

Den aktuellen Zustand der Generationen kannst du jederzeit prüfen:

```bash
PYTHONPATH=. python domains/prompt_design/state.py status
```

Die Ausgabe zeigt pro Generation Score, Parent, Snapshot-Status und ob die
Generation als Parent für weitere Evolutionsschritte auswählbar ist.

### 6. Generation bewerten

Die aktuelle Implementierung verwendet eine manuelle Evaluation.

Lege folgende Datei an:

```text
outputs/prompt_design/gen_000/manual_evaluation.json
```

Beispiel:

```json
{
  "score": 67,
  "methodology": 21,
  "consistency": 18,
  "robustness": 14,
  "efficiency": 14,
  "feedback": "Describe the most important weaknesses and possible improvements."
}
```

Die vier Teilbewertungen müssen jeweils zwischen `0` und `25` liegen:

- `methodology`
- `consistency`
- `robustness`
- `efficiency`

Ihre Summe muss dem Wert von `score` entsprechen.

### 7. Evaluation validieren

```bash
PYTHONPATH=. python domains/prompt_design/manual_evaluator.py --generation 0
```

Dadurch entsteht:

```text
outputs/prompt_design/gen_000/report.json
```

Dieser Report dient als Feedback für den Meta-Agenten.

### 8. Meta-Agent ausführen

#### Prompt-Evolution

```bash
PYTHONPATH=. python domains/prompt_design/meta_step.py \
  --generation 0 \
  --target-generation 1 \
  --scope prompt
```

Im Modus `prompt` bleibt die öffentliche Schnittstelle

```python
generate_prompt(task: str) -> str
```

erhalten.

Der Task-Agent verwendet weiterhin einen einzelnen Modellaufruf. Der Meta-Agent
optimiert die Strategie, mit der der vorhandene Source Prompt verbessert wird.

Der frühere `full`-Scope ist in der schlanken Prompt-Evolution-Mini-Loop noch
nicht aktiviert, weil dieser Ablauf aktuell nur `prompt_design_agent.py` sauber
snapshotet und patcht.

Der Meta-Step erstellt oder aktualisiert:

```text
outputs/prompt_design/gen_001/prompt_design_agent.py
outputs/prompt_design/gen_001/model_patch.diff
outputs/prompt_design/gen_001/meta_agent_chat_history.md
outputs/prompt_design/gen_001/meta_workspace/
outputs/prompt_design/gen_001/metadata.json
```

Am Ende des Meta-Steps läuft automatisch eine Validierung. Sie prüft, ob ein
kompilierbarer Agent-Snapshot existiert, ob sich `prompt_design_agent.py`
gegenüber dem Parent wirklich geändert hat und ob `model_patch.diff` nicht leer
ist. Fehlgeschlagene Läufe werden in `metadata.json` als `failed` markiert und
nicht als auswählbarer Parent verwendet.

Eine Generation kann auch manuell geprüft werden:

```bash
PYTHONPATH=. python domains/prompt_design/state.py validate --generation 1
```

Wenn ein Lauf wegen eines Tokenlimits abbricht, wird ein Resume-State
gespeichert:

```text
outputs/prompt_design/gen_001/meta_agent_resume_state.json
```

Nach Anpassung des Limits kann derselbe Lauf fortgesetzt werden:

```bash
PYTHONPATH=. python domains/prompt_design/meta_step.py \
  --generation 0 \
  --target-generation 1 \
  --scope prompt \
  --resume
```

Beim Resume wird der Parent nicht erneut restored und der bestehende Chatlog
nicht gelöscht.

### 9. Nächste Generation erzeugen

Nach dem Meta-Schritt:

```bash
PYTHONPATH=. python domains/prompt_design/harness.py --generation 1
```

Der nächste Candidate Prompt liegt dann unter:

```text
outputs/prompt_design/gen_001/candidate_prompt.txt
```

Danach kann Generation 1 wieder bewertet, validiert und als Feedback für einen weiteren Meta-Schritt verwendet werden.

```text
Generation 0
    |
    v
candidate_prompt.txt
    |
    v
manual_evaluation.json
    |
    v
report.json
    |
    v
Meta-Agent verändert die Implementierung
    |
    v
Generation 1
```

## Parent-Auswahl und Restore

Der nächste Evolutionsschritt kann explizit von einer bestimmten Generation
starten:

```bash
PYTHONPATH=. python domains/prompt_design/meta_step.py \
  --generation 7 \
  --target-generation 9 \
  --scope prompt
```

Alternativ kann der Parent automatisch gewählt werden:

```bash
PYTHONPATH=. python domains/prompt_design/meta_step.py \
  --parent-selection best \
  --target-generation 9 \
  --scope prompt
```

Verfügbare Auswahlmethoden:

```text
best
latest
random
score_prop
score_child_prop
```

Eine gespeicherte Generation kann in den Arbeitsbaum zurückkopiert werden:

```bash
PYTHONPATH=. python domains/prompt_design/state.py restore --generation 7
```

Das überschreibt `prompt_design_agent.py` mit dem Snapshot aus der gewählten
Generation.

## Typischer Zyklus

```bash
# 1. Candidate Prompt aus vorhandenem Source Prompt erzeugen
PYTHONPATH=. python domains/prompt_design/harness.py --generation 0

# 2. outputs/prompt_design/gen_000/manual_evaluation.json anlegen

# 3. Bewertung validieren
PYTHONPATH=. python domains/prompt_design/manual_evaluator.py --generation 0

# 4. Aus bestem Parent neue Generation erzeugen
PYTHONPATH=. python domains/prompt_design/meta_step.py --parent-selection best --scope prompt

# 5. Candidate Prompt der neuen Generation erzeugen
PYTHONPATH=. python domains/prompt_design/harness.py --generation 1
```

Danach wird die neue Generation wieder bewertet und als Feedback für den
nächsten Meta-Schritt verwendet.

## Evolutionsmodi

### `prompt`

Der konservative Modus.

Der Meta-Agent optimiert die Prompt-Generierungsstrategie, während die zentrale `generate_prompt(task: str) -> str`-Schnittstelle und der einzelne Task-Agent-Modellaufruf erhalten bleiben.

Ein späterer `full`-Modus müsste mehrere Dateien als Snapshot oder Git-Patch
verwalten. Für diesen offenen Modus ist weiterhin die ursprüngliche
HyperAgents-`generate_loop.py` die passendere Grundlage.

## Aktueller Modellaufbau

```text
Task-Agent:  hosted_vllm/gemma-4
Meta-Agent:  anthropic/claude-haiku-4-5-20251001
```

Modelle, per-call Output-Limits und kumulative Token-Limits werden in
`hyperagent_config.json` konfiguriert.

## Output-Struktur

Ein Lauf erzeugt beispielsweise:

```text
outputs/
└── prompt_design/
    ├── archive.jsonl
    ├── gen_000/
    │   ├── prompt_design_agent.py
    │   ├── candidate_prompt.txt
    │   ├── manual_evaluation.json
    │   ├── report.json
    │   └── metadata.json
    └── gen_001/
        ├── prompt_design_agent.py
        ├── model_patch.diff
        ├── meta_agent_chat_history.md
        ├── meta_workspace/
        ├── candidate_prompt.txt
        ├── manual_evaluation.json
        ├── report.json
        └── metadata.json
```

Diese Dateien sind Experiment-Artefakte und werden nicht in Git eingecheckt.

Ein HTML-/Webseiten-Report-Generator ist im aktuellen Repository nicht enthalten.

## Projektstruktur

```text
agent/
    Foundation-Model- und Tool-Anbindung aus HyperAgents

domains/
    HyperAgents-Domains und Prompt-Evolution-Domains

domains/prompt_design/
    prompt.md
        vorhandener Source Prompt, der verbessert werden soll

    guidance.md
        Verbesserungsleitlinie für den Source Prompt

    harness.py
        erzeugt Candidate Prompts für eine Generation aus prompt.md und guidance.md

    manual_evaluator.py
        validiert manuelle Bewertungen und erzeugt report.json

    meta_step.py
        führt den Meta-Agenten mit Evaluation und Evolutionsmodus aus

    state.py
        verwaltet Snapshots, Parent-Auswahl, Restore, Validierung und archive.jsonl

prompt_design_agent.py
    initialer Prompt-Verbesserer für Generation 0

outputs/
    generierte Experiment-Artefakte
    (nicht in Git gespeichert)

README_HYPERAGENTS.md
    ursprüngliche HyperAgents-Dokumentation

NOTICE.md
    Attribution und Herkunft des Projekts
```

## Sicherheit

Der Meta-Agent kann Dateien und Code verändern. In der aktuellen
Prompt-Evolution-Mini-Loop ist dieser Schreibpfad auf `prompt_design_agent.py`
und den jeweiligen `meta_workspace` ausgerichtet.

Damit gilt dieselbe grundlegende Sicherheitsproblematik wie bei HyperAgents: modellgenerierter Code sollte als nicht vertrauenswürdig behandelt werden.

Experimente sollten bevorzugt in einer isolierten Umgebung, einem Container oder einem entbehrlichen Git-Checkout durchgeführt werden.

Produktionssysteme, sensible Dateien und Zugangsdaten sollten nicht für autonome Code-Evolution freigegeben werden.

## Reproduzierbarkeit und Git

Der eingecheckte Stand enthält die Ausgangsimplementierung vor der ersten Evolution.

Generierte Prompts und spätere Evolutionsstände gehören zu einem Experimentlauf und werden nicht als Ausgangszustand des Projekts eingecheckt.

Für reproduzierbare Experimente sollte jeder Lauf von einem bekannten Git-Commit beziehungsweise Tag gestartet werden.

Der verwendete HyperAgents-Upstream-Stand ist mit folgendem Tag markiert:

```text
hyperagents-base-59a68f6
```

## HyperAgents

Prompt Evolution basiert auf dem HyperAgents-Projekt von Meta Platforms, Inc. and affiliates:

https://github.com/facebookresearch/HyperAgents

Verwendeter Upstream-Basis-Commit:

```text
59a68f6
```

Dieser Stand ist in diesem Repository zusätzlich markiert als:

```text
hyperagents-base-59a68f6
```

Die ursprüngliche HyperAgents-Dokumentation befindet sich in [`README_HYPERAGENTS.md`](README_HYPERAGENTS.md).

Prompt Evolution ist ein unabhängiges Projekt und ist weder mit Meta Platforms, Inc. verbunden noch von Meta unterstützt.

Weitere Hinweise zur Herkunft befinden sich in [`NOTICE.md`](NOTICE.md).

## Lizenz

Prompt Evolution wird unter der **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License** veröffentlicht.

Siehe:

- [`LICENSE.md`](LICENSE.md)
- [`NOTICE.md`](NOTICE.md)

Die Lizenz erlaubt Nutzung, Veränderung und Weitergabe unter ihren Bedingungen, einschließlich Attribution, NonCommercial und ShareAlike.
