import { useState, useEffect } from 'react';
import { Mail, Send, Inbox, Clock, X, Loader2, CheckCircle2, AlertCircle, RefreshCw, ArrowLeft, Reply, Star, Archive, Trash2, MoreHorizontal, Search, ChevronDown } from 'lucide-react';
import { fetchGmailUnread, fetchGmailLatest, sendGmail, replyGmail } from '../services/api';

export default function Gmail() {
  const [unread, setUnread] = useState([]);
  const [latest, setLatest] = useState([]);
  const [loadingUnread, setLoadingUnread] = useState(true);
  const [loadingLatest, setLoadingLatest] = useState(true);
  const [showCompose, setShowCompose] = useState(false);
  const [to, setTo] = useState('');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState(null);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [activeTab, setActiveTab] = useState('unread');
  const [searchQuery, setSearchQuery] = useState('');
  const [replyTo, setReplyTo] = useState(null); // {threadId, messageId} when replying

  const loadEmails = () => {
    setLoadingUnread(true);
    setLoadingLatest(true);
    fetchGmailUnread()
      .then(data => setUnread(Array.isArray(data) ? data : []))
      .catch(() => setUnread([]))
      .finally(() => setLoadingUnread(false));
    fetchGmailLatest()
      .then(data => setLatest(Array.isArray(data) ? data : []))
      .catch(() => setLatest([]))
      .finally(() => setLoadingLatest(false));
  };

  useEffect(() => { loadEmails(); }, []);

  const handleSend = async () => {
    if (!to.trim() || !subject.trim() || !message.trim()) return;
    setSending(true);
    setSendResult(null);
    try {
      if (replyTo) {
        await replyGmail(to.trim(), subject.trim(), message.trim(), replyTo.threadId, replyTo.messageId);
      } else {
        await sendGmail(to.trim(), subject.trim(), message.trim());
      }
      setSendResult({ type: 'success', text: replyTo ? 'Reply sent successfully!' : 'Email sent successfully!' });
      setTo('');
      setSubject('');
      setMessage('');
      setReplyTo(null);
      setTimeout(() => {
        setShowCompose(false);
        setSendResult(null);
        loadEmails();
      }, 2500);
    } catch (err) {
      setSendResult({ type: 'error', text: err.response?.data?.error || err.message });
    } finally {
      setSending(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      const now = new Date();
      const isToday = d.toDateString() === now.toDateString();
      if (isToday) {
        return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
      }
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch { return dateStr; }
  };

  const formatSender = (from) => {
    if (!from) return 'Unknown';
    const match = from.match(/^"?([^"<]+)"?\s*</);
    return match ? match[1].trim() : from.split('@')[0];
  };

  const extractEmail = (from) => {
    if (!from) return '';
    const match = from.match(/<(.+?)>/);
    return match ? match[1] : from;
  };

  const currentEmails = activeTab === 'unread' ? unread : latest;
  const isLoading = activeTab === 'unread' ? loadingUnread : loadingLatest;

  const filteredEmails = searchQuery
    ? currentEmails.filter(e =>
        (e.subject || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (e.from || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (e.snippet || '').toLowerCase().includes(searchQuery.toLowerCase())
      )
    : currentEmails;

  // ── Email Detail View ──
  if (selectedEmail) {
    return (
      <div className="space-y-6 bg-mesh min-h-screen animate-fade-in">
        {/* Top bar */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => setSelectedEmail(null)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800/60 transition-all duration-200"
          >
            <ArrowLeft size={16} />
            Back to Inbox
          </button>
          <div className="flex items-center gap-2">
            <button className="p-2.5 rounded-lg text-slate-500 hover:text-white hover:bg-slate-800/60 transition-all" title="Archive">
              <Archive size={16} />
            </button>
            <button className="p-2.5 rounded-lg text-slate-500 hover:text-white hover:bg-slate-800/60 transition-all" title="Delete">
              <Trash2 size={16} />
            </button>
            <button className="p-2.5 rounded-lg text-slate-500 hover:text-white hover:bg-slate-800/60 transition-all" title="More">
              <MoreHorizontal size={16} />
            </button>
          </div>
        </div>

        {/* Email header */}
        <div className="email-detail-panel">
          <h2 className="text-xl font-bold text-white mb-5">{selectedEmail.subject}</h2>
          <div className="flex items-start gap-4">
            {/* Avatar */}
            <div className="w-11 h-11 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shrink-0 shadow-lg shadow-blue-500/20">
              <span className="text-white font-bold text-sm">
                {formatSender(selectedEmail.from).charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-white font-semibold text-sm">{formatSender(selectedEmail.from)}</span>
                <span className="text-slate-600 text-xs">&lt;{extractEmail(selectedEmail.from)}&gt;</span>
              </div>
              <p className="text-slate-500 text-xs mt-1">{selectedEmail.date}</p>
            </div>
            <button className="p-2 rounded-lg text-slate-600 hover:text-yellow-400 transition-all">
              <Star size={16} />
            </button>
          </div>

          {/* Divider */}
          <div className="divider-subtle my-6" />

          {/* Email body */}
          <div className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap min-h-[120px] max-h-[500px] overflow-y-auto pr-2">
            {selectedEmail.body || selectedEmail.snippet || '(No preview available)'}
          </div>
        </div>

        {/* Quick reply bar */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setTo(extractEmail(selectedEmail.from));
              setSubject(`Re: ${selectedEmail.subject}`);
              setReplyTo({ threadId: selectedEmail.threadId, messageId: selectedEmail.messageId });
              setShowCompose(true);
              setSendResult(null);
            }}
            className="flex items-center gap-2.5 px-5 py-3 rounded-xl text-sm font-semibold transition-all duration-300"
            style={{
              background: 'linear-gradient(135deg, rgba(59,130,246,0.2), rgba(99,102,241,0.12))',
              border: '1px solid rgba(59,130,246,0.25)',
              color: '#60a5fa',
            }}
          >
            <Reply size={15} />
            Reply
          </button>
        </div>
      </div>
    );
  }

  // ── Inbox List View ──
  return (
    <div className="space-y-6 bg-mesh min-h-screen">
      {/* Header */}
      <div className="animate-fade-in-up">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-1 h-8 bg-gradient-to-b from-blue-400 to-indigo-600 rounded-full" />
            <div>
              <h2 className="text-2xl font-extrabold bg-gradient-to-r from-blue-400 via-indigo-400 to-blue-300 bg-clip-text text-transparent" style={{ backgroundSize: '200% 200%', animation: 'gradient-shift 4s ease infinite' }}>
                Gmail
              </h2>
              <div className="flex items-center gap-2 mt-1">
                <Mail size={11} className="text-blue-600" />
                <p className="text-slate-500 text-xs">Inbox overview & compose emails</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadEmails}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 hover:scale-[1.02]"
              style={{ background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', color: '#818cf8' }}
            >
              <RefreshCw size={14} className={(loadingUnread || loadingLatest) ? 'animate-spin' : ''} />
              Refresh
            </button>
            <button
              onClick={() => { setShowCompose(true); setSendResult(null); setTo(''); setSubject(''); setMessage(''); setReplyTo(null); }}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 hover:scale-[1.02]"
              style={{ background: 'linear-gradient(135deg, rgba(59,130,246,0.25), rgba(99,102,241,0.15))', border: '1px solid rgba(59,130,246,0.3)', color: '#60a5fa' }}
            >
              <Send size={14} />
              Compose
            </button>
          </div>
        </div>
      </div>

      {/* Search + Tabs bar */}
      <div className="flex items-center gap-4 animate-fade-in-up" style={{ animationDelay: '60ms' }}>
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search emails..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-11 py-2.5 text-sm bg-slate-800/40 border border-slate-700/30 hover:border-slate-600/40 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/40 focus:ring-1 focus:ring-blue-500/20 transition-all"
          />
        </div>

        {/* Tabs */}
        <div className="flex items-center bg-slate-800/30 rounded-xl p-1 border border-slate-700/20">
          <button
            onClick={() => setActiveTab('unread')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
              activeTab === 'unread'
                ? 'bg-blue-500/15 text-blue-400 border border-blue-500/20'
                : 'text-slate-500 hover:text-slate-300 border border-transparent'
            }`}
          >
            <Inbox size={13} />
            Unread
            {unread.length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 text-[10px] font-bold">
                {unread.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('all')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
              activeTab === 'all'
                ? 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/20'
                : 'text-slate-500 hover:text-slate-300 border border-transparent'
            }`}
          >
            <Clock size={13} />
            All Mail
            <span className="ml-1 px-1.5 py-0.5 rounded-full bg-slate-700/50 text-slate-400 text-[10px] font-bold">
              {latest.length}
            </span>
          </button>
        </div>
      </div>

      {/* Email List */}
      <div className="animate-fade-in-up" style={{ animationDelay: '120ms' }}>
        <div className="rounded-2xl border border-slate-700/20 overflow-hidden" style={{ background: 'linear-gradient(180deg, rgba(15,23,42,0.4), rgba(15,23,42,0.2))' }}>
          {/* List header */}
          <div className="px-6 py-3.5 border-b border-slate-700/20 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                activeTab === 'unread' ? 'bg-blue-500/15' : 'bg-indigo-500/15'
              }`}>
                {activeTab === 'unread' ? <Inbox size={15} className="text-blue-400" /> : <Clock size={15} className="text-indigo-400" />}
              </div>
              <div>
                <h3 className="text-white font-semibold text-sm">
                  {activeTab === 'unread' ? 'Unread Emails' : 'All Emails'}
                </h3>
                <p className="text-slate-600 text-[10px]">
                  {filteredEmails.length} {filteredEmails.length === 1 ? 'email' : 'emails'}
                  {searchQuery && ' matching search'}
                </p>
              </div>
            </div>
          </div>

          {/* Email rows */}
          <div className="divide-y divide-slate-700/10">
            {isLoading ? (
              <div className="flex items-center justify-center py-20">
                <div className="text-center">
                  <Loader2 size={28} className="text-blue-400 animate-spin mx-auto mb-3" />
                  <p className="text-slate-500 text-xs">Loading emails...</p>
                </div>
              </div>
            ) : filteredEmails.length === 0 ? (
              <div className="text-center py-20">
                <div className="w-16 h-16 rounded-2xl bg-slate-800/40 flex items-center justify-center mx-auto mb-4">
                  {activeTab === 'unread'
                    ? <CheckCircle2 size={28} className="text-emerald-500/60" />
                    : <Mail size={28} className="text-slate-600" />
                  }
                </div>
                <p className="text-slate-400 text-sm font-medium">
                  {searchQuery
                    ? 'No emails match your search'
                    : activeTab === 'unread' ? 'All caught up!' : 'No emails found'}
                </p>
                <p className="text-slate-600 text-xs mt-1">
                  {searchQuery
                    ? 'Try different keywords'
                    : activeTab === 'unread' ? 'Your inbox is clean' : 'Check your Gmail account'}
                </p>
              </div>
            ) : (
              filteredEmails.map((email, idx) => (
                <div
                  key={email.id}
                  onClick={() => setSelectedEmail(email)}
                  className={`
                    group flex items-center gap-4 px-6 py-4 cursor-pointer transition-all duration-200
                    hover:bg-slate-800/40
                    ${email.unread ? 'bg-blue-500/[0.02]' : ''}
                  `}
                  style={{ animationDelay: `${idx * 30}ms` }}
                >
                  {/* Unread indicator */}
                  <div className="w-2.5 shrink-0">
                    {email.unread && (
                      <div className="w-2.5 h-2.5 rounded-full bg-blue-400 dot-pulse" />
                    )}
                  </div>

                  {/* Avatar */}
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${
                    email.unread
                      ? 'bg-gradient-to-br from-blue-500/30 to-indigo-500/30 text-blue-300'
                      : 'bg-slate-800/60 text-slate-500'
                  }`}>
                    {formatSender(email.from).charAt(0).toUpperCase()}
                  </div>

                  {/* Sender */}
                  <div className="w-44 shrink-0 overflow-hidden">
                    <p className={`text-sm truncate ${
                      email.unread ? 'text-white font-semibold' : 'text-slate-400 font-medium'
                    }`}>
                      {formatSender(email.from)}
                    </p>
                  </div>

                  {/* Subject + Snippet */}
                  <div className="flex-1 min-w-0 overflow-hidden">
                    <div className="flex items-baseline gap-2">
                      <span className={`text-sm truncate ${
                        email.unread ? 'text-slate-200 font-semibold' : 'text-slate-400'
                      }`}>
                        {email.subject}
                      </span>
                      <span className="text-slate-600 text-xs truncate hidden lg:inline">
                        — {email.snippet}
                      </span>
                    </div>
                  </div>

                  {/* Date */}
                  <div className="shrink-0 text-right ml-4">
                    <span className={`text-xs ${
                      email.unread ? 'text-blue-400 font-semibold' : 'text-slate-600'
                    }`}>
                      {formatDate(email.date)}
                    </span>
                  </div>

                  {/* Hover actions */}
                  <div className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center gap-1">
                    <button
                      onClick={(e) => { e.stopPropagation(); }}
                      className="p-1.5 rounded-md text-slate-600 hover:text-yellow-400 hover:bg-slate-700/40 transition-all"
                      title="Star"
                    >
                      <Star size={14} />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); }}
                      className="p-1.5 rounded-md text-slate-600 hover:text-slate-300 hover:bg-slate-700/40 transition-all"
                      title="Archive"
                    >
                      <Archive size={14} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Compose Modal */}
      {showCompose && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={() => !sending && setShowCompose(false)}>
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in" />
          <div
            className="relative w-full max-w-lg mx-4 rounded-2xl border border-slate-700/30 animate-fade-in-up shadow-2xl"
            style={{ background: 'linear-gradient(135deg, #0f172a 0%, #0c1222 100%)' }}
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-700/20 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500/20 to-indigo-500/20 flex items-center justify-center">
                  <Send size={15} className="text-blue-400" />
                </div>
                <div>
                  <h3 className="text-white font-semibold text-sm">New Message</h3>
                  <p className="text-slate-600 text-[10px]">Compose and send email</p>
                </div>
              </div>
              <button
                onClick={() => !sending && setShowCompose(false)}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-500 hover:text-white hover:bg-slate-700/50 transition-all"
              >
                <X size={16} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4">
              <div>
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2 block">To</label>
                <input
                  type="email"
                  placeholder="recipient@example.com"
                  value={to}
                  onChange={e => setTo(e.target.value)}
                  disabled={sending}
                  className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/40 focus:ring-1 focus:ring-blue-500/20 transition-all disabled:opacity-50"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2 block">Subject</label>
                <input
                  type="text"
                  placeholder="Email subject"
                  value={subject}
                  onChange={e => setSubject(e.target.value)}
                  disabled={sending}
                  className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/40 focus:ring-1 focus:ring-blue-500/20 transition-all disabled:opacity-50"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2 block">Message</label>
                <textarea
                  placeholder="Type your message..."
                  rows={6}
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                  disabled={sending}
                  className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-blue-500/40 focus:ring-1 focus:ring-blue-500/20 transition-all disabled:opacity-50"
                />
              </div>

              {/* Send Button */}
              <button
                onClick={handleSend}
                disabled={sending || !to.trim() || !subject.trim() || !message.trim()}
                className="w-full flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl font-semibold text-sm transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed hover:scale-[1.01]"
                style={{
                  background: sending
                    ? 'linear-gradient(135deg, rgba(59,130,246,0.08), rgba(59,130,246,0.04))'
                    : 'linear-gradient(135deg, rgba(59,130,246,0.2), rgba(99,102,241,0.12))',
                  border: '1px solid rgba(59,130,246,0.25)',
                  color: '#60a5fa',
                }}
              >
                {sending ? (
                  <>
                    <div className="w-5 h-5 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
                    <span>Sending...</span>
                  </>
                ) : (
                  <>
                    <Send size={15} />
                    <span>Send Email</span>
                  </>
                )}
              </button>

              {/* Result Alert */}
              {sendResult && (
                <div className={`flex items-center gap-3 p-4 rounded-xl border animate-fade-in-up ${
                  sendResult.type === 'success'
                    ? 'text-emerald-400 bg-emerald-500/8 border-emerald-500/15'
                    : 'text-red-400 bg-red-500/8 border-red-500/15'
                }`}>
                  {sendResult.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                  <span className="text-xs font-medium">{sendResult.text}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
