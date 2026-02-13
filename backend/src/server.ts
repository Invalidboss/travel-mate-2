import express from 'express';
import cors from 'cors';
import { expenses, reimbursements, type Expense, type ExpenseStatus } from './data';

interface Filters {
  startDate?: string;
  endDate?: string;
  customer?: string;
  project?: string;
  status?: ExpenseStatus;
}

const app = express();
app.use(cors());
app.use(express.json());

const toNumber = (v: number) => Number(v.toFixed(2));

const parseFilters = (query: Record<string, unknown>): Filters => ({
  startDate: typeof query.startDate === 'string' ? query.startDate : undefined,
  endDate: typeof query.endDate === 'string' ? query.endDate : undefined,
  customer: typeof query.customer === 'string' ? query.customer : undefined,
  project: typeof query.project === 'string' ? query.project : undefined,
  status: typeof query.status === 'string' ? (query.status as ExpenseStatus) : undefined,
});

const applyFilters = (rows: Expense[], filters: Filters) => {
  return rows.filter((row) => {
    if (filters.startDate && row.date < filters.startDate) return false;
    if (filters.endDate && row.date > filters.endDate) return false;
    if (filters.customer && row.customer !== filters.customer) return false;
    if (filters.project && row.project !== filters.project) return false;
    if (filters.status && row.status !== filters.status) return false;
    return true;
  });
};

const bucketFor = (date: string, granularity: 'month' | 'quarter') => {
  const [yearStr, monthStr] = date.split('-');
  const year = Number(yearStr);
  const month = Number(monthStr);

  if (granularity === 'month') {
    return `${year}-${String(month).padStart(2, '0')}`;
  }

  const quarter = Math.floor((month - 1) / 3) + 1;
  return `${year}-Q${quarter}`;
};

app.get('/reports/expenses-over-time', (req, res) => {
  const filters = parseFilters(req.query as Record<string, unknown>);
  const granularity = req.query.granularity === 'quarter' ? 'quarter' : 'month';

  const filtered = applyFilters(expenses, filters);
  const totals = filtered.reduce<Record<string, number>>((acc, item) => {
    const bucket = bucketFor(item.date, granularity);
    acc[bucket] = toNumber((acc[bucket] ?? 0) + item.amount);
    return acc;
  }, {});

  const data = Object.entries(totals)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([period, total]) => ({ period, total }));

  res.json({ granularity, data, count: filtered.length });
});

app.get('/reports/by-project', (req, res) => {
  const filters = parseFilters(req.query as Record<string, unknown>);
  const filtered = applyFilters(expenses, filters);

  const grouped = filtered.reduce<Record<string, { customer: string; project: string; category: string; total: number }>>((acc, item) => {
    const key = `${item.customer}__${item.project}__${item.category}`;

    if (!acc[key]) {
      acc[key] = {
        customer: item.customer,
        project: item.project,
        category: item.category,
        total: 0,
      };
    }

    acc[key].total = toNumber(acc[key].total + item.amount);
    return acc;
  }, {});

  const data = Object.values(grouped).sort((a, b) => b.total - a.total);
  res.json({ data, count: filtered.length });
});

app.get('/reports/open-reimbursements', (req, res) => {
  const filters = parseFilters(req.query as Record<string, unknown>);
  const filteredExpenses = applyFilters(expenses, filters);

  const byTrip = filteredExpenses.reduce<Record<number, { tripId: number; customer: string; project: string; expected: number }>>((acc, item) => {
    if (!acc[item.tripId]) {
      acc[item.tripId] = {
        tripId: item.tripId,
        customer: item.customer,
        project: item.project,
        expected: 0,
      };
    }

    acc[item.tripId].expected = toNumber(acc[item.tripId].expected + item.amount);
    return acc;
  }, {});

  const paidByTrip = reimbursements.reduce<Record<number, number>>((acc, payment) => {
    acc[payment.tripId] = toNumber((acc[payment.tripId] ?? 0) + payment.amount);
    return acc;
  }, {});

  const data = Object.values(byTrip)
    .map((trip) => {
      const paid = paidByTrip[trip.tripId] ?? 0;
      const openAmount = toNumber(trip.expected - paid);
      return {
        ...trip,
        paid,
        openAmount,
      };
    })
    .filter((item) => item.openAmount > 0)
    .sort((a, b) => b.openAmount - a.openAmount);

  res.json({ data });
});

app.post('/trips/:id/reimbursements', (req, res) => {
  const tripId = Number(req.params.id);
  const amount = Number(req.body?.amount);
  const date = typeof req.body?.date === 'string' ? req.body.date : new Date().toISOString().slice(0, 10);
  const note = typeof req.body?.note === 'string' ? req.body.note : undefined;

  if (!Number.isFinite(tripId)) {
    res.status(400).json({ message: 'Invalid trip id' });
    return;
  }

  if (!Number.isFinite(amount) || amount <= 0) {
    res.status(400).json({ message: 'Amount must be a positive number' });
    return;
  }

  const newReimbursement = {
    id: reimbursements.length ? Math.max(...reimbursements.map((r) => r.id)) + 1 : 1,
    tripId,
    amount: toNumber(amount),
    date,
    note,
  };

  reimbursements.push(newReimbursement);
  res.status(201).json(newReimbursement);
});

const port = Number(process.env.PORT ?? 4000);
app.listen(port, () => {
  console.log(`Travel Mate API listening on ${port}`);
});
