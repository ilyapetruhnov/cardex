import { useEffect, useState } from "react";
import { getProducts, getSets, valueProduct } from "./api";
import type { ProductOut, SetOut, ValuationResponse } from "./api";

interface RowState {
  price: string;
  loading: boolean;
  error: string | null;
  result: ValuationResponse | null;
}

function emptyRow(): RowState {
  return { price: "", loading: false, error: null, result: null };
}

export default function App() {
  const [sets, setSets] = useState<SetOut[] | null>(null);
  const [setsError, setSetsError] = useState<string | null>(null);

  const [selectedSetId, setSelectedSetId] = useState<string>("");
  const [products, setProducts] = useState<ProductOut[]>([]);
  const [productsError, setProductsError] = useState<string | null>(null);

  const [rows, setRows] = useState<Record<number, RowState>>({});

  useEffect(() => {
    getSets()
      .then((data) => {
        setSets(data);
        if (data.length > 0) setSelectedSetId(data[0].id);
      })
      .catch((err: Error) => setSetsError(err.message));
  }, []);

  useEffect(() => {
    if (!selectedSetId) {
      setProducts([]);
      return;
    }
    setProductsError(null);
    getProducts(selectedSetId)
      .then((data) => {
        setProducts(data);
        setRows(Object.fromEntries(data.map((p) => [p.id, emptyRow()])));
      })
      .catch((err: Error) => setProductsError(err.message));
  }, [selectedSetId]);

  function setRow(productId: number, patch: Partial<RowState>) {
    setRows((prev) => ({ ...prev, [productId]: { ...prev[productId], ...patch } }));
  }

  async function handleCalculate(productId: number) {
    const row = rows[productId];
    const price = Number(row?.price);
    if (!row?.price || Number.isNaN(price) || price <= 0) {
      setRow(productId, { error: "Enter a price greater than 0", result: null });
      return;
    }
    setRow(productId, { loading: true, error: null });
    try {
      const result = await valueProduct(productId, price);
      setRow(productId, { loading: false, result });
    } catch (err) {
      setRow(productId, { loading: false, error: (err as Error).message, result: null });
    }
  }

  if (setsError) {
    return <div className="app-error">Failed to load sets: {setsError}</div>;
  }

  if (sets === null) {
    return <div className="app-loading">Loading…</div>;
  }

  if (sets.length === 0) {
    return (
      <div className="app-empty">
        No sets found. Run <code>uv run cardex sync-sets --name "151"</code> to pull one in.
      </div>
    );
  }

  return (
    <div className="app">
      <h1>Cardex</h1>

      <label className="set-picker">
        Set
        <select value={selectedSetId} onChange={(e) => setSelectedSetId(e.target.value)}>
          {sets.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>

      {productsError && <div className="app-error">Failed to load products: {productsError}</div>}

      {products.length === 0 && !productsError ? (
        <p>
          No products for this set yet. Run <code>uv run cardex seed-products</code>.
        </p>
      ) : (
        <table className="products-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Type</th>
              <th>Packs</th>
              <th>Retail price</th>
              <th></th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => {
              const row = rows[p.id] ?? emptyRow();
              return (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td>{p.product_type}</td>
                  <td>{p.packs_per_product}</td>
                  <td>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={row.price}
                      onChange={(e) => setRow(p.id, { price: e.target.value })}
                      placeholder="4.99"
                    />
                  </td>
                  <td>
                    <button onClick={() => handleCalculate(p.id)} disabled={row.loading}>
                      {row.loading ? "Calculating…" : "Calculate"}
                    </button>
                  </td>
                  <td>
                    {row.error && <span className="row-error">{row.error}</span>}
                    {row.result && (
                      <div className="result">
                        <div>EV: ${row.result.ev.toFixed(2)}</div>
                        <div>Profit: ${row.result.expected_profit.toFixed(2)}</div>
                        <div>ROI: {row.result.roi_pct.toFixed(1)}%</div>
                        <div>P(profit): {(row.result.prob_profit * 100).toFixed(0)}%</div>
                        <div>
                          p10/p50/p90: ${row.result.p10.toFixed(2)} / ${row.result.p50.toFixed(2)} / $
                          {row.result.p90.toFixed(2)}
                        </div>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
