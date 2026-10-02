

The issue is that `better-sqlite3` is a native C++ module that doesn't compile on Node.js 26. I'll replace it with Node's built-in `node:sqlite` module (stable since Node 22.5+, no native compilation needed).

### server/package.json
```json
{
  "name": "books-server",
  "version": "1.0.0",
  "private": true,
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.21.0"
  }
}
```

### server/index.js
```js
const express = require('express');
const { DatabaseSync } = require('node:sqlite');
const path = require('path');

const app = express();
app.use(express.json());

const db = new DatabaseSync(path.join(__dirname, 'data.db'));

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read BOOLEAN DEFAULT 0
  )
`);

function rowToBook(row) {
  if (!row) return null;
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    read: !!row.read
  };
}

// GET /api/books
app.get('/api/books', (req, res) => {
  const rows = db.prepare('SELECT * FROM books ORDER BY id').all();
  res.json(rows.map(rowToBook));
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!row) return res.status(404).json({ error: 'Book not found' });
  res.json(rowToBook(row));
});

// POST /api/books
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body || {};
  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required' });
  }
  const stmt = db.prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)');
  const result = stmt.run(title.trim(), author.trim(), year ?? null, read ? 1 : 0);
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
  res.status(201).json(rowToBook(row));
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const { title, author, year, read } = req.body || {};
  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required' });
  }
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });
  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?')
    .run(title.trim(), author.trim(), year ?? null, read ? 1 : 0, req.params.id);
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  res.json(rowToBook(row));
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });
  db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
  res.status(204).end();
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Books API listening on http://localhost:${PORT}`);
});
```