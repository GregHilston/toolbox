

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
    "better-sqlite3": "^11.7.0",
    "express": "^4.21.0"
  }
}
```

### server/index.js
```js
import express from 'express';
import Database from 'better-sqlite3';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const db = new Database(path.join(__dirname, 'data.db'));

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
    id: result.lastInsertRowid,
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
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^5.4.11"
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
    <title>Books Manager</title>
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
import App from './App.jsx';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### client/src/index.css
```css
* {
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  margin: 0;
  padding: 20px;
  background: #f5f5f5;
  color: #333;
}

h1 {
  text-align: center;
}

.container {
  max-width: 900px;
  margin: 0 auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
}

th, td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  background: #fafafa;
  font-weight: 600;
}

tr:last-child td {
  border-bottom: none;
}

tr:hover td {
  background: #f9f9f9;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.85em;
  font-weight: 500;
}

.badge-read {
  background: #d4edda;
  color: #155724;
}

.badge-unread {
  background: #e2e3e5;
  color: #383d41;
}

.form-section {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
}

.form-section h2 {
  margin-top: 0;
  font-size: 1.2em;
}

.form-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 120px;
}

.form-group label {
  font-size: 0.9em;
  font-weight: 500;
}

.form-group input {
  padding: 8px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1em;
}

button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: background 0.2s;
}

button:hover {
  opacity: 0.85;
}

.btn-primary {
  background: #007bff;
  color: #fff;
}

.btn-secondary {
  background: #6c757d;
  color: #fff;
}

.btn-danger {
  background: #dc3545;
  color: #fff;
}

.btn-toggle {
  background: #28a745;
  color: #fff;
}

.actions {
  display: flex;
  gap: 8px;
}

.empty-msg {
  text-align: center;
  color: #888;
  padding: 20px;
}
```

### client/src/App.jsx
```jsx
import { useState, useEffect, useCallback } from 'react';

function App() {
  const [books, setBooks] = useState([]);
  const [loadError, setLoadError] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({ title: '', author: '', year: '', read: false });
  const [showForm, setShowForm] = useState(false);

  const fetchBooks = useCallback(async () => {
    try {
      const res = await fetch('/api/books');
      if (!res.ok) throw new Error('Failed to load books');
      const data = await res.json();
      setBooks(data);
      setLoadError(null);
    } catch (err) {
      setLoadError(err.message);
    }
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  const resetForm = () => {
    setForm({ title: '', author: '', year: '', read: false });
    setEditingId(null);
    setShowForm(false);
  };

  const startCreate = () => {
    resetForm();
    setShowForm(true);
  };

  const startEdit = (book) => {
    setEditingId(book.id);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year ?? '',
      read: book.read
    });
    setShowForm(true);
  };

  const handleFormChange = (e) => {
    const { name, value, type, checked } = e.target;
    if (type === 'checkbox') {
      setForm((f) => ({ ...f, [name]: checked }));
    } else {
      setForm((f) => ({ ...f, [name]: value }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      title: form.title,
      author: form.author,
      year: form.year ? Number(form.year) : null,
      read: form.read
    };

    try {
      if (editingId) {
        const res = await fetch(`/api/books/${editingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error((await res.json()).error || 'Update failed');
      } else {
        const res = await fetch('/api/books', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error((await res.json()).error || 'Create failed');
      }
      resetForm();
      fetchBooks();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleToggleRead = async (book) => {
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
      if (!res.ok) throw new Error('Toggle failed');
      fetchBooks();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this book?')) return;
    try {
      const res = await fetch(`/api/books/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
      fetchBooks();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div className="container">
      <h1>📚 Books Manager</h1>

      {showForm && (
        <div className="form-section">
          <h2>{editingId ? 'Edit Book' : 'Add New Book'}</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label>Title *</label>
                <input
                  type="text"
                  name="title"
                  value={form.title}
                  onChange={handleFormChange}
                  required
                />
              </div>
              <div className="form-group">
                <label>Author *</label>
                <input
                  type="text"
                  name="author"
                  value={form.author}
                  onChange={handleFormChange}
                  required
                />
              </div>
              <div className="form-group">
                <label>Year</label>
                <input
                  type="number"
                  name="year"
                  value={form.year}
                  onChange={handleFormChange}
                  placeholder="Optional"
                />
              </div>
              <div className="form-group" style={{ minWidth: 80 }}>
                <label>Read</label>
                <input
                  type="checkbox"
                  name="read"
                  checked={form.read}
                  onChange={handleFormChange}
                />
              </div>
              <div>
                <button type="submit" className="btn-primary">
                  {editingId ? 'Update' : 'Add'}
                </button>
                <button type="button" className="btn-secondary" onClick={resetForm}>
                  Cancel
                </button>
              </div>
            </div>
          </form>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <button className="btn-primary" onClick={startCreate}>+ Add Book</button>
      </div>

      {loadError && <p style={{ color: 'red' }}>Error: {loadError}</p>}

      {books.length === 0 && !loadError ? (
        <p className="empty-msg">No books yet. Click "Add Book" to get started.</p>
      ) : (
        <table>
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
              <tr key={book.id}>
                <td>{book.id}</td>
                <td>{book.title}</td>
                <td>{book.author}</td>
                <td>{book.year ?? '—'}</td>
                <td>
                  <span className={`badge ${book.read ? 'badge-read' : 'badge-unread'}`}>
                    {book.read ? 'Read' : 'Unread'}
                  </span>
                </td>
                <td>
                  <div className="actions">
                    <button
                      className="btn-toggle"
                      onClick={() => handleToggleRead(book)}
                      title={book.read ? 'Mark as unread' : 'Mark as read'}
                    >
                      {book.read ? '↩ Unread' : '✓ Read'}
                    </button>
                    <button className="btn-secondary" onClick={() => startEdit(book)}>
                      Edit
                    </button>
                    <button className="btn-danger" onClick={() => handleDelete(book.id)}>
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default App;
```

### README.md
```markdown
# Books CRUD App

A full-stack CRUD app for managing a list of books.

## Stack

- **Backend:** Node.js + Express + SQLite (`better-sqlite3`)
- **Frontend:** React + Vite

## Prerequisites

- Node.js 26

## Running

### 1. Start the API server

```bash
cd server
npm install
npm start
```

The API listens on port **3001** by default (override with the `PORT` env var).
SQLite data is stored in `server/data.db` (created automatically).

### 2. Start the frontend (dev server)

In a second terminal:

```bash
cd client
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

### Production build (frontend)

```bash
cd client
npm run build
```

Outputs a static bundle to `client/dist/`.

## API Endpoints

| Method | Path              | Description            |
|--------|-------------------|------------------------|
| GET    | /api/books        | List all books         |
| GET    | /api/books/:id    | Get a single book      |
| POST   | /api/books        | Create a book          |
| PUT    | /api/books/:id    | Update a book          |
| DELETE | /api/books/:id    | Delete a book          |

All responses are JSON. Missing/empty `title` or `author` on POST/PUT returns **400**. Unknown `id` returns **404**.
```