import { Package, Users, DollarSign, ShoppingCart, Clock, TrendingUp } from 'lucide-react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, AreaChart } from 'recharts';
import StatCard from '../components/StatCard';
import ChartCard from '../components/ChartCard';
import { useApiData } from '../hooks/useApiData';
import { fetchDashboardStats } from '../services/api';

const PIE_COLORS = [
  '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444',
  '#06b6d4', '#ec4899', '#6366f1', '#14b8a6', '#f97316', '#84cc16'
];

const CustomTooltip = ({ active, payload }) => {
  if (active && payload?.length) {
    return (
      <div className="glass rounded-xl px-4 py-2.5 shadow-2xl border border-slate-600/30">
        <p className="text-white text-xs font-semibold">{payload[0].name || payload[0].payload?.name}</p>
        <p className="text-blue-400 text-xs mt-0.5 font-medium">
          {typeof payload[0].value === 'number' && payload[0].value > 100
            ? `Rs. ${payload[0].value.toLocaleString()}`
            : payload[0].value}
        </p>
      </div>
    );
  }
  return null;
};

export default function Dashboard() {
  const { data: stats, loading } = useApiData(fetchDashboardStats);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[80vh]">
        <div className="text-center animate-fade-in">
          <div className="relative w-16 h-16 mx-auto mb-6">
            <div className="absolute inset-0 rounded-full border-4 border-blue-500/20" />
            <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-blue-500 animate-spin" />
            <div className="absolute inset-2 rounded-full border-4 border-transparent border-t-purple-500 animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
          </div>
          <p className="text-slate-400 text-sm font-medium">Connecting to Odoo 19...</p>
          <p className="text-slate-600 text-xs mt-1">Fetching live data</p>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-8 bg-mesh min-h-screen">
      {/* Page Header */}
      <div className="animate-fade-in-up">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-1 h-8 bg-gradient-to-b from-blue-400 to-purple-500 rounded-full" />
          <div>
            <h2 className="text-2xl font-extrabold gradient-text">Dashboard Overview</h2>
            <div className="flex items-center gap-2 mt-1">
              <Clock size={11} className="text-slate-600" />
              <p className="text-slate-500 text-xs">Real-time data from Odoo 19 ERP</p>
            </div>
          </div>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 stagger-children">
        <StatCard icon={Package} label="Total Products" value={stats.total_products} color="blue" subtitle="In inventory" />
        <StatCard icon={Users} label="Customers" value={stats.total_customers || stats.total_partners} color="green" subtitle={`${stats.total_partners} total partners`} />
        <StatCard icon={DollarSign} label="Revenue" value={stats.total_revenue || 0} color="purple" subtitle="Posted invoices" />
        <StatCard icon={ShoppingCart} label="Orders" value={stats.total_orders} color="orange" subtitle={`${stats.total_invoices} invoices`} />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Pie Chart */}
        <ChartCard title="Product Categories" subtitle="Distribution across categories">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={stats.category_breakdown}
                cx="50%"
                cy="50%"
                innerRadius={65}
                outerRadius={110}
                paddingAngle={4}
                dataKey="value"
                strokeWidth={0}
              >
                {stats.category_breakdown?.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} opacity={0.85} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
          {/* Legend */}
          <div className="flex flex-wrap gap-x-4 gap-y-2 mt-3 justify-center">
            {stats.category_breakdown?.map((cat, i) => (
              <div key={cat.name} className="flex items-center gap-1.5 text-[11px] text-slate-400">
                <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                <span>{cat.name.replace('Expenses / ', '')}</span>
                <span className="text-slate-600 font-medium">({cat.value})</span>
              </div>
            ))}
          </div>
        </ChartCard>

        {/* Top Products Bar Chart */}
        <ChartCard title="Top Products by Price" subtitle="Highest value items in inventory">
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={stats.top_products} layout="vertical" margin={{ left: 5, right: 20, top: 5, bottom: 5 }}>
              <defs>
                <linearGradient id="barGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.8} />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.9} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" width={130} tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="price" fill="url(#barGrad)" radius={[0, 8, 8, 0]} barSize={18} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Quick Info Banner */}
      <div className="glass-card rounded-2xl p-5 animate-fade-in-up">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
              <TrendingUp size={18} className="text-blue-400" />
            </div>
            <div>
              <p className="text-white text-sm font-semibold">System Status</p>
              <p className="text-slate-500 text-xs">All systems operational — Odoo 19 connected</p>
            </div>
          </div>
          <div className="flex items-center gap-6 text-xs">
            <div className="text-center">
              <p className="text-slate-400 font-bold text-lg">{stats.total_products}</p>
              <p className="text-slate-600">Products</p>
            </div>
            <div className="w-px h-8 bg-slate-700/50" />
            <div className="text-center">
              <p className="text-slate-400 font-bold text-lg">{stats.total_partners}</p>
              <p className="text-slate-600">Partners</p>
            </div>
            <div className="w-px h-8 bg-slate-700/50" />
            <div className="text-center">
              <p className="text-slate-400 font-bold text-lg">{stats.category_breakdown?.length || 0}</p>
              <p className="text-slate-600">Categories</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
