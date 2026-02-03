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
    setResults(null);  // Clear old results on new submit
    const formData = new FormData();
    formData.append('idea', idea);
    formData.append('csv', csvFile);
    try {
      // Use environment variable for API URL, fallback to relative path
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '/api/rank';
      const res = await fetch(apiUrl, { method: 'POST', body: formData });
      if (res.ok) {
        setResults(await res.json());
      } else {
        const errorData = await res.json();
        alert('Error: ' + errorData.error);
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
        <input
          type="text"
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="Idea (e.g., AI tools for marketing)"
          required
        />
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setCsvFile(e.target.files[0])}
          required
        />
        <button type="submit" disabled={loading || !csvFile}>{loading ? 'Ranking...' : 'Rank Leads'}</button>
      </form>
      {loading && <p>Processing - this may take a moment...</p>}
      {results && (
        <div>
          <h2>Ranked Leads</h2>
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr style={{ background: '#f0f0f0' }}>
                <th style={{ padding: '8px', textAlign: 'left' }}>Name</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Company</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Position</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Score</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Reason</th>
              </tr>
            </thead>
            <tbody>
              {results.map((lead, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #ddd' }}>
                  <td style={{ padding: '8px' }}>{lead['First Name']} {lead['Last Name']}</td>
                  <td style={{ padding: '8px' }}>{lead.Company}</td>
                  <td style={{ padding: '8px' }}>{lead.Position}</td>
                  <td style={{ padding: '8px' }}>{lead.score}</td>
                  <td style={{ padding: '8px' }}>{lead.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <iframe style={{ width: '100%', height: '600px' }} src="https://wandb.ai/pipelineom/warm_ranker" title="Weave Traces" />
        </div>
      )}
    </div>
  );
}