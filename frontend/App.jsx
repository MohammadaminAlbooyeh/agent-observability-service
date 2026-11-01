import React, { useState, useMemo } from 'react';
import useTodos from './src/useTodos';
import AddTaskBar from './src/components/AddTaskBar';
import TaskItem from './src/components/TaskItem';
import './App.css';

const CATEGORIES = ['All', 'Personal', 'Work', 'Shopping', 'Health', 'Finance'];

const NAV_ITEMS = [
  { key: 'all', label: 'All Tasks' },
  { key: 'active', label: 'Active' },
  { key: 'completed', label: 'Completed' },
  { key: 'archived', label: 'Archived' },
];

function App() {
  const { incomplete, completed, archivedTodos, loading, error, stats, add, toggle, remove, update, archive, restore } = useTodos();
  const [newTitle, setNewTitle] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [currentView, setCurrentView] = useState('all');

  const total = incomplete.length + completed.length;
  const progress = total > 0 ? completed.length / total : 0;

  const handleAdd = (priority, dueDate, category) => {
    add(newTitle, priority, dueDate, category);
    setNewTitle('');
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

  const showArchived = currentView === 'archived';
  const showCompleted = currentView === 'completed' || currentView === 'all';
  const showActive = currentView === 'active' || currentView === 'all';

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-logo">EC</div>
          <span className="sidebar-brand-text">Evreghen</span>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map(item => (
            <button
              key={item.key}
              className={`nav-item ${currentView === item.key ? 'nav-item-active' : ''}`}
              onClick={() => setCurrentView(item.key)}
            >
              {item.label}
              <span className="nav-count">
                {item.key === 'all' ? total :
                 item.key === 'active' ? incomplete.length :
                 item.key === 'completed' ? completed.length :
                 archivedTodos.length}
              </span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="nav-item" onClick={() => setSelectedCategory('All')}>
            Categories
          </button>
        </div>
      </aside>

      <div className="main-area">
        <div className="main-header">
          <div className="main-header-top">
            <div>
              <div className="main-greeting">Tasks</div>
              <div className="main-greeting-sub">
                {stats ? `${stats.completed} of ${stats.total} complete` : 'Loading...'}
              </div>
            </div>
            <div className="main-header-right">
              <div className="stat-item">
                <span className="stat-number">{stats?.pending ?? 0}</span>
                <span className="stat-label">Pending</span>
              </div>
              <div className="stat-item">
                <span className="stat-number stat-number-primary">{stats?.completed ?? 0}</span>
                <span className="stat-label">Done</span>
              </div>
              <div className="stat-item">
                <span className="stat-number">{total}</span>
                <span className="stat-label">Total</span>
              </div>
            </div>
          </div>
          <div className="progress-section">
            <div className="progress-header">
              <span className="progress-label">Progress</span>
              <span className="progress-pct">{Math.round(progress * 100)}%</span>
            </div>
            <div className="progress-track">
              <div className="progress-bar" style={{ width: `${progress * 100}%` }} />
            </div>
          </div>
        </div>

        <div className="main-body">
          <AddTaskBar value={newTitle} onChange={setNewTitle} onSubmit={handleAdd} />

          <div className="filter-section">
            <div className="search-box">
              <span className="search-icon">/</span>
              <input
                type="text"
                className="search-input"
                placeholder="Search tasks..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="filter-cats">
              {CATEGORIES.map(cat => (
                <button
                  key={cat}
                  className={`filter-cat-btn ${selectedCategory === cat ? 'filter-cat-active' : ''}`}
                  onClick={() => setSelectedCategory(cat)}
                >
                  {cat}
                </button>
              ))}
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
            <>
              {showArchived ? (
                <div className="task-list">
                  {filteredArchived.length > 0 && (
                    <>
                      <div className="section-header">
                        <span className="section-title">Archived</span>
                        <span className="section-count">{filteredArchived.length}</span>
                      </div>
                      {filteredArchived.map(item => (
                        <TaskItem
                          key={item.id}
                          item={item}
                          onToggle={() => {}}
                          onDelete={() => {}}
                          onUpdate={() => {}}
                          onArchive={() => restore(item.id)}
                        />
                      ))}
                    </>
                  )}
                  {filteredArchived.length === 0 && (
                    <div className="empty">
                      <div className="empty-icon">~</div>
                      <span className="empty-text">{searchQuery || selectedCategory !== 'All' ? 'No results' : 'No archived tasks'}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="task-list">
                  {showActive && filteredIncomplete.length > 0 && (
                    <>
                      <div className="section-header">
                        <span className="section-title">Active</span>
                        <span className="section-count">{filteredIncomplete.length}</span>
                      </div>
                      {filteredIncomplete.map(item => (
                        <TaskItem key={item.id} item={item} onToggle={(id, done) => toggle(id, done)} onDelete={(id) => remove(id)} onUpdate={(id, data) => update(id, data)} onArchive={(id) => archive(id)} />
                      ))}
                    </>
                  )}

                  {showCompleted && filteredCompleted.length > 0 && (
                    <>
                      <div className="section-header" style={{ marginTop: showActive && filteredIncomplete.length > 0 ? 28 : 0 }}>
                        <span className="section-title">Completed</span>
                        <span className="section-count">{filteredCompleted.length}</span>
                      </div>
                      {filteredCompleted.map(item => (
                        <TaskItem key={item.id} item={item} onToggle={(id, done) => toggle(id, done)} onDelete={(id) => remove(id)} onUpdate={(id, data) => update(id, data)} onArchive={(id) => archive(id)} />
                      ))}
                    </>
                  )}

                  {filteredIncomplete.length === 0 && filteredCompleted.length === 0 && (
                    <div className="empty">
                      <div className="empty-icon">~</div>
                      <span className="empty-text">{searchQuery ? 'No results' : 'No tasks yet'}</span>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
