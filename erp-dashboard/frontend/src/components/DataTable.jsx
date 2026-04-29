import { useState, useMemo } from 'react';
import { Search, ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight } from 'lucide-react';

const PAGE_SIZE = 12;

export default function DataTable({ columns, data, searchKey, title }) {
  const [search, setSearch] = useState('');
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    if (!data) return [];
    let result = data;
    if (search && searchKey) {
      const q = search.toLowerCase();
      result = result.filter(row => {
        if (Array.isArray(searchKey)) {
          return searchKey.some(key => String(row[key] || '').toLowerCase().includes(q));
        }
        return String(row[searchKey] || '').toLowerCase().includes(q);
      });
    }
    if (sortCol) {
      result = [...result].sort((a, b) => {
        const va = a[sortCol] ?? '';
        const vb = b[sortCol] ?? '';
        if (typeof va === 'number' && typeof vb === 'number') return sortDir === 'asc' ? va - vb : vb - va;
        return sortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
      });
    }
    return result;
  }, [data, search, searchKey, sortCol, sortDir]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const toggleSort = (key) => {
    if (sortCol === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(key); setSortDir('asc'); }
  };

  return (
    <div className="glass-card rounded-2xl overflow-hidden animate-fade-in-up">
      {/* Header Bar */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700/30">
        <div className="flex items-center gap-3">
          {title && <h3 className="text-white font-semibold text-sm">{title}</h3>}
          <span className="badge bg-slate-700/50 text-slate-400 text-[10px]">
            {filtered.length} records
          </span>
        </div>
        {searchKey && (
          <div className="relative group">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
            <input
              type="text"
              placeholder="Search..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(0); }}
              className="w-56 bg-slate-800/60 border border-slate-700/50 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/40 focus:bg-slate-800 focus:shadow-lg focus:shadow-blue-500/5 transition-all duration-300"
            />
          </div>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-700/30">
              {columns.map(col => (
                <th
                  key={col.key}
                  onClick={() => col.sortable !== false && toggleSort(col.key)}
                  className={`text-left px-5 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-[0.1em] ${
                    col.sortable !== false ? 'cursor-pointer hover:text-slate-300 select-none group/th' : ''
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    {col.label}
                    {col.sortable !== false && (
                      sortCol === col.key
                        ? (sortDir === 'asc' ? <ArrowUp size={10} className="text-blue-400" /> : <ArrowDown size={10} className="text-blue-400" />)
                        : <ArrowUpDown size={10} className="text-slate-700 group-hover/th:text-slate-500 transition-colors" />
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="text-center py-16">
                  <div className="text-slate-600">
                    <Search size={32} className="mx-auto mb-3 opacity-30" />
                    <p className="text-sm font-medium">No data found</p>
                    <p className="text-xs mt-1">Try a different search term</p>
                  </div>
                </td>
              </tr>
            ) : (
              paged.map((row, idx) => (
                <tr key={row.id || idx} className="border-b border-slate-800/30 table-row-hover">
                  {columns.map(col => (
                    <td key={col.key} className="px-5 py-3.5 text-[13px] text-slate-300">
                      {col.render ? col.render(row[col.key], row) : (row[col.key] ?? <span className="text-slate-700">—</span>)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-5 py-3 border-t border-slate-700/30">
          <span className="text-[11px] text-slate-500">
            Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, filtered.length)} of {filtered.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="p-1.5 rounded-lg hover:bg-slate-800 disabled:opacity-30 transition-all text-slate-400"
            >
              <ChevronLeft size={14} />
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const pageNum = totalPages <= 5 ? i : Math.max(0, Math.min(page - 2, totalPages - 5)) + i;
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={`w-7 h-7 rounded-lg text-xs font-medium transition-all ${
                    pageNum === page
                      ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                      : 'text-slate-500 hover:bg-slate-800 hover:text-slate-300'
                  }`}
                >
                  {pageNum + 1}
                </button>
              );
            })}
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page === totalPages - 1}
              className="p-1.5 rounded-lg hover:bg-slate-800 disabled:opacity-30 transition-all text-slate-400"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
