

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
    "express": "^4.21.2"
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

function mapBook(row) {
  if (!row) return null;
  return { id: row.id, title: row.title, author: row.author, year: row.year, read: !!row.read };
}

// GET /api/books
app.get('/api/books', (req, res) => {
  const stmt = db.prepare('SELECT * FROM books ORDER BY id');
  const rows = stmt.all();
  res.json(rows.map(mapBook));
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const stmt = db.prepare('SELECT * FROM books WHERE id = ?');
  const row = stmt.get(Number(req.params.id));
  if (!row) return res.status(404).json({ error: 'Book not found' });
  res.json(mapBook(row));
});

// POST /api/books
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;
  if (!title || !String(title).trim() || !author || !String(author).trim()) {
    return res.status(400).json({ error: 'title and author are required' });
  }
  const yearVal = year !== null && year !== undefined && year !== '' ? Number(year) : null;
  const readVal = read ? 1 : 0;
  const stmt = db.prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)');
  const result = stmt.run(String(title).trim(), String(author).trim(), yearVal, readVal);
  const newId = Number(result.lastInsertRowid);
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(newId);
  res.status(201).json(mapBook(row));
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });

  const { title, author, year, read } = req.body;
  if (!title || !String(title).trim() || !author || !String(author).trim()) {
    return res.status(400).json({ error: 'title and author are required' });
  }
  const yearVal = year !== null && year !== undefined && year !== '' ? Number(year) : null;
  const readVal = read ? 1 : 0;
  const stmt = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?');
  stmt.run(String(title).trim(), String(author).trim(), yearVal, readVal, id);
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  res.json(mapBook(row));
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });
  db.prepare('DELETE FROM books WHERE id = ?').run(id);
  res.json({ message: 'Deleted' });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Books API listening on http://localhost:${PORT}`);
});
```

### client/package.json
```json
{
  "name": "books-client",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.0"
  }
}
```

### client/vite.config.js
```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:3001'
    }
  }
});
```

### client/index.html
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Books</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

### client/src/main.jsx
```jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### client/src/App.jsx
```jsx
import { useState, useEffect, useCallback } from 'react';

const EMPTY_FORM = { title: '', author: '', year: '', read: false };

export default function App() {
  const [books, setBooks] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState('');

  const fetchBooks = useCallback(async () => {
    try {
      const res = await fetch('/api/books');
      const data = await res.json();
      setBooks(data);
    } catch (e) {
      setError('Failed to load books');
    }
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  function resetForm() {
    setForm(EMPTY_FORM);
    setEditingId(null);
    setError('');
  }

  function handleCreate(e) {
    e.preventDefault();
    createBook();
  }

  async function createBook() {
    const payload = {
      title: form.title,
      author: form.author,
      year: form.year ? Number(form.year) : null,
      read: form.read
    };
    try {
      const res = await fetch('/api/books', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.error || 'Failed to create book');
        return;
      }
      resetForm();
      fetchBooks();
    } catch (e) {
      setError('Network error');
    }
  }

  async function saveEdit() {
    const payload = {
      title: form.title,
      author: form.author,
      year: form.year ? Number(form.year) : null,
      read: form.read
    };
    try {
      const res = await fetch(`/api/books/${editingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.error || 'Failed to update book');
        return;
      }
      resetForm();
      fetchBooks();
    } catch (e) {
      setError('Network error');
    }
  }

  function startEdit(book) {
    setEditingId(book.id);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year !== null && book.year !== undefined ? String(book.year) : '',
      read: book.read
    });
    setError('');
  }

  async function toggleRead(book) {
    try {
      const res = await fetch(`/api/books/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: book.title,
          author: book.author,
          year: book.year,
          read: !book.read
        })
      });
      if (!res.ok) return;
      fetchBooks();
    } catch (e) {
      setError('Network error');
    }
  }

  async function deleteBook(id) {
    if (!confirm('Delete this book?')) return;
    try {
      const res = await fetch(`/api/books/${id}`, { method: 'DELETE' });
      if (!res.ok) return;
      if (editingId === id) resetForm();
      fetchBooks();
    } catch (e) {
      setError('Network error');
    }
  }

  return (
    <div className="container">
      <h1>📚 Books</h1>

      {error && (
        <div className="error" onClick={() => setError('')}>
          {error} ✕
        </div>
      )}

      <form className="book-form" onSubmit={handleCreate}>
        <h2>{editingId ? 'Edit Book' : 'Add a Book'}</h2>
        <div className="form-row">
          <input
            type="text"
            placeholder="Title *"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
          />
          <input
            type="text"
            placeholder="Author *"
            value={form.author}
            onChange={(e) => setForm({ ...form, author: e.target.value })}
            required
          />
          <input
            type="number"
            placeholder="Year"
            value={form.year}
            onChange={(e) => setForm({ ...form, year: e.target.value })}
            min="0"
            max="9999"
          />
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={form.read}
              onChange={(e) => setForm({ ...form, read: e.target.checked })}
            />
            Read
          </label>
        </div>
        <div className="form-actions">
          <button type="submit" className="btn btn-primary">
            {editingId ? 'Save' : 'Add'}
          </button>
          {editingId && (
            <button type="button" className="btn" onClick={resetForm}>
              Cancel
            </button>
          )}
        </div>
      </form>

      <table className="book-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Title</th>
            <th>Author</th>
            <th>Year</th>
            <th>Read</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.length === 0 ? (
            <tr>
              <td colSpan={6} className="empty">No books yet. Add one above!</td>
            </tr>
          ) : (
            books.map((book) => (
              <tr key={book.id} className={book.read ? 'read' : ''}>
                <td>{book.id}</td>
                <td>{book.title}</td>
                <td>{book.author}</td>
                <td>{book.year ?? ''}</td>
                <td>
                  <button
                    className="toggle-btn"
                    onClick={() => toggleRead(book)}
                    title="Toggle read"
                  >
                    {book.read ? '✓ Read' : '○ Unread'}
                  </button>
                </td>
                <td className="actions">
                  <button className="btn btn-small" onClick={() => startEdit(book)}>
                    Edit
                  </button>
                  <button className="btn btn-small btn-danger" onClick={() => deleteBook(book.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
```

### client/src/index.css
```css
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f7fa;
  color: #333;
}

.container {
  max-width: 800px;
  margin: 2rem auto;
  padding: 0 1rem;
}

h1 {
  text-align: center;
  margin-bottom: 1.5rem;
}

.error {
  background: #fee;
  color: #c0392b;
  border: 1px solid #e74c3c;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  cursor: pointer;
}

.book-form {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.book-form h2 {
  margin: 0 0 0.75rem;
  font-size: 1.1rem;
}

.form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.form-row input[type='text'],
.form-row input[type='number'] {
  flex: 1;
  min-width: 100px;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.9rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.9rem;
  white-space: nowrap;
}

.form-actions {
  display: flex;
  gap: 0.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn:hover {
  background: #f0f0f0;
}

.btn-primary {
  background: #3498db;
  color: #fff;
  border-color: #2980b9;
}

.btn-primary:hover {
  background: #2980b9;
}

.btn-danger {
  background: #e74c3c;
  color: #fff;
  border-color: #c0392b;
}

.btn-danger:hover {
  background: #c0392b;
}

.btn-small {
  padding: 0.3rem 0.6rem;
  font-size: 0.8rem;
}

.book-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.book-table th,
.book-table td {
  padding: 0.6rem 0.75rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.book-table th {
  background: #f8f9fa;
  font-weight: 600;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.book-table tr:last-child td {
  border-bottom: none;
}

.book-table tr.read td {
  opacity: 0.7;
}

.empty {
  text-align: center;
  color: #888;
  padding: 1.5rem !important;
}

.actions {
  display: flex;
  gap: 0.3rem;
}

.toggle-btn {
  background: none;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  font-size: 0.8rem;
}

.toggle-btn:hover {
  background: #f0f0f0;
}
```

### README.md
```markdown
# Books CRUD App

A small full-stack CRUD application for managing a list of books.

## Running

### 1. Start the API server

```bash
cd server
npm install
npm start
```

The API listens on **http://localhost:3001** (override with the `PORT` env var).

### 2. Start the frontend (dev server)

In a second terminal:

```bash
cd client
npm install
npm run dev
```

Open the URL printed by Vite (typically **http://localhost:5173**). The dev server proxies all `/api` requests to the backend.

### 3. Production build (frontend)

```bash
cd client
npm run build
```

Outputs a static bundle to `client/dist/`.

## Tech Stack

| Layer    | Technology            |
|----------|-----------------------|
| Backend  | Node.js + Express + SQLite (`node:sqlite`) |
| Frontend | React 18 + Vite       |
| Database | SQLite file at `server/data.db` (auto-created) |
```