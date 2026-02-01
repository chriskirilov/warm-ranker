import formidable from 'formidable';
import fs from 'fs';
import { promisify } from 'util';
import { exec } from 'child_process';

const execPromise = promisify(exec);

export const config = {
  api: {
    bodyParser: false,  // Disable Next.js body parsing
  },
};

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const form = formidable({ 
      multiples: false,
      keepExtensions: true,
      uploadDir: '/tmp'  // Use /tmp for Vercel compatibility
    });
    const [fields, files] = await form.parse(req);
    
    const csvPath = files.csv?.[0]?.filepath;
    const idea = fields.idea?.[0] || '';

    if (!csvPath || !idea) {
      return res.status(400).json({ error: 'Missing idea or CSV file' });
    }

    try {
      // Try venv python first, fallback to python3
      const pythonCmd = fs.existsSync('.venv/bin/python3') 
        ? '.venv/bin/python3' 
        : 'python3';
      
      // Call Python script (assume main prints JSON)
      const { stdout, stderr } = await execPromise(`${pythonCmd} warm_ranker.py "${idea}" "${csvPath}"`);
      if (stderr && !stdout) {
        console.error(stderr);
        return res.status(500).json({ error: 'Python error: ' + stderr });
      }
      const ranked = JSON.parse(stdout);
      res.status(200).json(ranked);
    } catch (error) {
      console.error(error);
      res.status(500).json({ error: error.message });
    } finally {
      if (csvPath && fs.existsSync(csvPath)) {
        fs.unlinkSync(csvPath);  // Cleanup
      }
    }
  } catch (error) {
    console.error('Form parse error:', error);
    res.status(500).json({ error: 'Form parse error: ' + error.message });
  }
}