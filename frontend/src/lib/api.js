import axios from "axios";
import { createContext, useContext, useEffect, useState } from "react";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const http = axios.create({ baseURL: API });

export function useApi(path, params) {
  const key = `${path}?${JSON.stringify(params || {})}`;
  const [state, setState] = useState({ key: null, data: null, error: null });
  useEffect(() => {
    let alive = true;
    http
      .get(path, { params })
      .then((r) => alive && setState({ key, data: r.data, error: null }))
      .catch((e) => alive && setState({ key, data: null, error: e }));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  if (state.key !== key) return { data: null, loading: true, error: null };
  return { data: state.data, loading: false, error: state.error };
}

export const CatalogContext = createContext(null);

export async function downloadFile(path, filename) {
  const { data } = await http.get(path, { responseType: "blob" });
  const url = URL.createObjectURL(data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const useCatalog = () => useContext(CatalogContext);

export function usePrefersReducedMotion() {
  const query = "(prefers-reduced-motion: reduce)";
  const [reduced, setReduced] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return reduced;
}
