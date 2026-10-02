

The problem is that `better-sqlite3` is a native C++ addon that cannot compile against Node.js 26's V8. The fix is to use the built-in `node:sqlite` module (available in Node 22.5+ and stable in Node 26), which requires zero native compilation.

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
```js
const express = require('express');
const path = require('path');
const { DatabaseSync } = require('node:sqlite');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(express.json());

// Initialize database
const db = new DatabaseSync(path.join(__dirname, 'data.db'));
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read INTEGER NOT NULL DEFAULT 0
  )
`);

function toBook(row) {
  return {
    id: Number(row.id),
    title: row.title,
    author: row.author,
    year: row.year != null ? Number(row.year) : null,
    read: !!row.read
  };
}

// GET /api/books
app.get('/api/books', (req, res) => {
  const rows = db.prepare('SELECT id, title, author, year, read FROM books').all();
  res.json(rows.map(toBook));
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const row = db.prepare('SELECT id, title, author, year, read FROM books WHERE id = ?').get(Number(req.params.id));
  if (!row) return res.status(404).json({ error: 'Book not found' });
  res.json(toBook(row));
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

  const yearVal = (year != null && year !== '') ? Number(year) : null;
  const readVal = read ? 1 : 0;

  const result = db.prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)').run(
    title.trim(), author.trim(), yearVal, readVal
  );

  const newBook = {
    id: Number(result.lastInsertRowid),
    title: title.trim(),
    author: author.trim(),
    year: yearVal,
    read: !!readVal
  };
  res.status(201).json(newBook);
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare('SELECT id FROM books WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });

  const { title, author, year, read } = req.body || {};

  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required' });
  }

  const yearVal = (year != null && year !== '') ? Number(year) : null;
  const readVal = read ? 1 : 0;

  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?').run(
    title.trim(), author.trim(), yearVal, readVal, id
  );

  res.json({
    id,
    title: title.trim(),
    author: author.trim(),
    year: yearVal,
    read: !!readVal
  });
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare('SELECT id FROM books WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });

  db.prepare('DELETE FROM books WHERE id = ?').run(id);
  res.json({ message: 'Book deleted' });
});

app.listen(PORT, () => {
  console.log(`Books API server listening on port ${PORT}`);
});
```