import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Bell, CheckCheck, FileText } from 'lucide-react';

export default function NotificationsMenu({ onClose }) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const loadNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getNotifications();
      setNotifications(data || []);
    } catch (err) {
      console.warn('Failed to load notifications:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  async function handleMarkAllRead() {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (err) {
      console.error(err);
    }
  }

  async function handleClickNotification(notif) {
    if (!notif.is_read) {
      try {
        await api.markNotificationRead(notif.id);
        setNotifications((prev) =>
          prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
        );
      } catch (err) {
        console.error(err);
      }
    }
    if (notif.deal_id) {
      onClose();
      navigate(`/deal/${notif.deal_id}`);
    }
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div 
      className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-lg shadow-xl border border-slate-200 z-50 overflow-hidden animate-in fade-in"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="px-4 py-3 border-b border-slate-100 flex justify-between items-center bg-slate-50">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-semibold text-slate-900">Notifications</span>
          {unreadCount > 0 && (
            <span className="bg-blue-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
              {unreadCount}
            </span>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            className="text-[11px] text-blue-600 hover:text-blue-800 flex items-center space-x-1"
          >
            <CheckCheck className="w-3.5 h-3.5" />
            <span>Mark all read</span>
          </button>
        )}
      </div>

      <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
        {loading ? (
          <div className="p-6 text-center text-xs text-slate-400">Loading notifications...</div>
        ) : notifications.length === 0 ? (
          <div className="p-8 text-center">
            <Bell className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-xs font-medium text-slate-600">No notifications yet</p>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Updates about deal approvals, reviews, and amendments will appear here.
            </p>
          </div>
        ) : (
          notifications.map((n) => (
            <div
              key={n.id}
              onClick={() => handleClickNotification(n)}
              className={`p-3 text-left hover:bg-slate-50 cursor-pointer transition-colors ${
                !n.is_read ? 'bg-blue-50/40' : ''
              }`}
            >
              <div className="flex items-start space-x-2.5">
                <div className={`mt-0.5 w-6 h-6 rounded-full flex items-center justify-center text-white shrink-0 ${
                  n.title.includes('Confirmed') ? 'bg-emerald-600' :
                  n.title.includes('Review') ? 'bg-blue-600' :
                  n.title.includes('Changes') ? 'bg-amber-600' : 'bg-slate-700'
                }`}>
                  <FileText className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-slate-900 leading-tight">
                    {n.title}
                  </p>
                  <p className="text-[11px] text-slate-600 mt-0.5 line-clamp-2">
                    {n.message}
                  </p>
                  <span className="text-[10px] text-slate-400 mt-1 block">
                    {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                {!n.is_read && (
                  <span className="w-2 h-2 rounded-full bg-blue-600 shrink-0 mt-1.5"></span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
