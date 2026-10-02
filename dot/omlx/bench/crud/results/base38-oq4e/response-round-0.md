

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
    "better-sqlite3": "^11.0.0",
    "express": "^4.21.0"
  }
}
```

### server/index.js
```js
const express = require('express');
const path = require('path');
const Database = require('better-sqlite3');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(express.json());

// Initialize database
const db = new Database(path.join(__dirname, 'data.db'));
db.pragma('journal_mode = WAL');
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read BOOLEAN NOT NULL DEFAULT 0
  )
`);

// GET /api/books
app.get('/api/books', (req, res) => {
  const rows = db.prepare('SELECT id, title, author, year, read FROM books').all();
  const books = rows.map(r => ({
    id: r.id,
    title: r.title,
    author: r.author,
    year: r.year ?? null,
    read: !!r.read
  }));
  res.json(books);
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const row = db.prepare('SELECT id, title, author, year, read FROM books WHERE id = ?').get(req.params.id);
  if (!row) return res.status(404).json({ error: 'Book not found' });
  res.json({
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year ?? null,
    read: !!row.read
  });
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

  const yearVal = year != null && year !== '' ? parseInt(year, 10) : null;
  const readVal = read ? 1 : 0;

  const stmt = db.prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)');
  const result = stmt.run(title.trim(), author.trim(), yearVal, readVal);

  const newBook = {
    id: result.lastInsertRowid,
    title: title.trim(),
    author: author.trim(),
    year: yearVal,
    read: !!readVal
  };
  res.status(201).json(newBook);
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT id FROM books WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });

  const { title, author, year, read } = req.body || {};

  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'author is required' });
  }

  const yearVal = year != null && year !== '' ? parseInt(year, 10) : null;
  const readVal = read ? 1 : 0;

  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?').run(
    title.trim(), author.trim(), yearVal, readVal, req.params.id
  );

  res.json({
    id: Number(req.params.id),
    title: title.trim(),
    author: author.trim(),
    year: yearVal,
    read: !!readVal
  });
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT id FROM books WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });

  db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
  res.json({ message: 'Book deleted' });
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
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^5.4.0"
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

### client/src/index.css
```css
* {
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  margin: 0;
  padding: 2rem;
  background: #f5f5f5;
  color: #333;
}

h1 {
  text-align: center;
  margin-bottom: 1.5rem;
}

.container {
  max-width: 900px;
  margin: 0 auto;
}

.form-card {
  background: #fff;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.form-card h2 {
  margin-top: 0;
  font-size: 1.1rem;
}

.form-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.form-row label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.9rem;
}

.form-row label input[type="text"],
.form-row label input[type="number"] {
  padding: 0.4rem 0.6rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.9rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
}

.checkbox-label input[type="checkbox"] {
  width: 1rem;
  height: 1rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.btn-primary {
  background: #3366dd;
  color: #fff;
}

.btn-primary:hover {
  background: #2a55bb;
}

.btn-secondary {
  background: #888;
  color: #fff;
}

.btn-secondary:hover {
  background: #666;
}

.btn-danger {
  background: #dd3333;
  color: #fff;
}

.btn-danger:hover {
  background: #bb2a2a;
}

.btn-sm {
  padding: 0.3rem 0.6rem;
  font-size: 0.8rem;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

th, td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  background: #fafafa;
  font-weight: 600;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

td {
  font-size: 0.9rem;
}

.badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-read {
  background: #d4edda;
  color: #155724;
}

.badge-unread {
  background: #f8d7da;
  color: #721c24;
}

.actions {
  display: flex;
  gap: 0.4rem;
}

.empty-msg {
  text-align: center;
  padding: 2rem;
  color: #888;
}
```

### client/src/App.jsx
```jsx
import { useState, useEffect, useCallback } from 'react';

export default function App() {
  const [books, setBooks] = useState([]);
  const [form, setForm] = useState({ title: '', author: '', year: '', read: false });
  const [editingId, setEditingId] = useState(null);
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
      title: form.title.trim(),
      author: form.author.trim(),
      year: form.year !== '' ? Number(form.year) : null,
      read: form.read
    };

    try {
      let res;
      if (editingId) {
        res = await fetch(`/api/books/${editingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch('/api/books', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }

      if (!res.ok) {
        const err = await res.json();
        setError(err.error || 'Request failed');
        return;
      }

      resetForm();
      fetchBooks();
    } catch (err) {
      setError('Network error');
    }
  };

  const handleEdit = (book) => {
    setEditingId(book.id);
    setForm({
      title: book.title,
      author: book.author,
      year: book.year != null ? String(book.year) : '',
      read: book.read
    });
    setError('');
  };

  const handleDelete = async (id) => {
    try {
      await fetch(`/api/books/${id}`, { method: 'DELETE' });
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
          read: !book.read
        })
      });
      fetchBooks();
    } catch (err) {
      setError('Failed to toggle read');
    }
  };

  return (
    <div className="container">
      <h1>📚 Books</h1>

      <div className="form-card">
        <h2>{editingId ? `Edit Book #${editingId}` : 'Add a Book'}</h2>
        {error && <p style={{ color: '#dd3333', marginBottom: '0.5rem' }}>{error}</p>}
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Title
              <input
                type="text"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
              />
            </label>
            <label>
              Author
              <input
                type="text"
                value={form.author}
                onChange={(e) => setForm({ ...form, author: e.target.value })}
                required
              />
            </label>
            <label>
              Year
              <input
                type="number"
                value={form.year}
                onChange={(e) => setForm({ ...form, year: e.target.value })}
                placeholder="e.g. 2024"
              />
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={form.read}
                onChange={(e) => setForm({ ...form, read: e.target.checked })}
              />
              Read
            </label>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button type="submit" className="btn btn-primary">
              {editingId ? 'Update' : 'Add Book'}
            </button>
            {editingId && (
              <button type="button" className="btn btn-secondary" onClick={resetForm}>
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Author</th>
            <th>Year</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.length === 0 && (
            <tr>
              <td colSpan={6} className="empty-msg">No books yet. Add one above!</td>
            </tr>
          )}
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
                  <button className="btn btn-sm btn-secondary" onClick={() => handleEdit(book)}>
                    Edit
                  </button>
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={() => handleToggleRead(book)}
                  >
                    {book.read ? 'Mark Unread' : 'Mark Read'}
                  </button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDelete(book.id)}>
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### README.md
```markdown
# Books CRUD App

A full-stack CRUD application for managing a list of books.

## Prerequisites

- Node.js 26

## Running the Project

### 1. Start the API server

```bash
cd server
npm install
npm start
```

The API will be available at `http://localhost:3001` (or the port in the `PORT` env variable).

### 2. Start the frontend (dev)

In a second terminal:

```bash
cd client
npm install
npm run dev
```

Open the URL Vite prints (typically `http://localhost:5173`). The Vite dev server proxies all `/api` requests to the backend.

### 3. Production build (optional)

```bash
cd client
npm run build
```

Outputs a static bundle to `client/dist/`.

## API Endpoints

| Method | Path             | Description           |
|--------|------------------|-----------------------|
| GET    | /api/books       | List all books        |
| GET    | /api/books/:id   | Get a single book     |
| POST   | /api/books       | Create a book         |
| PUT    | /api/books/:id   | Update a book         |
| DELETE | /api/books/:id   | Delete a book         |

`POST` and `PUT` require `title` and `author` (non-empty strings); `year` and `read` are optional.
```