import { getDeals } from "@/lib/deals";
import type { FlightDeal } from "@/types/deal";

export const dynamic = "force-dynamic";

const routeNames: Record<string, string> = {
  ATH: "Athen",
  IST: "Istanbul",
  NAP: "Neapel",
  SAW: "Istanbul-Sabiha Gökçen",
  SKG: "Thessaloniki",
};

const priceFormatter = new Intl.NumberFormat("de-DE", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

const dateFormatter = new Intl.DateTimeFormat("de-DE", {
  weekday: "short",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

function formatDate(value: string) {
  return dateFormatter.format(new Date(`${value}T00:00:00`));
}

function formatPrice(deal: FlightDeal) {
  if (!deal.currency || deal.currency === "EUR") {
    return priceFormatter.format(deal.price);
  }

  return `${Math.round(deal.price)} ${deal.currency}`;
}

function DealCard({ deal }: { deal: FlightDeal }) {
  return (
    <article className="deal-card">
      <div className="price">{formatPrice(deal)}</div>
      <div className="route-codes">
        {deal.origin} <span aria-hidden="true">→</span> {deal.destination}
      </div>
      <h2>{routeNames[deal.destination] ?? deal.destination}</h2>
      <p className="dates">
        {formatDate(deal.departure)} bis {formatDate(deal.return)}
      </p>
      <div className="airline">✈ Airline: {deal.airline}</div>
    </article>
  );
}

export default async function Home() {
  const deals = await getDeals();

  return (
    <main>
      <section className="hero" aria-labelledby="title">
        <p className="eyebrow">NRW Wochenendtrips</p>
        <h1 id="title">Flight Deal Radar</h1>
        <p className="subtitle">
          Günstige Donnerstag-bis-Sonntag-Flüge ab DUS, CGN, DTM und PAD nach Istanbul,
          Athen, Neapel und Thessaloniki — automatisch per Amadeus API aktualisiert.
        </p>
        <dl className="stats" aria-label="Suchparameter">
          <div>
            <dt>Budget</dt>
            <dd>≤ 160 €</dd>
          </div>
          <div>
            <dt>Fenster</dt>
            <dd>8 Wochen</dd>
          </div>
          <div>
            <dt>Rhythmus</dt>
            <dd>Montags</dd>
          </div>
        </dl>
      </section>

      {deals.length > 0 ? (
        <section className="deals-grid" aria-label="Gefundene Flugdeals">
          {deals.map((deal) => (
            <DealCard
              deal={deal}
              key={`${deal.origin}-${deal.destination}-${deal.departure}-${deal.return}-${deal.price}`}
            />
          ))}
        </section>
      ) : (
        <section className="empty-state" aria-label="Keine Deals gefunden">
          <p className="empty-kicker">Noch keine Treffer</p>
          <h2>Keine günstigen Deals unter 160 € gefunden.</h2>
          <p>
            Der GitHub Actions Bot aktualisiert die Datei <code>data/deals.json</code>. Sobald
            passende Amadeus-Angebote vorhanden sind, erscheinen sie hier automatisch.
          </p>
        </section>
      )}
    </main>
  );
}
