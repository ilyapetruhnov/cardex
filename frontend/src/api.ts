export interface SetOut {
  id: string;
  name: string;
  series: string;
  release_date: string;
  total_cards: number;
}

export interface ProductOut {
  id: number;
  set_id: string;
  name: string;
  product_type: string;
  packs_per_product: number;
  bonus_card_value: string | number;
}

export interface ValuationResponse {
  product_id: number;
  product_name: string;
  set_id: string;
  ev: number;
  std_dev: number;
  price_paid: number;
  expected_profit: number;
  roi_pct: number;
  prob_profit: number;
  p10: number;
  p50: number;
  p90: number;
  risk_adjusted_return: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail ?? res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export function getSets(): Promise<SetOut[]> {
  return request<SetOut[]>("/api/sets");
}

export function getProducts(setId: string): Promise<ProductOut[]> {
  return request<ProductOut[]>(`/api/sets/${encodeURIComponent(setId)}/products`);
}

export function valueProduct(productId: number, retailPrice: number): Promise<ValuationResponse> {
  return request<ValuationResponse>("/api/valuation", {
    method: "POST",
    body: JSON.stringify({ product_id: productId, retail_price: retailPrice }),
  });
}
