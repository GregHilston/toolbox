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
    "cors": "^2.8.5",
    "express": "^4.21.2",
    "sqlite3": "^5.1.7"
  }
}
```

### server/index.js
```javascript
const express = require('express');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
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
  db = new sqlite3.Database(dbPath);
  
  // Create table if it doesn't exist
  db.run(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      read INTEGER DEFAULT 0
    )
  `);
} catch (err) {
  console.error('Database initialization failed:', err);
  process.exit(1);
}

// Helper to convert sqlite3 boolean (0/1) to JS boolean
const formatBook = (book) => {
  if (!book) return null;
  return {
    ...book,
    read: !!book.read
  };
};

// GET /api/books - Get all books
app.get('/api/books', (req, res) => {
  db.all('SELECT * FROM books ORDER BY id ASC', [], (err, rows) => {
    if (err) {
      console.error('Error fetching books:', err);
      return res.status(500).json({ error: 'Internal server error' });
    }
    res.json(rows.map(formatBook));
  });
});

// GET /api/books/:id - Get a single book
app.get('/api/books/:id', (req, res) => {
  const id = req.params.id;
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      console.error('Error fetching book:', err);
      return res.status(500).json({ error: 'Internal server error' });
    }
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json(formatBook(row));
  });
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
  
  const trimmedTitle = title.trim();
  const trimmedAuthor = author.trim();
  const yearValue = year !== undefined ? year : null;
  const readValue = read ? 1 : 0;
  
  const stmt = `INSERT INTO books (title, author, year, read) VALUES (?, ?, ?, ?)`;
  
  db.run(stmt, [trimmedTitle, trimmedAuthor, yearValue, readValue], function(err) {
    if (err) {
      console.error('Error creating book:', err);
      return res.status(500).json({ error: 'Internal server error' });
    }
    
    const newId = this.lastID;
    db.get('SELECT * FROM books WHERE id = ?', [newId], (err, row) => {
      if (err) {
        console.error('Error fetching created book:', err);
        return res.status(500).json({ error: 'Internal server error' });
      }
      res.status(201).json(formatBook(row));
    });
  });
});

// PUT /api/books/:id - Update a book
app.put('/api/books/:id', (req, res) => {
  const id = req.params.id;
  const { title, author, year, read } = req.body;
  
  // First check if book exists
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, existingBook) => {
    if (err) {
      console.error('Error fetching book:', err);
      return res.status(500).json({ error: 'Internal server error' });
    }
    
    if (!existingBook) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    // Validation
    // If title is provided, it must be valid
    let finalTitle = existingBook.title;
    let finalAuthor = existingBook.author;
    let finalYear = existingBook.year;
    let finalRead = existingBook.read;
    
    if (title !== undefined) {
      if (typeof title !== 'string' || title.trim() === '') {
        return res.status(400).json({ error: 'Title cannot be empty' });
      }
      finalTitle = title.trim();
    }
    
    if (author !== undefined) {
      if (typeof author !== 'string' || author.trim() === '') {
        return res.status(400).json({ error: 'Author cannot be empty' });
      }
      finalAuthor = author.trim();
    }
    
    if (year !== undefined) {
      finalYear = year;
    }
    
    if (read !== undefined) {
      finalRead = read ? 1 : 0;
    }
    
    const stmt = `UPDATE books SET title = ?, author = ?, year = ?, read = ? WHERE id = ?`;
    
    db.run(stmt, [finalTitle, finalAuthor, finalYear, finalRead, id], function(err) {
      if (err) {
        console.error('Error updating book:', err);
        return res.status(500).json({ error: 'Internal server error' });
      }
      
      db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
        if (err) {
          console.error('Error fetching updated book:', err);
          return res.status(500).json({ error: 'Internal server error' });
        }
        res.json(formatBook(row));
      });
    });
  });
});

// DELETE /api/books/:id - Delete a book
app.delete('/api/books/:id', (req, res) => {
  const id = req.params.id;
  
  // First check if book exists
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, existingBook) => {
    if (err) {
      console.error('Error fetching book:', err);
      return res.status(500).json({ error: 'Internal server error' });
    }
    
    if (!existingBook) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    const stmt = `DELETE FROM books WHERE id = ?`;
    
    db.run(stmt, [id], function(err) {
      if (err) {
        console.error('Error deleting book:', err);
        return res.status(500).json({ error: 'Internal server error' });
      }
      res.json({ message: 'Book deleted successfully' });
    });
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  if (db) {
    db.close((err) => {
      if (err) {
        console.error('Error closing database:', err);
      }
      process.exit(0);
    });
  } else {
    process.exit(0);
  }
});
```