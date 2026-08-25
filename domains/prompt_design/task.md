## Ziel

Entwickle und optimiere einen **System-Prompt für einen KI-basierten Fact-Checker von X-Posts**.

Der erzeugte Prompt soll ein KI-Modell dazu zwingen, X-Posts nicht nur auf einzelne wahre oder falsche Aussagen zu prüfen, sondern einen vollständigen **Quellen-, Kontext-, Zeit-, Zuschreibungs-, Kausalitäts- und Argumentationscheck** durchzuführen.

Der HyperAgent darf den Prompt über mehrere Generationen verändern und verbessern. Ziel ist ein möglichst zuverlässiger, reproduzierbarer und kompakter Fact-Checking-Workflow.

---

## Anforderungen an den zu entwickelnden Prompt

### 1. Originalpost prüfen

Der Fact-Checker soll zunächst den vollständigen Originalpost auf X ermitteln.

Wenn ein Screenshot vorliegt:

- Originalpost suchen,
- Screenshot mit Originalpost vergleichen,
- prüfen, ob Text fehlt oder verändert wurde,
- zusätzliche Aussagen des Originalposts berücksichtigen.

Der Screenshot allein darf nicht als vollständige Quelle behandelt werden.

---

### 2. Tatsachenbehauptungen einzeln prüfen

Alle wesentlichen überprüfbaren Behauptungen müssen getrennt identifiziert und bewertet werden.

Für jede wesentliche Behauptung sollen möglichst **2–3 unabhängige Quellen** verwendet werden.

Bevorzugte Mischung:

1. Primärquelle, Behörde oder offizielle Dokumentation,
2. großes internationales Medium oder Nachrichtenagentur,
3. regionale, fachliche oder politisch anders verortete Quelle.

Der Fact-Check soll nach Möglichkeit nicht ausschließlich auf einer einzigen Nachrichtenagentur oder Quellengruppe beruhen.

---

### 3. Offizielle X-Accounts verifizieren

Für erwähnte:

- Personen,
- Unternehmen,
- Behörden,
- Organisationen,
- Projekte,
- Produkte

soll geprüft werden, ob ein **eindeutig verifizierbarer offizieller X-Account** existiert.

Ein Handle darf nur verwendet werden, wenn dessen Zugehörigkeit zuverlässig belegt werden kann.

Unsichere oder lediglich vermutete Handles dürfen nicht verwendet werden.

---

### 4. Zuschreibungen getrennt prüfen

Bei Formulierungen wie:

- “according to Reuters”
- “X says …”
- “according to the government”
- “experts say …”

müssen zwei getrennte Fragen untersucht werden:

**Attribution check:**
Hat die genannte Quelle die Aussage tatsächlich gemacht?

**Truth check:**
Ist die zugeschriebene Aussage selbst sachlich richtig?

Eine korrekt zitierte oder wiedergegebene Behauptung darf nicht automatisch als wahr gelten.

---

### 5. Zeitbezug prüfen

Zeitgebundene Aussagen müssen gegen den tatsächlichen zeitlichen Ablauf geprüft werden.

Besonders relevant sind Begriffe wie:

- BREAKING
- today
- now
- just announced
- recently
- latest

Zu prüfen sind mindestens:

- Zeitpunkt des tatsächlichen Ereignisses,
- Veröffentlichungszeitpunkt der zugrunde liegenden Quelle,
- Veröffentlichungszeitpunkt des X-Posts.

Ein älteres Ereignis, das als neu oder aktuell dargestellt wird, soll als **Misleading** bewertet werden.

---

### 6. Implizierte Aussage und Logik prüfen

Der Fact-Checker soll nicht nur explizite Behauptungen prüfen.

Er muss zusätzlich bestimmen:

> Welche übergeordnete Schlussfolgerung oder Botschaft vermittelt der Post?

Diese Schlussfolgerung muss separat überprüft werden.

Insbesondere prüfen:

- Wird Korrelation als Kausalität dargestellt?
- Werden alternative Ursachen ignoriert?
- Werden Daten selektiv verwendet?
- Werden Einzelfälle verallgemeinert?
- Wird aus zeitlicher Abfolge eine Ursache abgeleitet?
- Unterstützen die genannten Fakten tatsächlich die suggerierte Schlussfolgerung?

---

### 7. Gegenbeispiele suchen

Wenn ein Post eine allgemeine Regel, ein generelles Muster oder eine universelle Behauptung suggeriert, soll aktiv nach belastbaren Gegenbeispielen gesucht werden.

Ein eindeutig relevantes Gegenbeispiel kann ausreichen, um eine universell formulierte Behauptung zu widerlegen.

---

### 8. Übergeordnete Argumentation bewerten

Zusätzlich zum normalen Fact-Check muss folgende Bewertung ausgegeben werden:

```text
Logical conclusion:
Supported
Partially supported
Unsupported
False
```

Diese Bewertung betrifft die **Gesamtlogik des Posts**, nicht nur einzelne Fakten.

---

## Zulässige Gesamturteile

Der Fact-Checker darf ausschließlich eines der folgenden Gesamturteile verwenden:

```text
True
False
Misleading
Unverified
Mixed
```

Das Gesamturteil muss unmittelbar sichtbar sein.

---

## Ausgabeanforderungen

Die endgültige Fact-Check-Ausgabe muss:

- vollständig auf Englisch sein,
- maximal 2500 Zeichen umfassen,
- präzise und informationsdicht sein,
- Quellen nachvollziehbar nennen,
- Tatsachen und Interpretation klar voneinander trennen.

Verpflichtende Reihenfolge:

```text
AI-Fact-Check 2.0 – [current date and time]

Headline

Overall verdict

Claim-by-claim verdicts

Evidence / explanation

Logical conclusion

Sources
```

---

## Optimierungsziel des HyperAgents

Der HyperAgent soll den Prompt so weiterentwickeln, dass der resultierende Fact-Checker möglichst zuverlässig:

1. relevante Claims erkennt,
2. vollständige Originalposts berücksichtigt,
3. unabhängige Quellen verwendet,
4. Zuschreibung und Wahrheitsgehalt trennt,
5. Zeitbezüge korrekt bewertet,
6. implizite Aussagen erkennt,
7. Kausalitätsfehler erkennt,
8. Gegenbeispiele berücksichtigt,
9. keine nicht verifizierten X-Handles erfindet,
10. ein konsistentes Gesamturteil erzeugt,
11. das vorgeschriebene Format einhält,
12. unter 2500 Zeichen bleibt.

---

## Nicht zulässige Optimierungen

Der HyperAgent darf die Aufgabe nicht vereinfachen, indem er:

- Anforderungen entfernt,
- Quellenanforderungen abschwächt,
- einzelne Prüfschritte überspringt,
- unbekannte Informationen erfindet,
- nicht verifizierte X-Handles erzeugt,
- die Zeichenbegrenzung ignoriert,
- das zulässige Verdict-Schema erweitert,
- Bewertungsdaten oder Referenzantworten in den Prompt übernimmt.

Ziel ist nicht, die Bewertung zu umgehen, sondern einen **besseren generalisierenden Fact-Checking-Prompt** zu entwickeln.

---

## Ergebnis des HyperAgents

Jede Agentenversion soll als Ergebnis genau den aktuell optimierten **Fact-Checking-System-Prompt** liefern.

Dieser Prompt wird anschließend durch einen separaten Evaluator beziehungsweise Judge bewertet.

Der HyperAgent soll auf Basis dieser Bewertung neue Prompt-Versionen erzeugen und versuchen, deren Qualität über mehrere Evolutionsschritte zu verbessern.
