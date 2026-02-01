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

  // Validate Content-Length BEFORE parsing to prevent buffer overflow
  const MAX_CONTENT_LENGTH = 10 * 1024 * 1024; // 10MB
  const MAX_BUFFER_SIZE = 4294967296; // Node.js max buffer size (4GB)
  
  const contentLength = req.headers['content-length'];
  if (contentLength) {
    const size = parseInt(contentLength, 10);
    if (isNaN(size) || size < 0) {
      return res.status(400).json({ error: 'Invalid Content-Length header' });
    }
    if (size > MAX_BUFFER_SIZE) {
      return res.status(413).json({ error: `Content-Length exceeds maximum buffer size (${MAX_BUFFER_SIZE} bytes)` });
    }
    if (size > MAX_CONTENT_LENGTH) {
      return res.status(413).json({ error: `File too large (max ${MAX_CONTENT_LENGTH} bytes)` });
    }
  }

  try {
    const form = formidable({ 
      multiples: false,
      keepExtensions: true,
      maxFileSize: MAX_CONTENT_LENGTH,
      maxTotalFileSize: MAX_CONTENT_LENGTH,
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
      // Call Python script - try multiple Python paths for Vercel compatibility
      const pythonPaths = [
        '/usr/local/bin/python3',
        '/usr/bin/python3',
        'python3',
        'python',
        process.env.PYTHON_PATH
      ].filter(Boolean);
      
      let stdout, stderr;
      let lastError;
      
      for (const pythonCmd of pythonPaths) {
        try {
          const result = await execPromise(
            `${pythonCmd} warm_ranker.py "${idea}" "${csvPath}"`,
            { 
              maxBuffer: 10 * 1024 * 1024, // 10MB output limit
              env: { ...process.env, PYTHONUNBUFFERED: '1' }
            }
          );
          stdout = result.stdout;
          stderr = result.stderr;
          break;
        } catch (error) {
          lastError = error;
          // If it's a "command not found" error, try next path
          if (error.message.includes('command not found') || error.message.includes('ENOENT')) {
            continue;
          }
          // Otherwise, rethrow
          throw error;
        }
      }
      
      if (!stdout && lastError) {
        throw new Error(`Python not found. Tried: ${pythonPaths.join(', ')}. Error: ${lastError.message}`);
      }
      
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
