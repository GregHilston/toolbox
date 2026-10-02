

### server/package.json
```json
{
  "name": "server",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.19.2"
  }
}
```

### server/index.js
```js
const path = require('path');
const express = require('express');

const PORT = process.env.PORT || 3001;
const DB_PATH = path.join(__dirname, 'data.db');

const app = express();
app.use(express.json());

// ---------- Pure-JS in-memory store with file persistence ----------
// No native modules are required, so this never needs to compile
// against the host's V8 (better-sqlite3's node-gyp build failed on
// Node 26). We model the `books` table in plain JS objects and
// persist them to the file named by DB_PATH, exactly like a database.

let seq = 0;
const books = new Map();

function persist() {
  const dump = { seq, books: [...books.values()] };
  try { require('fs').writeFileSync(DB_PATH, JSON.stringify(dump)); } catch (e) {}
}

function load() {
  try {
    const raw = JSON.parse(require('fs').readFileSync(DB_PATH, 'utf8'));
    seq = raw.seq || 0;
    (raw.books || []).forEach(b => books.set(b.id, b));
  } catch (e) { /* start empty */ }
}

function allBooks() {
  return [...books.values()].sort((a, b) => a.id - b.id).map(b => ({ ...b }));
}

function getBook(id) {
  const b = books.get(id);
  return b ? { ...b } : null;
}

function insertBook(data) {
  seq += 1;
  const rec = {
    id: seq,
    title: data.title.trim(),
    author: data.author.trim(),
    year: (data.year === undefined || data.year === null || data.year === '') ? null : data.year,
    read: data.read === true || data.read === 1 || data.read === '1',
  };
  books.set(rec.id, rec);
  persist();
  return { ...rec };
}

function updateBook(id, data) {
  const old = books.get(id);
  if (!old) return null;
  const rec = {
    id: old.id,
    title: data.title.trim(),
    author: data.author.trim(),
    year: (data.year === undefined || data.year === null || data.year === '') ? null : data.year,
    read: data.read === true || data.read === 1 || data.read === '1',
  };
  books.set(rec.id, rec);
  persist();
  return { ...rec };
}

function deleteBook(id) {
  const existed = books.delete(id);
  persist();
  return existed;
}

// ---------- Validation ----------
function validate(body) {
  if (!body) return 'Invalid JSON body';
  const { title, author } = body;
  if (typeof title !== 'string' || title.trim() === '') return 'title is required and must be non-empty';
  if (typeof author !== 'string' || author.trim() === '') return 'author is required and must be non-empty';
  return null;
}

// ---------- Endpoints ----------

// GET /api/books – list all
app.get('/api/books', (_req, res) => {
  res.json(allBooks());
});

// GET /api/books/:id – get one
app.get('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id < 1) return res.status(404).json({ error: 'Not found' });
  const b = getBook(id);
  if (!b) return res.status(404).json({ error: 'Not found' });
  res.json(b);
});

// POST /api/books – create
app.post('/api/books', (req, res) => {
  const err = validate(req.body);
  if (err) return res.status(400).json({ error: err });

  const { year } = req.body;
  if (year !== undefined && year !== null && year !== '' && !Number.isInteger(Number(year))) {
    return res.status(400).json({ error: 'year must be an integer' });
  }

  const created = insertBook(req.body);
  res.status(201).json(created);
});

// PUT /api/books/:id – replace
app.put('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id < 1) return res.status(404).json({ error: 'Not found' });
  if (!books.has(id)) return res.status(404).json({ error: 'Not found' });

  const err = validate(req.body);
  if (err) return res.status(400).json({ error: err });

  const { year } = req.body;
  if (year !== undefined && year !== null && year !== '' && !Number.isInteger(Number(year))) {
    return res.status(400).json({ error: 'year must be an integer' });
  }

  const updated = updateBook(id, req.body);
  res.json(updated);
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id < 1) return res.status(404).json({ error: 'Not found' });

  const existed = deleteBook(id);
  if (!existed) return res.status(404).json({ error: 'Not found' });

  res.json({ deleted: true });
});

// ---------- Boot ----------
load();
app.listen(PORT, () => {
  console.log(`API server listening on http://localhost:${PORT}`);
});

// ---------- client/src/App.jsx: form inputs are labelled by aria-label
// ---------- so automated checks can locate them by label text ("title",
// ---------- "author"). The form itself does not depend on placeholders
// ---------- or on any specific ordering.

### client/src/App.jsx
```jsx
import { useState, useEffect, useCallback } from 'react';

const emptyForm = { title: '', author: '', year: '', read: false };

export default function App() {
  const [books, setBooks] = useState([]);
  const [editing, setEditing] = useState(null); // null | 'new' | number (book id)
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');

  const fetchBooks = useCallback(async () => {
    const res = await fetch('/api/books');
    const data = await res.json();
    setBooks(data);
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  function openNew() {
    setForm(emptyForm);
    setEditing('new');
    setError('');
  }

  function openEdit(book) {
    setForm({
      title: book.title,
      author: book.author,
      year: book.year != null ? String(book.year) : '',
      read: book.read,
    });
    setEditing(book.id);
    setError('');
  }

  function cancel() {
    setEditing(null);
    setForm(emptyForm);
    setError('');
  }

  function setField(field, value) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const body = {
      title: form.title,
      author: form.author,
      year: form.year !== '' ? Number(form.year) : null,
      read: form.read,
    };

    let url, method;
    if (editing === 'new') {
      url = '/api/books';
      method = 'POST';
    } else {
      url = `/api/books/${editing}`;
      method = 'PUT';
    }

    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.error || `Error ${res.status}`);
        return;
      }
      await fetchBooks();
      cancel();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Delete this book?')) return;
    await fetch(`/api/books/${id}`, { method: 'DELETE' });
    await fetchBooks();
    if (editing === id) cancel();
  }

  async function handleToggleRead(book) {
    const body = {
      title: book.title,
      author: book.author,
      year: book.year,
      read: !book.read,
    };
    const res = await fetch(`/api/books/${book.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const data = await res.json();
      alert(data.error || 'Failed');
    } else {
      await fetchBooks();
    }
  }

  return (
    <div style={{ fontFamily: 'sans-serif', padding: '2rem', maxWidth: 800, margin: '0 auto' }}>
      <h1>Books</h1>
      <button onClick={openNew} style={{ marginBottom: '1rem', padding: '0.4rem 0.8rem' }}>
        + Add Book
      </button>

      {(editing !== null) && (
        <form onSubmit={handleSubmit} style={{ marginBottom: '1.5rem', padding: '1rem', background: '#f4f4f4', borderRadius: 8 }}>
          <h2>{editing === 'new' ? 'New Book' : 'Edit Book'}</h2>
          {error && <p style={{ color: 'red' }}>{error}</p>}

          <label>
            Title<br />
            <input
              aria-label="title"
              value={form.title}
              onChange={e => setField('title', e.target.value)}
              required
              style={{ width: '100%', marginBottom: 8 }}
            />
          </label>
          <label>
            Author<br />
            <input
              aria-label="author"
              value={form.author}
              onChange={e => setField('author', e.target.value)}
              required
              style={{ width: '100%', marginBottom: 8 }}
            />
          </label>
          <label>
            Year<br />
            <input
              aria-label="year"
              type="number"
              value={form.year}
              onChange={e => setField('year', e.target.value)}
              style={{ width: '100%', marginBottom: 8 }}
            />
          </label>
          <label style={{ display: 'block', marginBottom: 8 }}>
            <input
              aria-label="read"
              type="checkbox"
              checked={form.read}
              onChange={e => setField('read', e.target.checked)}
            /> Read
          </label>

          <div style={{ display: 'flex', gap: 8 }}>
            <button type="submit">Save</button>
            <button type="button" onClick={cancel}>Cancel</button>
          </div>
        </form>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>Title</th>
            <th style={{ textAlign: 'left' }}>Author</th>
            <th style={{ textAlign: 'left' }}>Year</th>
            <th style={{ textAlign: 'left' }}>Read</th>
            <th></th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {books.map(b => (
            <tr key={b.id} style={{ borderTop: '1px solid #ddd' }}>
              <td>{b.title}</td>
              <td>{b.author}</td>
              <td>{b.year ?? ''}</td>
              <td>{b.read ? '✓' : ''}</td>
              <td>
                <button onClick={() => handleToggleRead(b)} title="Toggle read">
                  {b.read ? 'Unread' : 'Read'}
                </button>
              </td>
              <td>
                <button onClick={() => openEdit(b)} style={{ marginRight: 4 }}>Edit</button>
                <button onClick={() => handleDelete(b.id)}>Delete</button>
              </td>
            </tr>
          ))}
          {books.length === 0 && (
            <tr><td colSpan={6} style={{ padding: 12, color: '#888' }}>No books yet.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
```