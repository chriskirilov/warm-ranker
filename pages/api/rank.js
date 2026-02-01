import formidable from 'formidable';
import fs from 'fs';
import { promisify } from 'util';
import { exec } from 'child_process';

const execPromise = promisify(exec);

export const config = {
  api: {
    bodyParser: false,  // Disable Next.js body parsing for formidable
  },
};

export default async function handler(req, res) {
  if (req.method === 'POST') {
    const form = formidable({ multiples: false });  // New v3+ syntax: no IncomingForm
    form.parse(req, async (err, fields, files) => {
      if (err) {
        console.error(err);
        return res.status(500).json({ error: 'Form parse error' });
      }
      const csvPath = files.csv ? files.csv.filepath : null;  // Handle if no file
      const idea = fields.idea ? fields.idea[0] : '';  // Handle no idea

      if (!csvPath || !idea) {
        return res.status(400).json({ error: 'Missing idea or CSV file' });
      }

      try {
        // Call Python script via subprocess (adjust path if needed)
        const { stdout, stderr } = await execPromise(`python warm_ranker.py "${idea}" "${csvPath}"`);
        if (stderr) {
          console.error(stderr);
          return res.status(500).json({ error: 'Python execution error: ' + stderr });
        }
        const ranked = JSON.parse(stdout);  // Assume main prints JSON output
        res.status(200).json(ranked);
      } catch (error) {
        console.error(error);
        res.status(500).json({ error: error.message });
      } finally {
        if (csvPath) fs.unlinkSync(csvPath);  // Clean up temp CSV
      }
    });
  } else {
    res.status(405).json({ error: 'Method not allowed' });
  }
}