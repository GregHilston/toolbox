

### README.md
```markdown
# Book Manager CRUD App

A full-stack CRUD web application for managing books.

## Prerequisites

- Node.js 18+ (or Node.js 26 as specified)
- npm

## Setup & Run

### Backend (API Server)

```bash
cd server
npm install
npm start
```

The API server will start on port 3001 (or the port specified by the `PORT` environment variable).

### Frontend (React UI)

```bash
cd client
npm install
npm run dev
```

The Vite dev server will start on port 5173 (default) and proxy `/api` requests to `http://localhost:3001`.

### Build Frontend

```bash
cd client
npm install
npm run build
```

## API Endpoints

- `GET /api/books` - List all books
- `GET /api/books/:id` - Get a single book
- `POST /api/books` - Create a new book
- `PUT /api/books/:id` - Update a book
- `DELETE /api/books/:id` - Delete a book

All endpoints return JSON. POST and PUT require `title` and `author` fields (non-empty strings). Missing or invalid IDs return 404. Validation errors return 400.
```

### server/package.json
```json
{
  "name": "book-manager-server",
  "version": "1.0.0",
  "description": "REST API for book management",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "better-sqlite3": "^11.7.0",
    "cors": "^2.8.5",
    "express": "^4.21.2"
  }
}
```

### server/index.js
```javascript
const express = require('express');
const cors = require('cors');
const Database = require('better-sqlite3');
const path = require('path');

const app = express();
const port = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

const dbPath = path.join(__dirname, 'data.db');
const db = new Database(dbPath);

// Initialize database schema
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read BOOLEAN DEFAULT 0
  )
`);

// Helper to normalize boolean read field
const normalizeBook = (book) => ({
  ...book,
  read: !!book.read
});

// GET /api/books
app.get('/api/books', (req, res) => {
  const books = db.prepare('SELECT * FROM books').all().map(normalizeBook);
  res.json(books);
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }
  res.json(normalizeBook(book));
});

// POST /api/books
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;
  
  if (!title || !author || title.trim() === '' || author.trim() === '') {
    return res.status(400).json({ error: 'Title and author are required' });
  }
  
  const stmt = db.prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)');
  const result = stmt.run(title, author, year || null, read ? 1 : 0);
  
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
  res.status(201).json(normalizeBook(book));
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const { title, author, year, read } = req.body;
  
  if (!title || !author || title.trim() === '' || author.trim() === '') {
    return res.status(400).json({ error: 'Title and author are required' });
  }
  
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }
  
  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?')
    .run(title, author, year || null, read ? 1 : 0, req.params.id);
  
  const updated = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  res.json(normalizeBook(updated));
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }
  
  db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
  res.json({ success: true });
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
```

### client/package.json
```json
{
  "name": "book-manager-client",
  "private": true,
  "version": "1.0.0",
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
    "vite": "^5.0.0"
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
        changeOrigin: true
      }
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
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
  padding: 20px;
}

.container {
  max-width: 900px;
  margin: 0 auto;
  background: white;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

h1 {
  margin-bottom: 20px;
  color: #2c3e50;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  margin-right: 8px;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-success {
  background: #2ecc71;
  color: white;
}

.btn-warning {
  background: #f39c12;
  color: white;
}

.btn-danger {
  background: #e74c3c;
  color: white;
}

.btn-secondary {
  background: #95a5a6;
  color: white;
}

.btn:hover {
  opacity: 0.9;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

th, td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  background: #f8f9fa;
  font-weight: 600;
}

tr:hover {
  background: #f8f9fa;
}

.error {
  color: #e74c3c;
  margin-bottom: 15px;
  padding: 10px;
  background: #fde8e8;
  border-radius: 4px;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
```

### client/src/App.jsx
```jsx
import React, { useState, useEffect } from 'react';

function App() {
  const [books, setBooks] = useState([]);
  const [formData, setFormData] = useState({ title: '', author: '', year: '', read: false });
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchBooks = async () => {
    try {
      const res = await fetch('/api/books');
      if (!res.ok) throw new Error('Failed to fetch books');
      const data = await res.json();
      setBooks(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
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
    
    try {
      const url = editingId ? `/api/books/${editingId}` : '/api/books';
      const method = editingId ? 'PUT' : 'POST';
      
      const body = {
        title: formData.title,
        author: formData.author,
        year: formData.year ? parseInt(formData.year) : null,
        read: formData.read
      };

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Request failed');
      }

      await fetchBooks();
      resetForm();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEdit = (book) => {
    setFormData({
      title: book.title,
      author: book.author,
      year: book.year || '',
      read: !!book.read
    });
    setEditingId(book.id);
    setError('');
  };

  const handleCancel = () => {
    resetForm();
  };

  const resetForm = () => {
    setFormData({ title: '', author: '', year: '', read: false });
    setEditingId(null);
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this book?')) return;
    
    try {
      const res = await fetch(`/api/books/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete book');
      await fetchBooks();
    } catch (err) {
      setError(err.message);
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
      
      if (!res.ok) throw new Error('Failed to update read status');
      await fetchBooks();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <div className="container"><p>Loading...</p></div>;

  return (
    <div className="container">
      <h1>{editingId ? 'Edit Book' : 'Book Manager'}</h1>
      
      {error && <div className="error">{error}</div>}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="title">Title *</label>
          <input
            type="text"
            id="title"
            name="title"
            value={formData.title}
            onChange={handleChange}
            required
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="author">Author *</label>
          <input
            type="text"
            id="author"
            name="author"
            value={formData.author}
            onChange={handleChange}
            required
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="year">Year</label>
          <input
            type="number"
            id="year"
            name="year"
            value={formData.year}
            onChange={handleChange}
            placeholder="e.g., 2023"
          />
        </div>
        
        <div className="form-group">
          <label>
            <input
              type="checkbox"
              name="read"
              checked={formData.read}
              onChange={handleChange}
            />
            {' '}Read
          </label>
        </div>
        
        <button type="submit" className="btn btn-primary">
          {editingId ? 'Update Book' : 'Add Book'}
        </button>
        
        {editingId && (
          <button type="button" onClick={handleCancel} className="btn btn-secondary">
            Cancel
          </button>
        )}
      </form>
      
      <table>
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
          {books.length === 0 ? (
            <tr>
              <td colSpan="5" style={{ textAlign: 'center', padding: '20px' }}>
                No books found. Add one above!
              </td>
            </tr>
          ) : (
            books.map(book => (
              <tr key={book.id}>
                <td>{book.title}</td>
                <td>{book.author}</td>
                <td>{book.year || '-'}</td>
                <td>
                  <span style={{ color: book.read ? 'green' : 'red', fontWeight: 500 }}>
                    {book.read ? 'Yes' : 'No'}
                  </span>
                </td>
                <td className="actions">
                  <button onClick={() => handleEdit(book)} className="btn btn-warning">Edit</button>
                  <button onClick={() => handleToggleRead(book)} className="btn btn-success">
                    {book.read ? 'Mark Unread' : 'Mark Read'}
                  </button>
                  <button onClick={() => handleDelete(book.id)} className="btn btn-danger">Delete</button>
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