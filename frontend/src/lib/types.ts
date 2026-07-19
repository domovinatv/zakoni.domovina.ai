export interface AktSummary {
  eli: string;
  broj: number;
  clanak: number;
  naslov?: string;
  tip?: string;
  datum?: string;
  donositelj?: string;
  /** "cjeloviti akt" | "izmjene i dopune" | "ukidanje" … — iz službenog Kazala */
  izmjena?: string;
  /** je li puni tekst akta dostupan (NN za dio akata objavi samo PDF) */
  ima_tekst?: boolean;
  /** duljina teksta u znakovima; izostaje kad teksta nema */
  znakova?: number;
  /** postoji li PDF za tu godinu — tek od 2023., pa se tekst inače ne može dopuniti */
  pdf?: boolean;
}

export interface Veza {
  predikat: string;
  to_eli?: string;
  from_eli?: string;
}

export interface Oznaka {
  vrsta: string;
  uri: string;
  label?: string;
}

export interface AktDetail extends AktSummary {
  godina: number;
  datum_akta?: string;
  datum_objave?: string;
  tekst?: string;
  veze: Veza[];
  veze_na_ovaj: Veza[];
  oznake: Oznaka[];
}

export interface GodinaStat {
  godina: number;
  akata: number;
  izdanja: number;
}

export interface Stats {
  godine: GodinaStat[];
  tipovi: Record<string, number>;
  ukupno: number;
}
