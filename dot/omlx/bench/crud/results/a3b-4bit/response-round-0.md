

### README.md
```markdown
# Book Manager Full-Stack App

This project consists of a Node.js backend API and a React frontend.

## Prerequisites
- Node.js (v18 or higher recommended, though specified as 26)
- npm

## Backend (Server)
The backend is located in the `server/` directory. It uses Express and SQLite.

1. Navigate to the server directory:
   ```bash
   cd server
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the server:
   ```bash
   npm start
   ```
   The server will listen on port 3001 by default (or the value of the `PORT` environment variable).

## Frontend (Client)
The frontend is located in the `client/` directory. It uses React and Vite.

1. Navigate to the client directory:
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
   The Vite dev server will start (usually on port 5173) and proxy API requests to the backend.

4. To build for production:
   ```bash
   npm run build
   ```
```

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
const PORT = process.env.PORT || 3001;
const db = new Database(path.join(__dirname, 'data.db'));

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

app.use(express.json());

// GET /api/books
app.get('/api/books', (req, res) => {
  const books = db.prepare('SELECT * FROM books').all();
  res.json(books);
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }
  res.json(book);
});

// POST /api/books
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;

  if (!title || !author) {
    return res.status(400).json({ error: 'Title and Author are required' });
  }

  const stmt = db.prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)');
  const result = stmt.run(title, author, year || null, read ? 1 : 0);
  
  const newBook = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
  res.status(201).json(newBook);
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const { title, author, year, read } = req.body;
  const id = req.params.id;

  const existingBook = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!existingBook) {
    return res.status(404).json({ error: 'Book not found' });
  }

  if (!title || !author) {
    return res.status(400).json({ error: 'Title and Author are required' });
  }

  const stmt = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?');
  stmt.run(title, author, year || null, read ? 1 : 0, id);
  
  const updatedBook = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  res.json(updatedBook);
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  const id = req.params.id;
  const result = db.prepare('DELETE FROM books WHERE id = ?').run(id);
  
  if (result.changes === 0) {
    return res.status(404).json({ error: 'Book not found' });
  }
  
  res.json({ message: 'Book deleted' });
});

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
    "@types/react": "^18.2.15",
    "@types/react-dom": "^18.2.7",
    "@vitejs/plugin-react": "^4.0.3",
    "vite": "^4.4.5"
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

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
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