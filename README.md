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

Der erste Referenz-Task ist die Evolution eines System-Prompts für einen evidenzbasierten Fact-Checker von X-Posts.

## Grundprinzip

```text
Task / Ausgangsspezifikation
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

Der Task-Agent erzeugt zunächst einen Kandidaten-Prompt. Dieser wird bewertet. Anschließend erhält der Meta-Agent die Evaluation und analysiert die aktuelle Implementierung.

Im eingeschränkten Modus optimiert er die Prompt-Generierungsstrategie. Im vollständigen Modus darf er zusätzlich relevante Teile des Agenten-Codes und des Workflows verändern.

Evaluationsdaten dürfen nicht verändert werden, um den Score künstlich zu verbessern.

## Aktuelles Beispiel: Fact Check

Die Prompt-Evolution-Domain befindet sich unter:

```text
domains/prompt_design/
```

Die Datei [`domains/prompt_design/task.md`](domains/prompt_design/task.md) enthält die Ausgangsspezifikation für einen Fact-Checking-System-Prompt.

Sie enthält bewusst konkrete Designannahmen. Diese müssen nicht zwangsläufig optimal sein. Der Meta-Agent erhält die Bewertung einer Generation als Feedback für den nächsten Evolutionsschritt.

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
```

Für den aktuellen Meta-Agenten wird ein Anthropic API-Key benötigt:

```text
ANTHROPIC_API_KEY=...
```

Die mitgelieferte `.env.example` enthält außerdem einen lokalen OpenAI-kompatiblen vLLM-Endpunkt:

```text
HOSTED_VLLM_API_BASE=http://127.0.0.1:8000/v1
```

### 4. Task-Agent-Modell bereitstellen

Der aktuelle Prompt-Generator verwendet:

```text
hosted_vllm/gemma-4
```

Vor dem ersten Evolutionslauf muss der dafür verwendete OpenAI-kompatible Modell-Endpunkt erreichbar sein.

### 5. Generation 0 erzeugen

```bash
PYTHONPATH=. python domains/prompt_design/harness.py --generation 0
```

Der erzeugte Prompt wird gespeichert unter:

```text
outputs/prompt_design/gen_000/candidate_prompt.txt
```

Damit entsteht die Ausgangsgeneration aus der eingecheckten, noch nicht evolvierten Prompt-Generierungsstrategie.

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
  --scope prompt
```

Im Modus `prompt` bleibt die öffentliche Schnittstelle

```python
generate_prompt(task: str) -> str
```

erhalten.

Der Task-Agent verwendet weiterhin einen einzelnen Modellaufruf. Der Meta-Agent optimiert die Strategie, mit der der eigentliche System-Prompt erzeugt wird.

#### Full Evolution

```bash
PYTHONPATH=. python domains/prompt_design/meta_step.py \
  --generation 0 \
  --scope full
```

Im Modus `full` darf der Meta-Agent relevante Teile der Agentenimplementierung und des Workflows verändern, sofern der Experimentablauf funktionsfähig bleibt.

Evaluationsdaten und die aktuelle Task-Definition dürfen dabei nicht verändert werden.

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

## Evolutionsmodi

### `prompt`

Der konservative Modus.

Der Meta-Agent optimiert die Prompt-Generierungsstrategie, während die zentrale `generate_prompt(task: str) -> str`-Schnittstelle und der einzelne Task-Agent-Modellaufruf erhalten bleiben.

### `full`

Dieser Modus behält die weitergehende HyperAgents-Idee bei.

Der Meta-Agent darf relevante Teile des Agenten-Codes und des Workflows verändern. Dadurch kann nicht nur der Text eines Prompts, sondern auch die Strategie zur Prompt-Erzeugung beziehungsweise der Agentenablauf selbst verändert werden.

Die aktuelle `task.md` bleibt in beiden Modi geschützt.

## Aktueller Modellaufbau

```text
Task-Agent:  hosted_vllm/gemma-4
Meta-Agent:  anthropic/claude-haiku-4-5-20251001
```

Für den Meta-Agenten ist in `agent/llm.py` ein separates maximales Output-Budget definiert.

## Output-Struktur

Ein Lauf erzeugt beispielsweise:

```text
outputs/
└── prompt_design/
    ├── gen_000/
    │   ├── candidate_prompt.txt
    │   ├── manual_evaluation.json
    │   └── report.json
    └── gen_001/
        ├── candidate_prompt.txt
        ├── manual_evaluation.json
        └── report.json
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
    task.md
        Ausgangsspezifikation

    harness.py
        erzeugt Candidate Prompts für eine Generation

    manual_evaluator.py
        validiert manuelle Bewertungen und erzeugt report.json

    meta_step.py
        führt den Meta-Agenten mit Evaluation und Evolutionsmodus aus

prompt_design_agent.py
    initialer Prompt-Generator für Generation 0

outputs/
    generierte Experiment-Artefakte
    (nicht in Git gespeichert)

README_HYPERAGENTS.md
    ursprüngliche HyperAgents-Dokumentation

NOTICE.md
    Attribution und Herkunft des Projekts
```

## Sicherheit

Der Meta-Agent kann insbesondere im Modus `full` Dateien und Code verändern.

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
