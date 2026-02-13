import { useEffect, useMemo, useState } from 'react';

type Granularity = 'month' | 'quarter';

type TimePoint = { period: string; total: number };
type BreakdownRow = { customer: string; project: string; category: string; total: number };

type Filters = {
  startDate: string;
  endDate: string;
  customer: string;
  project: string;
  status: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:4000';

const toQuery = (filters: Filters, granularity: Granularity) => {
  const params = new URLSearchParams();
  if (filters.startDate) params.set('startDate', filters.startDate);
  if (filters.endDate) params.set('endDate', filters.endDate);
  if (filters.customer) params.set('customer', filters.customer);
  if (filters.project) params.set('project', filters.project);
  if (filters.status) params.set('status', filters.status);
  params.set('granularity', granularity);
  return params.toString();
};

export default function Dashboard() {
  const [granularity, setGranularity] = useState<Granularity>('month');
  const [timeSeries, setTimeSeries] = useState<TimePoint[]>([]);
  const [breakdown, setBreakdown] = useState<BreakdownRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<Filters>({
    startDate: '',
    endDate: '',
    customer: '',
    project: '',
    status: '',
  });

  const queryString = useMemo(() => toQuery(filters, granularity), [filters, granularity]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const [timeRes, projectRes] = await Promise.all([
        fetch(`${API_BASE}/reports/expenses-over-time?${queryString}`),
        fetch(`${API_BASE}/reports/by-project?${queryString}`),
      ]);

      const timeJson = await timeRes.json();
      const projectJson = await projectRes.json();

      setTimeSeries(timeJson.data ?? []);
      setBreakdown(projectJson.data ?? []);
      setLoading(false);
    };

    void load();
  }, [queryString]);

  return (
    <div style={{ padding: '1rem' }}>
      <h1>Dashboard</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, minmax(0, 1fr))', gap: '0.5rem' }}>
        <input type="date" value={filters.startDate} onChange={(e) => setFilters((f) => ({ ...f, startDate: e.target.value }))} />
        <input type="date" value={filters.endDate} onChange={(e) => setFilters((f) => ({ ...f, endDate: e.target.value }))} />
        <input placeholder="Customer" value={filters.customer} onChange={(e) => setFilters((f) => ({ ...f, customer: e.target.value }))} />
        <input placeholder="Project" value={filters.project} onChange={(e) => setFilters((f) => ({ ...f, project: e.target.value }))} />
        <select value={filters.status} onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}>
          <option value="">Any status</option>
          <option value="submitted">Submitted</option>
          <option value="approved">Approved</option>
          <option value="reimbursed">Reimbursed</option>
        </select>
        <select value={granularity} onChange={(e) => setGranularity(e.target.value as Granularity)}>
          <option value="month">Monthly</option>
          <option value="quarter">Quarterly</option>
        </select>
      </div>

      <h2 style={{ marginTop: '1rem' }}>Expenses over time</h2>
      {loading ? <p>Loading...</p> : (
        <table width="100%" cellPadding={6}>
          <thead>
            <tr><th align="left">Period</th><th align="right">Total</th></tr>
          </thead>
          <tbody>
            {timeSeries.map((item) => (
              <tr key={item.period}>
                <td>{item.period}</td>
                <td align="right">${item.total.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2 style={{ marginTop: '1rem' }}>Breakdown by customer/project/category</h2>
      <table width="100%" cellPadding={6}>
        <thead>
          <tr>
            <th align="left">Customer</th>
            <th align="left">Project</th>
            <th align="left">Category</th>
            <th align="right">Total</th>
          </tr>
        </thead>
        <tbody>
          {breakdown.map((row) => (
            <tr key={`${row.customer}-${row.project}-${row.category}`}>
              <td>{row.customer}</td>
              <td>{row.project}</td>
              <td>{row.category}</td>
              <td align="right">${row.total.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
