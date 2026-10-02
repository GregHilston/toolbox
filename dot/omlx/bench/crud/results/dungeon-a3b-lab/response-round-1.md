The `better-sqlite3` library requires native compilation (C++), which is failing due to incompatibility with Node.js 26 (likely a very new or experimental version) or missing build tools. Since the requirement is a full-stack CRUD app and we cannot run native compilation, we will switch to `sql.js`, a pure JavaScript SQLite implementation that runs in Node.js without native dependencies.

Here are the updated files for the server.

### server/package.json
```json
{
  "name": "server",
  "version": "1.0.0",
  "description": "Backend API for Books CRUD",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "cors": "^2.8.5",
    "express": "^4.18.2",
    "sql.js": "^1.10.2"
  }
}
```

### server/index.js
```javascript
const express = require('express');
const initSqlJs = require('sql.js');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(express.json());
app.use(cors());

// Database Setup
const DB_PATH = path.join(__dirname, 'data.db');
let db;

// Initialize Database
async function initDatabase() {
  const SQL = await initSqlJs();
  
  // Load existing data or create new
  let data = null;
  if (fs.existsSync(DB_PATH)) {
    data = fs.readFileSync(DB_PATH);
  }
  
  db = new SQL.Database(data);
  
  // Create table if it doesn't exist
  db.run(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      read BOOLEAN DEFAULT 0
    )
  `);
}

// Helper to save database to file
function saveDatabase() {
  const data = db.export();
  const buffer = Buffer.from(data);
  fs.writeFileSync(DB_PATH, buffer);
}

// Initialize DB before starting server
initDatabase().then(() => {
  // --- Endpoints ---

  // GET /api/books
  app.get('/api/books', (req, res) => {
    try {
      const result = db.exec('SELECT * FROM books');
      // Parse result into array of objects
      const books = result[0].values.map(row => {
        const cols = result[0].columns;
        const obj = {};
        cols.forEach((col, index) => {
          obj[col] = row[index];
        });
        return obj;
      });
      res.json(books);
    } catch (err) {
      console.error(err);
      res.status(500).json({ error: 'Database error' });
    }
  });

  // GET /api/books/:id
  app.get('/api/books/:id', (req, res) => {
    const id = req.params.id;
    try {
      const result = db.exec('SELECT * FROM books WHERE id = ?', [id]);
      if (result.length === 0 || result[0].values.length === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }
      const row = result[0].values[0];
      const cols = result[0].columns;
      const book = {};
      cols.forEach((col, index) => {
        book[col] = row[index];
      });
      res.json(book);
    } catch (err) {
      console.error(err);
      res.status(500).json({ error: 'Database error' });
    }
  });

  // POST /api/books
  app.post('/api/books', (req, res) => {
    const { title, author, year, read } = req.body;

    // Validation
    if (!title || title.trim() === '') {
      return res.status(400).json({ error: 'Title is required' });
    }
    if (!author || author.trim() === '') {
      return res.status(400).json({ error: 'Author is required' });
    }

    try {
      db.run(
        'INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)',
        [title.trim(), author.trim(), year || null, read ? 1 : 0]
      );
      const id = db.exec('SELECT last_insert_rowid() as id')[0].values[0][0];
      const result = db.exec('SELECT * FROM books WHERE id = ?', [id]);
      const row = result[0].values[0];
      const cols = result[0].columns;
      const book = {};
      cols.forEach((col, index) => {
        book[col] = row[index];
      });
      
      saveDatabase();
      res.status(201).json(book);
    } catch (err) {
      console.error(err);
      res.status(500).json({ error: 'Database error' });
    }
  });

  // PUT /api/books/:id
  app.put('/api/books/:id', (req, res) => {
    const id = req.params.id;
    const { title, author, year, read } = req.body;

    // Validation
    if (!title || title.trim() === '') {
      return res.status(400).json({ error: 'Title is required' });
    }
    if (!author || author.trim() === '') {
      return res.status(400).json({ error: 'Author is required' });
    }

    try {
      // Check existence
      const checkResult = db.exec('SELECT * FROM books WHERE id = ?', [id]);
      if (checkResult.length === 0 || checkResult[0].values.length === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }

      db.run(
        'UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?',
        [title.trim(), author.trim(), year || null, read ? 1 : 0, id]
      );
      
      const result = db.exec('SELECT * FROM books WHERE id = ?', [id]);
      const row = result[0].values[0];
      const cols = result[0].columns;
      const book = {};
      cols.forEach((col, index) => {
        book[col] = row[index];
      });
      
      saveDatabase();
      res.json(book);
    } catch (err) {
      console.error(err);
      res.status(500).json({ error: 'Database error' });
    }
  });

  // DELETE /api/books/:id
  app.delete('/api/books/:id', (req, res) => {
    const id = req.params.id;

    try {
      const checkResult = db.exec('SELECT * FROM books WHERE id = ?', [id]);
      if (checkResult.length === 0 || checkResult[0].values.length === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }

      db.run('DELETE FROM books WHERE id = ?', [id]);
      saveDatabase();
      res.json({ message: 'Book deleted' });
    } catch (err) {
      console.error(err);
      res.status(500).json({ error: 'Database error' });
    }
  });

  // Start Server
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });

}).catch(err => {
  console.error('Failed to initialize database:', err);
  process.exit(1);
});
```