import React, { useState } from 'react';
import './TaskItem.css';

const PRIORITY_COLORS = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#22c55e',
};

const PRIORITIES = [
  { key: 'low', label: 'Low', color: '#22c55e' },
  { key: 'medium', label: 'Med', color: '#f59e0b' },
  { key: 'high', label: 'High', color: '#ef4444' },
];

const CATEGORIES = ['Personal', 'Work', 'Shopping', 'Health', 'Finance'];

export default function TaskItem({ item, onToggle, onDelete, onUpdate, onArchive }) {
  const [isHovering, setIsHovering] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(item.title);
  const [editPriority, setEditPriority] = useState(item.priority);
  const [editCategory, setEditCategory] = useState(item.category || 'Personal');
  const [editDueDate, setEditDueDate] = useState(item.due_date || '');
  const priorityColor = PRIORITY_COLORS[item.priority] || '#f59e0b';

  const formatDate = (dateStr) => {
    if (!dateStr) return null;
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const isOverdue = (dateStr) => {
    if (!dateStr) return false;
    const d = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return d < today;
  };

  const handleSaveEdit = () => {
    if (!editTitle.trim()) return;
    onUpdate(item.id, {
      title: editTitle.trim(),
      priority: editPriority,
      category: editCategory,
      due_date: editDueDate || null
    });
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditTitle(item.title);
    setEditPriority(item.priority);
    setEditCategory(item.category || 'Personal');
    setEditDueDate(item.due_date || '');
    setIsEditing(false);
  };

  const handleArchive = (e) => {
    e.stopPropagation();
    if (onArchive) onArchive(item.id);
  };

  if (isEditing) {
    return (
      <div className="task-item task-edit-mode">
        <div className="edit-form">
          <input
            type="text"
            className="edit-title-input"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            maxLength={200}
            autoFocus
          />
          <div className="edit-priority-row">
            {PRIORITIES.map(p => (
              <button
                key={p.key}
                type="button"
                className={`pill ${editPriority === p.key ? 'pill-active' : 'pill-inactive'}`}
                style={editPriority === p.key ? { backgroundColor: p.color, borderColor: p.color } : {}}
                onClick={() => setEditPriority(p.key)}
              >
                <span className={`pill-text ${editPriority === p.key ? 'pill-text-active' : ''}`}>{p.label}</span>
              </button>
            ))}
          </div>
          <div className="edit-category-row">
            {CATEGORIES.map(cat => (
              <button
                key={cat}
                type="button"
                className={`pill ${editCategory === cat ? 'pill-category-active' : 'pill-inactive'}`}
                onClick={() => setEditCategory(cat)}
              >
                <span className={`pill-text ${editCategory === cat ? 'pill-text-active' : ''}`}>{cat}</span>
              </button>
            ))}
          </div>
          <div className="edit-date-row">
            <label className="edit-date-label">Due Date</label>
            <input
              type="date"
              className="edit-date-input"
              value={editDueDate}
              onChange={(e) => setEditDueDate(e.target.value)}
            />
          </div>
          <div className="edit-actions">
            <button
              className="save-btn"
              onClick={handleSaveEdit}
              disabled={!editTitle.trim()}
            >
              Save
            </button>
            <button
              className="cancel-btn"
              onClick={handleCancelEdit}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`task-item ${item.done ? 'task-done' : ''}`}
      data-priority={item.priority}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      <button
        className="task-content"
        onClick={() => onToggle(item.id, !item.done)}
      >
        <div
          className="check"
          style={item.done ? { backgroundColor: priorityColor, borderColor: priorityColor } : {}}
        >
          {item.done && <span className="check-mark">✓</span>}
        </div>
        <div className="text-details">
          <div className={`title ${item.done ? 'title-done' : ''}`}>
            {item.title}
          </div>
          <div className="meta">
            <div className="priority-tag" style={{ backgroundColor: priorityColor + '15' }}>
              <div className="priority-dot" style={{ backgroundColor: priorityColor }} />
              <span className="priority-text" style={{ color: priorityColor }}>
                {item.priority}
              </span>
            </div>
            {item.category && (
              <div className="category-tag">
                <span className="category-text">{item.category}</span>
              </div>
            )}
            {item.due_date && (
              <div className={`due-tag ${isOverdue(item.due_date) && !item.done ? 'due-overdue' : ''}`}>
                <span className="due-text">
                  {isOverdue(item.due_date) && !item.done ? '⚠ ' : '📅 '}
                  {formatDate(item.due_date)}
                </span>
              </div>
            )}
          </div>
        </div>
      </button>

      <div className="task-actions">
        <button
          className="edit-btn"
          onClick={() => setIsEditing(true)}
          title="Edit task"
        >
          ✎
        </button>
        <button
          className="archive-btn"
          onClick={handleArchive}
          title="Archive task"
        >
          📦
        </button>
        <button
          className="delete-btn"
          onClick={() => onDelete(item.id)}
          style={{ opacity: isHovering ? 1 : 0.55 }}
          title="Delete task"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
