export default function ChartCard({ title, subtitle, children, className = '' }) {
  return (
    <div className={`glass-card rounded-2xl p-6 animate-fade-in-up ${className}`}>
      <div className="mb-5">
        <h3 className="text-white font-semibold text-sm">{title}</h3>
        {subtitle && <p className="text-slate-500 text-[11px] mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}
