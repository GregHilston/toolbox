

### server/package.json
```json
{
  "name": "server",
  "version": "1.0.0",
  "description": "Book Manager API",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "sql.js": "^1.10.1"
  }
}
```

### server/index.js
```javascript
const express = require('express');
const initSqlJs = require('sql.js');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;
const DB_PATH = path.join(__dirname, 'data.db');

app.use(express.json());

async function initDatabase() {
  const SQL = await initSqlJs();
  let db;

  try {
    if (fs.existsSync(DB_PATH)) {
      const fileBuffer = fs.readFileSync(DB_PATH);
      db = new SQL.Database(fileBuffer);
    } else {
      db = new SQL.Database();
    }
  } catch (err) {
    console.error("Failed to load database:", err);
    process.exit(1);
  }

  // Create table
  try {
    db.run(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        read BOOLEAN DEFAULT 0
      )
    `);
  } catch (err) {
    console.error("Failed to create table:", err);
    process.exit(1);
  }

  function save() {
    const data = db.export();
    const buffer = Buffer.from(data);
    fs.writeFileSync(DB_PATH, buffer);
  }

  function parseResult(result) {
    if (result.length === 0 || result[0].values.length === 0) {
      return null;
    }
    const columns = result[0].columns;
    const row = result[0].values[0];
    const book = {};
    columns.forEach((col, index) => {
      let val = row[index];
      if (col === 'id') book.id = val;
      else if (col === 'title') book.title = val;
      else if (col === 'author') book.author = val;
      else if (col === 'year') book.year = val;
      else if (col === 'read') book.read = val === 1;
    });
    return book;
  }

  // GET /api/books
  app.get('/api/books', (req, res) => {
    try {
      const result = db.exec("SELECT * FROM books");
      const books = [];
      if (result.length > 0) {
        const columns = result[0].columns;
        const values = result[0].values;
        values.forEach(row => {
          const book = {};
          columns.forEach((col, index) => {
            let val = row[index];
            if (col === 'id') book.id = val;
            else if (col === 'title') book.title = val;
            else if (col === 'author') book.author = val;
            else if (col === 'year') book.year = val;
            else if (col === 'read') book.read = val === 1;
          });
          books.push(book);
        });
      }
      res.json(books);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // GET /api/books/:id
  app.get('/api/books/:id', (req, res) => {
    try {
      const id = parseInt(req.params.id, 10);
      const result = db.exec("SELECT * FROM books WHERE id = ?", [id]);
      const book = parseResult(result);
      if (!book) {
        return res.status(404).json({ error: 'Book not found' });
      }
      res.json(book);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // POST /api/books
  app.post('/api/books', (req, res) => {
    try {
      const { title, author, year, read } = req.body;
      if (!title || !author) {
        return res.status(400).json({ error: 'Title and Author are required' });
      }
      
      const resRun = db.run("INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)", 
                            [title, author, year || null, read ? 1 : 0]);
      const newId = resRun.lastID;
      
      const result = db.exec("SELECT * FROM books WHERE id = ?", [newId]);
      const book = parseResult(result);
      if (!book) {
         return res.status(500).json({ error: 'Failed to retrieve new book' });
      }
      save();
      res.status(201).json(book);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // PUT /api/books/:id
  app.put('/api/books/:id', (req, res) => {
    try {
      const { title, author, year, read } = req.body;
      const id = parseInt(req.params.id, 10);
      
      if (!title || !author) {
        return res.status(400).json({ error: 'Title and Author are required' });
      }

      const checkRes = db.exec("SELECT * FROM books WHERE id = ?", [id]);
      if (!parseResult(checkRes)) {
        return res.status(404).json({ error: 'Book not found' });
      }

      db.run("UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?", 
             [title, author, year || null, read ? 1 : 0, id]);
      
      const result = db.exec("SELECT * FROM books WHERE id = ?", [id]);
      const book = parseResult(result);
      save();
      res.json(book);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // DELETE /api/books/:id
  app.delete('/api/books/:id', (req, res) => {
    try {
      const id = parseInt(req.params.id, 10);
      const resRun = db.run("DELETE FROM books WHERE id = ?", [id]);
      if (resRun.changes === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }
      save();
      res.json({ message: 'Book deleted' });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}

initDatabase().catch(err => {
  console.error("Failed to start server:", err);
  process.exit(1);
});
```

### client/src/App.jsx
```jsx
import { useState, useEffect } from 'react';

const API_URL = '/api/books';

function App() {
  const [books, setBooks] = useState([]);
  const [formData, setFormData] = useState({ title: '', author: '', year: '', read: false });
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');

  const fetchBooks = async () => {
    try {
      const res = await fetch(API_URL);
      if (!res.ok) {
        throw new Error('Failed to fetch books');
      }
      const data = await res.json();
      setBooks(data);
    } catch (err) {
      console.error('Failed to fetch books', err);
    }
  };

  useEffect(() => {
    fetchBooks();
  }, []);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!formData.title.trim() || !formData.author.trim()) {
      setError('Title and Author are required.');
      return;
    }

    try {
      const url = editingId ? `${API_URL}/${editingId}` : API_URL;
      const method = editingId ? 'PUT' : 'POST';
      
      const payload = {
        title: formData.title,
        author: formData.author,
        year: formData.year ? parseInt(formData.year, 10) : null,
        read: formData.read
      };

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Request failed');
      }

      fetchBooks();
      setFormData({ title: '', author: '', year: '', read: false });
      setEditingId(null);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEdit = (book) => {
    setFormData({
      title: book.title,
      author: book.author,
      year: book.year ? String(book.year) : '',
      read: book.read
    });
    setEditingId(book.id);
    setError('');
  };

  const handleCancel = () => {
    setFormData({ title: '', author: '', year: '', read: false });
    setEditingId(null);
    setError('');
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this book?')) return;
    
    try {
      const res = await fetch(`${API_URL}/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Delete failed');
      }
      fetchBooks();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleToggleRead = async (book) => {
    try {
      const res = await fetch(`${API_URL}/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: book.title,
          author: book.author,
          year: book.year,
          read: !book.read
        })
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Update failed');
      }
      
      fetchBooks();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>Book Manager</h1>
      
      {error && <div style={{ color: 'red', marginBottom: '10px' }}>{error}</div>}

      <form onSubmit={handleSubmit} style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ccc', borderRadius: '5px' }}>
        <h2>{editingId ? 'Edit Book' : 'Add New Book'}</h2>
        <div style={{ marginBottom: '10px' }}>
          <label>Title: </label>
          <input name="title" value={formData.title} onChange={handleChange} required style={{ width: '100%', padding: '5px' }} />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Author: </label>
          <input name="author" value={formData.author} onChange={handleChange} required style={{ width: '100%', padding: '5px' }} />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Year: </label>
          <input name="year" type="number" value={formData.year} onChange={handleChange} style={{ width: '100%', padding: '5px' }} />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            <input type="checkbox" name="read" checked={formData.read} onChange={handleChange} /> Read
          </label>
        </div>
        <button type="submit" style={{ padding: '8px 16px', cursor: 'pointer' }}>
          {editingId ? 'Update Book' : 'Add Book'}
        </button>
        {editingId && (
          <button type="button" onClick={handleCancel} style={{ marginLeft: '10px', padding: '8px 16px' }}>
            Cancel
          </button>
        )}
      </form>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ backgroundColor: '#f4f4f4', textAlign: 'left' }}>
            <th style={{ padding: '10px', borderBottom: '2px solid #ddd' }}>Title</th>
            <th style={{ padding: '10px', borderBottom: '2px solid #ddd' }}>Author</th>
            <th style={{ padding: '10px', borderBottom: '2px solid #ddd' }}>Year</th>
            <th style={{ padding: '10px', borderBottom: '2px solid #ddd' }}>Read</th>
            <th style={{ padding: '10px', borderBottom: '2px solid #ddd' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.length === 0 ? (
            <tr><td colSpan="5" style={{ padding: '20px', textAlign: 'center' }}>No books found.</td></tr>
          ) : (
            books.map(book => (
              <tr key={book.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '10px' }}>{book.title}</td>
                <td style={{ padding: '10px' }}>{book.author}</td>
                <td style={{ padding: '10px' }}>{book.year || '-'}</td>
                <td style={{ padding: '10px' }}>
                  <button 
                    onClick={() => handleToggleRead(book)}
                    style={{ 
                      padding: '4px 8px', 
                      backgroundColor: book.read ? '#4CAF50' : '#f44336',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    {book.read ? 'Yes' : 'No'}
                  </button>
                </td>
                <td style={{ padding: '10px' }}>
                  <button 
                    onClick={() => handleEdit(book)}
                    style={{ marginRight: '5px', padding: '4px 8px', cursor: 'pointer' }}
                  >
                    Edit
                  </button>
                  <button 
                    onClick={() => handleDelete(book.id)}
                    style={{ padding: '4px 8px', backgroundColor: '#ff4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                  >
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

export default App;
```