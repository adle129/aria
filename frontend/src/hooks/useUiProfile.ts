"use client";

import { useEffect, useState } from "react";
import { fetchHealth, type HealthData } from "@/api/client";
import {
  isFormalDeliveryProfile,
  resolveUiProfile,
  showDemoChrome,
  type UiProfile,
} from "@/lib/uiProfile";

export function useUiProfile() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [profile, setProfile] = useState<UiProfile>(() => resolveUiProfile());
  /** Until /health returns, do not enable Demo chrome (avoids /demo/* calls under r1). */
  const [healthReady, setHealthReady] = useState(false);

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setHealth(h);
        setProfile(resolveUiProfile(h.aria_ui_profile));
      })
      .catch(() => setHealth(null))
      .finally(() => setHealthReady(true));
  }, []);

  return {
    health,
    profile: healthReady ? profile : "r1",
    healthReady,
    showDemoChrome: healthReady && showDemoChrome(profile),
    isFormalDelivery: healthReady ? isFormalDeliveryProfile(profile) : true,
  };
}
