### README.md
```markdown
# Full-Stack CRUD Book App

A simple application to manage a list of books using Node.js, Express, SQLite, and React.

## Prerequisites

- Node.js (v26)

## Running the Application

### 1. Backend (Server)

1. Navigate to the `server` directory:
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
   The API will be available at `http://localhost:3001`.

### 2. Frontend (Client)

1. In a separate terminal, navigate to the `client` directory:
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
   The UI will be available at `http://localhost:5173` (or another port specified by Vite).

### 3. Building for Production

To build the frontend for production:

```bash
cd client
npm run build
```

## API Endpoints

- `GET /api/books`: Get all books.
- `GET /api/books/:id`: Get a specific book by ID.
- `POST /api/books`: Create a new book.
- `PUT /api/books/:id`: Update an existing book.
- `DELETE /api/books/:id`: Delete a book.
```

### server/package.json
```json
{
  "name": "server",
  "version": "1.0.0",
  "description": "Backend API for Book CRUD application",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "better-sqlite3": "^11.6.0",
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
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Initialize Database
const dbPath = path.join(__dirname, 'data.db');
let db;

try {
  db = new Database(dbPath);
  // Enable WAL mode for better concurrent access
  db.pragma('journal_mode = WAL');
  
  // Create table if it doesn't exist
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      read BOOLEAN DEFAULT 0
    )
  `);
} catch (err) {
  console.error('Database initialization failed:', err);
  process.exit(1);
}

// GET /api/books - Get all books
app.get('/api/books', (req, res) => {
  try {
    const books = db.prepare('SELECT * FROM books ORDER BY id ASC').all();
    // Convert boolean to actual boolean (SQLite stores as 0/1)
    const formattedBooks = books.map(book => ({
      ...book,
      read: !!book.read
    }));
    res.json(formattedBooks);
  } catch (err) {
    console.error('Error fetching books:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/books/:id - Get a single book
app.get('/api/books/:id', (req, res) => {
  const id = req.params.id;
  try {
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    // Convert boolean to actual boolean
    res.json({
      ...book,
      read: !!book.read
    });
  } catch (err) {
    console.error('Error fetching book:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/books - Create a new book
app.post('/api/books', (req, res) => {
  const { title, author, year, read } = req.body;
  
  // Validation
  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'Title is required and cannot be empty' });
  }
  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'Author is required and cannot be empty' });
  }
  
  try {
    const stmt = db.prepare(`
      INSERT INTO books (title, author, year, read)
      VALUES (@title, @author, @year, @read)
    `);
    
    const result = stmt.run({
      title: title.trim(),
      author: author.trim(),
      year: year || null,
      read: read ? 1 : 0
    });
    
    const newBook = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
    
    res.status(201).json({
      ...newBook,
      read: !!newBook.read
    });
  } catch (err) {
    console.error('Error creating book:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/books/:id - Update a book
app.put('/api/books/:id', (req, res) => {
  const id = req.params.id;
  const { title, author, year, read } = req.body;
  
  try {
    // Check if book exists first
    const existingBook = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    if (!existingBook) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    // Validation
    if (title !== undefined && (typeof title !== 'string' || title.trim() === '')) {
      return res.status(400).json({ error: 'Title cannot be empty' });
    }
    if (author !== undefined && (typeof author !== 'string' || author.trim() === '')) {
      return res.status(400).json({ error: 'Author cannot be empty' });
    }
    
    const updateTitle = title !== undefined ? title.trim() : existingBook.title;
    const updateAuthor = author !== undefined ? author.trim() : existingBook.author;
    const updateYear = year !== undefined ? year : existingBook.year;
    const updateRead = read !== undefined ? (read ? 1 : 0) : existingBook.read;
    
    const stmt = db.prepare(`
      UPDATE books 
      SET title = @title, author = @author, year = @year, read = @read 
      WHERE id = @id
    `);
    
    stmt.run({
      id: id,
      title: updateTitle,
      author: updateAuthor,
      year: updateYear,
      read: updateRead
    });
    
    const updatedBook = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    
    res.json({
      ...updatedBook,
      read: !!updatedBook.read
    });
  } catch (err) {
    console.error('Error updating book:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/books/:id - Delete a book
app.delete('/api/books/:id', (req, res) => {
  const id = req.params.id;
  
  try {
    // Check if book exists first
    const existingBook = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    if (!existingBook) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    const stmt = db.prepare('DELETE FROM books WHERE id = ?');
    stmt.run(id);
    
    res.json({ message: 'Book deleted successfully' });
  } catch (err) {
    console.error('Error deleting book:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  if (db) {
    db.close();
  }
  process.exit(0);
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
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.0"
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
        secure: false
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
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
        margin: 0;
        padding: 20px;
        background-color: #f5f5f5;
        color: #333;
      }
      
      .container {
        max-width: 1200px;
        margin: 0 auto;
      }
      
      header {
        text-align: center;
        margin-bottom: 30px;
      }
      
      h1 {
        color: #2c3e50;
        margin-bottom: 10px;
      }
      
      .controls {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding: 15px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      }
      
      .btn {
        padding: 10px 15px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        transition: background-color 0.2s;
      }
      
      .btn-primary {
        background-color: #3498db;
        color: white;
      }
      
      .btn-primary:hover {
        background-color: #2980b9;
      }
      
      .btn-success {
        background-color: #27ae60;
        color: white;
      }
      
      .btn-success:hover {
        background-color: #219a52;
      }
      
      .btn-warning {
        background-color: #f39c12;
        color: white;
      }
      
      .btn-warning:hover {
        background-color: #d68910;
      }
      
      .btn-danger {
        background-color: #e74c3c;
        color: white;
      }
      
      .btn-danger:hover {
        background-color: #c0392b;
      }
      
      .btn-secondary {
        background-color: #95a5a6;
        color: white;
      }
      
      .btn-secondary:hover {
        background-color: #7f8c8d;
      }
      
      table {
        width: 100%;
        border-collapse: collapse;
        background: white;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      }
      
      th, td {
        padding: 12px 15px;
        text-align: left;
        border-bottom: 1px solid #eee;
      }
      
      th {
        background-color: #34495e;
        color: white;
        font-weight: 600;
      }
      
      tr:hover {
        background-color: #f8f9fa;
      }
      
      .actions {
        display: flex;
        gap: 5px;
      }
      
      .form-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
      }
      
      .form-content {
        background: white;
        padding: 30px;
        border-radius: 8px;
        width: 90%;
        max-width: 500px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      }
      
      .form-group {
        margin-bottom: 15px;
      }
      
      label {
        display: block;
        margin-bottom: 5px;
        font-weight: 500;
        color: #555;
      }
      
      input[type="text"],
      input[type="number"] {
        width: 100%;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 14px;
        box-sizing: border-box;
      }
      
      input[type="text"]:focus,
      input[type="number"]:focus {
        outline: none;
        border-color: #3498db;
        box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
      }
      
      .error {
        color: #e74c3c;
        font-size: 12px;
        margin-top: 5px;
      }
      
      .empty-state {
        text-align: center;
        padding: 40px;
        color: #7f8c8d;
      }
      
      .read-yes {
        color: #27ae60;
        font-weight: 600;
      }
      
      .read-no {
        color: #e74c3c;
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
import { useState, useEffect } from 'react';

function App() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingBook, setEditingBook] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    author: '',
    year: '',
    read: false
  });
  const [formErrors, setFormErrors] = useState({});

  // Fetch books on component mount
  useEffect(() => {
    fetchBooks();
  }, []);

  const fetchBooks = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/books');
      if (!response.ok) {
        throw new Error('Failed to fetch books');
      }
      const data = await response.json();
      setBooks(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching books:', err);
    } finally {
      setLoading(false);
    }
  };

  const validateForm = () => {
    const errors = {};
    
    if (!formData.title || formData.title.trim() === '') {
      errors.title = 'Title is required';
    }
    
    if (!formData.author || formData.author.trim() === '') {
      errors.author = 'Author is required';
    }
    
    if (formData.year !== '' && (isNaN(formData.year) || Number(formData.year) < 0)) {
      errors.year = 'Year must be a positive number or empty';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error when user starts typing
    if (formErrors[field]) {
      setFormErrors(prev => ({
        ...prev,
        [field]: null
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    try {
      const response = await fetch('/api/books', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: formData.title.trim(),
          author: formData.author.trim(),
          year: formData.year ? Number(formData.year) : null,
          read: formData.read
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create book');
      }
      
      const newBook = await response.json();
      setBooks(prev => [...prev, newBook]);
      resetForm();
      setShowForm(false);
    } catch (err) {
      setError(err.message);
      console.error('Error creating book:', err);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    try {
      const response = await fetch(`/api/books/${editingBook.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: formData.title.trim(),
          author: formData.author.trim(),
          year: formData.year ? Number(formData.year) : null,
          read: formData.read
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update book');
      }
      
      const updatedBook = await response.json();
      setBooks(prev => 
        prev.map(book => 
          book.id === updatedBook.id ? updatedBook : book
        )
      );
      resetForm();
      setShowForm(false);
      setEditingBook(null);
    } catch (err) {
      setError(err.message);
      console.error('Error updating book:', err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this book?')) {
      return;
    }
    
    try {
      const response = await fetch(`/api/books/${id}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete book');
      }
      
      setBooks(prev => prev.filter(book => book.id !== id));
    } catch (err) {
      setError(err.message);
      console.error('Error deleting book:', err);
    }
  };

  const handleToggleRead = async (book) => {
    try {
      const response = await fetch(`/api/books/${book.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...book,
          read: !book.read
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update book');
      }
      
      const updatedBook = await response.json();
      setBooks(prev => 
        prev.map(b => 
          b.id === updatedBook.id ? updatedBook : b
        )
      );
    } catch (err) {
      setError(err.message);
      console.error('Error toggling read status:', err);
    }
  };

  const openEditForm = (book) => {
    setEditingBook(book);
    setFormData({
      title: book.title,
      author: book.author,
      year: book.year ? String(book.year) : '',
      read: book.read
    });
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({
      title: '',
      author: '',
      year: '',
      read: false
    });
    setFormErrors({});
    setEditingBook(null);
  };

  const openCreateForm = () => {
    resetForm();
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    resetForm();
  };

  if (loading) {
    return (
      <div className="container">
        <header>
          <h1>📚 Book Manager</h1>
          <p>Loading books...</p>
        </header>
      </div>
    );
  }

  return (
    <div className="container">
      <header>
        <h1>📚 Book Manager</h1>
        <p>Manage your book collection</p>
      </header>

      {error && (
        <div style={{
          backgroundColor: '#fde8e8',
          color: '#e74c3c',
          padding: '10px 15px',
          borderRadius: '4px',
          marginBottom: '20px',
          border: '1px solid #f5c6cb'
        }}>
          {error}
        </div>
      )}

      <div className="controls">
        <h2>All Books ({books.length})</h2>
        <button 
          onClick={openCreateForm}
          className="btn btn-primary"
        >
          + Add New Book
        </button>
      </div>

      {books.length === 0 ? (
        <div className="empty-state">
          <p>No books found. Add your first book to get started!</p>
        </div>
      ) : (
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
                <td>{book.year || 'N/A'}</td>
                <td>
                  <span className={book.read ? 'read-yes' : 'read-no'}>
                    {book.read ? '✓ Yes' : '✗ No'}
                  </span>
                </td>
                <td>
                  <div className="actions">
                    <button
                      onClick={() => handleToggleRead(book)}
                      className="btn btn-success"
                      title="Toggle Read Status"
                    >
                      {book.read ? 'Unread' : 'Read'}
                    </button>
                    <button
                      onClick={() => openEditForm(book)}
                      className="btn btn-warning"
                      title="Edit Book"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(book.id)}
                      className="btn btn-danger"
                      title="Delete Book"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Form Modal */}
      {showForm && (
        <div className="form-modal" onClick={closeForm}>
          <div className="form-content" onClick={(e) => e.stopPropagation()}>
            <h2>{editingBook ? 'Edit Book' : 'Add New Book'}</h2>
            
            <form onSubmit={editingBook ? handleUpdate : handleSubmit}>
              <div className="form-group">
                <label htmlFor="title">Title *</label>
                <input
                  type="text"
                  id="title"
                  value={formData.title}
                  onChange={(e) => handleInputChange('title', e.target.value)}
                  placeholder="Enter book title"
                />
                {formErrors.title && (
                  <span className="error">{formErrors.title}</span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="author">Author *</label>
                <input
                  type="text"
                  id="author"
                  value={formData.author}
                  onChange={(e) => handleInputChange('author', e.target.value)}
                  placeholder="Enter author name"
                />
                {formErrors.author && (
                  <span className="error">{formErrors.author}</span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="year">Year (optional)</label>
                <input
                  type="number"
                  id="year"
                  value={formData.year}
                  onChange={(e) => handleInputChange('year', e.target.value)}
                  placeholder="Enter publication year"
                  min="0"
                />
                {formErrors.year && (
                  <span className="error">{formErrors.year}</span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="read">Read Status</label>
                <select
                  id="read"
                  value={formData.read ? 'true' : 'false'}
                  onChange={(e) => handleInputChange('read', e.target.value === 'true')}
                >
                  <option value="false">Not Read</option>
                  <option value="true">Read</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={closeForm}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                >
                  {editingBook ? 'Update Book' : 'Create Book'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
```