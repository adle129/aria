export type UiProfile =
  | "dev"
  | "experience"
  | "r1"
  | "m3"
  | "m4"
  | "m5"
  | "full";

const DEFAULT_PROFILE =
  (process.env.NEXT_PUBLIC_ARIA_UI_PROFILE as UiProfile | undefined) || "experience";

/** R1 formal delivery: only KB Debug is blocked (dev-only). M3/M4/M5 use milestone scaffold pages. */
export const R1_LOCKED_PATHS = ["/knowledge/debug"] as const;

/** @deprecated Use R1_LOCKED_PATHS — quoting steps are navigable as milestone scaffolds in r1. */
export const R1_LOCKED_QUOTING_PATHS = R1_LOCKED_PATHS;

export type QuotingStep = "rfq" | "proposal" | "qa" | "quote";

export function resolveUiProfile(healthProfile?: string | null): UiProfile {
  const raw = (healthProfile || DEFAULT_PROFILE).trim().toLowerCase();
  const allowed: UiProfile[] = ["dev", "experience", "r1", "m3", "m4", "m5", "full"];
  if (allowed.includes(raw as UiProfile)) {
    return raw as UiProfile;
  }
  return DEFAULT_PROFILE;
}

export function isR1Profile(profile: UiProfile): boolean {
  return profile === "r1";
}

/** Demo / experience rehearsal UI (capability banners, sample RFQ, Phase 2 placeholders). */
export function showDemoChrome(profile: UiProfile): boolean {
  return profile === "experience" || profile === "dev";
}

export function isFormalDeliveryProfile(profile: UiProfile): boolean {
  return !showDemoChrome(profile);
}

export function isPathLockedInR1(pathname: string): boolean {
  if (pathname.startsWith("/knowledge/debug")) return true;
  return R1_LOCKED_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/** Formal profile step not yet delivered — show static milestone scaffold (no Mock API). */
export function showsMilestoneScaffold(profile: UiProfile, step: QuotingStep): boolean {
  return isFormalDeliveryProfile(profile) && !isQuotingStepDelivered(profile, step);
}

export function shouldBlockPath(profile: UiProfile, pathname: string): boolean {
  if (!isR1Profile(profile)) return false;
  return isPathLockedInR1(pathname);
}

export function isTaskContextBarVisible(pathname: string): boolean {
  if (
    pathname === "/" ||
    pathname.startsWith("/knowledge") ||
    pathname.startsWith("/login") ||
    pathname.startsWith("/admin")
  ) {
    return false;
  }
  return true;
}

export function isQuotingStepDelivered(profile: UiProfile, step: QuotingStep): boolean {
  const delivered: Record<UiProfile, readonly ("rfq" | "proposal" | "qa" | "quote")[]> = {
    dev: ["rfq", "proposal", "qa", "quote"],
    experience: ["rfq", "proposal", "qa", "quote"],
    full: ["rfq", "proposal", "qa", "quote"],
    r1: ["rfq"],
    m3: ["rfq", "quote"],
    m4: ["rfq", "quote", "qa"],
    m5: ["rfq", "quote", "qa", "proposal"],
  };
  return delivered[profile].includes(step);
}

/**
 * Returns the contract milestone label that first delivers this step.
 * Returns null for steps delivered in R1 (the base milestone).
 */
export function getStepMilestone(step: QuotingStep): string | null {
  const milestones: Partial<Record<QuotingStep, string>> = {
    quote: "M3",
    qa: "M4",
    proposal: "M5",
  };
  return milestones[step] ?? null;
}
