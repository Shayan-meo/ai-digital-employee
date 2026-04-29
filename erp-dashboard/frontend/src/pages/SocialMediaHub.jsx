import { useState, useRef } from 'react';
import { Share2, Send, AtSign, Globe, Briefcase, Camera, Image, AlertTriangle, CheckCircle2, XCircle, Loader2, Eye } from 'lucide-react';
import { postSocial } from '../services/api';

const PLATFORMS = [
  { id: 'facebook',  label: 'Facebook',    icon: Globe,     color: 'from-blue-500 to-indigo-600', bg: 'bg-blue-500/15', border: 'border-blue-500/30', text: 'text-blue-400'  },
  { id: 'linkedin',  label: 'LinkedIn',    icon: Briefcase, color: 'from-blue-600 to-cyan-500',   bg: 'bg-cyan-500/15', border: 'border-cyan-500/30', text: 'text-cyan-400'  },
  { id: 'instagram', label: 'Instagram',   icon: Camera,    color: 'from-pink-500 to-orange-400', bg: 'bg-pink-500/15', border: 'border-pink-500/30', text: 'text-pink-400'  },
  { id: 'twitter',   label: 'Twitter / X', icon: AtSign,    color: 'from-sky-400 to-blue-500',   bg: 'bg-sky-500/15',  border: 'border-sky-500/30',  text: 'text-sky-400'   },
];

export default function SocialMediaHub() {
  const [text, setText] = useState('');
  const [selected, setSelected] = useState({ twitter: true, facebook: true, linkedin: true, instagram: false });
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [posting, setPosting] = useState(false);
  const [results, setResults] = useState(null);
  const fileRef = useRef(null);

  const selectedList = PLATFORMS.filter(p => selected[p.id]);
  const charCount = text.length;
  const twitterWarn = selected.twitter && charCount > 280;
  const canPost = text.trim().length > 0 && selectedList.length > 0 && confirmed === true && posting === false;

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const removeImage = () => {
    setImage(null);
    setImagePreview(null);
    if (fileRef.current) fileRef.current.value = '';
  };

  const togglePlatform = (id) => {
    setSelected(prev => ({ ...prev, [id]: !prev[id] }));
    setResults(null);
  };

  const handlePost = async () => {
    console.log('[SocialHub] handlePost fired', {
      canPost,
      textLen: text.trim().length,
      platforms: selectedList.map(p => p.id),
      confirmed,
      posting,
    });

    if (!canPost) {
      console.warn('[SocialHub] canPost is false, aborting');
      return;
    }

    setPosting(true);
    setResults(null);

    try {
      const formData = new FormData();
      formData.append('text', text.trim());
      formData.append('platforms', selectedList.map(p => p.id).join(','));
      formData.append('confirmed', 'true');  // LIVE MODE guard
      if (image) formData.append('image', image);

      console.log('[SocialHub] Calling API /social/post ...');
      const data = await postSocial(formData);
      console.log('[SocialHub] API response:', data);
      setResults(data.results || data);
    } catch (err) {
      console.error('[SocialHub] API error:', err);
      const errMsg = err.response?.data?.error || err.message || 'Unknown error';
      setResults({ _error: errMsg });
    } finally {
      setPosting(false);
      setConfirmed(false);
    }
  };

  return (
    <div className="space-y-8 bg-mesh min-h-screen">
      {/* Header */}
      <div className="animate-fade-in-up">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-1 h-8 bg-gradient-to-b from-purple-400 to-pink-500 rounded-full" />
          <div>
            <h2 className="text-2xl font-extrabold bg-gradient-to-r from-purple-400 via-pink-400 to-orange-300 bg-clip-text text-transparent" style={{ backgroundSize: '200% 200%', animation: 'gradient-shift 4s ease infinite' }}>
              Social Media Hub
            </h2>
            <div className="flex items-center gap-2 mt-1">
              <Share2 size={11} className="text-purple-500" />
              <p className="text-slate-500 text-xs">Compose once, publish everywhere</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* ── LEFT: Compose ── */}
        <div className="xl:col-span-3 space-y-5 animate-fade-in-up">

          {/* Post Text */}
          <div className="rounded-2xl border border-purple-500/15 overflow-hidden" style={{ background: 'linear-gradient(135deg, rgba(168,85,247,0.06), rgba(15,23,42,0.8))' }}>
            <div className="px-6 py-4 border-b border-purple-500/10 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-500/15 flex items-center justify-center">
                <Send size={18} className="text-purple-400" />
              </div>
              <div>
                <h3 className="text-white font-semibold text-sm">Compose Post</h3>
                <p className="text-slate-500 text-[11px]">Same content goes to all selected platforms</p>
              </div>
            </div>

            <div className="p-6 space-y-5">
              <textarea
                placeholder="What's on your mind? Write your post here..."
                rows={7}
                value={text}
                onChange={e => { setText(e.target.value); setResults(null); }}
                disabled={posting}
                className="w-full bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-purple-500/40 focus:ring-1 focus:ring-purple-500/20 focus:shadow-lg focus:shadow-purple-500/5 transition-all duration-300 disabled:opacity-50"
              />
              <div className="flex items-center justify-between px-1">
                <p className="text-[11px] text-slate-500">{charCount} characters</p>
                {twitterWarn && (
                  <p className="text-[11px] text-amber-400 flex items-center gap-1">
                    <AlertTriangle size={11} /> Over 280 — Twitter may truncate
                  </p>
                )}
              </div>

              {/* Image Upload */}
              <div>
                <label className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  <Image size={12} className="text-purple-500" />
                  Attach Image (optional — default used for Instagram)
                </label>
                <div className="flex items-center gap-3">
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
                    onChange={handleImageChange}
                    disabled={posting}
                    className="flex-1 text-sm text-slate-400 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-purple-500/15 file:text-purple-400 hover:file:bg-purple-500/25 file:cursor-pointer file:transition-all disabled:opacity-50"
                  />
                  {image && (
                    <button onClick={removeImage} className="text-xs text-red-400 hover:text-red-300 transition-colors">
                      Remove
                    </button>
                  )}
                </div>
                {imagePreview && (
                  <div className="mt-3 relative inline-block">
                    <img src={imagePreview} alt="Preview" className="rounded-xl max-h-48 border border-slate-700/50" />
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Live Preview */}
          {text.trim() && (
            <div className="rounded-2xl border border-slate-700/30 overflow-hidden animate-fade-in-up" style={{ background: 'rgba(15,23,42,0.6)' }}>
              <div className="px-5 py-3 border-b border-slate-700/20 flex items-center gap-2">
                <Eye size={14} className="text-purple-400" />
                <h3 className="text-white font-semibold text-sm">Live Preview</h3>
              </div>
              <div className="p-5">
                <div className="bg-slate-800/40 rounded-xl p-4 border border-slate-700/20 text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                  {text}
                </div>
                {imagePreview && (
                  <p className="text-[11px] text-slate-500 mt-2 flex items-center gap-1">
                    <Image size={10} /> Image attached: {image.name}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── RIGHT: Platform Select + Post ── */}
        <div className="xl:col-span-2 space-y-5 animate-fade-in-up" style={{ animationDelay: '120ms' }}>

          {/* Platform Selection */}
          <div className="glass-card rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-700/30 flex items-center gap-2">
              <Share2 size={14} className="text-purple-400" />
              <h3 className="text-white font-semibold text-sm">Select Platforms</h3>
              <span className="badge bg-purple-500/20 text-purple-400 text-[10px] ml-auto">{selectedList.length} selected</span>
            </div>

            <div className="p-4 space-y-2">
              {PLATFORMS.map(({ id, label, icon: Icon, bg, border, text: textCls }) => (
                <button
                  key={id}
                  onClick={() => togglePlatform(id)}
                  disabled={posting}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-300 ${
                    selected[id]
                      ? `${bg} ${border} ${textCls}`
                      : 'bg-slate-800/30 border-slate-700/20 text-slate-500 hover:border-slate-600/40'
                  } disabled:opacity-50`}
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${selected[id] ? bg : 'bg-slate-800/50'}`}>
                    <Icon size={16} />
                  </div>
                  <span className="text-sm font-semibold flex-1 text-left">{label}</span>
                  <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all ${
                    selected[id] ? `${border} ${textCls}` : 'border-slate-600'
                  }`}>
                    {selected[id] && <CheckCircle2 size={12} />}
                  </div>
                </button>
              ))}
            </div>

            {selected.instagram && !image && (
              <div className="mx-4 mb-4 p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs flex items-center gap-2">
                <Camera size={14} />
                Instagram will use the default AI image. Upload your own to override.
              </div>
            )}
          </div>

          {/* Confirmation + Post */}
          <div className="glass-card rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-700/30">
              <h3 className="text-white font-semibold text-sm flex items-center gap-2">
                <AlertTriangle size={14} className="text-amber-400" />
                Confirmation
              </h3>
            </div>

            <div className="p-4 space-y-4">
              {/* Toggle */}
              <button
                onClick={() => setConfirmed(c => !c)}
                disabled={posting}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-300 ${
                  confirmed
                    ? 'bg-red-500/10 border-red-500/30 text-red-400'
                    : 'bg-slate-800/30 border-slate-700/20 text-slate-400 hover:border-slate-600/40'
                } disabled:opacity-50`}
              >
                <div className={`w-10 h-5 rounded-full relative transition-all duration-300 ${confirmed ? 'bg-red-500' : 'bg-slate-600'}`}>
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all duration-300 ${confirmed ? 'left-5' : 'left-0.5'}`} />
                </div>
                <span className="text-sm font-medium">
                  {confirmed ? 'LIVE MODE — Posts will go live!' : 'Are you sure? Enable to post.'}
                </span>
              </button>

              {confirmed && (
                <div className="p-3 rounded-xl bg-red-500/5 border border-red-500/15 text-[11px] text-red-300 animate-fade-in-up">
                  Clicking "Approve & Post" will publish your content to {selectedList.map(p => p.label).join(', ')} immediately.
                </div>
              )}

              {/* Post Button */}
              <button
                onClick={handlePost}
                disabled={!canPost}
                className="group w-full relative flex items-center justify-center gap-2.5 px-6 py-4 rounded-xl font-semibold text-sm transition-all duration-300 overflow-hidden disabled:opacity-30 disabled:cursor-not-allowed"
                style={{
                  background: canPost
                    ? 'linear-gradient(135deg, rgba(168,85,247,0.25), rgba(236,72,153,0.15))'
                    : 'rgba(30,30,60,0.4)',
                  border: canPost ? '1px solid rgba(168,85,247,0.4)' : '1px solid rgba(100,100,150,0.2)',
                  color: canPost ? '#c084fc' : '#64748b',
                }}
              >
                {posting ? (
                  <>
                    <div className="w-5 h-5 border-2 border-purple-400/30 border-t-purple-400 rounded-full animate-spin" />
                    <span>Posting to {selectedList.length} platform{selectedList.length > 1 ? 's' : ''}...</span>
                  </>
                ) : (
                  <>
                    <Send size={16} className="transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                    <span>Approve & Post</span>
                  </>
                )}
              </button>

              {!confirmed && text.trim() && selectedList.length > 0 && (
                <p className="text-[10px] text-slate-600 text-center">Enable the confirmation toggle to unlock posting</p>
              )}
            </div>
          </div>

          {/* Results */}
          {results && (
            <div className="glass-card rounded-2xl overflow-hidden animate-fade-in-up">
              <div className="px-5 py-4 border-b border-slate-700/30">
                <h3 className="text-white font-semibold text-sm">Results</h3>
              </div>
              <div className="p-4 space-y-2">
                {results._error ? (
                  <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
                    <XCircle size={16} />
                    {results._error}
                  </div>
                ) : (
                  Object.entries(results).map(([platform, res]) => {
                    const info = PLATFORMS.find(p => p.id === platform);
                    const Icon = info?.icon || Share2;
                    return (
                      <div
                        key={platform}
                        className={`p-3 rounded-xl border flex items-center gap-3 ${
                          res.success
                            ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                            : 'bg-red-500/10 border-red-500/20 text-red-400'
                        }`}
                      >
                        <Icon size={16} />
                        <span className="text-sm font-semibold flex-1">{info?.label || platform}</span>
                        {res.success ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                        <span className="text-xs opacity-80">{res.message}</span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
