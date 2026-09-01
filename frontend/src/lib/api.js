import axios from "axios";

// Vite exposes both `VITE_*` and (via envPrefix) `REACT_APP_*` variables.
// Support the legacy Node-style `process.env` shim if some code paths still use it.
const runtimeEnv = (typeof import.meta !== "undefined" && import.meta.env) || {};
const nodeEnv = (typeof process !== "undefined" && process.env) || {};
const BACKEND_URL = runtimeEnv.REACT_APP_BACKEND_URL || nodeEnv.REACT_APP_BACKEND_URL || "";

export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

// Attach JWT from localStorage as a fallback (backend also supports httpOnly cookies).
api.interceptors.request.use((config) => {
  const t = typeof localStorage !== "undefined" ? localStorage.getItem("g360_token") : null;
  if (t && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${t}`;
  }
  return config;
});

export const fmtMoney = (v) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(v || 0));

export const fmtDate = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR");
};

export const fmtDateTime = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
};

export const computeLineNet = (line) => {
  const gross = Number(line.quantity || 0) * Number(line.unit_price || 0);
  return gross * (1 - Number(line.discount_pct || 0) / 100);
};

export const computeTotals = (lines, opts = {}) => {
  let gross = 0, disc = 0;
  for (const l of lines || []) {
    const g = Number(l.quantity || 0) * Number(l.unit_price || 0);
    const n = g * (1 - Number(l.discount_pct || 0) / 100);
    gross += g;
    disc += (g - n);
  }
  const lineNet = gross - disc;
  const gpct = Number(opts.global_discount_pct || 0);
  const gamt = Number(opts.global_discount_amount || 0);
  const globalDisc = lineNet * (gpct / 100) + gamt;
  const net = Math.max(lineNet - globalDisc, 0);
  return { gross, disc, lineNet, globalDisc, net };
};
