import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API_BASE_URL } from './config';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 8000
});

export default function useTodos() {
  const [todos, setTodos] = useState([]);
  const [archivedTodos, setArchivedTodos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/todos');
      setTodos(data);
      setError(null);
    } catch (err) {
      setError('Cannot reach server');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchArchived = useCallback(async () => {
    try {
      const { data } = await api.get('/todos', { params: { archived: true } });
      setArchivedTodos(data);
    } catch (err) {
      console.error('Failed to fetch archived');
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const { data } = await api.get('/stats');
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats');
    }
  }, []);

  useEffect(() => {
    fetch();
    fetchArchived();
    fetchStats();
  }, [fetch, fetchArchived, fetchStats]);

  const add = useCallback(async (title, priority = 'medium', dueDate = null, category = 'Personal') => {
    const trimmed = title.trim();
    if (!trimmed) return;
    try {
      const { data } = await api.post('/todos', { title: trimmed, priority, due_date: dueDate, category });
      setTodos(prev => [...prev, data]);
      fetchStats();
      setError(null);
    } catch (err) {
      setError('Failed to add task');
    }
  }, [fetchStats]);

  const update = useCallback(async (id, updateData) => {
    const prev = [...todos];
    setTodos(prev => prev.map(t => t.id === id ? { ...t, ...updateData } : t));
    try {
      await api.put(`/todos/${id}`, updateData);
      fetchStats();
      setError(null);
    } catch (err) {
      setTodos(prev);
      setError('Failed to update');
    }
  }, [todos, fetchStats]);

  const toggle = useCallback(async (id, done) => {
    update(id, { done });
  }, [update]);

  const remove = useCallback(async (id) => {
    const prev = [...todos];
    setTodos(prev => prev.filter(t => t.id !== id));
    try {
      await api.delete(`/todos/${id}`);
      fetchStats();
      setError(null);
    } catch (err) {
      setTodos(prev);
      setError('Failed to delete');
    }
  }, [todos, fetchStats]);

  const archive = useCallback(async (id) => {
    const prev = [...todos];
    setTodos(prev => prev.filter(t => t.id !== id));
    try {
      await api.put(`/todos/${id}`, { archived: true });
      fetchArchived();
      fetchStats();
      setError(null);
    } catch (err) {
      setTodos(prev);
      setError('Failed to archive');
    }
  }, [todos, fetchArchived, fetchStats]);

  const restore = useCallback(async (id) => {
    const prev = [...archivedTodos];
    setArchivedTodos(prev => prev.filter(t => t.id !== id));
    try {
      await api.put(`/todos/${id}`, { archived: false });
      fetch();
      fetchStats();
      setError(null);
    } catch (err) {
      setArchivedTodos(prev);
      setError('Failed to restore');
    }
  }, [archivedTodos, fetch, fetchStats]);

  const incomplete = Array.isArray(todos) ? todos.filter(t => !t.done) : [];
  const completed = Array.isArray(todos) ? todos.filter(t => t.done) : [];

  return { todos, archivedTodos, incomplete, completed, loading, error, stats, fetch, add, toggle, update, remove, archive, restore };
}
