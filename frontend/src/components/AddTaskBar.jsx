import React, { useState } from 'react';
import './AddTaskBar.css';

const PRIORITIES = [
  { key: 'low', label: 'Low', color: '#22c55e' },
  { key: 'medium', label: 'Med', color: '#f59e0b' },
  { key: 'high', label: 'High', color: '#ef4444' },
];

const CATEGORIES = ['Personal', 'Work', 'Shopping', 'Health', 'Finance'];

export default function AddTaskBar({ value, onChange, onSubmit }) {
  const [priority, setPriority] = useState(null);
  const [category, setCategory] = useState('Personal');
  const [dueDate, setDueDate] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const showErrorNotification = (message) => {
    setErrorMessage(message);
    setTimeout(() => setErrorMessage(null), 3000);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!value || !value.trim()) {
      showErrorNotification('Please enter a task name');
      return;
    }
    if (!priority) {
      showErrorNotification('Please select a priority (Low, Medium, or High)');
      return;
    }
    onSubmit(priority, dueDate || null, category);
    setPriority(null);
    setCategory('Personal');
    setDueDate('');
    setIsFocused(false);
  };

  const handleFormKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (!value || !value.trim()) {
        showErrorNotification('Please enter a task name');
      } else if (!priority) {
        showErrorNotification('Please select a priority (Low, Medium, or High)');
      } else {
        handleSubmit(e);
      }
    }
  };

  return (
    <div className="add-task-wrap">
      <form onSubmit={handleSubmit} onKeyDown={handleFormKeyDown} className={`input-row ${isFocused ? 'input-row-focused' : ''}`}>
        <input
          type="text"
          className="task-input"
          placeholder="What needs to be done?"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              if (!value || !value.trim()) {
                showErrorNotification('Please enter a task name');
              } else if (!priority) {
                showErrorNotification('Please select a priority (Low, Medium, or High)');
              } else {
                handleSubmit(e);
              }
            }
          }}
          maxLength={200}
        />
        <div className="priority-inline">
          {PRIORITIES.map(p => (
            <button
              key={p.key}
              type="button"
              className={`pill ${priority === p.key ? 'pill-active' : 'pill-inactive'}`}
              style={priority === p.key ? { backgroundColor: p.color, borderColor: p.color } : {}}
              onClick={() => setPriority(p.key)}
            >
              <span className={`pill-text ${priority === p.key ? 'pill-text-active' : ''}`}>{p.label}</span>
            </button>
          ))}
        </div>
        <button type="submit" className={`add-btn ${!value || !value.trim() || !priority ? 'add-btn-disabled' : ''}`}>
          +
        </button>
      </form>

      {errorMessage && (
        <div className="error-notification">
          <span className="error-icon">⚠️</span>
          <span className="error-message">{errorMessage}</span>
        </div>
      )}

      {isFocused && (
        <div className="options">
          <div className="option-section">
            <label className="option-label">Due Date</label>
            <input
              type="date"
              className="date-input"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>
          <div className="option-section">
            <label className="option-label">Category</label>
            <div className="pill-row">
              {CATEGORIES.map(cat => (
                <button
                  key={cat}
                  type="button"
                  className={`pill ${category === cat ? 'pill-category-active' : 'pill-inactive'}`}
                  onClick={() => setCategory(cat)}
                >
                  <span className={`pill-text ${category === cat ? 'pill-text-active' : ''}`}>{cat}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
