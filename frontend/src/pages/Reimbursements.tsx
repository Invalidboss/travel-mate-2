import { useEffect, useMemo, useState } from 'react';

type OpenReimbursement = {
  tripId: number;
  customer: string;
  project: string;
  expected: number;
  paid: number;
  openAmount: number;
};

type Filters = {
  startDate: string;
  endDate: string;
  customer: string;
  project: string;
  status: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:4000';

const toQuery = (filters: Filters) => {
  const params = new URLSearchParams();
  if (filters.startDate) params.set('startDate', filters.startDate);
  if (filters.endDate) params.set('endDate', filters.endDate);
  if (filters.customer) params.set('customer', filters.customer);
  if (filters.project) params.set('project', filters.project);
  if (filters.status) params.set('status', filters.status);
  return params.toString();
};

export default function Reimbursements() {
  const [rows, setRows] = useState<OpenReimbursement[]>([]);
  const [filters, setFilters] = useState<Filters>({
    startDate: '',
    endDate: '',
    customer: '',
    project: '',
    status: '',
  });
  const [paymentAmount, setPaymentAmount] = useState<Record<number, string>>({});

  const queryString = useMemo(() => toQuery(filters), [filters]);

  const load = async () => {
    const res = await fetch(`${API_BASE}/reports/open-reimbursements?${queryString}`);
    const json = await res.json();
    setRows(json.data ?? []);
  };

  useEffect(() => {
    void load();
  }, [queryString]);

  const recordPayment = async (tripId: number) => {
    const amount = Number(paymentAmount[tripId]);
    if (!Number.isFinite(amount) || amount <= 0) {
      return;
    }

    await fetch(`${API_BASE}/trips/${tripId}/reimbursements`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount }),
    });

    setPaymentAmount((prev) => ({ ...prev, [tripId]: '' }));
    await load();
  };

  return (
    <div style={{ padding: '1rem' }}>
      <h1>Open Reimbursements</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: '0.5rem' }}>
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
      </div>

      <table width="100%" cellPadding={6} style={{ marginTop: '1rem' }}>
        <thead>
          <tr>
            <th align="left">Trip</th>
            <th align="left">Customer</th>
            <th align="left">Project</th>
            <th align="right">Expected</th>
            <th align="right">Paid</th>
            <th align="right">Open</th>
            <th align="left">Record payback</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.tripId}>
              <td>{row.tripId}</td>
              <td>{row.customer}</td>
              <td>{row.project}</td>
              <td align="right">${row.expected.toFixed(2)}</td>
              <td align="right">${row.paid.toFixed(2)}</td>
              <td align="right">${row.openAmount.toFixed(2)}</td>
              <td>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={paymentAmount[row.tripId] ?? ''}
                  onChange={(e) => setPaymentAmount((prev) => ({ ...prev, [row.tripId]: e.target.value }))}
                />
                <button type="button" onClick={() => void recordPayment(row.tripId)}>Save</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
