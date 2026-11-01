import React, { useState } from 'react';
import './TaskItem.css';

const PRIORITY_COLORS = {
  high: '#fb2c36',
  medium: '#edb200',
  low: '#00c758',
};

const PRIORITIES = [
  { key: 'low', label: 'Low', color: '#00c758' },
  { key: 'medium', label: 'Med', color: '#edb200' },
  { key: 'high', label: 'High', color: '#fb2c36' },
];

const CATEGORIES = ['Personal', 'Work', 'Shopping', 'Health', 'Finance'];

export default function TaskItem({ item, onToggle, onDelete, onUpdate, onArchive }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(item.title);
  const [editPriority, setEditPriority] = useState(item.priority);
  const [editCategory, setEditCategory] = useState(item.category || 'Personal');
  const [editDueDate, setEditDueDate] = useState(item.due_date || '');
  const [editTags, setEditTags] = useState(item.tags || '');

  const priorityColor = PRIORITY_COLORS[item.priority] || '#edb200';

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
    const tagsStr = editTags.trim() ? editTags.split(',').map(t => t.trim()).filter(Boolean).join(',') : null;
    onUpdate(item.id, {
      title: editTitle.trim(),
      priority: editPriority,
      category: editCategory,
      due_date: editDueDate || null,
      tags: tagsStr
    });
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditTitle(item.title);
    setEditPriority(item.priority);
    setEditCategory(item.category || 'Personal');
    setEditDueDate(item.due_date || '');
    setEditTags(item.tags || '');
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <div className="task-card task-edit">
        <input
          type="text"
          className="edit-title"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          maxLength={200}
          autoFocus
        />
        <div className="edit-row">
          {PRIORITIES.map(p => (
            <button
              key={p.key}
              type="button"
              className={`edit-pill ${editPriority === p.key ? 'edit-pill-active' : ''}`}
              style={editPriority === p.key ? { borderColor: p.color, color: p.color } : {}}
              onClick={() => setEditPriority(p.key)}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="edit-row">
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              type="button"
              className={`edit-pill ${editCategory === cat ? 'edit-pill-cat' : ''}`}
              onClick={() => setEditCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
        <div className="edit-row">
          <div className="edit-field">
            <label className="edit-label">Due</label>
            <input
              type="date"
              className="edit-input"
              value={editDueDate}
              onChange={(e) => setEditDueDate(e.target.value)}
            />
          </div>
          <div className="edit-field">
            <label className="edit-label">Tags</label>
            <input
              type="text"
              className="edit-input"
              placeholder="comma-sep"
              value={editTags}
              onChange={(e) => setEditTags(e.target.value)}
            />
          </div>
        </div>
        <div className="edit-actions">
          <button className="btn-primary" onClick={handleSaveEdit} disabled={!editTitle.trim()}>Save</button>
          <button className="btn-ghost" onClick={handleCancelEdit}>Cancel</button>
        </div>
      </div>
    );
  }

  return (
    <div className={`task-card ${item.done ? 'task-done' : ''}`}>
      <button
        className={`check ${item.done ? 'check-done' : ''}`}
        style={item.done ? { backgroundColor: priorityColor, borderColor: priorityColor } : {}}
        onClick={() => onToggle(item.id, !item.done)}
      >
        {item.done && (
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        )}
      </button>

      {item.priority && (
        <div className="priority-strip" style={{ backgroundColor: priorityColor }} />
      )}

      <div className="task-body">
        <div className={`task-title ${item.done ? 'task-title-done' : ''}`}>
          {item.title}
        </div>
        <div className="task-meta">
          <span className="meta-priority" style={{ color: priorityColor }}>{item.priority}</span>
          {item.category && <span className="meta-cat">{item.category}</span>}
          {item.due_date && (
            <span className={`meta-date ${isOverdue(item.due_date) && !item.done ? 'meta-overdue' : ''}`}>
              {formatDate(item.due_date)}
            </span>
          )}
          {item.tags && item.tags.split(',').map((tag, i) => (
            <span key={i} className="meta-tag">{tag.trim()}</span>
          ))}
        </div>
      </div>

      <div className="actions">
        <button className="action" onClick={() => setIsEditing(true)} title="Edit">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
        </button>
        {onArchive && (
          <button className="action" onClick={() => onArchive(item.id)} title="Archive">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="21 8 21 21 3 21 3 8" />
              <rect x="1" y="3" width="22" height="5" />
              <line x1="10" y1="12" x2="14" y2="12" />
            </svg>
          </button>
        )}
        <button className="action action-del" onClick={() => onDelete(item.id)} title="Delete">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
      </div>
    </div>
  );
}
