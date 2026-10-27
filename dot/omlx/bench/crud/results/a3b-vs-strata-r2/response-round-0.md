

### README.md
```markdown
# Books CRUD App

## Prerequisites
- Node.js (v18 or later)
- npm

## Setup

### Backend
```bash
cd server
npm install
npm start
```
The API will start on port 3001 (or the port specified by the `PORT` environment variable).

### Frontend
```bash
cd client
npm install
npm run dev
```
The Vite dev server will start, proxying API requests to the backend.

## Usage
- View books in the table.
- Click "Add Book" to create a new entry.
- Click "Edit" to modify an existing book.
- Toggle the "Read" checkbox to update reading status.
- Click "Delete" to remove a book.
```

### server/package.json
```json
{
  "name": "server",
  "version": "1.0.0",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "better-sqlite3": "^9.4.3"
  }
}
```

### server/index.js
```javascript
const express = require('express');
const Database = require('better-sqlite3');
const path = require('path');

const app = express();
app.use(express.json());

const dbPath = path.join(__dirname, 'data.db');
const db = new Database(dbPath);

// Enable WAL mode for better concurrency
db.pragma('journal_mode = WAL');

// Initialize Database Schema
const createTableSql = `
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read BOOLEAN DEFAULT 0
  )
`;
db.exec(createTableSql);

// GET /api/books
app.get('/api/books', (req, res) => {
  try {
    const books = db.prepare('SELECT * FROM books').all();
    res.json(books);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/books/:id
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

// POST /api/books
app.post('/api/books', (req, res) => {
  try {
    const { title, author, year, read } = req.body;

    // Validation
    if (!title || title.trim() === '') {
      return res.status(400).json({ error: 'Title is required' });
    }
    if (!author || author.trim() === '') {
      return res.status(400).json({ error: 'Author is required' });
    }

    const stmt = db.prepare(`
      INSERT INTO books (title, author, year, read)
      VALUES (@title, @author, @year, @read)
    `);
    
    const result = stmt.run({
      title: title.trim(),
      author: author.trim(),
      year: year ? parseInt(year) : null,
      read: read ? 1 : 0
    });

    // Fetch the inserted book to return the ID
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
    res.status(201).json(book);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  try {
    const { title, author, year, read } = req.body;
    const id = req.params.id;

    // Check if book exists
    const existingBook = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    if (!existingBook) {
      return res.status(404).json({ error: 'Book not found' });
    }

    // Validation
    if (!title || title.trim() === '') {
      return res.status(400).json({ error: 'Title is required' });
    }
    if (!author || author.trim() === '') {
      return res.status(400).json({ error: 'Author is required' });
    }

    const stmt = db.prepare(`
      UPDATE books
      SET title = @title, author = @author, year = @year, read = @read
      WHERE id = @id
    `);

    stmt.run({
      id: id,
      title: title.trim(),
      author: author.trim(),
      year: year ? parseInt(year) : null,
      read: read ? 1 : 0
    });

    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    res.json(book);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  try {
    const id = req.params.id;
    const existingBook = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    if (!existingBook) {
      return res.status(404).json({ error: 'Book not found' });
    }

    db.prepare('DELETE FROM books WHERE id = ?').run(id);
    res.json({ message: 'Book deleted' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

### client/package.json
```json
{
  "name": "client",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.0.0",
    "vite": "^4.4.0"
  }
}
```

### client/vite.config.js
```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
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
    <title>Book Manager</title>
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

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### client/src/App.jsx
```jsx
import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [books, setBooks] = useState([]);
  const [formData, setFormData] = useState({ title: '', author: '', year: '', read: false });
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch books on mount
  useEffect(() => {
    fetchBooks();
  }, []);

  const fetchBooks = async () => {
    try {
      const res = await fetch('/api/books');
      if (!res.ok) throw new Error('Failed to fetch books');
      const data = await res.json();
      setBooks(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const url = editingId ? `/api/books/${editingId}` : '/api/books';
      const method = editingId ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Request failed');
      }

      const newBook = await res.json();
      
      if (editingId) {
        setBooks(books.map(b => b.id === editingId ? newBook : b));
        setEditingId(null);
      } else {
        setBooks([...books, newBook]);
      }
      
      resetForm();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this book?')) return;
    
    try {
      const res = await fetch(`/api/books/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error);
      }
      setBooks(books.filter(b => b.id !== id));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEdit = (book) => {
    setFormData({
      title: book.title,
      author: book.author,
      year: book.year || '',
      read: book.read
    });
    setEditingId(book.id);
  };

  const handleToggleRead = async (book) => {
    const updatedBook = { ...book, read: !book.read };
    try {
      const res = await fetch(`/api/books/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedBook),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error);
      }
      const data = await res.json();
      setBooks(books.map(b => b.id === book.id ? data : b));
    } catch (err) {
      setError(err.message);
    }
  };

  const resetForm = () => {
    setFormData({ title: '', author: '', year: '', read: false });
    setEditingId(null);
  };

  return (
    <div className="container">
      <h1>Book Manager</h1>
      
      {error && <div className="error-message">{error}</div>}

      <form onSubmit={handleSubmit} className="book-form">
        <h2>{editingId ? 'Edit Book' : 'Add New Book'}</h2>
        <div className="form-group">
          <label>Title *</label>
          <input
            type="text"
            name="title"
            value={formData.title}
            onChange={handleInputChange}
            required
          />
        </div>
        <div className="form-group">
          <label>Author *</label>
          <input
            type="text"
            name="author"
            value={formData.author}
            onChange={handleInputChange}
            required
          />
        </div>
        <div className="form-group">
          <label>Year</label>
          <input
            type="number"
            name="year"
            value={formData.year}
            onChange={handleInputChange}
            placeholder="Optional"
          />
        </div>
        <div className="form-group checkbox-group">
          <label>
            <input
              type="checkbox"
              name="read"
              checked={formData.read}
              onChange={handleInputChange}
            />
            Read
          </label>
        </div>
        <div className="form-actions">
          <button type="submit" disabled={loading}>
            {loading ? 'Saving...' : (editingId ? 'Update Book' : 'Add Book')}
          </button>
          {editingId && (
            <button type="button" onClick={resetForm}>Cancel</button>
          )}
        </div>
      </form>

      <table className="book-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Author</th>
            <th>Year</th>
            <th>Read</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.map(book => (
            <tr key={book.id}>
              <td>{book.title}</td>
              <td>{book.author}</td>
              <td>{book.year || '-'}</td>
              <td>
                <input
                  type="checkbox"
                  checked={!!book.read}
                  onChange={() => handleToggleRead(book)}
                />
              </td>
              <td className="actions">
                <button onClick={() => handleEdit(book)}>Edit</button>
                <button onClick={() => handleDelete(book.id)} className="delete-btn">Delete</button>
              </td>
            </tr>
          ))}
          {books.length === 0 && (
            <tr>
              <td colSpan="5" className="no-books">No books found. Add one above!</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default App;
```

### client/src/App.css
```css
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  background-color: #f4f4f9;
  color: #333;
  margin: 0;
  padding: 20px;
}

.container {
  max-width: 900px;
  margin: 0 auto;
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

h1 {
  text-align: center;
  color: #2c3e50;
}

.book-form {
  background: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid #e0e0e0;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-group input[type="text"],
.form-group input[type="number"] {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  font-weight: normal;
  cursor: pointer;
}

.checkbox-group input {
  margin-right: 10px;
}

.form-actions {
  display: flex;
  gap: 10px;
}

button {
  padding: 10px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

button[type="submit"] {
  background-color: #27ae60;
  color: white;
}

button[type="submit"]:disabled {
  background-color: #95a5a6;
  cursor: not-allowed;
}

button[type="button"] {
  background-color: #95a5a6;
  color: white;
}

button.delete-btn {
  background-color: #e74c3c;
  color: white;
  margin-left: 5px;
}

button:hover:not(:disabled) {
  opacity: 0.9;
}

.book-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

.book-table th,
.book-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.book-table th {
  background-color: #2c3e50;
  color: white;
}

.book-table tr:hover {
  background-color: #f1f1f1;
}

.actions button {
  margin-right: 5px;
}

.error-message {
  background-color: #f8d7da;
  color: #721c24;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 20px;
  text-align: center;
}

.no-books {
  text-align: center;
  color: #7f8c8d;
  padding: 20px;
}
```