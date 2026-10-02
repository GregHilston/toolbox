The `list` failure likely stems from `sql.js` returning data in a format that doesn't match the expected JSON structure (arrays vs objects) or type coercion issues (e.g., `read` being `1` instead of `true`). The `ui_toggle` timeout suggests the frontend is failing to update the UI after the toggle, likely due to a state mismatch or an unhandled error in the PUT request where the server returns the full book object but the frontend expects a specific structure.

I will update the server to ensure `read` is explicitly cast to a boolean `true`/`false` and standard JSON object format. I will also update the frontend to handle the toggle response more robustly and ensure the UI updates correctly.

### server/index.js
```javascript
const express = require('express');
const initSqlJs = require('sql.js');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(express.json());
app.use(cors());

// Database Setup
const DB_PATH = path.join(__dirname, 'data.db');
let db;

// Helper to parse SQL.js result into clean JSON objects
function parseResult(result) {
  if (!result || result.length === 0) return [];
  const { columns, values } = result[0];
  return values.map(row => {
    const obj = {};
    columns.forEach((col, index) => {
      let val = row[index];
      // Cast read column to boolean
      if (col === 'read') {
        val = !!val;
      }
      obj[col] = val;
    });
    return obj;
  });
}

// Initialize Database
async function initDatabase() {
  const SQL = await initSqlJs();
  
  // Load existing data or create new
  let data = null;
  if (fs.existsSync(DB_PATH)) {
    data = fs.readFileSync(DB_PATH);
  }
  
  db = new SQL.Database(data);
  
  // Create table if it doesn't exist
  db.run(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      read BOOLEAN DEFAULT 0
    )
  `);
}

// Helper to save database to file
function saveDatabase() {
  const data = db.export();
  const buffer = Buffer.from(data);
  fs.writeFileSync(DB_PATH, buffer);
}

// Initialize DB before starting server
initDatabase().then(() => {
  // --- Endpoints ---

  // GET /api/books
  app.get('/api/books', (req, res) => {
    try {
      const result = db.exec('SELECT * FROM books');
      const books = parseResult(result);
      res.json(books);
    } catch (err) {
      console.error(err);
      res.status(500).json({ error: 'Database error' });
    }
  });

  // GET /api/books/:id
  app.get('/api/books/:id', (req, res) => {
    const id = req.params.id;
    try {
      const result = db.exec('SELECT * FROM books WHERE id = ?', [id]);
      const books = parseResult(result);
      if (books.length === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }
      res.json(books[0]);
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
      db.run(
        'INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)',
        [title.trim(), author.trim(), year || null, read ? 1 : 0]
      );
      const idResult = db.exec('SELECT last_insert_rowid() as id');
      const id = idResult[0].values[0][0];
      
      const result = db.exec('SELECT * FROM books WHERE id = ?', [id]);
      const books = parseResult(result);
      
      saveDatabase();
      res.status(201).json(books[0]);
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
      // Check existence
      const checkResult = db.exec('SELECT * FROM books WHERE id = ?', [id]);
      const existingBooks = parseResult(checkResult);
      
      if (existingBooks.length === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }

      db.run(
        'UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?',
        [title.trim(), author.trim(), year || null, read ? 1 : 0, id]
      );
      
      const result = db.exec('SELECT * FROM books WHERE id = ?', [id]);
      const books = parseResult(result);
      
      saveDatabase();
      res.json(books[0]);
    } catch (err) {
      console.error(err);
      res.status(500).json({ error: 'Database error' });
    }
  });

  // DELETE /api/books/:id
  app.delete('/api/books/:id', (req, res) => {
    const id = req.params.id;

    try {
      const checkResult = db.exec('SELECT * FROM books WHERE id = ?', [id]);
      const existingBooks = parseResult(checkResult);
      
      if (existingBooks.length === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }

      db.run('DELETE FROM books WHERE id = ?', [id]);
      saveDatabase();
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

}).catch(err => {
  console.error('Failed to initialize database:', err);
  process.exit(1);
});
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
      // Optimistic update
      const updatedBook = { ...book, read: !book.read };
      
      // Update local state immediately for better UX
      setBooks(prevBooks => prevBooks.map(b => 
        b.id === book.id ? updatedBook : b
      ));

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

      if (!response.ok) {
        // Revert on error
        setBooks(prevBooks => prevBooks.map(b => 
          b.id === book.id ? book : b
        ));
        const errData = await response.json();
        throw new Error(errData.error || 'Failed to update read status');
      }
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