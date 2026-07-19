import { Link, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="mx-auto max-w-4xl px-4 pb-16">
      <header className="py-6">
        <Link to="/" className="text-navy font-bold text-xl tracking-wide">
          DOMOVINA <span className="font-normal">Zakoni</span>
        </Link>
        <p className="text-muted text-sm mt-1">
          Otvoreni katalog akata službenog dijela Narodnih novina
        </p>
      </header>
      <Outlet />
      <footer className="mt-16 border-t border-border pt-4 text-xs text-muted">
        Izvor podataka: <a className="underline" href="https://narodne-novine.nn.hr" target="_blank" rel="noreferrer">Narodne novine</a> (ELI).
        Podaci: CC BY 4.0 · Neslužbeni prikaz — mjerodavan je službeni tekst u NN.
      </footer>
    </div>
  );
}
