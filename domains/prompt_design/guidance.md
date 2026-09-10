## Ziel

Verbessere einen vorhandenen System-Prompt, ohne dessen Wesen zu verändern.

Der Prompt soll nicht neu erfunden werden. Der Agent soll zuerst erkennen,
welche Aufgabe der vorhandene Prompt erfüllt, für welche Zielgruppe er gedacht
ist, welche Ausgaben er erzwingen soll und welche Einschränkungen wesentlich
sind. Danach soll er den Prompt so überarbeiten, dass dieselbe Aufgabe
zuverlässiger, klarer und robuster erfüllt wird.

---

## Verbesserungsziele

Der verbesserte Prompt soll:

1. den ursprünglichen Zweck und die fachliche Domäne beibehalten,
2. harte Anforderungen, Ausgabeformat, Sprache, Verbote und Sicherheitsregeln
   erhalten,
3. unklare oder zu breite Regeln operationalisieren,
4. Entscheidungskriterien, Fallbacks und Prioritäten explizit machen,
5. redundante oder widersprüchliche Formulierungen reduzieren,
6. robuste Behandlung von Grenzfällen und fehlenden Informationen beschreiben,
7. Prompt-Injection und Rollenverwechslung klar abwehren,
8. für ein LLM direkt ausführbar bleiben,
9. kompakter und konsistenter werden, ohne wichtige Substanz zu verlieren.

---

## Nicht zulässige Optimierungen

Der Agent darf den Prompt nicht verbessern, indem er:

- die eigentliche Aufgabe austauscht,
- zentrale Anforderungen entfernt,
- das Ausgabeformat ohne guten Grund verändert,
- Sicherheits- oder Quellenanforderungen abschwächt,
- unbekannte Informationen ergänzt,
- Bewertungskriterien oder Referenzantworten in den Prompt übernimmt,
- nur eine Zusammenfassung oder Analyse statt eines verbesserten Prompts
  ausgibt.

---

## Ergebnis

Das Ergebnis ist genau der verbesserte Prompt.

Es soll keine Erklärung, kein Änderungsprotokoll und keine zusätzliche
Metadaten-Ausgabe enthalten sein.
