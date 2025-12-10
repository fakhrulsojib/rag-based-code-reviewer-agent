import { useState, useEffect } from 'react';
import axios from 'axios';
import { Loader2, Sparkles, Command } from 'lucide-react';
import ReviewResults from './components/ReviewResults';

// Base API URL
const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [prId, setPrId] = useState('');
  const [reviewData, setReviewData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Parse URL for direct access: /review/:prId/:reportId
  useEffect(() => {
    const path = window.location.pathname;
    const parts = path.split('/').filter(Boolean);
    if (parts[0] === 'review' && parts[1]) {
      const pid = parts[1];
      setPrId(pid);

      if (parts[2]) {
        fetchReview(pid, parts[2]);
      }
    }
  }, []);

  const handleReviewTrigger = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prId) return;

    setLoading(true);
    setError('');
    setReviewData(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/review/${prId}`);

      if (response.status === 202 || response.data.status === 'success' || response.data.status === 'partial') {
        const newReportId = response.data.report_dir;

        // Start polling
        pollReviewStatus(prId, newReportId);

        window.history.pushState({}, '', `/review/${prId}/${newReportId}`);
      } else {
        setError(response.data.message || 'Review failed');
        setLoading(false);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to trigger review');
      setLoading(false);
    }
  };

  const pollReviewStatus = async (pid: string, rid: string) => {
    try {
      const url = rid ? `${API_BASE_URL}/reviews/${pid}/${rid}` : `${API_BASE_URL}/reviews/${pid}`;
      const response = await axios.get(url);
      setReviewData(response.data);

      const status = response.data.status;

      if (status === 'in_progress' || status === 'pending' || status === 'started') {
        // Continue polling
        setTimeout(() => pollReviewStatus(pid, rid), 2000);
      } else {
        // Done or error
        setLoading(false);
      }
    } catch (err: any) {
      // If 404, might be too early, retry? 
      // For now, if error, stop loading
      console.error("Poll error", err);
      // If it was just triggered, maybe file System hasn't written yet.
      // Retry a few times?
      // Let's just create a retry counter or simple tolerance?
      // For now simple: if error, maybe just wait a bit longer if it was a 404
      if (err.response && err.response.status === 404) {
        setTimeout(() => pollReviewStatus(pid, rid), 2000);
      } else {
        setError('Failed to load review data');
        setLoading(false);
      }
    }
  };

  const fetchReview = async (pid: string, rid: string) => {
    setLoading(true);
    pollReviewStatus(pid, rid);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 selection:bg-indigo-100 selection:text-indigo-900">

      {/* Premium Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-slate-200/60 sticky top-0 z-50 transition-all duration-300">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-600/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <span className="font-bold text-lg tracking-tight text-slate-900">CodeReview<span className="text-indigo-600">AI</span></span>
          </div>

          {!reviewData && (
            <div className="text-xs font-medium text-slate-500 bg-slate-100 px-3 py-1.5 rounded-full hidden sm:block">
              Automated Pull Request Analysis
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 lg:px-6 py-8">

        {/* Landing / Input View */}
        {!reviewData && !loading && (
          <div className="max-w-xl mx-auto mt-20 animate-in fade-in slide-in-from-bottom-8 duration-700">
            <div className="text-center mb-10">
              <h1 className="text-4xl font-extrabold text-slate-900 mb-4 tracking-tight">
                Review Code <span className="text-indigo-600">Smarter</span>
              </h1>
              <p className="text-lg text-slate-500 max-w-md mx-auto leading-relaxed">
                Enter a PR ID below to instantly analyze code changes, catch bugs, and generate improvements.
              </p>
            </div>

            <div className="bg-white p-2 rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200 transform transition-all hover:scale-[1.01] duration-300">
              <form onSubmit={handleReviewTrigger} className="relative flex items-center">
                <div className="absolute left-4 text-slate-400">
                  <Command className="w-5 h-5" />
                </div>
                <input
                  type="number"
                  value={prId}
                  onChange={(e) => setPrId(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 rounded-xl bg-transparent text-lg font-medium text-slate-800 placeholder:text-slate-400 outline-none"
                  placeholder="Enter PR ID (e.g. 930)"
                  required
                  autoFocus
                />
                <button
                  type="submit"
                  disabled={loading || !prId}
                  className="absolute right-2 px-6 py-2.5 bg-slate-900 hover:bg-indigo-600 text-white font-semibold rounded-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg"
                >
                  Analyze
                </button>
              </form>
            </div>

            {error && (
              <div className="mt-6 p-4 bg-red-50 border border-red-100 text-red-700 rounded-xl text-sm flex items-start gap-3 animate-in shake duration-300">
                <div className="p-1 bg-red-100 rounded-full shrink-0">
                  <Sparkles className="w-4 h-4 text-red-600 rotate-180" />
                </div>
                {error}
              </div>
            )}

            {/* Quick features chips */}
            <div className="mt-12 flex flex-wrap justify-center gap-3">
              {['RAG-Powered', 'Secure Analysis', 'Bitbucket Integration', 'Instant Feedback'].map((tag) => (
                <span key={tag} className="px-3 py-1 bg-slate-100 text-slate-500 rounded-full text-xs font-medium border border-slate-200">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Loading View */}
        {loading && (
          <div className="flex flex-col items-center justify-center mt-32 animate-in fade-in duration-500">
            <div className="relative">
              <div className="absolute inset-0 bg-indigo-500 blur-2xl opacity-20 rounded-full"></div>
              <Loader2 className="relative w-16 h-16 text-indigo-600 animate-spin" />
            </div>
            <h3 className="text-xl font-bold text-slate-800 mt-8 mb-2">Analyzing Pull Request #{prId}</h3>
            <p className="text-slate-500">Retrieving context and applying rules...</p>
          </div>
        )}

        {/* Results View - Show if we have data OR if we are loading but have partial data */}
        {(reviewData || (loading && reviewData)) && (
          <ReviewResults
            data={reviewData || { pr_id: prId, chunks: [] }}
            loading={loading && (!reviewData || reviewData.status === 'in_progress')}
            onReset={() => {
              setReviewData(null);
              window.history.pushState({}, '', '/');
              setPrId('');
              setError('');
            }}
          />
        )}
      </main>
    </div>
  );
}

export default App;
