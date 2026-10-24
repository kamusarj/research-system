"use client";

import { useState } from "react";
import { useI18n } from "@/lib/i18n";
import type { Provider } from "@/lib/types";

type Props = {
  providers: Provider[];
  onPreflight: () => Promise<void>;
};

/**
 * Show whether each AI provider will actually answer before a submission depends on it.
 *
 * The listing reports `reachable: null` for hosted providers until a preflight runs, so a
 * wrong or expired key was previously invisible until a source had already been fetched,
 * classified and failed.
 */
export function ProviderStatus({ providers, onPreflight }: Props) {
  const { t } = useI18n();
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");
  const configured = providers.filter((provider) => provider.configured);
  if (configured.length === 0) return null;

  const unreachable = configured.filter((provider) => provider.reachable === false);

  async function check() {
    setChecking(true);
    setError("");
    try {
      await onPreflight();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("actionFailed"));
    } finally {
      setChecking(false);
    }
  }

  return (
    <section className="card provider-status" aria-labelledby="provider-status-title">
      <div>
        <p className="eyebrow">{t("aiProviders")}</p>
        <h2 id="provider-status-title">{t("providerStatusTitle")}</h2>
        <ul className="provider-status-list">
          {configured.map((provider) => (
            <li key={provider.id} data-testid={`provider-${provider.id}`}>
              <span
                className={`provider-dot provider-${
                  provider.reachable === true
                    ? "ok"
                    : provider.reachable === false
                      ? "down"
                      : "unknown"
                }`}
                aria-hidden="true"
              />
              <strong>{provider.id}</strong>
              <small>{provider.model}</small>
              <span className="provider-state">
                {provider.reachable === true
                  ? t("providerReachable")
                  : provider.reachable === false
                    ? t("providerUnreachable")
                    : t("providerUnchecked")}
              </span>
              {provider.active && <span className="provider-active">{t("providerActive")}</span>}
            </li>
          ))}
        </ul>
        {unreachable.length > 0 && (
          <p className="row-error">{t("providerUnreachableHint")}</p>
        )}
        {error && <p className="row-error" role="alert">{error}</p>}
      </div>
      <button className="secondary" onClick={check} disabled={checking}>
        {checking ? t("loading") : t("runProviderPreflight")}
      </button>
    </section>
  );
}
