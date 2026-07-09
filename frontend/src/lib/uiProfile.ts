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

/** Routes not delivered in R1 (M3/M4/M5 milestones). */
export const R1_LOCKED_QUOTING_PATHS = ["/proposal", "/qa", "/quote"] as const;

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
  return R1_LOCKED_QUOTING_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

export function shouldBlockPath(profile: UiProfile, pathname: string): boolean {
  if (!isR1Profile(profile)) return false;
  return isPathLockedInR1(pathname);
}

export function isTaskContextBarVisible(pathname: string): boolean {
  if (pathname === "/" || pathname.startsWith("/knowledge") || pathname.startsWith("/login")) {
    return false;
  }
  return true;
}

export function isQuotingStepDelivered(profile: UiProfile, step: "rfq" | "proposal" | "qa" | "quote"): boolean {
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
export function getStepMilestone(step: "rfq" | "proposal" | "qa" | "quote"): string | null {
  const milestones: Partial<Record<"rfq" | "proposal" | "qa" | "quote", string>> = {
    quote: "M3",
    qa: "M4",
    proposal: "M5",
  };
  return milestones[step] ?? null;
}
