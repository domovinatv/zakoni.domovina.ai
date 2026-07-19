export interface AktSummary {
  eli: string;
  broj: number;
  clanak: number;
  naslov?: string;
  tip?: string;
  datum?: string;
  donositelj?: string;
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
