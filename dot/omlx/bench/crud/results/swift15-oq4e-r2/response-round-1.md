

The problem is that `better-sqlite3` v11 cannot compile against Node 26's V8 headers. The fix is to use Node 26's built-in `node:sqlite` module, which requires no native compilation.

### server/package.json
```json
{
  "name": "books-server",
  "version": "1.0.0",
  "private": true,
  "type": "module",
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
import express from 'express';
import { DatabaseSync } from 'node:sqlite';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

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

const app = express();
app.use(express.json());

// GET /api/books
app.get('/api/books', (req, res) => {
  const rows = db.prepare('SELECT id, title, author, year, read FROM books').all();
  const books = rows.map(r => ({
    id: r.id,
    title: r.title,
    author: r.author,
    year: r.year,
    read: Boolean(r.read)
  }));
  res.json(books);
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const row = db.prepare('SELECT id, title, author, year, read FROM books WHERE id = ?').get(req.params.id);
  if (!row) {
    return res.status(404).json({ error: 'Book not found' });
  }
  res.json({
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    read: Boolean(row.read)
  });
});

// POST /api/books
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;

  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required' });
  }

  const stmt = db.prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)');
  const result = stmt.run(title.trim(), author.trim(), year ?? null, read ? 1 : 0);

  const newBook = {
    id: Number(result.lastInsertRowid),
    title: title.trim(),
    author: author.trim(),
    year: year ?? null,
    read: Boolean(read)
  };
  res.status(201).json(newBook);
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT id FROM books WHERE id = ?').get(req.params.id);
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const { title, author, year, read } = req.body;

  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required' });
  }

  const stmt = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?');
  stmt.run(title.trim(), author.trim(), year ?? null, read ? 1 : 0, req.params.id);

  res.json({
    id: Number(req.params.id),
    title: title.trim(),
    author: author.trim(),
    year: year ?? null,
    read: Boolean(read)
  });
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT id FROM books WHERE id = ?').get(req.params.id);
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
  res.json({ message: 'Deleted' });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Books API listening on port ${PORT}`);
});
```