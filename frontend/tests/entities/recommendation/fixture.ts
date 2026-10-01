import type { Recommendation } from "@/entities/recommendation/model"

export const recommendationFixture: Recommendation = {
  fileName: "lot.xlsx",
  requestTitle: "Food supply",
  lotLabel: "Lot 1",
  products: [
    { id: "rice", name: "Rice", okpd2: "01.12.10", origin: "notice" },
    { id: "sugar", name: "Sugar", okpd2: "10.81.12", origin: "inferred" },
    { id: "tea", name: "Tea", okpd2: "10.83.13", origin: "user" },
  ],
  companies: [
    {
      id: "north",
      name: "North Foods",
      inn: "7800000011",
      role: "Supplier",
      status: "recommended",
      coveredProductIds: ["rice", "sugar"],
      similarPurchases: 1,
      why: ["Rice and sugar are in the catalogue."],
      evidence: [{ kind: "Catalogue", title: "Groceries page", url: "#rice", meta: "2026" }],
      clarify: ["Delivery terms."],
    },
    {
      id: "south",
      name: "South Trade",
      inn: "7800000022",
      role: "Distributor",
      status: "check",
      coveredProductIds: ["tea"],
      similarPurchases: 3,
      why: ["Tea is in the catalogue."],
      evidence: [
        { kind: "Purchase", title: "Lot 42", url: "#lot", meta: "winner" },
        { kind: "Catalogue", title: "Drinks page", url: "#tea", meta: "2025" },
      ],
      clarify: ["Role is not confirmed.", "Volume."],
    },
  ],
}
