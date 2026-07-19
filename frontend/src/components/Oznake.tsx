import type { AktSummary } from "@/lib/types";

/** Boja po vrsti akta — jača pravna snaga = tamnija/istaknutija oznaka. */
const TIP_BOJA: Record<string, string> = {
  ZAKON: "bg-navy text-white",
  UREDBA: "bg-navy-700 text-white",
  PRAVILNIK: "bg-navy-100 text-navy-700",
  ODLUKA: "bg-slate-100 text-slate-700",
  RJEŠENJE: "bg-slate-100 text-slate-600",
  PRESUDA: "bg-amber-100 text-amber-800",
  NAREDBA: "bg-slate-100 text-slate-700",
  NAPUTAK: "bg-slate-100 text-slate-700",
  UPUTA: "bg-slate-100 text-slate-700",
  STATUT: "bg-slate-100 text-slate-700",
  KOLEKTIVNI_UGOVOR: "bg-emerald-100 text-emerald-800",
  OSTALO: "bg-slate-100 text-slate-500",
};

const BADGE = "inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium leading-none";

export function TipBadge({ tip }: { tip?: string }) {
  if (!tip) return <span className={`${BADGE} bg-slate-100 text-slate-400`}>bez vrste</span>;
  const boja = TIP_BOJA[tip] ?? "bg-slate-100 text-slate-700";
  return <span className={`${BADGE} ${boja}`}>{tip.replace(/_/g, " ").toLowerCase()}</span>;
}

/** Mijenja li akt neki drugi propis — iz Kazala; korisno za snalaženje u listi. */
export function IzmjenaBadge({ izmjena }: { izmjena?: string }) {
  if (!izmjena || izmjena === "cjeloviti akt") return null;
  return <span className={`${BADGE} bg-violet-100 text-violet-800`}>{izmjena}</span>;
}

/**
 * Dostupnost punog teksta. NN za dio akata (npr. strukovni kurikuli, veliki prilozi)
 * objavi samo PDF, a zadnje izdanje zna dulje ostati bez HTML-a. Korisnik to mora
 * vidjeti iz liste, prije nego otvori akt.
 */
export function TekstBadge({ akt }: { akt: AktSummary }) {
  if (akt.ima_tekst) {
    const kb = akt.znakova ? Math.round(akt.znakova / 1000) : 0;
    return (
      <span className={`${BADGE} bg-emerald-100 text-emerald-800`}>
        tekst{kb >= 1 ? ` · ${kb}k` : ""}
      </span>
    );
  }
  if (akt.pdf) {
    return (
      <span className={`${BADGE} bg-amber-100 text-amber-800`} title="Tekst postoji u PDF-u izdanja; bit će uvezen naknadno">
        samo PDF
      </span>
    );
  }
  return (
    <span className={`${BADGE} bg-slate-100 text-slate-500`} title="NN nema ni HTML ni PDF za ovaj akt">
      bez teksta
    </span>
  );
}
