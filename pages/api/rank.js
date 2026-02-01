import formidable from 'formidable';
import fs from 'fs';
import { promisify } from 'util';
import { exec } from 'child_process';

const execPromise = promisify(exec);

export const config = {
  api: {
    bodyParser: false,
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
      maxFileSize: 10 * 1024 * 1024, // 10MB limit
      uploadDir: '/tmp'
    });
    
    const [fields, files] = await form.parse(req);
    
    const csvFile = files.csv?.[0];
    const idea = fields.idea?.[0] || '';

    if (!idea || !csvFile) {
      return res.status(400).json({ error: 'Missing idea or CSV file' });
    }

    const csvPath = csvFile.filepath;
    
    try {
      // Call Python script
      const pythonCmd = process.env.PYTHON_PATH || 'python3';
      const { stdout, stderr } = await execPromise(
        `${pythonCmd} warm_ranker.py "${idea}" "${csvPath}"`,
        { maxBuffer: 10 * 1024 * 1024 } // 10MB output limit
      );
      
      if (stderr && !stdout) {
        console.error('Python stderr:', stderr);
        return res.status(500).json({ error: 'Python error: ' + stderr });
      }
      
      const ranked = JSON.parse(stdout);
      res.status(200).json(ranked);
    } catch (error) {
      console.error('Execution error:', error);
      res.status(500).json({ error: error.message });
    } finally {
      // Cleanup
      if (csvPath && fs.existsSync(csvPath)) {
        try {
          fs.unlinkSync(csvPath);
        } catch (e) {
          console.error('Cleanup error:', e);
        }
      }
    }
  } catch (error) {
    console.error('Form parse error:', error);
    res.status(500).json({ error: 'Form parse error: ' + error.message });
  }
}
