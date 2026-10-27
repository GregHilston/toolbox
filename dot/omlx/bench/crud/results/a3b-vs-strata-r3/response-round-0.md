

### server/package.json
```json
{
  "name": "server",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "sqlite3": "^5.1.6"
  }
}
```

### server/server.js
```javascript
const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;
const DB_PATH = path.join(__dirname, 'data.db');

const db = new sqlite3.Database(DB_PATH, (err) => {
  if (err) console.error('Failed to connect to database', err);
  else console.log('Connected to SQLite database');
});

// Initialize table
db.run(`CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  year INTEGER,
  read BOOLEAN DEFAULT 0
)`, (err) => {
  if (err) console.error('Failed to create table', err);
  else console.log('Table ready');
});

app.use(express.json());

// GET /api/books
app.get('/api/books', (req, res) => {
  db.all('SELECT * FROM books', (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

// GET /api/books/:id
app.get('/api/books/:id', (req, res) => {
  db.get('SELECT * FROM books WHERE id = ?', [req.params.id], (err, row) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!row) return res.status(404).json({ error: 'Book not found' });
    res.json(row);
  });
});

// POST /api/books
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;
  if (!title || !author) return res.status(400).json({ error: 'Title and author are required' });
  
  db.run('INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)', 
    [title, author, year, read || false], 
    function(err) {
      if (err) return res.status(500).json({ error: err.message });
      res.status(201).json({ id: this.lastID, ...req.body });
    }
  );
});

// PUT /api/books/:id
app.put('/api/books/:id', (req, res) => {
  const { id } = req.params;
  const { title, author, year, read } = req.body;
  
  // Validation: POST or PUT with a missing or empty title or author returns HTTP 400
  // For PUT, we enforce that title and author must be present and non-empty in the body.
  if (!title || !author) return res.status(400).json({ error: 'Title and author are required' });

  // Construct update query dynamically
  let query = 'UPDATE books SET ';
  const params = [];
  const setClauses = [];

  if (req.body.title !== undefined) {
    setClauses.push('title = ?');
    params.push(req.body.title);
  }
  if (req.body.author !== undefined) {
    setClauses.push('author = ?');
    params.push(req.body.author);
  }
  if (req.body.year !== undefined) {
    setClauses.push('year = ?');
    params.push(req.body.year);
  }
  if (req.body.read !== undefined) {
    setClauses.push('read = ?');
    params.push(req.body.read);
  }

  if (setClauses.length === 0) {
    return res.status(400).json({ error: 'No fields to update' });
  }

  query += setClauses.join(', ') + ' WHERE id = ?';
  params.push(id);

  db.run(query, params, function(err) {
    if (err) return res.status(500).json({ error: err.message });
    if (this.changes === 0) return res.status(404).json({ error: 'Book not found' });
    res.json({ id, ...req.body });
  });
});

// DELETE /api/books/:id
app.delete('/api/books/:id', (req, res) => {
  db.run('DELETE FROM books WHERE id = ?', [req.params.id], function(err) {
    if (err) return res.status(500).json({ error: err.message });
    if (this.changes === 0) return res.status(404).json({ error: 'Book not found' });
    res.json({ message: 'Book deleted' });
  });
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

  useEffect(() => {
    fetchBooks();
  }, []);

  const fetchBooks = async () => {
    try {
      const res = await fetch('/api/books');
      const data = await res.json();
      setBooks(data);
    } catch (err) {
      console.error('Failed to fetch books', err);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`/api/books${editingId ? `/${editingId}` : ''}`, {
        method: editingId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...formData, year: formData.year ? Number(formData.year) : null, read: formData.read }),
      });
      
      if (res.ok) {
        fetchBooks();
        setFormData({ title: '', author: '', year: '', read: false });
        setEditingId(null);
      } else {
        const errData = await res.json();
        alert(errData.error || 'Error');
      }
    } catch (err) {
      console.error('Failed to save book', err);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure?')) return;
    try {
      const res = await fetch(`/api/books/${id}`, { method: 'DELETE' });
      if (res.ok) fetchBooks();
      else alert('Failed to delete');
    } catch (err) {
      console.error('Failed to delete book', err);
    }
  };

  const handleEdit = (book) => {
    setFormData({ title: book.title, author: book.author, year: book.year, read: book.read });
    setEditingId(book.id);
  };

  const handleToggleRead = async (book) => {
    try {
      const res = await fetch(`/api/books/${book.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ read: !book.read }),
      });
      if (res.ok) fetchBooks();
    } catch (err) {
      console.error('Failed to toggle read', err);
    }
  };

  return (
    <div className="container">
      <h1>Book Manager</h1>
      
      <form onSubmit={handleSubmit} className="form">
        <input name="title" placeholder="Title" value={formData.title} onChange={handleChange} required />
        <input name="author" placeholder="Author" value={formData.author} onChange={handleChange} required />
        <input name="year" type="number" placeholder="Year" value={formData.year} onChange={handleChange} />
        <label>
          <input type="checkbox" name="read" checked={formData.read} onChange={handleChange} /> Read
        </label>
        <button type="submit">{editingId ? 'Update' : 'Add Book'}</button>
        {editingId && <button type="button" onClick={() => { setEditingId(null); setFormData({ title: '', author: '', year: '', read: false }); }}>Cancel</button>}
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
          {books.map(book => (
            <tr key={book.id}>
              <td>{book.title}</td>
              <td>{book.author}</td>
              <td>{book.year || '-'}</td>
              <td>
                <input type="checkbox" checked={book.read} onChange={() => handleToggleRead(book)} />
              </td>
              <td>
                <button onClick={() => handleEdit(book)}>Edit</button>
                <button onClick={() => handleDelete(book.id)}>Delete</button>
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

### client/src/App.css
```css
body {
  font-family: sans-serif;
  margin: 0;
  padding: 20px;
  background-color: #f4f4f4;
}

.container {
  max-width: 900px;
  margin: 0 auto;
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

h1 {
  text-align: center;
  color: #333;
}

.form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 20px;
  padding: 15px;
  background: #f9f9f9;
  border-radius: 4px;
}

.form input[type="text"],
.form input[type="number"] {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  flex: 1;
  min-width: 150px;
}

.form label {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px;
}

.form button {
  padding: 8px 16px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.form button[type="button"] {
  background-color: #6c757d;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

th {
  background-color: #f8f9fa;
}

tr:hover {
  background-color: #f1f1f1;
}

td button {
  padding: 5px 10px;
  margin-right: 5px;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

td button:first-child {
  background-color: #ffc107;
}

td button:last-child {
  background-color: #dc3545;
  color: white;
}
```

### README.md
```markdown
# Book Manager CRUD App

A full-stack CRUD web application for managing books.

## Backend (Server)
- **Directory:** `server/`
- **Tech:** Node.js, Express, SQLite
- **Database:** `server/data.db`

### Setup & Run
```bash
cd server
npm install
npm start
```
The server listens on port 3001 by default (or `PORT` environment variable).

## Frontend (Client)
- **Directory:** `client/`
- **Tech:** React, Vite
- **Proxy:** `/api` requests are proxied to `http://localhost:3001`.

### Setup & Run
```bash
cd client
npm install
npm run dev
```

### Build
```bash
cd client
npm run build
```

## API Endpoints
- `GET /api/books`: List all books.
- `GET /api/books/:id`: Get a single book.
- `POST /api/books`: Create a new book.
- `PUT /api/books/:id`: Update a book.
- `DELETE /api/books/:id`: Delete a book.

Validation: POST or PUT with missing or empty title or author returns HTTP 400. Unknown ID returns 404.
```