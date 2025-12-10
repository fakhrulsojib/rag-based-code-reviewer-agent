import { useState } from 'react';
import axios from 'axios';
import { Check, ChevronLeft, Send, AlertTriangle, CheckCircle2, FileCode, AlertCircle, Info, Loader2 } from 'lucide-react';
import clsx from 'clsx';

const API_BASE_URL = 'http://localhost:8000';

interface ReviewResultsProps {
    data: any;
    loading?: boolean;
    onReset: () => void;
}

const SeverityBadge = ({ severity }: { severity: string }) => {
    const styles = {
        High: "bg-red-100 text-red-700 border-red-200",
        Medium: "bg-amber-100 text-amber-700 border-amber-200",
        Low: "bg-blue-50 text-blue-700 border-blue-200",
    }[severity] || "bg-slate-100 text-slate-700 border-slate-200";

    const icons = {
        High: AlertCircle,
        Medium: AlertTriangle,
        Low: Info
    };

    const Icon = icons[severity as keyof typeof icons] || Info;

    return (
        <span className={clsx("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border", styles)}>
            <Icon className="w-3.5 h-3.5" />
            {severity} Severity
        </span>
    );
};

export default function ReviewResults({ data, loading, onReset }: ReviewResultsProps) {
    const [activeTab, setActiveTab] = useState(0);
    const [posting, setPosting] = useState<Record<string, boolean>>({});
    const [posted, setPosted] = useState<Record<string, boolean>>({});

    const totalFindings = data.chunks.reduce((acc: number, chunk: any) =>
        acc + (chunk.possible_comments?.length || 0), 0);

    // Determine how many tabs to show
    // If we have total_chunks from backend, use that. Otherwise use chunks.length
    // If loading and we don't know total_chunks, maybe show chunks.length + 1?
    let chunkCount = data.chunks.length;
    if (data.total_chunks && data.total_chunks > chunkCount) {
        chunkCount = data.total_chunks;
    } else if (loading && !data.total_chunks) {
        // Fallback if we don't know total yet but are loading
        chunkCount = data.chunks.length + 1;
    }

    // Prepare tab indices
    const tabs = Array.from({ length: chunkCount }, (_, i) => i);

    const handlePostComment = async (chunkId: number, finding: any, index: number) => {
        const key = `${chunkId}-${index}`;
        setPosting(prev => ({ ...prev, [key]: true }));

        try {
            await axios.post(`${API_BASE_URL}/reviews/${data.pr_id}/${data.report_id}/comments`, finding);
            setPosted(prev => ({ ...prev, [key]: true }));
        } catch (error) {
            console.error(error);
            // Optionally add toast notification here
        } finally {
            setPosting(prev => ({ ...prev, [key]: false }));
        }
    };

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-5xl mx-auto">
            {/* Header / Stats */}
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
                <button
                    onClick={onReset}
                    className="group flex items-center text-slate-500 hover:text-slate-900 transition-colors font-medium px-4 py-2 -ml-4 rounded-lg hover:bg-slate-100/50"
                >
                    <ChevronLeft className="w-5 h-5 mr-1 group-hover:-translate-x-0.5 transition-transform" />
                    Back to Dashboard
                </button>

                <div className="flex items-center gap-4 bg-white p-2 rounded-xl border border-slate-200 shadow-sm">
                    <div className="px-4 border-r border-slate-100">
                        <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Pull Request</div>
                        <a
                            href={`https://bitbucket.org/therap-projects/suite/pull-requests/${data.pr_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-lg font-bold text-slate-900 hover:text-indigo-600 hover:underline transition-all decoration-2 underline-offset-2 flex items-center gap-1"
                        >
                            #{data.pr_id}
                        </a>
                    </div>
                    <div className="px-4">
                        <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Findings</div>
                        <div className="text-lg font-bold text-indigo-600">{totalFindings} Issues</div>
                    </div>
                </div>
            </div>

            {/* Main Content Card */}
            <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/60 overflow-hidden min-h-[600px] flex flex-col">

                {/* Horizontal Scrolling Tabs */}
                <div className="flex border-b border-slate-100 overflow-x-auto scrollbar-hide bg-slate-50/30">
                    {tabs.map((i) => {
                        const chunk = data.chunks[i];
                        const isLoaded = !!chunk;

                        return (
                            <button
                                key={i}
                                onClick={() => setActiveTab(i)}
                                className={clsx(
                                    "flex items-center gap-2 px-6 py-4 text-sm font-medium whitespace-nowrap transition-all border-b-2 outline-none focus:bg-slate-50",
                                    activeTab === i
                                        ? "border-indigo-600 text-indigo-700 bg-white shadow-[0_-1px_0_0_rgba(0,0,0,0.02)_inset]"
                                        : "border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50"
                                )}
                            >
                                <span>Chunk {i + 1}</span>
                                {isLoaded ? (
                                    chunk.possible_comments?.length > 0 && (
                                        <span className={clsx(
                                            "flex h-5 min-w-[1.25rem] items-center justify-center rounded-full px-1.5 text-[10px]",
                                            activeTab === i ? "bg-indigo-100 text-indigo-700" : "bg-slate-200 text-slate-600"
                                        )}>
                                            {chunk.possible_comments.length}
                                        </span>
                                    )
                                ) : (
                                    <Loader2 className="w-3 h-3 animate-spin text-slate-400" />
                                )}
                            </button>
                        );
                    })}
                </div>

                {/* Tab Content */}
                <div className="p-6 md:p-8 flex-1 bg-gradient-to-br from-white to-slate-50/50">
                    {!data.chunks[activeTab] ? (
                        <div className="h-full flex flex-col items-center justify-center text-slate-400 py-20 animate-in fade-in duration-500">
                            <div className="relative mb-6">
                                <div className="absolute inset-0 bg-indigo-500 blur-xl opacity-20 rounded-full"></div>
                                <Loader2 className="relative w-12 h-12 text-indigo-600 animate-spin" />
                            </div>
                            <h3 className="text-lg font-semibold text-slate-800 mb-2">Analyzing Chunk {activeTab + 1}...</h3>
                            <p className="text-slate-500">Applying review rules.</p>
                        </div>
                    ) : data.chunks[activeTab]?.possible_comments?.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-slate-400 py-20 animate-in zoom-in-95 duration-300">
                            <div className="w-20 h-20 bg-green-50 rounded-full flex items-center justify-center mb-6">
                                <CheckCircle2 className="w-10 h-10 text-green-500" />
                            </div>
                            <h3 className="text-xl font-semibold text-slate-800 mb-2">Clean Code!</h3>
                            <p className="text-slate-500">No issues detected in this chunk.</p>
                        </div>
                    ) : (
                        <div className="space-y-6 max-w-4xl mx-auto">
                            {data.chunks[activeTab].possible_comments.map((finding: any, idx: number) => {
                                const key = `${data.chunks[activeTab].id}-${idx}`;
                                return (
                                    <ReviewCard
                                        key={key}
                                        finding={finding}
                                        onPost={() => handlePostComment(data.chunks[activeTab].id, finding, idx)}
                                        isPosting={posting[key]}
                                        isPosted={posted[key]}
                                    />
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function ReviewCard({ finding, onPost, isPosting, isPosted }: { finding: any, onPost: () => void, isPosting: boolean, isPosted: boolean }) {
    return (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-all duration-300 overflow-hidden group">

            {/* Header Bar */}
            <div className="px-6 py-4 border-b border-slate-50 bg-slate-50/30 flex items-center justify-between">
                <div className="flex items-center gap-3 overflow-hidden">
                    <div className="p-2 bg-white rounded-lg border border-slate-100 shadow-sm text-slate-500">
                        <FileCode className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                        <div className="text-sm font-semibold text-slate-700 truncate" title={finding.file}>
                            {finding.file.split('/').pop()}
                        </div>
                        <div className="text-xs text-slate-400 truncate hidden md:block" title={finding.file}>
                            {finding.file}:{finding.line}
                        </div>
                    </div>
                </div>
                <SeverityBadge severity={finding.severity} />
            </div>

            <div className="p-6">
                {/* Rule & Suggestion */}
                <div className="mb-6">
                    <h4 className="text-sm font-bold text-slate-900 mb-2 flex items-center gap-2">
                        {finding.rule}
                        {finding.category && (
                            <span className="font-normal text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
                                {finding.category}
                            </span>
                        )}
                    </h4>
                    <p className="text-slate-600 text-[15px] leading-relaxed">
                        {finding.suggestion}
                    </p>
                </div>

                {/* Code Snippet */}
                {finding.code_snippet && (
                    <div className="mb-6 relative group/code">
                        <div className="absolute top-0 right-0 px-2 py-1 bg-slate-800 text-slate-400 text-[10px] rounded-bl-lg rounded-tr-lg font-mono">
                            Line {finding.line}
                        </div>
                        <div className="bg-[#1e293b] rounded-lg p-4 overflow-x-auto scrollbar-default">
                            <code className="text-sm font-mono text-slate-50 whitespace-pre font-light tracking-wide">
                                {finding.code_snippet}
                            </code>
                        </div>
                    </div>
                )}

                {/* Actions */}
                <div className="flex items-center justify-end pt-2">
                    {isPosted ? (
                        <div className="flex items-center gap-2 px-5 py-2.5 bg-green-50 text-green-700 rounded-lg text-sm font-semibold border border-green-100 select-none animate-in fade-in duration-300">
                            <Check className="w-4 h-4" />
                            Comment Posted
                        </div>
                    ) : (
                        <button
                            onClick={onPost}
                            disabled={isPosting}
                            className={clsx(
                                "flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 shadow-sm hover:shadow",
                                isPosting
                                    ? "bg-slate-100 text-slate-400 cursor-not-allowed"
                                    : "bg-indigo-600 hover:bg-indigo-700 text-white hover:-translate-y-0.5"
                            )}
                        >
                            {isPosting ? 'Posting...' : (
                                <>
                                    <Send className="w-4 h-4" />
                                    Post Comment
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
