/**
 * Application Sidebar Navigation
 */

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Zap,
  BookOpen,
  Code2,
  TrendingUp,
  Notebook,
  FileJson,
} from 'lucide-react';

const navigationItems = [
  {
    name: 'Training',
    href: '/training',
    icon: Zap,
    description: 'Submit training examples',
  },
  {
    name: 'Trading',
    href: '/trading',
    icon: TrendingUp,
    description: 'Trading interface',
  },
  {
    name: 'Editor',
    href: '/editor',
    icon: Code2,
    description: 'Code editor',
  },
  {
    name: 'Notes',
    href: '/notes',
    icon: Notebook,
    description: 'Notes & memories',
  },
  {
    name: 'Diary',
    href: '/diary',
    icon: BookOpen,
    description: 'Personal diary',
  },
  {
    name: 'Sandbox',
    href: '/sandbox',
    icon: FileJson,
    description: 'Sandbox environment',
  },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-gradient-to-b from-slate-900 to-slate-950 border-r border-slate-800 min-h-screen flex flex-col">
      {/* Logo/Header */}
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-8 h-8 bg-amber-500 rounded-lg flex items-center justify-center">
            <Zap className="w-5 h-5 text-black" />
          </div>
          <h1 className="font-bold text-lg text-white">ChatOS</h1>
        </div>
        <p className="text-xs text-slate-400">v2.0 Interface</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 overflow-y-auto">
        <div className="space-y-2">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
            
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                  isActive
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    : 'text-slate-400 hover:text-slate-300 hover:bg-slate-800/50'
                }`}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                <div className="flex-1">
                  <div className="font-medium text-sm">{item.name}</div>
                  <div className="text-xs text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity">
                    {item.description}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-800">
        <div className="text-xs text-slate-500 space-y-1">
          <p>🚀 Ready to train</p>
          <p>📊 {navigationItems.length} tools available</p>
        </div>
      </div>
    </aside>
  );
}

