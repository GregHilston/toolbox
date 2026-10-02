Here are the full contents of the files required to build the application.

### README.md
```markdown
# Books CRUD App

A full-stack CRUD application for managing books using Node.js, Express, SQLite, and React.

## Prerequisites
- Node.js (v18+)
- npm

## Setup and Run

### Backend (Server)
Navigate to the `server` directory:
```bash
cd server
npm install
npm start
```
The API will be available at `http://localhost:3001`.

### Frontend (Client)
Open a new terminal and navigate to the `client` directory:
```bash
cd client
npm install
npm run dev
```
The UI will be available at `http://localhost:5173` (default Vite port).

## Testing
To build the frontend for production:
```bash
cd client
npm run build
```
```

### server/package.json
```json
{
  "name": "server",
  "version": "1.0.0",
  "description": "Backend API for Books CRUD",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "better-sqlite3": "^9.4.3",
    "cors": "^2.8.5",
    "express": "^4.18.2"
  }
}
```

### server/index.js
```javascript
const express = require('express');
const Database = require('better-sqlite3');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(express.json());
app.use(cors());

// Database Setup
const DB_PATH = path.join(__dirname, 'data.db');
const db = new Database(DB_PATH);

// Initialize Table
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read BOOLEAN DEFAULT 0
  )
`);

// --- Endpoints ---

// GET /api/books
app.get('/api/books', (req, res) => {
  try {
    const books = db.prepare('SELECT * FROM books').all();
    // Ensure boolean representation is clean
    const formattedBooks = books.map(book => ({
      ...book,
      read: !!book.read
    }));
    res.json(formattedBooks);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const id = req.params.id;
  try {
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json({
      ...book,
      read: !!book.read
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

// POST /api/books
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;

  // Validation
  if (!title || title.trim() === '') {
    return res.status(400).json({ error: 'Title is required' });
  }
  if (!author || author.trim() === '') {
    return res.status(400).json({ error: 'Author is required' });
  }

  try {
    const stmt = db.prepare(`
      INSERT INTO books (title, author, year, read)
      VALUES (@title, @author, @year, @read)
    `);
    stmt.run({
      title: title.trim(),
      author: author.trim(),
      year: year || null,
      read: read ? 1 : 0
    });
    const newBook = db.prepare('SELECT * FROM books WHERE id = ?').get(db.lastInsertRowid);
    res.status(201).json({
      ...newBook,
      read: !!newBook.read
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const id = req.params.id;
  const { title, author, year, read } = req.body;

  // Validation
  if (!title || title.trim() === '') {
    return res.status(400).json({ error: 'Title is required' });
  }
  if (!author || author.trim() === '') {
    return res.status(400).json({ error: 'Author is required' });
  }

  try {
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }

    db.prepare(`
      UPDATE books
      SET title = @title, author = @author, year = @year, read = @read
      WHERE id = @id
    `).run({
      id: id,
      title: title.trim(),
      author: author.trim(),
      year: year || null,
      read: read ? 1 : 0
    });

    const updatedBook = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    res.json({
      ...updatedBook,
      read: !!updatedBook.read
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const id = req.params.id;

  try {
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }

    db.prepare('DELETE FROM books WHERE id = ?').run(id);
    res.json({ message: 'Book deleted' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

// Start Server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

### server/data.db
*(This file does not exist yet. It will be automatically created by `better-sqlite3` when `npm start` is run for the first time.)*

### client/package.json
```json
{
  "name": "client",
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
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8"
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
    <title>Books CRUD App</title>
    <style>
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
        background: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      }
      h1 {
        text-align: center;
        color: #2c3e50;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 20px;
      }
      th, td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #ddd;
      }
      th {
        background-color: #2c3e50;
        color: white;
      }
      tr:hover {
        background-color: #f1f1f1;
      }
      .btn {
        padding: 6px 12px;
        margin-right: 5px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
      }
      .btn-edit { background-color: #3498db; color: white; }
      .btn-delete { background-color: #e74c3c; color: white; }
      .btn-save { background-color: #27ae60; color: white; }
      .btn-cancel { background-color: #95a5a6; color: white; }
      .btn-toggle { background-color: #f39c12; color: white; }
      
      .form-group {
        margin-bottom: 15px;
      }
      .form-group label {
        display: block;
        margin-bottom: 5px;
        font-weight: bold;
      }
      .form-group input {
        width: 100%;
        padding: 8px;
        box-sizing: border-box;
        border: 1px solid #ddd;
        border-radius: 4px;
      }
      .error {
        color: #e74c3c;
        background-color: #fadbd8;
        padding: 10px;
        border-radius: 4px;
        margin-bottom: 15px;
      }
      .actions {
        text-align: right;
        margin-top: 20px;
      }
      .empty-msg {
        text-align: center;
        color: #7f8c8d;
        padding: 20px;
      }
    </style>
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

function App() {
  const [books, setBooks] = useState([]);
  const [error, setError] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({ title: '', author: '', year: '', read: false });

  // Fetch books on mount
  useEffect(() => {
    fetchBooks();
  }, []);

  const fetchBooks = async () => {
    try {
      const response = await fetch('/api/books');
      if (!response.ok) throw new Error('Failed to fetch books');
      const data = await response.json();
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

  const validateForm = () => {
    if (!formData.title.trim()) return 'Title is required';
    if (!formData.author.trim()) return 'Author is required';
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      const url = isEditing ? `/api/books/${editingId}` : '/api/books';
      const method = isEditing ? 'PUT' : 'POST';
      
      const payload = {
        title: formData.title,
        author: formData.author,
        year: formData.year ? parseInt(formData.year, 10) : null,
        read: formData.read
      };

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Operation failed');
      }

      await fetchBooks();
      resetForm();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this book?')) return;

    try {
      const response = await fetch(`/api/books/${id}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Delete failed');
      }

      await fetchBooks();
      if (editingId === id) resetForm();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEdit = (book) => {
    setFormData({
      title: book.title,
      author: book.author,
      year: book.year ? book.year : '',
      read: book.read
    });
    setEditingId(book.id);
    setIsEditing(true);
    setError(null);
  };

  const handleToggleRead = async (book) => {
    try {
      const response = await fetch(`/api/books/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: book.title,
          author: book.author,
          year: book.year,
          read: !book.read
        })
      });

      if (!response.ok) throw new Error('Failed to update read status');
      
      // Update local state immediately for better UX
      setBooks(prevBooks => prevBooks.map(b => 
        b.id === book.id ? { ...b, read: !b.read } : b
      ));
    } catch (err) {
      setError(err.message);
    }
  };

  const resetForm = () => {
    setFormData({ title: '', author: '', year: '', read: false });
    setEditingId(null);
    setIsEditing(false);
  };

  return (
    <div className="container">
      <h1>Books Manager</h1>

      {error && <div className="error">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Title</label>
          <input
            type="text"
            name="title"
            value={formData.title}
            onChange={handleInputChange}
            placeholder="Enter book title"
          />
        </div>
        <div className="form-group">
          <label>Author</label>
          <input
            type="text"
            name="author"
            value={formData.author}
            onChange={handleInputChange}
            placeholder="Enter author name"
          />
        </div>
        <div className="form-group">
          <label>Year (Optional)</label>
          <input
            type="number"
            name="year"
            value={formData.year}
            onChange={handleInputChange}
            placeholder="Publication Year"
          />
        </div>
        <div className="form-group">
          <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
            <input
              type="checkbox"
              name="read"
              checked={formData.read}
              onChange={handleInputChange}
              style={{ marginRight: '10px' }}
            />
            Read
          </label>
        </div>
        <div className="actions">
          <button type="submit" className="btn btn-save">
            {isEditing ? 'Update Book' : 'Add Book'}
          </button>
          {isEditing && (
            <button type="button" className="btn btn-cancel" onClick={resetForm}>
              Cancel
            </button>
          )}
        </div>
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
              <td colSpan="5" className="empty-msg">No books found. Add one above!</td>
            </tr>
          ) : (
            books.map(book => (
              <tr key={book.id}>
                <td>{book.title}</td>
                <td>{book.author}</td>
                <td>{book.year || '-'}</td>
                <td>
                  <button
                    className="btn btn-toggle"
                    onClick={() => handleToggleRead(book)}
                  >
                    {book.read ? 'Yes' : 'No'}
                  </button>
                </td>
                <td>
                  <button
                    className="btn btn-edit"
                    onClick={() => handleEdit(book)}
                  >
                    Edit
                  </button>
                  <button
                    className="btn btn-delete"
                    onClick={() => handleDelete(book.id)}
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