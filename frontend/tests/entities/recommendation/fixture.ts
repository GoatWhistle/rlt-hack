import type { Recommendation } from "@/entities/recommendation/model"

export const LONG_NAME =
  "South Trade House of Food Systems for the North-Western Region and Neighboring Areas"

export const recommendationFixture: Recommendation = {
  fileName: "lot.xlsx",
  requestTitle: "Food supply",
  lotLabel: "Lot 1",
  products: [
    { id: "rice", name: "Rice", okpd2: "01.12.10", origin: "notice" },
    {
      id: "sugar",
      name: "Sugar",
      okpd2: "10.81.12",
      origin: "inferred",
      originNote: { code: "similarPurchases", hits: 8, total: 10 },
    },
    {
      id: "tea",
      name: "Tea",
      okpd2: "10.83.13",
      origin: "user",
      originNote: { code: "userSpecified" },
    },
    { id: "salt", name: "Salt", okpd2: "10.84.30", origin: "notice" },
    { id: "oil", name: "Oil", okpd2: "10.41.54", origin: "notice" },
  ],
  companies: [
    {
      id: "north",
      name: "North Foods",
      inn: "7800000011",
      role: "supplier",
      status: "recommended",
      summary: "Covers most items by catalog.",
      matches: [
        { productId: "sugar", basis: "inferred" },
        {
          productId: "rice",
          basis: "catalog",
          source: {
            kind: "catalog",
            title: "Groceries page",
            url: "#rice",
            checkedAt: "2026-09-28",
          },
        },
        {
          productId: "tea",
          basis: "stock",
          source: { kind: "price", title: "Price list", url: "#price" },
        },
        {
          productId: "salt",
          basis: "catalog",
          source: { kind: "catalog", title: "Salt", url: "#s" },
        },
        {
          productId: "oil",
          basis: "catalog",
          source: { kind: "catalog", title: "Oil", url: "#o" },
        },
      ],
      similarPurchases: 11,
      wins: 4,
      purchases: [
        {
          lotId: "42",
          title: "Food supply",
          year: 2024,
          outcome: "winner",
          source: { kind: "purchase", title: "Protocol 42", url: "#42" },
        },
        { title: "Lot 43", year: 2025, outcome: "participant" },
        {
          title: "Lot 44",
          year: 2025,
          outcome: "participant",
          source: { kind: "registry", title: "Registry 44", url: "#44" },
        },
      ],
      clarify: ["Delivery terms."],
    },
    {
      id: "south",
      name: LONG_NAME,
      inn: "7800000022",
      role: "unknown",
      status: "check",
      checkReason: "rangeUnconfirmed",
      summary: "Only tea was found.",
      matches: [{ productId: "tea", basis: "inferred" }],
      similarPurchases: 1,
      wins: 0,
      purchases: [],
      clarify: [],
    },
    {
      id: "west",
      name: "West Trade",
      inn: "7800000033",
      role: "distributor",
      status: "check",
      summary: "Partial match.",
      matches: [{ productId: "missing", basis: "catalog" }],
      similarPurchases: 3,
      wins: 0,
      purchases: [],
      clarify: ["Role is not confirmed.", "Volume."],
    },
  ],
}
