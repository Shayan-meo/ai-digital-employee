import { useState, useEffect, useRef } from 'react';
import { MessageCircle, Send, Phone, FileText, Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { sendWhatsApp, fetchWhatsAppStatus, fetchWhatsAppHistory, clearWhatsAppHistory } from '../services/api';

const STATUS_MAP = {
  queued:  { label: 'Queued',  icon: Clock,        cls: 'text-yellow-400 bg-yellow-500/15 border-yellow-500/20' },
  running: { label: 'Sending', icon: Loader2,      cls: 'text-emerald-400 bg-emerald-500/15 border-emerald-500/20 animate-pulse' },
  sent:    { label: 'Sent',    icon: CheckCircle2,  cls: 'text-emerald-400 bg-emerald-500/15 border-emerald-500/20' },
  error:   { label: 'Failed',  icon: XCircle,       cls: 'text-red-400 bg-red-500/15 border-red-500/20' },
};

export default function WhatsApp() {
  const [phone, setPhone] = useState('');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [currentJob, setCurrentJob] = useState(null);  // { job_id, status, result }
  const [history, setHistory] = useState([]);
  const pollRef = useRef(null);

  // Load history on mount
  useEffect(() => {
    fetchWhatsAppHistory().then(setHistory).catch(() => {});
  }, []);

  // Poll job status while sending
  useEffect(() => {
    if (!currentJob || (currentJob.status !== 'queued' && currentJob.status !== 'running')) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const data = await fetchWhatsAppStatus(currentJob.job_id);
        setCurrentJob(prev => ({ ...prev, ...data }));
        if (data.status === 'sent' || data.status === 'error') {
          setSending(false);
          clearInterval(pollRef.current);
          // Refresh history
          fetchWhatsAppHistory().then(setHistory).catch(() => {});
        }
      } catch {}
    }, 5000);
    return () => clearInterval(pollRef.current);
  }, [currentJob?.job_id, currentJob?.status]);

  const handleSend = async () => {
    if (!phone.trim() || !message.trim()) return;
    setSending(true);
    setCurrentJob(null);
    try {
      const data = await sendWhatsApp(phone.trim(), message.trim());
      setCurrentJob({ job_id: data.job_id, status: 'queued', result: null });
    } catch (err) {
      setCurrentJob({ job_id: null, status: 'error', result: err.response?.data?.error || err.message });
      setSending(false);
    }
  };

  const statusInfo = currentJob ? STATUS_MAP[currentJob.status] || STATUS_MAP.error : null;
  const StatusIcon = statusInfo?.icon;

  return (
    <div className="space-y-8 bg-mesh min-h-screen">
      {/* Header */}
      <div className="animate-fade-in-up">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-1 h-8 bg-gradient-to-b from-emerald-400 to-green-600 rounded-full" />
          <div>
            <h2 className="text-2xl font-extrabold bg-gradient-to-r from-emerald-400 via-green-400 to-emerald-300 bg-clip-text text-transparent" style={{ backgroundSize: '200% 200%', animation: 'gradient-shift 4s ease infinite' }}>
              WhatsApp Messenger
            </h2>
            <div className="flex items-center gap-2 mt-1">
              <MessageCircle size={11} className="text-emerald-600" />
              <p className="text-slate-500 text-xs">Send messages via Playwright automation</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* ── Send Form ── */}
        <div className="xl:col-span-3 animate-fade-in-up">
          <div className="rounded-2xl border border-emerald-500/15 overflow-hidden" style={{ background: 'linear-gradient(135deg, rgba(16,185,129,0.06), rgba(15,23,42,0.8))' }}>
            {/* Form Header */}
            <div className="px-6 py-4 border-b border-emerald-500/10 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/15 flex items-center justify-center">
                <Send size={18} className="text-emerald-400" />
              </div>
              <div>
                <h3 className="text-white font-semibold text-sm">Send New Message</h3>
                <p className="text-slate-500 text-[11px]">Enter recipient number and message</p>
              </div>
            </div>

            {/* Form Body */}
            <div className="p-6 space-y-5">
              {/* Phone Input */}
              <div>
                <label className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  <Phone size={12} className="text-emerald-500" />
                  Recipient Number
                </label>
                <input
                  type="text"
                  placeholder="+923001234567 or 03001234567"
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  disabled={sending}
                  className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 font-mono focus:outline-none focus:border-emerald-500/40 focus:ring-1 focus:ring-emerald-500/20 focus:shadow-lg focus:shadow-emerald-500/5 transition-all duration-300 disabled:opacity-50"
                />
                <p className="text-[10px] text-slate-600 mt-1.5 px-1">Pakistani number: 03xx or +923xx format both work</p>
              </div>

              {/* Message Input */}
              <div>
                <label className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  <FileText size={12} className="text-emerald-500" />
                  Message Body
                </label>
                <textarea
                  placeholder="Type your message here..."
                  rows={5}
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                  disabled={sending}
                  className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-emerald-500/40 focus:ring-1 focus:ring-emerald-500/20 focus:shadow-lg focus:shadow-emerald-500/5 transition-all duration-300 disabled:opacity-50"
                />
                <p className="text-[10px] text-slate-600 mt-1 px-1">{message.length} characters</p>
              </div>

              {/* Send Button */}
              <button
                onClick={handleSend}
                disabled={sending || !phone.trim() || !message.trim()}
                className="group w-full relative flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl font-semibold text-sm transition-all duration-300 overflow-hidden disabled:opacity-40 disabled:cursor-not-allowed"
                style={{
                  background: sending
                    ? 'linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.05))'
                    : 'linear-gradient(135deg, rgba(16,185,129,0.25), rgba(5,150,105,0.15))',
                  border: '1px solid rgba(16,185,129,0.3)',
                  color: '#34d399',
                }}
              >
                {sending ? (
                  <>
                    <div className="w-5 h-5 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
                    <span>Sending via WhatsApp...</span>
                  </>
                ) : (
                  <>
                    <Send size={16} className="transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                    <span>Send Message</span>
                  </>
                )}
              </button>

              {/* Status Banner */}
              {currentJob && statusInfo && (
                <div className={`flex items-start gap-3 p-4 rounded-xl border ${statusInfo.cls} animate-fade-in-up`}>
                  <StatusIcon size={18} className={currentJob.status === 'running' ? 'animate-spin' : ''} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold">{statusInfo.label}</p>
                    {currentJob.result && (
                      <p className="text-xs mt-0.5 opacity-80">{currentJob.result}</p>
                    )}
                    {currentJob.status === 'running' && (
                      <p className="text-xs mt-1 opacity-60">Browser is opening and sending your message...</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Recent Messages ── */}
        <div className="xl:col-span-2 animate-fade-in-up" style={{ animationDelay: '120ms' }}>
          <div className="glass-card rounded-2xl overflow-hidden h-full">
            <div className="px-5 py-4 border-b border-slate-700/30 flex items-center gap-2">
              <Clock size={14} className="text-emerald-500" />
              <h3 className="text-white font-semibold text-sm">Recent Messages</h3>
              <span className="badge bg-slate-700/50 text-slate-400 text-[10px] ml-auto">{history.length}</span>
              {history.length > 0 && (
                <button
                  onClick={async () => {
                    await clearWhatsAppHistory();
                    setHistory([]);
                  }}
                  className="ml-2 px-2.5 py-1 rounded-lg text-[10px] font-semibold text-red-400 bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 transition-all"
                >
                  Clear
                </button>
              )}
            </div>

            <div className="p-3 space-y-2 max-h-[520px] overflow-y-auto">
              {history.length === 0 ? (
                <div className="text-center py-12">
                  <MessageCircle size={28} className="mx-auto mb-3 text-slate-700" />
                  <p className="text-slate-600 text-xs">No messages sent yet</p>
                </div>
              ) : (
                history.map((job, i) => {
                  const st = STATUS_MAP[job.status] || STATUS_MAP.error;
                  const StIcon = st.icon;
                  return (
                    <div key={i} className="p-3 rounded-xl bg-slate-800/30 border border-slate-700/20 hover:border-slate-700/40 transition-all">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-white font-mono text-xs">{job.phone}</span>
                        <div className={`flex items-center gap-1 badge border ${st.cls}`}>
                          <StIcon size={10} />
                          {st.label}
                        </div>
                      </div>
                      <p className="text-slate-400 text-[11px] leading-relaxed line-clamp-2">{job.message}</p>
                      {job.result && job.status === 'error' && (
                        <p className="text-red-400/70 text-[10px] mt-1">{job.result}</p>
                      )}
                      {job.started && (
                        <p className="text-slate-600 text-[10px] mt-1.5">
                          {new Date(job.started * 1000).toLocaleTimeString()}
                        </p>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
