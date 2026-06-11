import { readFile } from "node:fs/promises";
import path from "node:path";

import type { FlightDeal } from "@/types/deal";

const dealsFile = path.join(process.cwd(), "data", "deals.json");

function isFlightDeal(value: unknown): value is FlightDeal {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const deal = value as Record<string, unknown>;

  return (
    typeof deal.origin === "string" &&
    typeof deal.destination === "string" &&
    typeof deal.departure === "string" &&
    typeof deal.return === "string" &&
    typeof deal.price === "number" &&
    (typeof deal.currency === "string" || deal.currency === undefined) &&
    typeof deal.airline === "string"
  );
}

export async function getDeals(): Promise<FlightDeal[]> {
  try {
    const file = await readFile(dealsFile, "utf-8");
    const parsed: unknown = JSON.parse(file);

    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter(isFlightDeal).sort((left, right) => left.price - right.price);
  } catch (error) {
    console.error("Unable to read flight deals", error);
    return [];
  }
}
