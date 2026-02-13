import { useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

function App() {
  const [formData, setFormData] = useState({
    start: '',
    end: '',
    project: '',
    tripType: 'domestic',
  })
  const [receipts, setReceipts] = useState([])
  const [tripId, setTripId] = useState('')
  const [summary, setSummary] = useState(null)
  const [status, setStatus] = useState('')

  const canGenerate = useMemo(() => {
    return formData.start && formData.end && formData.project
  }, [formData])

  const onChange = (event) => {
    const { name, value } = event.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const onReceiptsChange = (event) => {
    setReceipts(Array.from(event.target.files ?? []))
  }

  const onGenerate = async () => {
    if (!canGenerate) {
      setStatus('Please fill in all required trip fields.')
      return
    }

    try {
      setStatus('Creating trip...')
      const createRes = await fetch(`${API_BASE}/trips`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start: new Date(formData.start).toISOString(),
          end: new Date(formData.end).toISOString(),
          project: formData.project,
          trip_type: formData.tripType,
        }),
      })

      if (!createRes.ok) throw new Error('Failed to create trip.')
      const trip = await createRes.json()
      setTripId(trip.id)

      if (receipts.length > 0) {
        setStatus('Uploading receipts...')
        const uploadBody = new FormData()
        receipts.forEach((file) => uploadBody.append('files', file))

        const uploadRes = await fetch(`${API_BASE}/trips/${trip.id}/receipts`, {
          method: 'POST',
          body: uploadBody,
        })

        if (!uploadRes.ok) throw new Error('Failed to upload receipts.')
      }

      setStatus('Calculating summary...')
      const summaryRes = await fetch(`${API_BASE}/trips/${trip.id}/summary`)
      if (!summaryRes.ok) throw new Error('Failed to fetch summary.')

      setSummary(await summaryRes.json())
      setStatus('Expense report is ready. Download your Excel file below.')
    } catch (error) {
      setStatus(error.message)
    }
  }

  return (
    <main className="page">
      <section className="card">
        <h1>Travel Mate Expense Reporter</h1>
        <p>Create a trip, upload receipts, and generate an expense report.</p>

        <label>
          Leave date/time
          <input type="datetime-local" name="start" value={formData.start} onChange={onChange} />
        </label>

        <label>
          Return date/time
          <input type="datetime-local" name="end" value={formData.end} onChange={onChange} />
        </label>

        <label>
          Project
          <input type="text" name="project" value={formData.project} onChange={onChange} placeholder="Project name" />
        </label>

        <label>
          Trip type
          <select name="tripType" value={formData.tripType} onChange={onChange}>
            <option value="domestic">Domestic</option>
            <option value="international">International</option>
          </select>
        </label>

        <label>
          Receipt uploads
          <input type="file" multiple accept="image/*" onChange={onReceiptsChange} />
        </label>

        <button onClick={onGenerate}>Generate Expense Report</button>

        {status && <p className="status">{status}</p>}

        {summary && (
          <div className="summary">
            <h2>Trip Summary</h2>
            <ul>
              <li>Trip ID: {summary.trip_id}</li>
              <li>Project: {summary.project}</li>
              <li>Type: {summary.trip_type}</li>
              <li>Duration (hours): {summary.duration_hours}</li>
              <li>Receipts: {summary.receipt_count}</li>
              <li>Estimated total: ${summary.estimated_total}</li>
            </ul>
            <a href={`${API_BASE}/trips/${tripId}/export.xlsx`} target="_blank" rel="noreferrer">
              Download export.xlsx
            </a>
          </div>
        )}
      </section>
    </main>
  )
}

export default App
