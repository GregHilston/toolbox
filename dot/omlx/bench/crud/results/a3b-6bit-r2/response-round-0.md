

### server/package.json
```json
{
  "name": "server",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "better-sqlite3": "^11.6.0",
    "express": "^4.21.2"
  }
}
```

### server/index.js
```javascript
import express from 'express';
import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

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
    read INTEGER DEFAULT 0
  )
`);

const parseYear = (year) => {
  if (year === '' || year === null || year === undefined) return null;
  const num = Number(year);
  return isNaN(num) ? null : num;
};

app.get('/api/books', (req, res) => {
  const books = db.prepare('SELECT * FROM books').all();
  res.json(books.map(b => ({ ...b, read: Boolean(b.read) })));
});

app.get('/api/books/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(404).json({ error: 'Book not found' });
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!book) return res.status(404).json({ error: 'Book not found' });
  res.json({ ...book, read: Boolean(book.read) });
});

app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;
  if (!title || !author) return res.status(400).json({ error: 'Title and author are required' });
  const stmt = db.prepare('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)');
  const result = stmt.run(title, author, parseYear(year), read ? 1 : 0);
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
  res.status(201).json({ ...book, read: Boolean(book.read) });
});

app.put('/api/books/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(404).json({ error: 'Book not found' });
  const { title, author, year, read } = req.body;
  if (!title || !author) return res.status(400).json({ error: 'Title and author are required' });
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });
  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?').run(title, author, parseYear(year), read ? 1 : 0, id);
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  res.json({ ...book, read: Boolean(book.read) });
});

app.delete('/api/books/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) return res.status(404).json({ error: 'Book not found' });
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Book not found' });
  db.prepare('DELETE FROM books WHERE id = ?').run(id);
  res.json({ message: 'Book deleted successfully' });
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
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.1"
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
import App from './App.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

### client/src/App.jsx
```jsx
import React, { useState, useEffect } from 'react';

const API_URL = '/api';

function App() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({ title: '', author: '', year: '', read: false });
  const [error, setError] = useState('');

  const fetchBooks = async () => {
    try {
      const res = await fetch(`${API_URL}/books`);
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

  const handleInputChange = (e) => {
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
      const res = await fetch(`${API_URL}/books${editingId ? `/${editingId}` : ''}`, {
        method: editingId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Failed to save book');
      }
      
      setFormData({ title: '', author: '', year: '', read: false });
      setEditingId(null);
      await fetchBooks();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEdit = (book) => {
    setEditingId(book.id);
    setFormData({
      title: book.title,
      author: book.author,
      year: book.year ?? '',
      read: book.read
    });
    setError('');
  };

  const handleCancel = () => {
    setEditingId(null);
    setFormData({ title: '', author: '', year: '', read: false });
    setError('');
  };

  const handleToggleRead = async (id) => {
    try {
      const book = books.find(b => b.id === id);
      if (!book) return;
      
      const res = await fetch(`${API_URL}/books/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...book, read: !book.read })
      });
      
      if (!res.ok) throw new Error('Failed to update');
      await fetchBooks();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this book?')) return;
    
    try {
      const res = await fetch(`${API_URL}/books/${id}`, {
        method: 'DELETE'
      });
      
      if (!res.ok) throw new Error('Failed to delete');
      await fetchBooks();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <div style={{ padding: '20px' }}>Loading...</div>;

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '20px', fontFamily: 'system-ui, sans-serif' }}>
      <h1>Book Manager</h1>
      
      {error && <div style={{ color: 'red', marginBottom: '10px', padding: '10px', background: '#ffe6e6', borderRadius: '4px' }}>{error}</div>}
      
      <form onSubmit={handleSubmit} style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ccc', borderRadius: '6px', background: '#f9f9f9' }}>
        <h3 style={{ marginTop: 0 }}>{editingId ? 'Edit Book' : 'Add New Book'}</h3>
        <div style={{ marginBottom: '10px' }}>
          <label>Title: </label>
          <input type="text" name="title" value={formData.title} onChange={handleInputChange} required style={{ width: '100%', padding: '6px', boxSizing: 'border-box' }} />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Author: </label>
          <input type="text" name="author" value={formData.author} onChange={handleInputChange} required style={{ width: '100%', padding: '6px', boxSizing: 'border-box' }} />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Year: </label>
          <input type="number" name="year" value={formData.year} onChange={handleInputChange} style={{ width: '100%', padding: '6px', boxSizing: 'border-box' }} />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            <input type="checkbox" name="read" checked={formData.read} onChange={handleInputChange} />
            {' '}Read
          </label>
        </div>
        <button type="submit" style={{ padding: '8px 16px', marginRight: '10px', cursor: 'pointer' }}>
          {editingId ? 'Update' : 'Add Book'}
        </button>
        {editingId && (
          <button type="button" onClick={handleCancel} style={{ padding: '8px 16px', cursor: 'pointer' }}>
            Cancel
          </button>
        )}
      </form>

      <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid #ccc' }}>
        <thead>
          <tr style={{ background: '#eee' }}>
            <th style={{ border: '1px solid #ccc', padding: '10px', textAlign: 'left' }}>Title</th>
            <th style={{ border: '1px solid #ccc', padding: '10px', textAlign: 'left' }}>Author</th>
            <th style={{ border: '1px solid #ccc', padding: '10px', textAlign: 'left' }}>Year</th>
            <th style={{ border: '1px solid #ccc', padding: '10px', textAlign: 'left' }}>Read</th>
            <th style={{ border: '1px solid #ccc', padding: '10px', textAlign: 'left' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {books.map(book => (
            <tr key={book.id}>
              <td style={{ border: '1px solid #ccc', padding: '10px' }}>{book.title}</td>
              <td style={{ border: '1px solid #ccc', padding: '10px' }}>{book.author}</td>
              <td style={{ border: '1px solid #ccc', padding: '10px' }}>{book.year ?? '-'}</td>
              <td style={{ border: '1px solid #ccc', padding: '10px' }}>{book.read ? 'Yes' : 'No'}</td>
              <td style={{ border: '1px solid #ccc', padding: '10px' }}>
                <button onClick={() => handleToggleRead(book.id)} style={{ marginRight: '5px', cursor: 'pointer' }}>
                  Toggle Read
                </button>
                <button onClick={() => handleEdit(book)} style={{ marginRight: '5px', cursor: 'pointer' }}>
                  Edit
                </button>
                <button onClick={() => handleDelete(book.id)} style={{ cursor: 'pointer' }}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {books.length === 0 && (
            <tr>
              <td colSpan="5" style={{ border: '1px solid #ccc', padding: '10px', textAlign: 'center' }}>
                No books found. Add one above!
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default App;
```

### README.md
```markdown
# Book Manager CRUD App

## Prerequisites
- Node.js 26+
- npm

## Setup & Run

### Backend
```bash
cd server
npm install
npm start
```
The API will start on port 3001 (or `$PORT` if set). Data is stored in `server/data.db`.

### Frontend
```bash
cd client
npm install
npm run dev
```
The Vite dev server will start on port 5173 and automatically proxy `/api` requests to the backend.

### Build Frontend
```bash
cd client
npm run build
```
This will generate a production-ready build in `client/dist/`.

## API Endpoints
- `GET /api/books` - List all books
- `GET /api/books/:id` - Get a specific book
- `POST /api/books` - Create a book (requires `title` and `author`)
- `PUT /api/books/:id` - Update a book (requires `title` and `author`)
- `DELETE /api/books/:id` - Delete a book
```