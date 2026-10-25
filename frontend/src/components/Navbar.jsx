import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  FileText, 
  Plus, 
  Bell, 
  User, 
  LogOut, 
  ChevronDown
} from 'lucide-react';
import NotificationsMenu from './NotificationsMenu';

export default function Navbar({ onOpenNewDeal, onOpenAuth, onOpenProfile }) {
  const { user, profile, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const displayName = profile?.full_name || user?.full_name || user?.email?.split('@')[0] || 'User';

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          
          {/* Logo & Tagline */}
          <div className="flex items-center space-x-3">
            <Link to={user ? "/dashboard" : "/"} className="flex items-center space-x-2.5 group">
              <div className="w-9 h-9 rounded-lg bg-navy-900 flex items-center justify-center text-white font-bold shadow-sm transition-transform group-hover:scale-105">
                <FileText className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <span className="text-lg font-bold text-navy-900 tracking-tight block leading-tight">
                  Legalbandu
                </span>
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-medium block">
                  Handshake to Contract
                </span>
              </div>
            </Link>
          </div>

          {/* Center Navigation Links (when authenticated) */}
          {user && (
            <nav className="hidden md:flex items-center space-x-1">
              <Link
                to="/dashboard"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  location.pathname === '/dashboard'
                    ? 'bg-slate-100 text-navy-900'
                    : 'text-slate-600 hover:text-navy-900 hover:bg-slate-50'
                }`}
              >
                My Deals
              </Link>
            </nav>
          )}

          {/* Right Action Items */}
          <div className="flex items-center space-x-3">
            {user ? (
              <>
                {/* New Deal Button */}
                <button
                  id="btn-new-deal-nav"
                  onClick={onOpenNewDeal}
                  className="hidden sm:inline-flex items-center space-x-1.5 px-3.5 py-1.5 bg-navy-900 hover:bg-navy-800 text-white text-xs sm:text-sm font-medium rounded-md shadow-sm transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  <span>New Deal</span>
                </button>

                {/* Notifications Button */}
                <div className="relative">
                  <button
                    id="btn-notifications-toggle"
                    onClick={() => setShowNotifications(!showNotifications)}
                    className="p-2 text-slate-500 hover:text-navy-900 hover:bg-slate-100 rounded-full transition-colors relative"
                    title="Notifications"
                  >
                    <Bell className="w-5 h-5" />
                  </button>

                  {showNotifications && (
                    <NotificationsMenu onClose={() => setShowNotifications(false)} />
                  )}
                </div>

                {/* User Dropdown */}
                <div className="relative">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center space-x-2 pl-2 pr-1 py-1 rounded-full border border-slate-200 hover:bg-slate-50 transition-colors"
                  >
                    <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-semibold text-xs">
                      {displayName.charAt(0).toUpperCase()}
                    </div>
                    <span className="text-xs font-medium text-slate-700 hidden lg:inline-block max-w-[120px] truncate">
                      {displayName}
                    </span>
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                  </button>

                  {showUserMenu && (
                    <div 
                      className="absolute right-0 mt-2 w-52 bg-white rounded-lg shadow-lg border border-slate-200 py-1.5 z-50 animate-in fade-in"
                      onMouseLeave={() => setShowUserMenu(false)}
                    >
                      <div className="px-4 py-2 border-b border-slate-100">
                        <p className="text-xs font-semibold text-slate-900 truncate">{displayName}</p>
                        <p className="text-[11px] text-slate-500 truncate">{user.email}</p>
                      </div>

                      <button
                        onClick={() => {
                          setShowUserMenu(false);
                          if (onOpenProfile) onOpenProfile();
                        }}
                        className="w-full text-left px-4 py-2 text-xs text-slate-700 hover:bg-slate-50 flex items-center space-x-2"
                      >
                        <User className="w-3.5 h-3.5 text-slate-500" />
                        <span>Profile Settings</span>
                      </button>

                      <div className="border-t border-slate-100 my-1"></div>

                      <button
                        onClick={() => {
                          setShowUserMenu(false);
                          signOut();
                          navigate('/');
                        }}
                        className="w-full text-left px-4 py-2 text-xs text-red-600 hover:bg-red-50 flex items-center space-x-2"
                      >
                        <LogOut className="w-3.5 h-3.5" />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex items-center space-x-2">
                <button
                  id="btn-sign-in"
                  onClick={() => onOpenAuth('signin')}
                  className="px-3.5 py-1.5 text-xs sm:text-sm font-medium text-slate-700 hover:text-navy-900 hover:bg-slate-100 rounded-md transition-colors"
                >
                  Sign In
                </button>
                <button
                  id="btn-create-account"
                  onClick={() => onOpenAuth('signup')}
                  className="px-3.5 py-1.5 text-xs sm:text-sm font-medium bg-navy-900 hover:bg-navy-800 text-white rounded-md shadow-sm transition-colors"
                >
                  Create Deal
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
