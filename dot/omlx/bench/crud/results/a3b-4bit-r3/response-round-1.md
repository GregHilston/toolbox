

### server/index.js
```javascript
const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
app.use(express.json());

const db = new sqlite3.Database(path.join(__dirname, 'data.db'));

db.run(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read BOOLEAN DEFAULT 0
  )
`);

app.get('/api/books', (req, res) => {
  db.all('SELECT * FROM books', (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

app.get('/api/books/:id', (req, res) => {
  db.get('SELECT * FROM books WHERE id = ?', [req.params.id], (err, row) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!row) return res.status(404).json({ error: 'Book not found' });
    res.json(row);
  });
});

app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;
  if (!title || title.trim() === '') {
    return res.status(400).json({ error: 'Title is required' });
  }
  if (!author || author.trim() === '') {
    return res.status(400).json({ error: 'Author is required' });
  }
  db.run(
    'INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)',
    [title, author, year || null, read ? 1 : 0],
    function (err) {
      if (err) return res.status(500).json({ error: err.message });
      db.get('SELECT * FROM books WHERE id = ?', [this.lastID], (err, row) => {
        if (err) return res.status(500).json({ error: err.message });
        res.status(201).json(row);
      });
    }
  );
});

app.put('/api/books/:id', (req, res) => {
  const { title, author, year, read } = req.body;
  if (!title || title.trim() === '') {
    return res.status(400).json({ error: 'Title is required' });
  }
  if (!author || author.trim() === '') {
    return res.status(400).json({ error: 'Author is required' });
  }
  db.run(
    'UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?',
    [title, author, year || null, read ? 1 : 0, req.params.id],
    function (err) {
      if (err) return res.status(500).json({ error: err.message });
      db.get('SELECT * FROM books WHERE id = ?', [req.params.id], (err, row) => {
        if (err) return res.status(500).json({ error: err.message });
        if (!row) return res.status(404).json({ error: 'Book not found' });
        res.json(row);
      });
    }
  );
});

app.delete('/api/books/:id', (req, res) => {
  db.get('SELECT * FROM books WHERE id = ?', [req.params.id], (err, row) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!row) return res.status(404).json({ error: 'Book not found' });
    db.run('DELETE FROM books WHERE id = ?', [req.params.id], (err) => {
      if (err) return res.status(500).json({ error: err.message });
      res.json({ message: 'Book deleted' });
    });
  });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

### client/src/App.jsx
```jsx
import { useState, useEffect } from 'react';

function App() {
  const [books, setBooks] = useState([]);
  const [editingBook, setEditingBook] = useState(null);
  const [formData, setFormData] = useState({ title: '', author: '', year: '', read: false });
  const [error, setError] = useState('');

  const fetchBooks = async () => {
    const res = await fetch('/api/books');
    const data = await res.json();
    setBooks(data);
  };

  useEffect(() => {
    fetchBooks();
  }, []);

  const handleCreate = async () => {
    try {
      const res = await fetch('/api/books', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (res.status === 400) {
        const err = await res.json();
        setError(err.error);
        return;
      }
      setFormData({ title: '', author: '', year: '', read: false });
      fetchBooks();
    } catch (e) {
      setError('Failed to create book');
    }
  };

  const handleUpdate = async () => {
    try {
      const res = await fetch(`/api/books/${editingBook.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (res.status === 400) {
        const err = await res.json();
        setError(err.error);
        return;
      }
      setEditingBook(null);
      setFormData({ title: '', author: '', year: '', read: false });
      fetchBooks();
    } catch (e) {
      setError('Failed to update book');
    }
  };

  const handleDelete = async (id) => {
    await fetch(`/api/books/${id}`, { method: 'DELETE' });
    fetchBooks();
  };

  const handleToggleRead = async (book) => {
    try {
      const updated = { ...book, read: !book.read };
      const res = await fetch(`/api/books/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated)
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.error || 'Failed to update');
        return;
      }
      fetchBooks();
    } catch (e) {
      setError('Network error while toggling read status');
    }
  };

  const startEdit = (book) => {
    setEditingBook(book);
    setFormData({ title: book.title, author: book.author, year: book.year || '', read: book.read });
  };

  const cancelEdit = () => {
    setEditingBook(null);
    setFormData({ title: '', author: '', year: '', read: false });
    setError('');
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>Book Manager</h1>

      {error && <div style={{ color: 'red', marginBottom: '10px', padding: '8px', backgroundColor: '#ffe0e0', borderRadius: '4px' }}>{error}</div>}

      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ccc', borderRadius: '5px' }}>
        <h2>{editingBook ? 'Edit Book' : 'Add New Book'}</h2>
        <div style={{ marginBottom: '10px' }}>
          <label>Title: </label>
          <input
            type="text"
            value={formData.title}
            onChange={e => setFormData({ ...formData, title: e.target.value })}
            placeholder="Enter title"
            style={{ padding: '4px', width: '200px' }}
          />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Author: </label>
          <input
            type="text"
            value={formData.author}
            onChange={e => setFormData({ ...formData, author: e.target.value })}
            placeholder="Enter author"
            style={{ padding: '4px', width: '200px' }}
          />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Year: </label>
          <input
            type="number"
            value={formData.year}
            onChange={e => setFormData({ ...formData, year: e.target.value })}
            placeholder="Optional"
            style={{ padding: '4px', width: '80px' }}
          />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            <input
              type="checkbox"
              checked={formData.read}
              onChange={e => setFormData({ ...formData, read: e.target.checked })}
            />
            Read
          </label>
        </div>
        <button onClick={editingBook ? handleUpdate : handleCreate}>
          {editingBook ? 'Update' : 'Create'}
        </button>
        {editingBook && (
          <button onClick={cancelEdit} style={{ marginLeft: '10px' }}>Cancel</button>
        )}
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ backgroundColor: '#f0f0f0' }}>
            <th style={{ border: '1px solid #ccc', padding: '8px', textAlign: 'left' }}>Title</th>
            <th style={{ border: '1px solid #ccc', padding: '8px', textAlign: 'left' }}>Author</th>
            <th style={{ border: '1px solid #ccc', padding: '8px', textAlign: 'left' }}>Year</th>
            <th style={{ border: '1px solid #ccc', padding: '8px', textAlign: 'left' }}>Read</th>
            <th style={{ border: '1px solid #ccc', padding: '8px', textAlign: 'left' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.map(book => (
            <tr key={book.id}>
              <td style={{ border: '1px solid #ccc', padding: '8px' }}>{book.title}</td>
              <td style={{ border: '1px solid #ccc', padding: '8px' }}>{book.author}</td>
              <td style={{ border: '1px solid #ccc', padding: '8px' }}>{book.year || ''}</td>
              <td style={{ border: '1px solid #ccc', padding: '8px' }}>
                <button
                  type="button"
                  onClick={() => handleToggleRead(book)}
                  aria-label="Toggle read status"
                  data-testid="toggle-read"
                >
                  {book.read ? 'Yes' : 'No'}
                </button>
              </td>
              <td style={{ border: '1px solid #ccc', padding: '8px' }}>
                <button onClick={() => startEdit(book)} style={{ marginRight: '5px' }}>Edit</button>
                <button onClick={() => handleDelete(book.id)} style={{ color: 'red' }}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;
```