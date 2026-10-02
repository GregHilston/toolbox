

The problem is that `better-sqlite3` v11.10.0 has native C++ code that doesn't compile against Node.js 26's V8 headers. The fix is to use Node.js's built-in `node:sqlite` module (stable since Node 22.5+), which requires zero native compilation.

### server/package.json
```json
{
  "name": "books-server",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.21.0"
  }
}
```

### server/index.js
```javascript
const express = require('express');
const { DatabaseSync } = require('node:sqlite');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;

// ── Database setup ──────────────────────────────────────────────
const db = new DatabaseSync(path.join(__dirname, 'data.db'));
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT    NOT NULL,
    author TEXT   NOT NULL,
    year  INTEGER,
    read  BOOLEAN NOT NULL DEFAULT 0
  )
`);

// ── Helpers ─────────────────────────────────────────────────────
function mapBook(row) {
  if (!row) return row;
  return { ...row, read: Boolean(row.read) };
}

app.use(express.json());

// ── GET /api/books ──────────────────────────────────────────────
app.get('/api/books', (_req, res) => {
  const rows = db.prepare('SELECT * FROM books ORDER BY id').all();
  res.json(rows.map(mapBook));
});

// ── GET /api/books/:id ──────────────────────────────────────────
app.get('/api/books/:id', (req, res) => {
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!row) return res.status(404).json({ error: 'Book not found' });
  res.json(mapBook(row));
});

// ── POST /api/books ─────────────────────────────────────────────
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body ?? {};

  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required' });
  }

  const stmt = db.prepare(
    'INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)'
  );
  const info = stmt.run(
    title.trim(),
    author.trim(),
    year != null ? Number(year) : null,
    read ? 1 : 0
  );
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(info.lastInsertRowid);
  res.status(201).json(mapBook(row));
});

// ── PUT /api/books/:id ──────────────────────────────────────────
app.put('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });

  const { title, author, year, read } = req.body ?? {};

  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required' });
  }

  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?').run(
    title.trim(),
    author.trim(),
    year != null ? Number(year) : null,
    read ? 1 : 0,
    req.params.id
  );
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  res.json(mapBook(row));
});

// ── DELETE /api/books/:id ───────────────────────────────────────
app.delete('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });
  db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
  res.json({ message: 'Book deleted' });
});

// ── Start ───────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`Books API listening on http://localhost:${PORT}`);
});
```