import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, Package, Users, FileText, MessageCircle, Mail, Zap, Database, PanelLeftClose, PanelLeftOpen, Share2, AtSign, Globe, Briefcase, Camera, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';

const links = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', desc: 'Overview & KPIs' },
  { to: '/products', icon: Package, label: 'Products', desc: 'Inventory items' },
  { to: '/customers', icon: Users, label: 'Customers', desc: 'Partners & contacts' },
  { to: '/invoices', icon: FileText, label: 'Invoices', desc: 'Billing & accounting' },
  { to: '/whatsapp', icon: MessageCircle, label: 'WhatsApp', desc: 'Send messages', green: true },
  { to: '/gmail', icon: Mail, label: 'Gmail', desc: 'Email inbox & send' },
];

const socialSubLinks = [
  { to: '/social?platform=twitter',   icon: AtSign,    label: 'Twitter / X', color: 'text-sky-400'  },
  { to: '/social?platform=facebook',  icon: Globe,     label: 'Facebook',    color: 'text-blue-400' },
  { to: '/social?platform=linkedin',  icon: Briefcase, label: 'LinkedIn',    color: 'text-cyan-400' },
  { to: '/social?platform=instagram', icon: Camera,    label: 'Instagram',   color: 'text-pink-400' },
];

export default function Sidebar({ connected, collapsed, onToggle }) {
  const [socialOpen, setSocialOpen] = useState(false);
  const location = useLocation();
  const isSocialActive = location.pathname === '/social';

  return (
    <aside
      className="h-screen flex flex-col border-r border-slate-700/20 transition-all duration-300 ease-in-out shrink-0 sticky top-0"
      style={{
        width: collapsed ? 68 : 260,
        minWidth: collapsed ? 68 : 260,
        background: 'linear-gradient(180deg, #0a101f 0%, #070c19 50%, #080d1a 100%)',
      }}
    >
      {/* ── Logo Section ── */}
      <div className={`p-4 pb-3 ${collapsed ? 'flex justify-center' : ''}`}>
        <div className={`flex items-center ${collapsed ? 'justify-center' : 'gap-3'}`}>
          <div className="relative shrink-0">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20 animate-float">
              <Zap size={20} className="text-white" />
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-400 rounded-full border-2 border-slate-900" />
          </div>
          {!collapsed && (
            <div className="overflow-hidden">
              <h1 className="text-sm font-bold text-white tracking-tight whitespace-nowrap">ERP Dashboard</h1>
              <p className="text-[10px] text-slate-500 font-medium tracking-widest uppercase whitespace-nowrap">Odoo 19 Enterprise</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Divider ── */}
      <div className="mx-3 h-px bg-gradient-to-r from-transparent via-slate-700/50 to-transparent" />

      {/* ── Toggle Button ── */}
      <div className={`px-3 pt-3 ${collapsed ? 'flex justify-center' : ''}`}>
        <button
          onClick={onToggle}
          className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-all duration-200 w-full"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          {!collapsed && <span className="text-xs font-medium">Collapse</span>}
        </button>
      </div>

      {/* ── Navigation ── */}
      <nav className="flex-1 px-3 py-4 space-y-2">
        {!collapsed && (
          <p className="text-[10px] text-slate-600 font-semibold tracking-widest uppercase px-3 mb-3">Navigation</p>
        )}
        {links.map(({ to, icon: Icon, label, desc, green }) => (
          <NavLink
            key={to}
            to={to}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              `group flex items-center ${collapsed ? 'justify-center' : 'gap-3'} ${collapsed ? 'px-0 py-3' : 'px-3.5 py-3'} rounded-xl text-sm font-medium transition-all duration-200 relative overflow-hidden ${
                isActive ? 'text-white' : 'text-slate-400 hover:text-slate-200'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {/* Active background glow — green variant for WhatsApp */}
                {isActive && !green && (
                  <div className="absolute inset-0 bg-gradient-to-r from-blue-500/15 via-indigo-500/10 to-purple-500/5 border border-blue-500/20 rounded-xl" />
                )}
                {isActive && green && (
                  <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/15 via-green-500/10 to-emerald-500/5 border border-emerald-500/20 rounded-xl" />
                )}
                {/* Hover background */}
                {!isActive && (
                  <div className="absolute inset-0 bg-white/0 group-hover:bg-white/[0.05] rounded-xl transition-all duration-200" />
                )}

                {/* Icon */}
                <div className={`relative shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-all duration-300 ${
                  isActive
                    ? green
                      ? 'bg-emerald-500/20 text-emerald-400 shadow-lg shadow-emerald-500/10'
                      : 'bg-blue-500/20 text-blue-400 shadow-lg shadow-blue-500/10'
                    : green
                      ? 'bg-emerald-900/30 text-emerald-600 group-hover:bg-emerald-800/30 group-hover:text-emerald-400'
                      : 'bg-slate-800/50 text-slate-500 group-hover:bg-slate-700/50 group-hover:text-slate-300'
                }`}>
                  <Icon size={17} />
                </div>

                {/* Label + desc — hidden when collapsed */}
                {!collapsed && (
                  <div className="relative overflow-hidden">
                    <p className={`text-[13px] font-semibold whitespace-nowrap ${isActive ? 'text-white' : ''}`}>{label}</p>
                    <p className={`text-[10px] whitespace-nowrap ${
                      isActive
                        ? green ? 'text-emerald-300/60' : 'text-blue-300/60'
                        : 'text-slate-600'
                    }`}>{desc}</p>
                  </div>
                )}

                {/* Active indicator bar */}
                {isActive && (
                  <div className={`absolute right-0 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-full shadow-lg ${
                    green
                      ? 'bg-gradient-to-b from-emerald-400 to-green-600 shadow-emerald-500/30'
                      : 'bg-gradient-to-b from-blue-400 to-purple-500 shadow-blue-500/30'
                  }`} />
                )}
              </>
            )}
          </NavLink>
        ))}

        {/* ── Social Media Hub ── */}
        {!collapsed && (
          <p className="text-[10px] text-slate-600 font-semibold tracking-widest uppercase px-3 mt-6 mb-3">Social</p>
        )}

        {/* Hub Toggle */}
        <button
          onClick={() => setSocialOpen(o => !o)}
          title={collapsed ? 'Social Media Hub' : undefined}
          className={`group flex items-center ${collapsed ? 'justify-center' : 'gap-3'} ${collapsed ? 'px-0 py-3' : 'px-3.5 py-3'} rounded-xl text-sm font-medium transition-all duration-200 relative overflow-hidden w-full ${
            isSocialActive ? 'text-white' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          {isSocialActive && (
            <div className="absolute inset-0 bg-gradient-to-r from-purple-500/15 via-pink-500/10 to-orange-500/5 border border-purple-500/20 rounded-xl" />
          )}
          {!isSocialActive && (
            <div className="absolute inset-0 bg-white/0 group-hover:bg-white/[0.05] rounded-xl transition-all duration-200" />
          )}
          <div className={`relative shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-all duration-300 ${
            isSocialActive
              ? 'bg-purple-500/20 text-purple-400 shadow-lg shadow-purple-500/10'
              : 'bg-slate-800/50 text-slate-500 group-hover:bg-slate-700/50 group-hover:text-slate-300'
          }`}>
            <Share2 size={17} />
          </div>
          {!collapsed && (
            <>
              <div className="relative overflow-hidden flex-1 text-left">
                <p className={`text-[13px] font-semibold whitespace-nowrap ${isSocialActive ? 'text-white' : ''}`}>Social Media</p>
                <p className={`text-[10px] whitespace-nowrap ${isSocialActive ? 'text-purple-300/60' : 'text-slate-600'}`}>Post everywhere</p>
              </div>
              <div className="relative text-slate-500">
                {socialOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </div>
            </>
          )}
          {isSocialActive && (
            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-full shadow-lg bg-gradient-to-b from-purple-400 to-pink-500 shadow-purple-500/30" />
          )}
        </button>

        {/* Sub-links */}
        {socialOpen && !collapsed && (
          <div className="ml-6 mt-1.5 space-y-2 animate-fade-in-up">
            {socialSubLinks.map(({ to, icon: SubIcon, label, color }) => (
              <NavLink
                key={label}
                to={to}
                className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                  location.pathname === '/social' && location.search.includes(label.toLowerCase())
                    ? `${color} bg-white/[0.06]`
                    : 'text-slate-500 hover:text-slate-300 hover:bg-white/[0.04]'
                }`}
              >
                <SubIcon size={14} />
                {label}
              </NavLink>
            ))}
          </div>
        )}

        {/* Collapsed: just icon link */}
        {collapsed && (
          <NavLink
            to="/social"
            title="Social Media Hub"
            className="flex justify-center py-1 mt-1"
          >
            {socialSubLinks.slice(0, 4).map(({ icon: SubIcon, label, color }) => (
              <div key={label} className={`w-4 h-4 flex items-center justify-center ${color}`} title={label}>
                <SubIcon size={10} />
              </div>
            ))}
          </NavLink>
        )}
      </nav>

      {/* ── Bottom Status ── */}
      <div className="px-3 pb-4">
        <div className="mx-1 h-px bg-gradient-to-r from-transparent via-slate-700/50 to-transparent mb-3" />

        {/* Connection Status Card */}
        <div className={`glass-card rounded-xl ${collapsed ? 'p-2 flex justify-center' : 'p-3'} ${connected ? 'glow-green' : ''}`}>
          {collapsed ? (
            /* Collapsed: just icon + dot */
            <div className="relative" title={connected ? 'Odoo Connected' : 'Odoo Disconnected'}>
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                connected ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
              }`}>
                <Database size={16} />
              </div>
              <div className={`absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-slate-900 ${
                connected ? 'bg-emerald-400' : 'bg-red-400'
              }`} />
            </div>
          ) : (
            /* Expanded: full status card */
            <div className="flex items-center gap-3">
              <div className={`shrink-0 w-9 h-9 rounded-lg flex items-center justify-center ${
                connected ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
              }`}>
                <Database size={16} />
              </div>
              <div className="flex-1 min-w-0 overflow-hidden">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full shrink-0 ${
                    connected ? 'bg-emerald-400 dot-pulse' : 'bg-red-400'
                  }`} />
                  <span className="text-xs font-semibold text-slate-300 whitespace-nowrap">
                    {connected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                <p className="text-[10px] text-slate-600 mt-0.5 whitespace-nowrap">
                  {connected ? 'Odoo 19 • localhost:8069' : 'Check Odoo server'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
