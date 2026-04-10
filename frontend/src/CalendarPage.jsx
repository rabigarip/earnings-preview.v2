import { useCallback, useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export default function CalendarPage({ onGenerate }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [filter, setFilter] = useState({ country: "", sector: "" });
  const [error, setError] = useState("");

  const fetchCalendar = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (filter.country) params.set("country", filter.country);
      if (filter.sector) params.set("sector", filter.sector);
      params.set("days", "90");
      const res = await fetch(`${API_BASE}/api/calendar?${params}`);
      const data = await res.json();
      setEvents(data.events || []);
    } catch (e) {
      setError("Failed to load calendar");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchCalendar();
  }, [fetchCalendar]);

  const startSync = async () => {
    setSyncing(true);
    try {
      await fetch(`${API_BASE}/api/calendar/sync`, { method: "POST" });
      // Poll every 5s for updates
      setTimeout(fetchCalendar, 10000);
      setTimeout(fetchCalendar, 30000);
      setTimeout(() => { fetchCalendar(); setSyncing(false); }, 60000);
    } catch {
      setSyncing(false);
    }
  };

  // Extract unique countries and sectors for filters
  const countries = [...new Set(events.map((e) => e.country).filter(Boolean))].sort();
  const sectors = [...new Set(events.map((e) => e.sector).filter(Boolean))].sort();

  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Earnings Calendar</h2>
        <button
          onClick={startSync}
          disabled={syncing}
          className="rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 px-3 py-1.5 text-sm"
        >
          {syncing ? "Syncing..." : "Sync Dates"}
        </button>
      </div>

      <div className="flex gap-3 mb-4">
        <select
          value={filter.country}
          onChange={(e) => setFilter((f) => ({ ...f, country: e.target.value }))}
          className="rounded-lg bg-slate-900 border border-slate-700 px-2 py-1.5 text-sm"
        >
          <option value="">All Countries</option>
          {countries.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <select
          value={filter.sector}
          onChange={(e) => setFilter((f) => ({ ...f, sector: e.target.value }))}
          className="rounded-lg bg-slate-900 border border-slate-700 px-2 py-1.5 text-sm"
        >
          <option value="">All Sectors</option>
          {sectors.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {error && <p className="text-rose-400 text-sm mb-2">{error}</p>}

      {loading ? (
        <p className="text-slate-400 text-sm">Loading...</p>
      ) : events.length === 0 ? (
        <div className="text-slate-500 text-sm py-8 text-center">
          <p>No upcoming earnings dates found.</p>
          <p className="mt-2">Click "Sync Dates" to fetch from MarketScreener & Yahoo.</p>
        </div>
      ) : (
        <div className="overflow-auto rounded-lg border border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-800 text-slate-300">
                <th className="text-left px-3 py-2">Date</th>
                <th className="text-left px-3 py-2">Ticker</th>
                <th className="text-left px-3 py-2">Company</th>
                <th className="text-left px-3 py-2">Country</th>
                <th className="text-left px-3 py-2">Sector</th>
                <th className="text-center px-3 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {events.map((ev, i) => (
                <tr
                  key={ev.ticker}
                  className={i % 2 === 0 ? "bg-slate-900/50" : "bg-slate-900"}
                >
                  <td className="px-3 py-2 font-mono text-blue-300">
                    {ev.next_earnings_date}
                  </td>
                  <td className="px-3 py-2 font-mono">{ev.ticker}</td>
                  <td className="px-3 py-2">{ev.company_name}</td>
                  <td className="px-3 py-2 text-slate-400">{ev.country}</td>
                  <td className="px-3 py-2 text-slate-400">{ev.sector}</td>
                  <td className="px-3 py-2 text-center">
                    <button
                      onClick={() => onGenerate && onGenerate(ev.ticker)}
                      className="rounded bg-blue-600 hover:bg-blue-500 px-2 py-0.5 text-xs font-medium"
                    >
                      Generate
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-slate-500 text-xs mt-3">
        {events.length} upcoming earnings in next 90 days • Source: MarketScreener / Yahoo Finance
      </p>
    </div>
  );
}
