import DataTable from '../components/DataTable';
import StatCard from '../components/StatCard';
import ChartCard from '../components/ChartCard';
import { FileText, TrendingUp, TrendingDown, Scale, Clock } from 'lucide-react';
import { useApiData } from '../hooks/useApiData';
import { fetchInvoices, fetchAccountingSummary } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell } from 'recharts';
import { useMemo } from 'react';

const STATUS_COLORS = { Posted: '#10b981', Draft: '#f59e0b', Cancel: '#ef4444' };
const TYPE_COLORS = { Customer: '#3b82f6', Vendor: '#f97316' };

const columns = [
  {
    key: 'name', label: 'Invoice #',
    render: (val) => <span className="text-white font-mono font-medium text-[12px]">{val}</span>
  },
  {
    key: 'partner_name', label: 'Partner',
    render: (val) => <span className="text-slate-200 font-medium">{val}</span>
  },
  {
    key: 'move_type', label: 'Type',
    render: (val) => (
      <span className={`badge border ${
        val === 'out_invoice'
          ? 'bg-blue-500/15 text-blue-400 border-blue-500/20'
          : 'bg-orange-500/15 text-orange-400 border-orange-500/20'
      }`}>
        {val === 'out_invoice' ? 'Customer' : 'Vendor'}
      </span>
    )
  },
  {
    key: 'amount_total', label: 'Amount',
    render: (val) => (
      <span className="text-emerald-400 font-bold">Rs. {(val || 0).toLocaleString()}</span>
    )
  },
  {
    key: 'state', label: 'Status',
    render: (val) => {
      const styles = {
        posted: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
        draft: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/20',
        cancel: 'bg-red-500/15 text-red-400 border-red-500/20',
      };
      return (
        <span className={`badge border ${styles[val] || 'bg-slate-700/50 text-slate-400 border-slate-600/20'}`}>
          {val ? val.charAt(0).toUpperCase() + val.slice(1) : 'N/A'}
        </span>
      );
    }
  },
  {
    key: 'date', label: 'Date',
    render: (val) => val
      ? <span className="text-slate-400 text-[12px]">{val}</span>
      : <span className="text-slate-700">—</span>
  },
];

export default function Invoices() {
  const { data: invoices, loading: invLoading } = useApiData(fetchInvoices);
  const { data: summary, loading: sumLoading } = useApiData(fetchAccountingSummary);

  const statusData = useMemo(() => {
    if (!invoices) return [];
    const counts = {};
    invoices.forEach(i => {
      const s = i.state || 'unknown';
      const label = s.charAt(0).toUpperCase() + s.slice(1);
      counts[label] = (counts[label] || 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [invoices]);

  const typeData = useMemo(() => {
    if (!invoices) return [];
    let cust = 0, vend = 0;
    invoices.forEach(i => {
      if (i.move_type === 'out_invoice') cust++; else vend++;
    });
    return [{ name: 'Customer', value: cust }, { name: 'Vendor', value: vend }].filter(d => d.value > 0);
  }, [invoices]);

  const loading = invLoading || sumLoading;

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
          <div className="w-1 h-8 bg-gradient-to-b from-purple-400 to-pink-500 rounded-full" />
          <div>
            <h2 className="text-2xl font-extrabold gradient-text">Invoices & Accounting</h2>
            <div className="flex items-center gap-2 mt-1">
              <Clock size={11} className="text-slate-600" />
              <p className="text-slate-500 text-xs">Financial overview from Odoo</p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 stagger-children">
        <StatCard
          icon={FileText}
          label="Total Invoices"
          value={invoices?.length || 0}
          color="blue"
          subtitle={`${summary?.open_invoices || 0} posted, ${summary?.draft_invoices || 0} draft`}
        />
        <StatCard
          icon={TrendingUp}
          label="Receivable"
          value={`Rs. ${(summary?.total_receivable || 0).toLocaleString()}`}
          color="green"
          subtitle="From customers"
        />
        <StatCard
          icon={TrendingDown}
          label="Payable"
          value={`Rs. ${(summary?.total_payable || 0).toLocaleString()}`}
          color="orange"
          subtitle="To vendors"
        />
        <StatCard
          icon={Scale}
          label="Net Position"
          value={`Rs. ${(summary?.net_position || 0).toLocaleString()}`}
          color={summary?.net_position >= 0 ? 'green' : 'red'}
          subtitle="Receivable - Payable"
        />
      </div>

      {/* Charts Row */}
      {(statusData.length > 0 || typeData.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartCard title="Invoice by Status" subtitle="Breakdown of invoice states">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={statusData}>
                <defs>
                  <linearGradient id="statusGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.8} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0.4} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip
                  content={({ active, payload }) =>
                    active && payload?.length ? (
                      <div className="glass rounded-xl px-3 py-2 shadow-2xl border border-slate-600/30">
                        <p className="text-white text-xs font-semibold">{payload[0].payload.name}</p>
                        <p className="text-blue-400 text-xs">{payload[0].value} invoices</p>
                      </div>
                    ) : null
                  }
                />
                <Bar dataKey="value" fill="url(#statusGrad)" radius={[8, 8, 0, 0]} barSize={45} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Invoice Types" subtitle="Customer vs vendor invoices">
            <div className="flex items-center justify-center">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={typeData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={5} dataKey="value" strokeWidth={0}>
                    {typeData.map((entry) => (
                      <Cell key={entry.name} fill={TYPE_COLORS[entry.name]} opacity={0.85} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={({ active, payload }) =>
                      active && payload?.length ? (
                        <div className="glass rounded-xl px-3 py-2 shadow-2xl border border-slate-600/30">
                          <p className="text-white text-xs font-semibold">{payload[0].payload.name}</p>
                          <p className="text-blue-400 text-xs">{payload[0].value} invoices</p>
                        </div>
                      ) : null
                    }
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-center gap-6 mt-2">
              {typeData.map(d => (
                <div key={d.name} className="flex items-center gap-2 text-[11px]">
                  <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: TYPE_COLORS[d.name] }} />
                  <span className="text-slate-400">{d.name}</span>
                  <span className="text-slate-300 font-semibold">{d.value}</span>
                </div>
              ))}
            </div>
          </ChartCard>
        </div>
      )}

      {/* Invoice Table */}
      <DataTable columns={columns} data={invoices} searchKey={['name', 'partner_name']} title="All Invoices" />
    </div>
  );
}
