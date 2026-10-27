

### server/index.js
```javascript
const express = require('express');
const Database = require('better-sqlite3');
const path = require('path');

const app = express();
app.use(express.json());

const db = new Database(path.join(__dirname, 'data.db'));

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read BOOLEAN DEFAULT FALSE
  )
`);

const PORT = process.env.PORT || 3001;

app.get('/api/books', (req, res) => {
  try {
    const books = db.prepare('SELECT * FROM books').all();
    res.json(books);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/books/:id', (req, res) => {
  try {
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json(book);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/books', (req, res) => {
  try {
    const { title, author, year, read } = req.body;
    if (!title || !author) {
      return res.status(400).json({ error: 'Title and author are required' });
    }
    const stmt = db.prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)');
    const yearValue = (year === '' || year === undefined || year === null) ? null : Number(year);
    const readValue = (read === undefined || read === null) ? false : !!read;
    const result = stmt.run(title, author, yearValue, readValue);
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
    res.status(201).json(book);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/books/:id', (req, res) => {
  try {
    const { title, author, year, read } = req.body;
    if (!title || !author) {
      return res.status(400).json({ error: 'Title and author are required' });
    }
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }
    const yearValue = (year === '' || year === undefined || year === null) ? null : Number(year);
    const readValue = (read === undefined || read === null) ? false : !!read;
    db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?')
      .run(title, author, yearValue, readValue, req.params.id);
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
    res.json(book);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/books/:id', (req, res) => {
  try {
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }
    db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
    res.json({ message: 'Book deleted' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

### client/src/App.jsx
```jsx
import React, { useState, useEffect } from 'react';

function App() {
  const [books, setBooks] = useState([]);
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState({ title: '', author: '', year: '', read: false });
  const [error, setError] = useState('');

  const fetchBooks = async () => {
    try {
      const res = await fetch('/api/books');
      const data = await res.json();
      setBooks(data);
    } catch (e) {
      setError('Failed to fetch books');
    }
  };

  useEffect(() => {
    fetchBooks();
  }, []);

  const handleCreate = async () => {
    try {
      const res = await fetch('/api/books', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (res.status === 400) {
        const err = await res.json();
        setError(err.error);
        return;
      }
      setError('');
      setFormData({ title: '', author: '', year: '', read: false });
      fetchBooks();
    } catch (e) {
      setError('Failed to create book');
    }
  };

  const handleUpdate = async () => {
    try {
      const res = await fetch(`/api/books/${editing.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (res.status === 400) {
        const err = await res.json();
        setError(err.error);
        return;
      }
      if (res.status === 404) {
        setError('Book not found');
        return;
      }
      setError('');
      setEditing(null);
      setFormData({ title: '', author: '', year: '', read: false });
      fetchBooks();
    } catch (e) {
      setError('Failed to update book');
    }
  };

  const handleDelete = async (id) => {
    try {
      await fetch(`/api/books/${id}`, { method: 'DELETE' });
      fetchBooks();
    } catch (e) {
      setError('Failed to delete book');
    }
  };

  const handleToggleRead = async (book) => {
    if (!book) return;
    try {
      const updated = { ...book, read: !book.read };
      await fetch(`/api/books/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      fetchBooks();
    } catch (e) {
      setError('Failed to update book');
    }
  };

  const startEdit = (book) => {
    setEditing(book);
    setFormData({
      title: book.title,
      author: book.author,
      year: book.year !== null && book.year !== undefined ? String(book.year) : '',
      read: book.read
    });
  };

  const cancelEdit = () => {
    setEditing(null);
    setFormData({ title: '', author: '', year: '', read: false });
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>Book Manager</h1>

      {error && <div style={{ color: 'red', marginBottom: '10px', padding: '10px', backgroundColor: '#ffe0e0', borderRadius: '4px' }}>{error}</div>}

      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ccc', borderRadius: '5px' }}>
        <h3>{editing ? 'Edit Book' : 'Add New Book'}</h3>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '10px' }}>
          <input
            placeholder="Title"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            style={{ flex: 2, padding: '8px', minWidth: '150px' }}
          />
          <input
            placeholder="Author"
            value={formData.author}
            onChange={(e) => setFormData({ ...formData, author: e.target.value })}
            style={{ flex: 2, padding: '8px', minWidth: '150px' }}
          />
          <input
            type="number"
            placeholder="Year"
            value={formData.year}
            onChange={(e) => setFormData({ ...formData, year: e.target.value })}
            style={{ flex: 1, padding: '8px', minWidth: '80px' }}
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <input
              type="checkbox"
              checked={formData.read}
              onChange={(e) => setFormData({ ...formData, read: e.target.checked })}
            />
            <span>Read</span>
          </label>
        </div>
        <button onClick={editing ? handleUpdate : handleCreate} style={{ padding: '8px 16px', marginRight: '10px', cursor: 'pointer' }}>
          {editing ? 'Update' : 'Add Book'}
        </button>
        {editing && <button onClick={cancelEdit} style={{ padding: '8px 16px', cursor: 'pointer' }}>Cancel</button>}
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ backgroundColor: '#f0f0f0' }}>
            <th style={{ padding: '10px', border: '1px solid #ccc', textAlign: 'center' }}>Read</th>
            <th style={{ padding: '10px', border: '1px solid #ccc' }}>Title</th>
            <th style={{ padding: '10px', border: '1px solid #ccc' }}>Author</th>
            <th style={{ padding: '10px', border: '1px solid #ccc' }}>Year</th>
            <th style={{ padding: '10px', border: '1px solid #ccc' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.length === 0 ? (
            <tr>
              <td colSpan="5" style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
                No books yet. Add one above!
              </td>
            </tr>
          ) : (
            books.map((book) => (
              <tr key={book.id}>
                <td style={{ padding: '10px', border: '1px solid #ccc', textAlign: 'center' }}>
                  <input
                    type="checkbox"
                    checked={book.read}
                    onChange={() => handleToggleRead(book)}
                  />
                </td>
                <td style={{ padding: '10px', border: '1px solid #ccc' }}>{book.title}</td>
                <td style={{ padding: '10px', border: '1px solid #ccc' }}>{book.author}</td>
                <td style={{ padding: '10px', border: '1px solid #ccc' }}>{book.year || ''}</td>
                <td style={{ padding: '10px', border: '1px solid #ccc' }}>
                  <button onClick={() => startEdit(book)} style={{ marginRight: '5px', padding: '4px 8px', cursor: 'pointer' }}>Edit</button>
                  <button onClick={() => handleDelete(book.id)} style={{ padding: '4px 8px', cursor: 'pointer' }}>Delete</button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default App;
```