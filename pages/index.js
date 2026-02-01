'use client';
import { useState } from 'react';

export default function Home() {
  const [idea, setIdea] = useState('');
  const [csvFile, setCsvFile] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const formData = new FormData();
    formData.append('idea', idea);
    formData.append('csv', csvFile);
    try {
      const res = await fetch('/api/rank', { method: 'POST', body: formData });
      if (res.ok) {
        setResults(await res.json());
      } else {
        const errorData = await res.json();
        alert('Error: ' + errorData.error);  // Show error to user
      }
    } catch (error) {
      alert('Network error: ' + error.message);
    }
    setLoading(false);
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>Warm Ranker: Self-Improving Lead Analyzer</h1>
      <form onSubmit={handleSubmit}>
        <input type="text" value={idea} onChange={(e) => setIdea(e.target.value)} placeholder="Idea (e.g., AI tools for marketing)" required />
        <input type="file" accept=".csv" onChange={(e) => setCsvFile(e.target.files[0])} required />
        <button type="submit" disabled={loading}>{loading ? 'Ranking...' : 'Rank Leads'}</button>
      </form>
      {results && (
        <div>
          <h2>Ranked Leads</h2>
          <table border="1">
            <thead>
              <tr><th>Name</th><th>Company</th><th>Position</th><th>Score</th><th>Reason</th></tr>
            </thead>
            <tbody>
              {results.map((lead, i) => (
                <tr key={i}>
                  <td>{lead['First Name']} {lead['Last Name']}</td>
                  <td>{lead.Company}</td>
                  <td>{lead.Position}</td>
                  <td>{lead.score}</td>
                  <td>{lead.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <iframe src="https://wandb.ai/pipelineom/warm_ranker" width="800" height="600" title="Weave Traces" />
        </div>
      )}
    </div>
  );
}