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

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setHealth(h);
        setProfile(resolveUiProfile(h.aria_ui_profile));
      })
      .catch(() => setHealth(null));
  }, []);

  return {
    health,
    profile,
    showDemoChrome: showDemoChrome(profile),
    isFormalDelivery: isFormalDeliveryProfile(profile),
  };
}
