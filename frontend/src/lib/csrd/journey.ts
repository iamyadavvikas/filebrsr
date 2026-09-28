/** Next-best-action rules for the CSRD guided journey.
 *
 * Pure functions over already-fetched workspace state (no I/O), so the
 * Overview hero can prescribe exactly one action. Rule order is the
 * consultant's critical path: data in -> materiality -> scope lock ->
 * filing. Covered by node:test suites (frontend/scripts/).
 */

export type JourneyStepId = "start" | "registry" | "materiality" | "lock" | "reports";

export interface JourneyState {
  entriesAssessed: number;
  entriesTotal: number;
  iroCount: number;
  orphanIroIds: string[];
  methodologyStatus: "draft" | "approved" | string;
  stakeholderRecords: number;
  reportsGenerated: number;
}

export interface NextAction {
  step: JourneyStepId;
  title: string;
  detail: string;
  cta: string;
  tab: "overview" | "registry" | "materiality" | "reports" | "vsme";
}

export function nextAction(s: JourneyState): NextAction {
  if (s.entriesAssessed <= 0) {
    return {
      step: "start",
      title: "Get your first datapoints in",
      detail: "Import your annual report, load sample data, or answer the VSME questionnaire — any of the three seeds the registry.",
      cta: "Import or seed",
      tab: "registry",
    };
  }
  if (s.iroCount <= 0) {
    return {
      step: "materiality",
      title: "Register your first material IRO",
      detail: "Double materiality decides scope. Record the impacts, risks and opportunities that drive which datapoints count.",
      cta: "Open Materiality",
      tab: "materiality",
    };
  }
  if (s.orphanIroIds.length > 0) {
    return {
      step: "materiality",
      title: `Trace ${s.orphanIroIds.length} orphan IRO${s.orphanIroIds.length > 1 ? "s" : ""} to disclosure requirements`,
      detail: "Material IROs without linked DRs leave scope holes an auditor will flag.",
      cta: "Link DRs",
      tab: "materiality",
    };
  }
  if (s.methodologyStatus !== "approved") {
    return {
      step: "lock",
      title: s.stakeholderRecords > 0 ? "Approve the methodology to lock scope" : "Log stakeholder input, then approve",
      detail: s.stakeholderRecords > 0
        ? "Thresholds are set and engagements logged — approval locks the assessment scope."
        : "Auditors expect a stakeholder record behind the thresholds. Log at least one engagement first.",
      cta: s.stakeholderRecords > 0 ? "Approve methodology" : "Log engagement",
      tab: "materiality",
    };
  }
  if (s.reportsGenerated <= 0) {
    return {
      step: "reports",
      title: "Generate your ESEF statement",
      detail: "Coverage is methodology-backed. Generate, validate, assure and file.",
      cta: "Open Reports",
      tab: "reports",
    };
  }
  return {
    step: "reports",
    title: "Review filings and variances",
    detail: "Statements exist — check validation, track submissions, or roll the year forward.",
    cta: "Open Reports",
    tab: "reports",
  };
}

export interface StepState {
  id: JourneyStepId;
  label: string;
  state: "done" | "current" | "todo";
  tab: NextAction["tab"];
}

/** Stepper states derived from the same journey state (single source of truth). */
export function stepStates(s: JourneyState): StepState[] {
  const registryDone = s.entriesAssessed > 0;
  const matDone = s.iroCount > 0 && s.orphanIroIds.length === 0;
  const lockDone = s.methodologyStatus === "approved";
  const repDone = s.reportsGenerated > 0;
  const current: JourneyStepId = !registryDone
    ? "registry"
    : !matDone
      ? "materiality"
      : !lockDone
        ? "lock"
        : "reports";
  const order: { id: JourneyStepId; label: string; tab: NextAction["tab"]; done: boolean }[] = [
    { id: "start", label: "Start", tab: "registry", done: registryDone },
    { id: "registry", label: "Registry", tab: "registry", done: registryDone },
    { id: "materiality", label: "Materiality", tab: "materiality", done: matDone },
    { id: "lock", label: "Lock scope", tab: "materiality", done: lockDone },
    { id: "reports", label: "Reports", tab: "reports", done: repDone },
  ];
  return order.map((o) => ({
    id: o.id,
    label: o.label,
    tab: o.tab,
    state: o.done ? "done" : o.id === current ? "current" : "todo",
  }));
}

/** Order unassessed datapoint ids for focus mode: standard order, then id. */
export function focusQueue(
  items: { id: string; standard: string }[],
  assessedIds: Set<string>,
  standardOrder: string[]
): string[] {
  const rank = new Map(standardOrder.map((s, i) => [s, i]));
  return items
    .filter((d) => !assessedIds.has(d.id))
    .sort((a, b) =>
      (rank.get(a.standard) ?? 999) - (rank.get(b.standard) ?? 999) ||
      a.id.localeCompare(b.id)
    )
    .map((d) => d.id);
}
