import { useMemo, useState } from 'react';
import { Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom';

const CATEGORIES = ['Travel', 'Meals', 'Lodging', 'Supplies', 'Other'];

const confidenceClass = (value) => {
  if (value >= 0.85) return 'high';
  if (value >= 0.65) return 'medium';
  return 'low';
};

const formatCurrency = (value) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(value) || 0);

const createMockExpenses = () => [
  { id: 'exp-1', date: '2026-02-01', merchant: 'SkyJet Airlines', category: 'Travel', amount: 620.2, confidence: 0.94 },
  { id: 'exp-2', date: '2026-02-02', merchant: 'Riverside Hotel', category: 'Lodging', amount: 420, confidence: 0.89 },
  { id: 'exp-3', date: '2026-02-03', merchant: 'City Bistro', category: 'Meals', amount: 73.8, confidence: 0.61 },
];

function TripBasicsAndUpload({ addTrip }) {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [tripBasics, setTripBasics] = useState({
    leaveAt: '',
    returnAt: '',
    customer: '',
    project: '',
    travelType: 'domestic',
  });
  const [warnings, setWarnings] = useState({});
  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);

  const setField = (field, value) => {
    setTripBasics((prev) => ({ ...prev, [field]: value }));
    setWarnings((prev) => ({ ...prev, [field]: '' }));
  };

  const validateBasics = () => {
    const nextWarnings = {};
    if (!tripBasics.leaveAt) nextWarnings.leaveAt = 'Departure date/time is required.';
    if (!tripBasics.returnAt) nextWarnings.returnAt = 'Return date/time is required.';
    if (!tripBasics.customer.trim()) nextWarnings.customer = 'Customer is required.';
    if (!tripBasics.project.trim()) nextWarnings.project = 'Project is required.';

    if (tripBasics.leaveAt && tripBasics.returnAt && new Date(tripBasics.returnAt) < new Date(tripBasics.leaveAt)) {
      nextWarnings.returnAt = 'Return time must be after departure time.';
    }

    setWarnings(nextWarnings);
    return Object.keys(nextWarnings).length === 0;
  };

  const addSelectedFiles = (incoming) => {
    const list = Array.from(incoming || []);
    if (!list.length) return;

    const withProgress = list.map((file, index) => ({
      id: `${file.name}-${Date.now()}-${index}`,
      file,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : '',
      progress: 0,
    }));

    setFiles((prev) => [...prev, ...withProgress]);

    withProgress.forEach((entry) => {
      let progress = 0;
      const timer = setInterval(() => {
        progress += 20;
        setFiles((prev) => prev.map((f) => (f.id === entry.id ? { ...f, progress: Math.min(progress, 100) } : f)));
        if (progress >= 100) clearInterval(timer);
      }, 180);
    });
  };

  const beginReview = () => {
    const id = addTrip({
      basics: tripBasics,
      receipts: files.map((item) => ({ name: item.file.name, size: item.file.size, type: item.file.type })),
      expenses: createMockExpenses(),
    });
    navigate(`/trip/${id}/review`);
  };

  return (
    <main className="container">
      <h1>Travel Expense Wizard</h1>
      <p className="subtle">Step {step} of 4</p>

      {step === 1 && (
        <section className="card">
          <h2>1) Trip Basics</h2>
          <div className="grid">
            <label>
              Leave date & time *
              <input
                type="datetime-local"
                value={tripBasics.leaveAt}
                onChange={(event) => setField('leaveAt', event.target.value)}
              />
              {warnings.leaveAt && <span className="warning">{warnings.leaveAt}</span>}
            </label>

            <label>
              Return date & time *
              <input
                type="datetime-local"
                value={tripBasics.returnAt}
                onChange={(event) => setField('returnAt', event.target.value)}
              />
              {warnings.returnAt && <span className="warning">{warnings.returnAt}</span>}
            </label>

            <label>
              Customer *
              <input value={tripBasics.customer} onChange={(event) => setField('customer', event.target.value)} />
              {warnings.customer && <span className="warning">{warnings.customer}</span>}
            </label>

            <label>
              Project *
              <input value={tripBasics.project} onChange={(event) => setField('project', event.target.value)} />
              {warnings.project && <span className="warning">{warnings.project}</span>}
            </label>
          </div>

          <fieldset>
            <legend>Trip type</legend>
            <label>
              <input
                type="radio"
                checked={tripBasics.travelType === 'domestic'}
                onChange={() => setField('travelType', 'domestic')}
              />
              Domestic
            </label>
            <label>
              <input
                type="radio"
                checked={tripBasics.travelType === 'international'}
                onChange={() => setField('travelType', 'international')}
              />
              International
            </label>
          </fieldset>

          <div className="actions">
            <button
              onClick={() => {
                if (validateBasics()) setStep(2);
              }}
            >
              Continue to Receipts
            </button>
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="card">
          <h2>2) Receipt Upload</h2>
          <div
            className={`dropzone ${isDragging ? 'dragging' : ''}`}
            onDragOver={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setIsDragging(false);
              addSelectedFiles(event.dataTransfer.files);
            }}
          >
            <p>Drag and drop receipts here, or browse files.</p>
            <input
              type="file"
              multiple
              accept="image/*,application/pdf"
              onChange={(event) => addSelectedFiles(event.target.files)}
            />
          </div>

          {files.length > 0 && (
            <div className="upload-list">
              {files.map((item) => (
                <article key={item.id} className="upload-item">
                  <div>
                    <strong>{item.file.name}</strong>
                    <small>{Math.round(item.file.size / 1024)} KB</small>
                  </div>
                  {item.preview && <img src={item.preview} alt={item.file.name} />}
                  <progress value={item.progress} max="100" />
                </article>
              ))}
            </div>
          )}

          <div className="actions">
            <button className="secondary" onClick={() => setStep(1)}>
              Back
            </button>
            <button onClick={beginReview}>Review Auto-Detected Expenses</button>
          </div>
        </section>
      )}
    </main>
  );
}

function ExpenseReview({ trips, updateTrip }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const trip = trips[id];
  const [categoryFilter, setCategoryFilter] = useState('All');

  if (!trip) return <Navigate to="/" replace />;

  const visibleExpenses =
    categoryFilter === 'All' ? trip.expenses : trip.expenses.filter((item) => item.category === categoryFilter);

  const total = visibleExpenses.reduce((sum, item) => sum + Number(item.amount || 0), 0);

  const onUpdateExpense = (expenseId, field, value) => {
    const normalized = field === 'amount' ? Number(value || 0) : value;
    updateTrip(id, {
      expenses: trip.expenses.map((item) => (item.id === expenseId ? { ...item, [field]: normalized } : item)),
    });
  };

  return (
    <main className="container">
      <h1>3) Review Auto-Detected Expenses</h1>
      <p className="subtle">Trip #{id}</p>

      <section className="card">
        <div className="toolbar">
          <label>
            Category filter
            <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
              <option>All</option>
              {CATEGORIES.map((category) => (
                <option key={category}>{category}</option>
              ))}
            </select>
          </label>
          <div className="pill">Total preview: {formatCurrency(total)}</div>
        </div>

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Merchant</th>
                <th>Category</th>
                <th>Amount</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {visibleExpenses.map((item) => (
                <tr key={item.id}>
                  <td>
                    <input type="date" value={item.date} onChange={(event) => onUpdateExpense(item.id, 'date', event.target.value)} />
                  </td>
                  <td>
                    <input value={item.merchant} onChange={(event) => onUpdateExpense(item.id, 'merchant', event.target.value)} />
                  </td>
                  <td>
                    <select value={item.category} onChange={(event) => onUpdateExpense(item.id, 'category', event.target.value)}>
                      {CATEGORIES.map((category) => (
                        <option key={category}>{category}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={item.amount}
                      onChange={(event) => onUpdateExpense(item.id, 'amount', event.target.value)}
                    />
                  </td>
                  <td>
                    <span className={`confidence ${confidenceClass(item.confidence)}`}>
                      {Math.round(item.confidence * 100)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="actions">
          <button className="secondary" onClick={() => navigate('/')}>
            Start Over
          </button>
          <button onClick={() => navigate(`/trip/${id}/summary`)}>Continue to Summary</button>
        </div>
      </section>
    </main>
  );
}

function Summary({ trips, updateTrip }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const trip = trips[id];
  const [warnings, setWarnings] = useState({});

  if (!trip) return <Navigate to="/" replace />;

  const totalsByCategory = trip.expenses.reduce((acc, row) => {
    acc[row.category] = (acc[row.category] || 0) + Number(row.amount || 0);
    return acc;
  }, {});

  const grandTotal = Object.values(totalsByCategory).reduce((sum, amount) => sum + amount, 0);

  const updateBasicsField = (field, value) => {
    updateTrip(id, { basics: { ...trip.basics, [field]: value } });
    setWarnings((prev) => ({ ...prev, [field]: '' }));
  };

  const updateExpense = (expenseId, field, value) => {
    const normalized = field === 'amount' ? Number(value || 0) : value;
    updateTrip(id, {
      expenses: trip.expenses.map((item) => (item.id === expenseId ? { ...item, [field]: normalized } : item)),
    });
  };

  const validateBeforeExport = () => {
    const nextWarnings = {};
    if (!trip.basics.leaveAt) nextWarnings.leaveAt = 'Departure date/time is required.';
    if (!trip.basics.returnAt) nextWarnings.returnAt = 'Return date/time is required.';
    if (!trip.basics.customer.trim()) nextWarnings.customer = 'Customer is required.';
    if (!trip.basics.project.trim()) nextWarnings.project = 'Project is required.';

    const hasEmptyExpense = trip.expenses.some((item) => !item.merchant.trim() || Number(item.amount) <= 0);
    if (hasEmptyExpense) nextWarnings.expenses = 'Each expense needs a merchant and amount greater than zero.';

    setWarnings(nextWarnings);
    return Object.keys(nextWarnings).length === 0;
  };

  const exportExcel = () => {
    if (!validateBeforeExport()) return;

    const header = ['Date', 'Merchant', 'Category', 'Amount'];
    const lines = trip.expenses.map((item) => [item.date, item.merchant, item.category, item.amount].join(','));
    const csv = [header.join(','), ...lines].join('\n');
    const blob = new Blob([csv], { type: 'application/vnd.ms-excel;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `trip-${id}-expenses.xlsx`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportPdfOverview = () => {
    if (!validateBeforeExport()) return;

    const lines = [
      `Trip ${id}`,
      `Customer: ${trip.basics.customer}`,
      `Project: ${trip.basics.project}`,
      `Type: ${trip.basics.travelType}`,
      `Leave: ${trip.basics.leaveAt}`,
      `Return: ${trip.basics.returnAt}`,
      `Grand Total: ${formatCurrency(grandTotal)}`,
    ];
    const blob = new Blob([lines.join('\n')], { type: 'application/pdf' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `trip-${id}-overview.pdf`;
    link.click();
  };

  return (
    <main className="container">
      <h1>4) Final Summary + Export</h1>
      <section className="card">
        <h2>Editable Trip Details</h2>
        <div className="grid">
          <label>
            Leave date & time *
            <input
              type="datetime-local"
              value={trip.basics.leaveAt}
              onChange={(event) => updateBasicsField('leaveAt', event.target.value)}
            />
            {warnings.leaveAt && <span className="warning">{warnings.leaveAt}</span>}
          </label>
          <label>
            Return date & time *
            <input
              type="datetime-local"
              value={trip.basics.returnAt}
              onChange={(event) => updateBasicsField('returnAt', event.target.value)}
            />
            {warnings.returnAt && <span className="warning">{warnings.returnAt}</span>}
          </label>
          <label>
            Customer *
            <input value={trip.basics.customer} onChange={(event) => updateBasicsField('customer', event.target.value)} />
            {warnings.customer && <span className="warning">{warnings.customer}</span>}
          </label>
          <label>
            Project *
            <input value={trip.basics.project} onChange={(event) => updateBasicsField('project', event.target.value)} />
            {warnings.project && <span className="warning">{warnings.project}</span>}
          </label>
        </div>

        <h3>Final Expense Corrections</h3>
        {warnings.expenses && <p className="warning">{warnings.expenses}</p>}
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Merchant</th>
                <th>Category</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              {trip.expenses.map((item) => (
                <tr key={item.id}>
                  <td>
                    <input value={item.merchant} onChange={(event) => updateExpense(item.id, 'merchant', event.target.value)} />
                  </td>
                  <td>
                    <select value={item.category} onChange={(event) => updateExpense(item.id, 'category', event.target.value)}>
                      {CATEGORIES.map((category) => (
                        <option key={category}>{category}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={item.amount}
                      onChange={(event) => updateExpense(item.id, 'amount', event.target.value)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3>Totals</h3>
        <ul>
          {Object.entries(totalsByCategory).map(([category, amount]) => (
            <li key={category}>
              {category}: {formatCurrency(amount)}
            </li>
          ))}
          <li>
            <strong>Grand Total: {formatCurrency(grandTotal)}</strong>
          </li>
        </ul>

        <div className="actions">
          <button className="secondary" onClick={() => navigate(`/trip/${id}/review`)}>
            Back to Review
          </button>
          <button onClick={exportExcel}>Download Excel</button>
          <button onClick={exportPdfOverview}>Optional PDF Overview</button>
        </div>
      </section>
    </main>
  );
}

export default function App() {
  const [trips, setTrips] = useState({});

  const addTrip = (trip) => {
    const id = `${Date.now()}`;
    setTrips((prev) => ({ ...prev, [id]: trip }));
    return id;
  };

  const updateTrip = (id, partial) => {
    setTrips((prev) => ({
      ...prev,
      [id]: {
        ...prev[id],
        ...partial,
      },
    }));
  };

  const value = useMemo(() => ({ trips, addTrip, updateTrip }), [trips]);

  return (
    <Routes>
      <Route path="/" element={<TripBasicsAndUpload addTrip={value.addTrip} />} />
      <Route path="/trip/:id/review" element={<ExpenseReview trips={value.trips} updateTrip={value.updateTrip} />} />
      <Route path="/trip/:id/summary" element={<Summary trips={value.trips} updateTrip={value.updateTrip} />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
