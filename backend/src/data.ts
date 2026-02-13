export type ExpenseStatus = 'submitted' | 'approved' | 'reimbursed';

export interface Expense {
  id: number;
  tripId: number;
  date: string; // ISO yyyy-mm-dd
  amount: number;
  customer: string;
  project: string;
  category: string;
  status: ExpenseStatus;
}

export interface Reimbursement {
  id: number;
  tripId: number;
  date: string; // ISO yyyy-mm-dd
  amount: number;
  note?: string;
}

export const expenses: Expense[] = [
  { id: 1, tripId: 100, date: '2025-01-07', amount: 520.1, customer: 'Acme Corp', project: 'Onboarding', category: 'Flight', status: 'approved' },
  { id: 2, tripId: 100, date: '2025-01-09', amount: 214.55, customer: 'Acme Corp', project: 'Onboarding', category: 'Hotel', status: 'submitted' },
  { id: 3, tripId: 101, date: '2025-02-03', amount: 80.2, customer: 'Globex', project: 'Migration', category: 'Meals', status: 'approved' },
  { id: 4, tripId: 101, date: '2025-02-11', amount: 340, customer: 'Globex', project: 'Migration', category: 'Train', status: 'reimbursed' },
  { id: 5, tripId: 102, date: '2025-03-17', amount: 98.45, customer: 'Acme Corp', project: 'Expansion', category: 'Taxi', status: 'approved' },
  { id: 6, tripId: 102, date: '2025-04-01', amount: 700, customer: 'Initech', project: 'Kickoff', category: 'Hotel', status: 'submitted' },
  { id: 7, tripId: 103, date: '2025-04-12', amount: 120.99, customer: 'Initech', project: 'Kickoff', category: 'Meals', status: 'approved' },
  { id: 8, tripId: 103, date: '2025-05-02', amount: 450.75, customer: 'Acme Corp', project: 'Expansion', category: 'Flight', status: 'reimbursed' },
];

export const reimbursements: Reimbursement[] = [
  { id: 1, tripId: 101, date: '2025-02-22', amount: 200, note: 'Partial payback' },
  { id: 2, tripId: 103, date: '2025-05-20', amount: 450.75, note: 'Settled in full' },
];
