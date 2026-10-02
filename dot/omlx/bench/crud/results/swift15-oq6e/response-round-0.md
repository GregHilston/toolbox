

### README.md
```markdown
# Books CRUD App

A full-stack CRUD application for managing a list of books.

## Prerequisites

- Node.js 26
- npm

## Running the App

### 1. Start the API server

```bash
cd server
npm install
npm start
```

The API will be available at `http://localhost:3001`.

### 2. Start the frontend (in a separate terminal)

```bash
cd client
npm install
npm run dev
```

The UI will be available at `http://localhost:5173`.

### Production build of the frontend

```bash
cd client
npm run build
```

This outputs a static site to `client/dist/`.
```

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
    "better-sqlite3": "^11.0.0",
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
app.use(express.json());

const db = new Database(path.join(__dirname, 'data.db'));
db.pragma('journal_mode = WAL');

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
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
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
}

.container {
  max-width: 800px;
  margin: 0 auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1.5rem;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

th, td {
  padding: 0.75rem 1rem;
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

form.book-form {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: flex-end;
  margin-top: 1.5rem;
  padding: 1rem;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

form.book-form label {
  display: flex;
  flex-direction: column;
  font-size: 0.85rem;
  gap: 0.25rem;
}

form.book-form input {
  padding: 0.4rem 0.6rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.95rem;
}

form.book-form input[type="number"] {
  width: 5rem;
}

button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

button.primary {
  background: #4a90d9;
  color: #fff;
}

button.primary:hover {
  background: #3a7bc8;
}

button.danger {
  background: #e74c3c;
  color: #fff;
}

button.danger:hover {
  background: #c0392b;
}

button.secondary {
  background: #95a5a6;
  color: #fff;
}

button.secondary:hover {
  background: #7f8c8d;
}

button.toggle {
  background: #2ecc71;
  color: #fff;
}

button.toggle.read {
  background: #f39c12;
}

.read-yes {
  color: #2ecc71;
  font-weight: 600;
}

.read-no {
  color: #aaa;
}

.actions {
  display: flex;
  gap: 0.4rem;
}

.empty {
  text-align: center;
  color: #888;
  padding: 2rem;
}
```

### client/src/App.jsx
```jsx
import { useState, useEffect, useCallback } from 'react';

const API = '/api/books';

export default function App() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Form state
  const [formId, setFormId] = useState(null);
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [year, setYear] = useState('');
  const [read, setRead] = useState(false);

  const fetchBooks = useCallback(async () => {
    try {
      const res = await fetch(API);
      if (!res.ok) throw new Error('Failed to fetch books');
      const data = await res.json();
      setBooks(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  function resetForm() {
    setFormId(null);
    setTitle('');
    setAuthor('');
    setYear('');
    setRead(false);
  }

  function handleEdit(book) {
    setFormId(book.id);
    setTitle(book.title);
    setAuthor(book.author);
    setYear(book.year ?? '');
    setRead(book.read);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const payload = {
      title,
      author,
      year: year === '' ? null : Number(year),
      read
    };

    try {
      let res;
      if (formId) {
        res = await fetch(`${API}/${formId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch(API, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Request failed');
      }
      resetForm();
      await fetchBooks();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleToggleRead(book) {
    try {
      const res = await fetch(`${API}/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: book.title,
          author: book.author,
          year: book.year,
          read: !book.read
        })
      });
      if (!res.ok) throw new Error('Failed to update');
      await fetchBooks();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Delete this book?')) return;
    try {
      const res = await fetch(`${API}/${id}`, { method: 'DELETE' });
      if (!res.ok && res.status !== 204) throw new Error('Failed to delete');
      await fetchBooks();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="container">
      <h1>📚 My Books</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      <form className="book-form" onSubmit={handleSubmit}>
        <label>
          Title
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </label>
        <label>
          Author
          <input
            type="text"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            required
          />
        </label>
        <label>
          Year
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(e.target.value)}
          />
        </label>
        <label>
          Read
          <input
            type="checkbox"
            checked={read}
            onChange={(e) => setRead(e.target.checked)}
          />
        </label>
        <button type="submit" className="primary">
          {formId ? 'Update' : 'Add Book'}
        </button>
        {formId && (
          <button type="button" className="secondary" onClick={resetForm}>
            Cancel
          </button>
        )}
      </form>

      {loading ? (
        <p>Loading…</p>
      ) : books.length === 0 ? (
        <p className="empty">No books yet. Add one above!</p>
      ) : (
        <table>
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
            {books.map((book) => (
              <tr key={book.id}>
                <td>{book.id}</td>
                <td>{book.title}</td>
                <td>{book.author}</td>
                <td>{book.year ?? '—'}</td>
                <td>
                  <button
                    className={`toggle ${book.read ? 'read' : ''}`}
                    onClick={() => handleToggleRead(book)}
                    title={book.read ? 'Mark as unread' : 'Mark as read'}
                  >
                    {book.read ? '✓ Read' : '✗ Unread'}
                  </button>
                </td>
                <td>
                  <div className="actions">
                    <button className="secondary" onClick={() => handleEdit(book)}>
                      Edit
                    </button>
                    <button className="danger" onClick={() => handleDelete(book.id)}>
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
```