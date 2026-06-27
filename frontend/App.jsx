import React, { useState, useMemo } from 'react';
import useTodos from './src/useTodos';
import AddTaskBar from './src/components/AddTaskBar';
import TaskItem from './src/components/TaskItem';
import './App.css';

const CATEGORIES = ['All', 'Personal', 'Work', 'Shopping', 'Health', 'Finance'];

function App() {
  const { incomplete, completed, archivedTodos, loading, error, stats, fetch, add, toggle, remove, update, archive, restore } = useTodos();
  const [newTitle, setNewTitle] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [showArchived, setShowArchived] = useState(false);

  const total = incomplete.length + completed.length;
  const progress = total > 0 ? completed.length / total : 0;

  const handleAdd = (priority, dueDate, category) => {
    add(newTitle, priority, dueDate, category);
    setNewTitle('');
  };

  const handleDelete = (id) => {
    if (window.confirm('Delete this task?')) remove(id);
  };

  const handleUpdate = (id, updateData) => {
    update(id, updateData);
  };

  const handleArchive = (id) => {
    if (window.confirm('Archive this task?')) archive(id);
  };

  const handleRestore = (id) => {
    restore(id);
  };

  const filteredIncomplete = useMemo(() => {
    return incomplete.filter(t =>
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
      (selectedCategory === 'All' || t.category === selectedCategory)
    );
  }, [incomplete, searchQuery, selectedCategory]);

  const filteredCompleted = useMemo(() => {
    return completed.filter(t =>
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
      (selectedCategory === 'All' || t.category === selectedCategory)
    );
  }, [completed, searchQuery, selectedCategory]);

  const filteredArchived = useMemo(() => {
    return archivedTodos.filter(t =>
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
      (selectedCategory === 'All' || t.category === selectedCategory)
    );
  }, [archivedTodos, searchQuery, selectedCategory]);

  return (
    <div className="container">
      <div className="header">
        <div className="brand-row">
          <div className="logo">◆</div>
          <div>
            <div className="brand-name">doflow</div>
            <div className="stats-subtitle">
              {stats ? (stats.completed + '/' + stats.total + ' tasks finished') : 'Loading...'}
            </div>
          </div>
        </div>

        <div className="progress-container">
          <div className="progress-track">
            <div className="progress-bar" style={{ width: (progress * 100) + '%' }}>
              <div className="progress-glow" />
            </div>
          </div>
          <div className="progress-percent">{Math.round(progress * 100)}%</div>
        </div>
      </div>

      {stats && (
        <div className="stats-scroll">
          <div className="stat-card">
            <div className="stat-val">{stats.pending}</div>
            <div className="stat-label">Pending</div>
          </div>
          <div className="stat-card stat-completed">
            <div className="stat-val" style={{ color: '#22c55e' }}>{stats.completed}</div>
            <div className="stat-label">Completed</div>
          </div>
          {Object.entries(stats.categories || {}).map(([cat, count]) => (
            <div key={cat} className="stat-card">
              <div className="stat-val">{count}</div>
              <div className="stat-label">{cat}</div>
            </div>
          ))}
        </div>
      )}

      <div className="body">
        <AddTaskBar value={newTitle} onChange={setNewTitle} onSubmit={handleAdd} />

        <div className="filter-section">
          <div className="search-box">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              className="search-input"
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="cat-scroll">
            {CATEGORIES.map(cat => (
              <button
                key={cat}
                className={`cat-pill ${selectedCategory === cat ? 'cat-pill-active' : ''}`}
                onClick={() => setSelectedCategory(cat)}
              >
                <span className={selectedCategory === cat ? 'cat-pill-text-active' : 'cat-pill-text'}>
                  {cat}
                </span>
              </button>
            ))}
            <button
              className={`cat-pill archive-toggle ${showArchived ? 'cat-pill-active' : ''}`}
              onClick={() => setShowArchived(v => !v)}
            >
              <span className={showArchived ? 'cat-pill-text-active' : 'cat-pill-text'}>
                📦 Archived ({archivedTodos.length})
              </span>
            </button>
          </div>
        </div>

        {loading && (
          <div className="loading-wrap">
            <div className="spinner" />
            <span className="loading-text">Loading tasks...</span>
          </div>
        )}

        {error && <div className="error"><span>{error}</span></div>}

        {!loading && (
        <div className="tasks-list">
          {showArchived ? (
            <>
              {filteredArchived.length > 0 && (
                <div>
                  <div className="section-header">
                    <span className="section-title">Archived</span>
                    <div className="badge" style={{ backgroundColor: 'rgba(124, 58, 237, 0.1)' }}>
                      <span className="badge-text" style={{ color: '#7c3aed' }}>{filteredArchived.length}</span>
                    </div>
                  </div>
                  {filteredArchived.map(item => (
                    <TaskItem
                      key={item.id}
                      item={item}
                      onToggle={toggle}
                      onDelete={handleDelete}
                      onUpdate={handleUpdate}
                      onArchive={handleRestore}
                    />
                  ))}
                </div>
              )}
              {filteredArchived.length === 0 && (
                <div className="empty">
                  <div className="empty-icon">📦</div>
                  <span className="empty-text">{searchQuery || selectedCategory !== 'All' ? 'No results found' : 'No archived tasks'}</span>
                </div>
              )}
            </>
          ) : (
            <>
              {filteredIncomplete.length > 0 && (
                <div>
                  <div className="section-header">
                    <span className="section-title">Active</span>
                    <div className="badge" style={{ backgroundColor: 'rgba(124, 58, 237, 0.1)' }}>
                      <span className="badge-text" style={{ color: '#7c3aed' }}>{filteredIncomplete.length}</span>
                    </div>
                  </div>
                  {filteredIncomplete.map(item => (
                    <TaskItem key={item.id} item={item} onToggle={toggle} onDelete={handleDelete} onUpdate={handleUpdate} onArchive={handleArchive} />
                  ))}
                </div>
              )}

              {filteredCompleted.length > 0 && (
                <div>
                  <div className="section-header">
                    <span className="section-title">Done</span>
                    <div className="badge" style={{ backgroundColor: 'rgba(34, 197, 94, 0.1)' }}>
                      <span className="badge-text" style={{ color: '#22c55e' }}>{filteredCompleted.length}</span>
                    </div>
                  </div>
                  {filteredCompleted.map(item => (
                    <TaskItem key={item.id} item={item} onToggle={toggle} onDelete={handleDelete} onUpdate={handleUpdate} onArchive={handleArchive} />
                  ))}
                </div>
              )}

              {filteredIncomplete.length === 0 && filteredCompleted.length === 0 && (
                <div className="empty">
                  <div className="empty-icon">✦</div>
                  <span className="empty-text">{searchQuery ? 'No results found' : 'No tasks yet'}</span>
                </div>
              )}
            </>
          )}
        </div>
        )}
      </div>
    </div>
  );
}

export default App;
