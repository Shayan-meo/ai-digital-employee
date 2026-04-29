import { useMemo } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import DataTable from '../components/DataTable';
import ChartCard from '../components/ChartCard';
import StatCard from '../components/StatCard';
import { Package, Tags, DollarSign, Clock } from 'lucide-react';
import { useApiData } from '../hooks/useApiData';
import { fetchProducts } from '../services/api';

const PIE_COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#6366f1', '#14b8a6', '#f97316', '#84cc16'];

const columns = [
  {
    key: 'name', label: 'Product Name',
    render: (val) => <span className="text-white font-medium">{val}</span>
  },
  {
    key: 'category', label: 'Category',
    render: (val) => (
      <span className="badge bg-indigo-500/15 text-indigo-400 border border-indigo-500/20">
        {(val || 'N/A').replace('Expenses / ', '')}
      </span>
    )
  },
  {
    key: 'list_price', label: 'Sale Price',
    render: (val) => (
      <span className="text-emerald-400 font-semibold">Rs. {(val || 0).toLocaleString()}</span>
    )
  },
  {
    key: 'standard_price', label: 'Cost',
    render: (val) => <span className="text-slate-400">Rs. {(val || 0).toLocaleString()}</span>
  },
  {
    key: 'type', label: 'Type',
    render: (val) => {
      const badges = {
        consu: { label: 'Consumable', cls: 'bg-blue-500/15 text-blue-400 border-blue-500/20' },
        service: { label: 'Service', cls: 'bg-purple-500/15 text-purple-400 border-purple-500/20' },
        product: { label: 'Storable', cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20' },
      };
      const b = badges[val] || { label: val, cls: 'bg-slate-700/50 text-slate-400 border-slate-600/20' };
      return <span className={`badge border ${b.cls}`}>{b.label}</span>;
    }
  },
];

export default function Products() {
  const { data: products, loading } = useApiData(fetchProducts);

  const categoryData = useMemo(() => {
    if (!products) return [];
    const counts = {};
    products.forEach(p => {
      const cat = (p.category || 'Uncategorized').replace('Expenses / ', '');
      counts[cat] = (counts[cat] || 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
  }, [products]);

  const avgPrice = useMemo(() => {
    if (!products?.length) return 0;
    return Math.round(products.reduce((s, p) => s + (p.list_price || 0), 0) / products.length);
  }, [products]);

  const maxPrice = useMemo(() => {
    if (!products?.length) return 0;
    return Math.max(...products.map(p => p.list_price || 0));
  }, [products]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[80vh]">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 rounded-full border-4 border-blue-500/20" />
          <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-blue-500 animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 bg-mesh min-h-screen">
      {/* Header */}
      <div className="animate-fade-in-up">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-1 h-8 bg-gradient-to-b from-blue-400 to-cyan-500 rounded-full" />
          <div>
            <h2 className="text-2xl font-extrabold gradient-text">Products</h2>
            <div className="flex items-center gap-2 mt-1">
              <Clock size={11} className="text-slate-600" />
              <p className="text-slate-500 text-xs">Complete inventory from Odoo</p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 stagger-children">
        <StatCard icon={Package} label="Total Products" value={products?.length || 0} color="blue" />
        <StatCard icon={Tags} label="Categories" value={categoryData.length} color="purple" subtitle={`Avg. Rs. ${avgPrice.toLocaleString()}`} />
        <StatCard icon={DollarSign} label="Highest Price" value={`Rs. ${maxPrice.toLocaleString()}`} color="green" />
      </div>

      {/* Table + Chart */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <DataTable columns={columns} data={products} searchKey={['name', 'category']} title="All Products" />
        </div>
        <ChartCard title="Category Distribution" subtitle="Products per category">
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={categoryData} cx="50%" cy="50%" innerRadius={50} outerRadius={90} paddingAngle={3} dataKey="value" strokeWidth={0}>
                {categoryData.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} opacity={0.85} />
                ))}
              </Pie>
              <Tooltip
                content={({ active, payload }) =>
                  active && payload?.length ? (
                    <div className="glass rounded-xl px-3 py-2 shadow-2xl border border-slate-600/30">
                      <p className="text-white text-xs font-semibold">{payload[0].payload.name}</p>
                      <p className="text-blue-400 text-xs">{payload[0].value} products</p>
                    </div>
                  ) : null
                }
              />
            </PieChart>
          </ResponsiveContainer>
          {/* Legend */}
          <div className="space-y-2 mt-3">
            {categoryData.map((cat, i) => (
              <div key={cat.name} className="flex items-center justify-between text-[11px] px-1 group hover:bg-slate-800/30 rounded-lg py-1 transition-all">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                  <span className="text-slate-400 group-hover:text-slate-200 transition-colors">{cat.name}</span>
                </div>
                <span className="text-slate-300 font-semibold">{cat.value}</span>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>
    </div>
  );
}
