"use client";

import Link from "next/link";
import { useI18n } from "@/lib/i18n";

export default function Dashboard() {
  const { t } = useI18n();
  return <div className="dashboard">
    <section className="hero">
      <div><p className="eyebrow">{t("workspace")}</p><h1>{t("headline")}</h1><p className="hero-copy">{t("intro")}</p><div className="actions"><Link className="primary-link" href="/ingestion">{t("openIntake")} <span>↗</span></Link><Link className="button-link" href="/graph">{t("exploreGraph")}</Link></div></div>
      <div className="orbital" aria-hidden="true"><span className="orbit orbit-a" /><span className="orbit orbit-b" /><span className="core">R</span><i className="satellite one" /><i className="satellite two" /><i className="satellite three" /></div>
    </section>
    <section className="flow-card"><div><p className="eyebrow">{t("systemFlow")}</p><h2>{t("flowText")}</h2></div><div className="pulse-line"><i /><i /><i /><i /><i /></div></section>
    <section className="grid feature-grid"><Link href="/ingestion" className="card feature"><span>01</span><h2>{t("intake")}</h2><p>{t("intakeIntro")}</p></Link><Link href="/graph" className="card feature"><span>02</span><h2>{t("graph")}</h2><p>{t("graphIntro")}</p></Link><Link href="/gaps" className="card feature"><span>03</span><h2>{t("gaps")}</h2><p>{t("gapCardDescription")}</p></Link></section>
  </div>;
}
