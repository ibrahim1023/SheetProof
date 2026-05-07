# Competitive Landscape

## Positioning Goal

SheetProof should be the local-first, deterministic spreadsheet trust layer for business-critical workbook review.

## Snapshot of Similar Projects

| Project | Type | Core Strength | Gaps Relative to SheetProof Target |
|---|---|---|---|
| ExceLint | Excel add-in (open-source/research) | Formula error detection patterns | Not a local CLI-first evidence/report pipeline across audit + diff + assumptions |
| ExcelCompare | CLI/library | Workbook diffing | Focused diff utility; no full risk engine or assumption impact layer |
| Microsoft Spreadsheet Compare | Office tool | Workbook version comparison | Limited extensibility, enterprise SKU constraints, not deterministic policy-pack oriented |
| OAK | Commercial Excel add-in | Financial model auditing workflow | Add-in-centric and proprietary; less open/local CLI integration flexibility |
| PerfectXL Risk Finder | Commercial risk tooling | Hidden/external/error visibility | Productized platform, but custom deterministic policy control is less code-native |
| SheetSage | Google Sheets add-on | Automated risk checks + fixes | Google Sheets scope; different trust boundary and deployment model |
| pycel / formulas | Python libraries | Formula parsing/compilation/interpreter capabilities | Building blocks, not end-to-end audit/risk/report product |

## Market Takeaway

This is a competitive category, but the market is fragmented by:
- add-ins vs CLI tools
- diff-only vs risk-only tools
- cloud workflows vs local-first workflows
- weak evidence lineage in many outputs

SheetProof can win by integrating deterministic audit + diff + assumption impact into one reproducible local workflow.

## USP Candidates (Prioritized)

1. Audit-Grade Reproducibility
- Same workbook input must produce stable deterministic findings and stable artifact hashes.

2. Evidence Lineage Graph
- Every finding links to workbook/sheet/cell/formula plus dependency path to impacted outputs.

3. Assumption Impact Register
- Treat assumptions as first-class entities with downstream influence and version-to-version change visibility.

4. Deterministic Policy Packs
- Configurable rulesets for finance, operations, compliance, and audit teams with explicit severities.

5. CI/Pre-Submission Gate
- Non-interactive mode for automated approval gates (e.g., fail on high-risk deltas or new external refs).

6. Human Review Artifacts
- Reports designed for sign-off workflows (markdown + json + csv) with review checklist and evidence appendix.

7. Deterministic/LLM Firewall
- LLM can explain findings but cannot generate facts, alter scores, or pass/fail gates.

## Risks to USP Delivery

- Formula parsing edge cases can erode trust if unsupported behavior is not disclosed clearly.
- Risk scoring credibility depends on transparent weighting and deterministic traceability.
- Performance on large workbooks can block adoption without incremental optimization.

## Near-Term Strategy

- Deliver deterministic core with reproducibility tests first.
- Add policy packs and CI gate second.
- Add optional local LLM explanation only after deterministic outputs are stable and measurable.
