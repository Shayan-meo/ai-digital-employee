import DataTable from '../components/DataTable';
import StatCard from '../components/StatCard';
import { Users, Building2, UserCircle, Clock, Mail } from 'lucide-react';
import { useApiData } from '../hooks/useApiData';
import { fetchPartners } from '../services/api';
import { useMemo } from 'react';

const columns = [
  {
    key: 'name', label: 'Name',
    render: (val, row) => (
      <div className="flex items-center gap-3">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${
          row.is_company ? 'bg-purple-500/15 text-purple-400' : 'bg-blue-500/15 text-blue-400'
        }`}>
          {(val || '?')[0].toUpperCase()}
        </div>
        <div>
          <p className="text-white font-medium text-[13px]">{val}</p>
          {row.city && <p className="text-slate-600 text-[10px]">{row.city}</p>}
        </div>
      </div>
    )
  },
  {
    key: 'email', label: 'Email',
    render: (val) => val
      ? <span className="text-blue-400 text-[12px] hover:text-blue-300 transition-colors">{val}</span>
      : <span className="text-slate-700">—</span>
  },
  {
    key: 'phone', label: 'Phone',
    render: (val) => val
      ? <span className="text-slate-300 font-mono text-[12px]">{val}</span>
      : <span className="text-slate-700">—</span>
  },
  {
    key: 'is_company', label: 'Type',
    render: (val) => (
      <span className={`badge border ${
        val
          ? 'bg-purple-500/15 text-purple-400 border-purple-500/20'
          : 'bg-cyan-500/15 text-cyan-400 border-cyan-500/20'
      }`}>
        {val ? 'Company' : 'Individual'}
      </span>
    )
  },
  {
    key: 'customer_rank', label: 'Status',
    render: (val, row) => {
      const tags = [];
      if (val > 0) tags.push({ label: 'Customer', cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20' });
      if (row.supplier_rank > 0) tags.push({ label: 'Vendor', cls: 'bg-orange-500/15 text-orange-400 border-orange-500/20' });
      if (tags.length === 0) return <span className="text-slate-700">—</span>;
      return (
        <div className="flex gap-1.5">
          {tags.map(t => <span key={t.label} className={`badge border ${t.cls}`}>{t.label}</span>)}
        </div>
      );
    }
  },
];

export default function Customers() {
  const { data: partners, loading } = useApiData(fetchPartners);

  const stats = useMemo(() => {
    if (!partners) return { total: 0, companies: 0, individuals: 0, withEmail: 0 };
    return {
      total: partners.length,
      companies: partners.filter(p => p.is_company).length,
      individuals: partners.filter(p => !p.is_company).length,
      withEmail: partners.filter(p => p.email).length,
    };
  }, [partners]);

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
          <div className="w-1 h-8 bg-gradient-to-b from-emerald-400 to-cyan-500 rounded-full" />
          <div>
            <h2 className="text-2xl font-extrabold gradient-text">Customers & Partners</h2>
            <div className="flex items-center gap-2 mt-1">
              <Clock size={11} className="text-slate-600" />
              <p className="text-slate-500 text-xs">All contacts from Odoo CRM</p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 stagger-children">
        <StatCard icon={Users} label="Total Partners" value={stats.total} color="blue" />
        <StatCard icon={Building2} label="Companies" value={stats.companies} color="purple" />
        <StatCard icon={UserCircle} label="Individuals" value={stats.individuals} color="cyan" />
        <StatCard icon={Mail} label="With Email" value={stats.withEmail} color="green" />
      </div>

      {/* Table */}
      <DataTable columns={columns} data={partners} searchKey={['name', 'email', 'city', 'phone']} title="All Partners" />
    </div>
  );
}
