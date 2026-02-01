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
  if (req.method === 'POST') {
    const form = formidable({ multiples: false });  # New syntax
    form.parse(req, async (err, fields, files) => {
      if (err) {
        console.error(err);
        return res.status(500).json({ error: 'Form parse error' });
      }
      const csvPath = files.csv?.filepath;  // Optional chaining for safety
      const idea = fields.idea?.[0] || '';  // Fallback if no idea

      if (!csvPath || !idea) {
        return res.status(400).json({ error: 'Missing idea or CSV file' });
      }

      try {
        // Call Python script (assume main prints JSON)
        const { stdout, stderr } = await execPromise(`python warm_ranker.py "${idea}" "${csvPath}"`);
        if (stderr) {
          console.error(stderr);
          return res.status(500).json({ error: 'Python error: ' + stderr });
        }
        const ranked = JSON.parse(stdout);
        res.status(200).json(ranked);
      } catch (error) {
        console.error(error);
        res.status(500).json({ error: error.message });
      } finally {
        if (csvPath) fs.unlinkSync(csvPath);  // Cleanup
      }
    });
  } else {
    res.status(405).json({ error: 'Method not allowed' });
  }
}