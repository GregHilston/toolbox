

### README.md
```markdown
# Book Manager CRUD App

A full-stack CRUD application for managing books.

## Prerequisites
- Node.js (v18 or later)
- npm

## Backend Setup (Server)

1. Navigate to the `server` directory:
   ```bash
   cd server
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the server (defaults to port 3001):
   ```bash
   npm start
   ```
   The API will be available at `http://localhost:3001`.

## Frontend Setup (Client)

1. Navigate to the `client` directory:
   ```bash
   cd client
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   The UI will be available at `http://localhost:5173` (or whatever port Vite picks). It proxies API requests to the backend.

## Building for Production

To build the frontend for production deployment:
```bash
cd client
npm run build
```

## API Endpoints

- `GET /api/books`: Get all books.
- `GET /api/books/:id`: Get a specific book.
- `POST /api/books`: Create a new book.
- `PUT /api/books/:id`: Update an existing book.
- `DELETE /api/books/:id`: Delete a book.

All inputs (title, author) are validated. Missing required fields return HTTP 400.
```

### server/package.json
```json
{
  "name": "book-server",
  "version": "1.0.0",
  "description": "Backend for Books CRUD",
  "main": "index.js",
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

// Initialize SQLite database
const dbPath = path.join(__dirname, 'data.db');
const db = new Database(dbPath);

// Create table if it doesn't exist
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    read INTEGER DEFAULT 0
  )
`);

// Helper to format the 'read' field as boolean
const formatBook = (book) => ({
  ...book,
  read: Boolean(book.read)
});

// GET /api/books - Get all books
app.get('/api/books', (req, res) => {
  try {
    const books = db.prepare('SELECT * FROM books').all();
    res.json(books.map(formatBook));
  } catch (err) {
    res.status(500).json({ error: 'Database error' });
  }
});

// GET /api/books/:id - Get a specific book
app.get('/api/books/:id', (req, res) => {
  try {
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json(formatBook(book));
  } catch (err) {
    res.status(500).json({ error: 'Database error' });
  }
});

// POST /api/books - Create a new book
app.post('/api/books', (req, res) => {
  try {
    const { title, author, year, read } = req.body;

    if (!title || typeof title !== 'string' || title.trim() === '') {
      return res.status(400).json({ error: 'Title is required' });
    }
    if (!author || typeof author !== 'string' || author.trim() === '') {
      return res.status(400).json({ error: 'Author is required' });
    }

    const stmt = db.prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)');
    const result = stmt.run(title.trim(), author.trim(), year || null, read ? 1 : 0);
    
    const newBook = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
    res.status(201).json(formatBook(newBook));
  } catch (err) {
    res.status(500).json({ error: 'Database error' });
  }
});

// PUT /api/books/:id - Update an existing book
app.put('/api/books/:id', (req, res) => {
  try {
    const { title, author, year, read } = req.body;
    const id = req.params.id;

    // Check existence first
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }

    if (!title || typeof title !== 'string' || title.trim() === '') {
      return res.status(400).json({ error: 'Title is required' });
    }
    if (!author || typeof author !== 'string' || author.trim() === '') {
      return res.status(400).json({ error: 'Author is required' });
    }

    const stmt = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?');
    stmt.run(title.trim(), author.trim(), year || null, read ? 1 : 0, id);
    
    const updatedBook = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    res.json(formatBook(updatedBook));
  } catch (err) {
    res.status(500).json({ error: 'Database error' });
  }
});

// DELETE /api/books/:id - Delete a book
app.delete('/api/books/:id', (req, res) => {
  try {
    const id = req.params.id;
    const result = db.prepare('DELETE FROM books WHERE id = ?').run(id);
    if (result.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json({ message: 'Book deleted' });
  } catch (err) {
    res.status(500).json({ error: 'Database error' });
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
  "name": "book-client",
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
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0"
  }
}
```

### client/vite.config.js
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

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
})
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
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './App.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

### client/src/App.jsx
```jsx
import React, { useState, useEffect } from 'react';

const API_URL = '/api/books';

function App() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Form state
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [year, setYear] = useState('');
  const [read, setRead] = useState(false);
  const [editingId, setEditingId] = useState(null);

  const fetchBooks = async () => {
    try {
      const res = await fetch(API_URL);
      if (!res.ok) throw new Error('Failed to fetch');
      const data = await res.json();
      setBooks(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBooks();
  }, []);

  const resetForm = () => {
    setTitle('');
    setAuthor('');
    setYear('');
    setRead(false);
    setEditingId(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !author.trim()) {
      alert('Title and Author are required.');
      return;
    }

    const payload = {
      title: title.trim(),
      author: author.trim(),
      year: year ? parseInt(year, 10) : null,
      read: read
    };

    try {
      let res;
      if (editingId) {
        res = await fetch(`${API_URL}/${editingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Operation failed');
      }

      const updatedBook = await res.json();
      
      if (editingId) {
        setBooks(books.map(b => b.id === editingId ? updatedBook : b));
      } else {
        setBooks([...books, updatedBook]);
      }
      
      resetForm();
      fetchBooks(); // Refresh list to ensure consistency
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEdit = (book) => {
    setTitle(book.title);
    setAuthor(book.author);
    setYear(book.year || '');
    setRead(book.read);
    setEditingId(book.id);
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure?')) return;
    try {
      const res = await fetch(`${API_URL}/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
      setBooks(books.filter(b => b.id !== id));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleToggleRead = async (book) => {
    const newRead = !book.read;
    try {
      const res = await fetch(`${API_URL}/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...book, read: newRead })
      });
      if (!res.ok) throw new Error('Update failed');
      const updatedBook = await res.json();
      setBooks(books.map(b => b.id === book.id ? updatedBook : b));
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <div className="container">Loading...</div>;
  if (error) return <div className="container error">Error: {error}</div>;

  return (
    <div className="container">
      <h1>Book Manager</h1>
      
      <form onSubmit={handleSubmit} className="book-form">
        <h2>{editingId ? 'Edit Book' : 'Add New Book'}</h2>
        <div className="form-group">
          <label>Title</label>
          <input 
            type="text" 
            value={title} 
            onChange={e => setTitle(e.target.value)} 
            required 
            placeholder="Enter title"
          />
        </div>
        <div className="form-group">
          <label>Author</label>
          <input 
            type="text" 
            value={author} 
            onChange={e => setAuthor(e.target.value)} 
            required 
            placeholder="Enter author"
          />
        </div>
        <div className="form-group">
          <label>Year (Optional)</label>
          <input 
            type="number" 
            value={year} 
            onChange={e => setYear(e.target.value)} 
            placeholder="e.g. 2023"
          />
        </div>
        <div className="form-group checkbox-group">
          <label>
            <input 
              type="checkbox" 
              checked={read} 
              onChange={e => setRead(e.target.checked)} 
            /> Read
          </label>
        </div>
        <div className="form-actions">
          <button type="submit">{editingId ? 'Update' : 'Add Book'}</button>
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
          {books.length === 0 ? (
            <tr><td colSpan="5">No books found.</td></tr>
          ) : (
            books.map(book => (
              <tr key={book.id}>
                <td>{book.title}</td>
                <td>{book.author}</td>
                <td>{book.year || '-'}</td>
                <td>
                  <input 
                    type="checkbox" 
                    checked={book.read} 
                    onChange={() => handleToggleRead(book)}
                  />
                </td>
                <td>
                  <button onClick={() => handleEdit(book)}>Edit</button>
                  <button onClick={() => handleDelete(book.id)} className="delete-btn">Delete</button>
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

### client/src/App.css
```css
body {
  font-family: sans-serif;
  background-color: #f4f4f9;
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

h1, h2 {
  color: #333;
}

.book-form {
  margin-bottom: 30px;
  padding: 15px;
  background: #fafafa;
  border: 1px solid #ddd;
  border-radius: 4px;
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
  box-sizing: border-box;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: normal;
}

.form-actions {
  display: flex;
  gap: 10px;
}

button {
  padding: 8px 16px;
  cursor: pointer;
  border: none;
  border-radius: 4px;
  background-color: #007bff;
  color: white;
  font-size: 14px;
}

button:hover {
  background-color: #0056b3;
}

button.delete-btn {
  background-color: #dc3545;
}

button.delete-btn:hover {
  background-color: #a71d2a;
}

button[type="button"] {
  background-color: #6c757d;
}

.book-table {
  width: 100%;
  border-collapse: collapse;
}

.book-table th, .book-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.book-table th {
  background-color: #f8f9fa;
}

.error {
  color: red;
}
```