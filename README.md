# Prompt Evolution

Prompt Evolution ist ein auf HyperAgents basierendes Framework zur evolutionären Optimierung von Prompts.

Ein Task-Agent erzeugt einen Kandidaten-Prompt. Dieser wird bewertet. Ein Meta-Agent analysiert die Bewertung und kann die Prompt-Generierungsstrategie sowie – je nach Experiment – weitere Teile des Agentenablaufs verändern. Die nächste Generation wird anschließend erneut ausgeführt und bewertet.

## Aktueller Schwerpunkt

Die erste Referenzaufgabe ist die Evolution eines System-Prompts für einen evidenzbasierten Fact-Checker.

Das Projekt soll später zusätzlich Deliberation zwischen mehreren Agenten unterstützen, beispielsweise:

1. gemeinsames Lesen eines Fachtexts,
2. Diskussion der darin beschriebenen Probleme,
3. Übertragung relevanter Erkenntnisse auf die aktuelle Aufgabe,
4. autonome Anpassung des Agentensystems.

## Basis

Prompt Evolution basiert auf:

**HyperAgents**
Meta Platforms, Inc. and affiliates
Upstream: https://github.com/facebookresearch/HyperAgents
Basis-Commit: `59a68f6`

Die ursprüngliche HyperAgents-Dokumentation befindet sich in
[`README_HYPERAGENTS.md`](README_HYPERAGENTS.md).

## Lizenz

Dieses Projekt wird unter der Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License veröffentlicht.

Siehe [`LICENSE.md`](LICENSE.md) und [`NOTICE.md`](NOTICE.md).

## Status

Das Projekt befindet sich derzeit im experimentellen Aufbau.

## Modelle

Das erste Prompt-Evolution-Beispiel verwendet standardmäßig:

- einen lokal über vLLM bereitgestellten Task-Agent (`hosted_vllm/gemma-4`)
- Claude Haiku 4.5 als Meta-Agent (`anthropic/claude-haiku-4-5-20251001`)

API-Schlüssel und lokale Endpunkte werden nicht eingecheckt. Eine Vorlage befindet sich in `.env.example`.

Die Modellkonfiguration soll in späteren Versionen vollständig konfigurierbar werden.
