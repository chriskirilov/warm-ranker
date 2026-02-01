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
    const form = new formidable.IncomingForm();
    form.parse(req, async (err, fields, files) => {
      if (err) {
        console.error(err);
        return res.status(500).json({ error: 'Form parse error' });
      }
      const csvPath = files.csv.filepath;  // Temp path to uploaded CSV
      const idea = fields.idea[0];  // Idea string

      try {
        // Call Python script via subprocess (adjust path if needed)
        const { stdout, stderr } = await execPromise(`python warm_ranker.py "${idea}" "${csvPath}"`);
        if (stderr) {
          console.error(stderr);
          return res.status(500).json({ error: 'Python execution error' });
        }
        const ranked = JSON.parse(stdout);  // Assume main prints JSON output
        res.status(200).json(ranked);
      } catch (error) {
        console.error(error);
        res.status(500).json({ error: error.message });
      } finally {
        fs.unlinkSync(csvPath);  // Clean up temp CSV
      }
    });
  } else {
    res.status(405).json({ error: 'Method not allowed' });
  }
}