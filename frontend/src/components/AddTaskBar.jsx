import React, { useState } from 'react';
import './AddTaskBar.css';

const PRIORITIES = [
  { key: 'low', label: 'Low', color: '#00c758' },
  { key: 'medium', label: 'Med', color: '#edb200' },
  { key: 'high', label: 'High', color: '#fb2c36' },
];

const CATEGORIES = ['Personal', 'Work', 'Shopping', 'Health', 'Finance'];

export default function AddTaskBar({ value, onChange, onSubmit }) {
  const [priority, setPriority] = useState(null);
  const [category, setCategory] = useState('Personal');
  const [dueDate, setDueDate] = useState('');
  const [tags, setTags] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const showError = (message) => {
    setErrorMessage(message);
    setTimeout(() => setErrorMessage(null), 3000);
  };

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!value || !value.trim()) {
      showError('Enter a task name');
      return;
    }
    if (!priority) {
      showError('Select a priority level');
      return;
    }
    const tagsStr = tags.trim() ? tags.split(',').map(t => t.trim()).filter(Boolean).join(',') : null;
    onSubmit(priority, dueDate || null, category, tagsStr);
    setPriority(null);
    setCategory('Personal');
    setDueDate('');
    setTags('');
    setIsFocused(false);
  };

  return (
    <div className="add-task-wrap">
      <form onSubmit={handleSubmit} className={`input-row ${isFocused ? 'input-row-focused' : ''}`}>
        <input
          type="text"
          className="task-input"
          placeholder="Add a new task..."
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 200)}
          maxLength={200}
        />
        {isFocused && (
          <div className="priority-group">
            {PRIORITIES.map(p => (
              <button
                key={p.key}
                type="button"
                className={`priority-pill ${priority === p.key ? 'priority-pill-active' : ''}`}
                style={priority === p.key ? { borderColor: p.color, color: p.color } : {}}
                onClick={() => setPriority(p.key)}
              >
                {p.label}
              </button>
            ))}
          </div>
        )}
        <button
          type="submit"
          className="add-btn"
          disabled={!value || !value.trim() || !priority}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
      </form>

      {errorMessage && (
        <div className="error-msg">{errorMessage}</div>
      )}

      {isFocused && (
        <div className="options">
          <div className="options-row">
            <div className="opt-group">
              <label className="opt-label">Due</label>
              <input
                type="date"
                className="opt-input"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </div>
            <div className="opt-group">
              <label className="opt-label">Tags</label>
              <input
                type="text"
                className="opt-input"
                placeholder="comma-sep"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
              />
            </div>
          </div>
          <div className="opt-group">
            <label className="opt-label">Category</label>
            <div className="cat-group">
              {CATEGORIES.map(cat => (
                <button
                  key={cat}
                  type="button"
                  className={`cat-pill ${category === cat ? 'cat-pill-active' : ''}`}
                  onClick={() => setCategory(cat)}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
