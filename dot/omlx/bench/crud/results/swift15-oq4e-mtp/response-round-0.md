

### README.md
```markdown
# Books CRUD App

A full-stack CRUD app for managing a list of books.

## Prerequisites

- Node.js 26

## Run the Server

```bash
cd server
npm install
npm start
```

The API listens on `http://localhost:3001` (or the port set in the `PORT` environment variable).

## Run the Client (dev)

```bash
cd client
npm install
npm run dev
```

The UI is served at `http://localhost:5173`. The Vite dev server proxies `/api` to `http://localhost:3001`.

## Build the Client

```bash
cd client
npm run build
```

## Database

SQLite database is stored at `server/data.db`. It is created automatically on first server start.
```

### server/package.json
```json
{
  "name": "books-server",
  "version": "1.0.0",
  "private": true,
  "engines": {
    "node": "26.x"
  },
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "better-sqlite3": "^11.10.0",
    "express": "^4.21.0"
  }
}
```

### server/index.js
```js
const express = require('express');
const Database = require('better-sqlite3');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(express.json());

// Initialize SQLite database
const db = new Database(path.join(__dirname, 'data.db'));
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read BOOLEAN DEFAULT 0
  )
`);

// GET /api/books
app.get('/api/books', (req, res) => {
  const rows = db.prepare('SELECT * FROM books').all();
  const books = rows.map((r) => ({
    id: r.id,
    title: r.title,
    author: r.author,
    year: r.year,
    read: !!r.read,
  }));
  res.json(books);
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!row) {
    return res.status(404).json({ error: 'Book not found' });
  }
  res.json({
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    read: !!row.read,
  });
});

// POST /api/books
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;

  if (!title || !title.trim() || !author || !author.trim()) {
    return res.status(400).json({ error: 'title and author are required' });
  }

  const stmt = db.prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)');
  const result = stmt.run(title.trim(), author.trim(), year || null, read ? 1 : 0);

  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
  res.status(201).json({
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    read: !!row.read,
  });
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const { title, author, year, read } = req.body;

  if (!title || !title.trim() || !author || !author.trim()) {
    return res.status(400).json({ error: 'title and author are required' });
  }

  const stmt = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?');
  stmt.run(title.trim(), author.trim(), year || null, read ? 1 : 0, req.params.id);

  const row = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  res.json({
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    read: !!row.read,
  });
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
  res.status(204).end();
});

app.listen(PORT, () => {
  console.log(`Books API server listening on port ${PORT}`);
});
```

### client/package.json
```json
{
  "name": "books-client",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
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
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
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
import './App.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### client/src/App.jsx
```jsx
import { useState, useEffect, useCallback } from 'react';

export default function App() {
  const [books, setBooks] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({ title: '', author: '', year: '', read: false });
  const [error, setError] = useState('');

  const fetchBooks = useCallback(async () => {
    try {
      const res = await fetch('/api/books');
      const data = await res.json();
      setBooks(data);
    } catch (e) {
      setError('Failed to fetch books');
    }
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  const resetForm = () => {
    setForm({ title: '', author: '', year: '', read: false });
    setEditingId(null);
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const payload = {
      title: form.title,
      author: form.author,
      year: form.year ? Number(form.year) : null,
      read: form.read,
    };

    try {
      if (editingId) {
        await fetch(`/api/books/${editingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        await fetch('/api/books', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }
      resetForm();
      fetchBooks();
    } catch (err) {
      setError('Request failed');
    }
  };

  const handleEdit = (book) => {
    setEditingId(book.id);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year ? String(book.year) : '',
      read: book.read,
    });
    setError('');
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this book?')) return;
    try {
      await fetch(`/api/books/${id}`, { method: 'DELETE' });
      if (editingId === id) resetForm();
      fetchBooks();
    } catch (err) {
      setError('Failed to delete');
    }
  };

  const handleToggleRead = async (book) => {
    try {
      await fetch(`/api/books/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: book.title,
          author: book.author,
          year: book.year,
          read: !book.read,
        }),
      });
      fetchBooks();
    } catch (err) {
      setError('Failed to update');
    }
  };

  return (
    <div className="container">
      <h1>Books</h1>

      {error && <div className="error">{error}</div>}

      <form onSubmit={handleSubmit} className="book-form">
        <h2>{editingId ? 'Edit Book' : 'Add Book'}</h2>
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
          />
          <label className="read-label">
            <input
              type="checkbox"
              checked={form.read}
              onChange={(e) => setForm({ ...form, read: e.target.checked })}
            />
            Read
          </label>
        </div>
        <div className="form-actions">
          <button type="submit">{editingId ? 'Update' : 'Add'}</button>
          {editingId && (
            <button type="button" onClick={resetForm} className="btn-secondary">
              Cancel
            </button>
          )}
        </div>
      </form>

      <table className="books-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Author</th>
            <th>Year</th>
            <th>Read</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.map((book) => (
            <tr key={book.id} className={book.read ? 'read' : ''}>
              <td>{book.id}</td>
              <td>{book.title}</td>
              <td>{book.author}</td>
              <td>{book.year ?? ''}</td>
              <td>
                <input
                  type="checkbox"
                  checked={book.read}
                  onChange={() => handleToggleRead(book)}
                />
              </td>
              <td>
                <button onClick={() => handleEdit(book)}>Edit</button>
                <button onClick={() => handleDelete(book.id)} className="btn-danger">
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {books.length === 0 && (
            <tr>
              <td colSpan={6} className="empty">
                No books yet. Add one above!
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
```

### client/src/App.css
```css
* {
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  margin: 0;
  background: #f5f5f5;
  color: #333;
}

.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

h1 {
  text-align: center;
  margin-bottom: 1.5rem;
}

.error {
  background: #fee;
  color: #c00;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  text-align: center;
}

.book-form {
  background: #fff;
  padding: 1.25rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.book-form h2 {
  margin-top: 0;
  font-size: 1.1rem;
}

.form-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.form-row input[type='text'],
.form-row input[type='number'] {
  flex: 1;
  min-width: 120px;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.read-label {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.9rem;
}

.form-actions {
  margin-top: 0.75rem;
  display: flex;
  gap: 0.5rem;
}

button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  background: #2563eb;
  color: #fff;
}

button:hover {
  background: #1d4ed8;
}

.btn-secondary {
  background: #6b7280;
}

.btn-secondary:hover {
  background: #4b5563;
}

.btn-danger {
  background: #dc2626;
  margin-left: 0.25rem;
}

.btn-danger:hover {
  background: #b91c1c;
}

.books-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.books-table th,
.books-table td {
  padding: 0.6rem 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.books-table th {
  background: #f9fafb;
  font-weight: 600;
}

.books-table tr.read td {
  color: #999;
}

.books-table tr:last-child td {
  border-bottom: none;
}

.empty {
  text-align: center;
  color: #999;
  padding: 1.5rem;
}
```