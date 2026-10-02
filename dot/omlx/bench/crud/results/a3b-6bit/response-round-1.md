

### server/package.json
```json
{
  "name": "book-manager-server",
  "version": "1.0.0",
  "description": "REST API for book management",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "cors": "^2.8.5",
    "express": "^4.21.2",
    "sql.js": "^1.10.2"
  }
}
```

### server/index.js
```javascript
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const initSqlJs = require('sql.js');

const app = express();
const port = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

let SQL;
let db;

function saveDatabase() {
  const data = db.export();
  const buffer = Buffer.from(data);
  fs.writeFileSync(path.join(__dirname, 'data.db'), buffer);
}

async function init() {
  SQL = await initSqlJs({
    locateFile: () => 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/sql-wasm.wasm'
  });
  
  const dbPath = path.join(__dirname, 'data.db');
  let fileData = null;
  if (fs.existsSync(dbPath)) {
    fileData = fs.readFileSync(dbPath);
  }
  
  db = fileData ? new SQL.Database(fileData) : new SQL.Database();
  
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      read BOOLEAN DEFAULT 0
    )
  `);
  
  saveDatabase();

  app.get('/api/books', (req, res) => {
    try {
      const rows = db.all('SELECT * FROM books');
      res.json(rows.map(b => ({ id: b.id, title: b.title, author: b.author, year: b.year, read: !!b.read })));
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get('/api/books/:id', (req, res) => {
    try {
      const book = db.get('SELECT * FROM books WHERE id = ?', [req.params.id]);
      if (!book) return res.status(404).json({ error: 'Book not found' });
      res.json({ id: book.id, title: book.title, author: book.author, year: book.year, read: !!book.read });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post('/api/books', (req, res) => {
    try {
      const { title, author, year, read } = req.body;
      if (!title || !author || title.trim() === '' || author.trim() === '') {
        return res.status(400).json({ error: 'Title and author are required' });
      }
      const result = db.run('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)', 
        [title, author, year || null, read ? 1 : 0]);
      saveDatabase();
      const book = db.get('SELECT * FROM books WHERE id = ?', [result.lastID]);
      res.status(201).json({ id: book.id, title: book.title, author: book.author, year: book.year, read: !!book.read });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.put('/api/books/:id', (req, res) => {
    try {
      const { title, author, year, read } = req.body;
      if (!title || !author || title.trim() === '' || author.trim() === '') {
        return res.status(400).json({ error: 'Title and author are required' });
      }
      const existing = db.get('SELECT * FROM books WHERE id = ?', [req.params.id]);
      if (!existing) return res.status(404).json({ error: 'Book not found' });
      
      db.run('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?', 
        [title, author, year || null, read ? 1 : 0, req.params.id]);
      saveDatabase();
      const updated = db.get('SELECT * FROM books WHERE id = ?', [req.params.id]);
      res.json({ id: updated.id, title: updated.title, author: updated.author, year: updated.year, read: !!updated.read });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.delete('/api/books/:id', (req, res) => {
    try {
      const existing = db.get('SELECT * FROM books WHERE id = ?', [req.params.id]);
      if (!existing) return res.status(404).json({ error: 'Book not found' });
      
      db.run('DELETE FROM books WHERE id = ?', [req.params.id]);
      saveDatabase();
      res.json({ success: true });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.listen(port, () => {
    console.log(`Server running on port ${port}`);
  });
}

init().catch(err => {
  console.error('Failed to initialize server:', err);
  process.exit(1);
});
```