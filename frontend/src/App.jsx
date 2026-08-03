import React, { useState, useEffect, useCallback } from "react";

const API_BASE_URL = "http://127.0.0.1:8000/api/v1";

// ------------------------------------------------------------------
// Small shared UI bits
// ------------------------------------------------------------------

function ModeToggle({ mode, setMode }) {
    return (
        <div className="inline-flex rounded-xl bg-slate-100 p-1 border border-slate-200">
            <button
                onClick={() => setMode("benchmark")}
                className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${mode === "benchmark"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-700"
                    }`}
            >
                Mode 1: Benchmark
            </button>
            <button
                onClick={() => setMode("live")}
                className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${mode === "live"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-700"
                    }`}
            >
                Mode 2: Live Testing
            </button>
        </div>
    );
}

function Spinner({ className = "h-4 w-4" }) {
    return (
        <svg
            className={`animate-spin ${className}`}
            viewBox="0 0 24 24"
            fill="none"
        >
            <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
            />
            <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
        </svg>
    );
}

// ------------------------------------------------------------------
// Mode 1: Benchmark
// ------------------------------------------------------------------

function BenchmarkMode() {
    const [leaderboard, setLeaderboard] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(null);

    const [syncing, setSyncing] = useState(false);
    const [syncMessage, setSyncMessage] = useState(null); // { type: 'success' | 'error', text }

    const fetchLeaderboard = useCallback(async () => {
        setLoading(true);
        setLoadError(null);
        try {
            const res = await fetch(`${API_BASE_URL}/analytics/metrics`);
            if (!res.ok) throw new Error(`Server responded ${res.status}`);
            const data = await res.json();
            setLeaderboard(data.leaderboard || []);
        } catch (err) {
            setLoadError(err.message || "Failed to load leaderboard.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchLeaderboard();
    }, [fetchLeaderboard]);

    const handleSyncAll = async () => {
        setSyncing(true);
        setSyncMessage(null);
        try {
            const res = await fetch(`${API_BASE_URL}/analytics/zoho/sync-all`, {
                method: "POST"
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data?.message || `Sync failed (${res.status})`);
            }
            setSyncMessage({
                type: "success",
                text: data?.message || "All records synced to Zoho successfully.",
            });
        } catch (err) {
            setSyncMessage({
                type: "error",
                text: err.message || "Failed to sync to Zoho.",
            });
        } finally {
            setSyncing(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h2 className="text-xl font-bold text-slate-900">Model Leaderboard</h2>
                    <p className="text-sm text-slate-500">
                        Aggregate accuracy, latency, and cost metrics per model.
                    </p>
                </div>
                <button
                    onClick={handleSyncAll}
                    disabled={syncing}
                    className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
                >
                    {syncing && <Spinner className="h-4 w-4 text-white" />}
                    {syncing ? "Syncing..." : "Sync All to Zoho"}
                </button>
            </div>

            {syncMessage && (
                <div
                    className={`rounded-lg border px-4 py-3 text-sm font-medium ${syncMessage.type === "success"
                        ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                        : "border-red-200 bg-red-50 text-red-700"
                        }`}
                >
                    {syncMessage.type === "success" ? "✅ " : "❌ "}
                    {syncMessage.text}
                </div>
            )}

            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                <table className="min-w-full divide-y divide-slate-200">
                    <thead className="bg-slate-50">
                        <tr>
                            <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                                Model
                            </th>
                            <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                                Avg. Accuracy
                            </th>
                            <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                                Avg. Latency
                            </th>
                            <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                                Cost / 1000 Bills
                            </th>
                            <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                                Bills Processed
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {loading && (
                            <tr>
                                <td colSpan={5} className="px-5 py-8 text-center text-sm text-slate-500">
                                    <div className="flex items-center justify-center gap-2">
                                        <Spinner className="h-4 w-4 text-slate-400" />
                                        Loading leaderboard...
                                    </div>
                                </td>
                            </tr>
                        )}

                        {!loading && loadError && (
                            <tr>
                                <td colSpan={5} className="px-5 py-8 text-center text-sm text-red-600">
                                    ⚠️ {loadError}
                                </td>
                            </tr>
                        )}

                        {!loading && !loadError && leaderboard.length === 0 && (
                            <tr>
                                <td colSpan={5} className="px-5 py-8 text-center text-sm text-slate-500">
                                    No leaderboard data yet.
                                </td>
                            </tr>
                        )}

                        {!loading &&
                            !loadError &&
                            leaderboard.map((row, idx) => (
                                <tr key={row.model_name ?? idx} className="hover:bg-slate-50">
                                    <td className="whitespace-nowrap px-5 py-3 text-sm font-semibold text-slate-800">
                                        {row.model_name}
                                    </td>
                                    <td className="whitespace-nowrap px-5 py-3 text-sm text-slate-600">
                                        {row.average_accuracy_percent?.toFixed
                                            ? row.average_accuracy_percent.toFixed(2)
                                            : row.average_accuracy_percent}
                                        %
                                    </td>
                                    <td className="whitespace-nowrap px-5 py-3 text-sm text-slate-600">
                                        {row.average_latency_seconds?.toFixed
                                            ? row.average_latency_seconds.toFixed(2)
                                            : row.average_latency_seconds}
                                        s
                                    </td>
                                    <td className="whitespace-nowrap px-5 py-3 text-sm text-slate-600">
                                        $
                                        {row.cost_per_1000_bills_usd?.toFixed
                                            ? row.cost_per_1000_bills_usd.toFixed(2)
                                            : row.cost_per_1000_bills_usd}
                                    </td>
                                    <td className="whitespace-nowrap px-5 py-3 text-sm text-slate-600">
                                        {row.total_bills_processed}
                                    </td>
                                </tr>
                            ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// ------------------------------------------------------------------
// Mode 2: Live Testing
// ------------------------------------------------------------------

const MODEL_CARDS = [
    { key: "gemini", name: "Gemini 2.0", live: true },
    { key: "gpt4o", name: "GPT-4o", live: false },
    { key: "claude", name: "Claude 3.5 Sonnet", live: false },
];

// Per-card state shape: { status, errorMessage, extractedJson, runId, zohoStatus, zohoMessage }
const initialCardState = {
    status: "idle", // idle | loading | success | error
    errorMessage: null,
    extractedJson: null,
    runId: null,
    zohoStatus: "idle", // idle | loading | success | error
    zohoMessage: null,
};

function ModelCard({ name, live, state, onCreateExpense }) {
    const isMocked = !live;

    return (
        <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
                <h3 className="font-bold text-slate-900">{name}</h3>
                {live ? (
                    <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-600">
                        Live
                    </span>
                ) : (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">
                        Mocked
                    </span>
                )}
            </div>

            <div className="flex-1">
                {state.status === "idle" && (
                    <p className="text-sm text-slate-400">
                        Run extraction to see results here.
                    </p>
                )}

                {state.status === "loading" && (
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                        <Spinner className="h-4 w-4 text-slate-400" />
                        Extracting...
                    </div>
                )}

                {state.status === "error" && isMocked && (
                    <p className="text-sm font-semibold text-amber-600">
                        🔒 API Key Unavailable
                    </p>
                )}

                {state.status === "error" && !isMocked && (
                    <p className="text-sm font-semibold text-red-600">
                        {state.errorMessage}
                    </p>
                )}

                {state.status === "success" && (
                    <pre className="max-h-64 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
                        {JSON.stringify(state.extractedJson, null, 2)}
                    </pre>
                )}
            </div>

            {live && state.status === "success" && (
                <div className="mt-4 space-y-2">
                    <button
                        onClick={onCreateExpense}
                        disabled={state.zohoStatus === "loading"}
                        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
                    >
                        {state.zohoStatus === "loading" && (
                            <Spinner className="h-4 w-4 text-white" />
                        )}
                        {state.zohoStatus === "loading"
                            ? "Creating..."
                            : "Create Expense in Zoho"}
                    </button>

                    {state.zohoStatus === "success" && (
                        <p className="text-xs font-medium text-emerald-700">
                            ✅ {state.zohoMessage || "Expense created in Zoho."}
                        </p>
                    )}
                    {state.zohoStatus === "error" && (
                        <p className="text-xs font-medium text-red-600">
                            ❌ {state.zohoMessage || "Failed to create expense in Zoho."}
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}

function LiveTestingMode() {
    const [file, setFile] = useState(null);
    const [running, setRunning] = useState(false);
    const [cardStates, setCardStates] = useState({
        gemini: { ...initialCardState },
        gpt4o: { ...initialCardState },
        claude: { ...initialCardState },
    });

    const updateCard = (key, patch) => {
        setCardStates((prev) => ({
            ...prev,
            [key]: { ...prev[key], ...patch },
        }));
    };

    const handleFileChange = (e) => {
        setFile(e.target.files?.[0] || null);
    };

    const runGeminiExtraction = async () => {
        updateCard("gemini", {
            status: "loading",
            errorMessage: null,
            extractedJson: null,
            runId: null,
            zohoStatus: "idle",
            zohoMessage: null,
        });

        try {
            const formData = new FormData();
            formData.append("file", file);

            const res = await fetch(`${API_BASE}/extract`, {
                method: "POST",
                body: formData,
            });

            if (res.status === 429 || res.status === 503) {
                updateCard("gemini", {
                    status: "error",
                    errorMessage: "⚠️ API Limit Exceeded. Please wait.",
                });
                return;
            }

            if (!res.ok) {
                throw new Error(`Extraction failed (${res.status})`);
            }

            const data = await res.json();
            updateCard("gemini", {
                status: "success",
                extractedJson: data.extracted_json,
                runId: data.run_id ?? null,
            });
        } catch (err) {
            // Network failure / fetch rejection also treated as limit/unavailable state
            updateCard("gemini", {
                status: "error",
                errorMessage: "⚠️ API Limit Exceeded. Please wait.",
            });
        }
    };

    const runMockedExtraction = (key) => {
        updateCard(key, {
            status: "error",
            errorMessage: "🔒 API Key Unavailable",
        });
    };

    const handleRunExtraction = async () => {
        if (!file) return;
        setRunning(true);

        // Mocked cards resolve immediately
        runMockedExtraction("gpt4o");
        runMockedExtraction("claude");

        // Live card
        await runGeminiExtraction();

        setRunning(false);
    };

    const handleCreateExpense = async () => {
        const runId = cardStates.gemini.runId;
        updateCard("gemini", { zohoStatus: "loading", zohoMessage: null });

        try {
            const res = await fetch(
                `${API_BASE}/leaderboard/zoho/create-expense/${runId}`,
                { method: "POST" }
            );
            const data = await res.json().catch(() => ({}));

            if (!res.ok) {
                throw new Error(data?.message || `Failed (${res.status})`);
            }

            updateCard("gemini", {
                zohoStatus: "success",
                zohoMessage: data?.message || "Expense created in Zoho.",
            });
        } catch (err) {
            updateCard("gemini", {
                zohoStatus: "error",
                zohoMessage: err.message || "Failed to create expense in Zoho.",
            });
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-xl font-bold text-slate-900">Live Testing</h2>
                <p className="text-sm text-slate-500">
                    Upload a receipt or bill and compare extraction results across models.
                </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                    <label className="flex-1">
                        <span className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">
                            Upload receipt / bill
                        </span>
                        <input
                            type="file"
                            accept="image/*,application/pdf"
                            onChange={handleFileChange}
                            className="block w-full cursor-pointer rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-600 file:mr-4 file:cursor-pointer file:rounded-lg file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-slate-800"
                        />
                    </label>

                    <button
                        onClick={handleRunExtraction}
                        disabled={!file || running}
                        className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60 transition-colors sm:mt-5"
                    >
                        {running && <Spinner className="h-4 w-4 text-white" />}
                        {running ? "Running..." : "Run Extraction"}
                    </button>
                </div>
                {file && (
                    <p className="mt-2 text-xs text-slate-500">
                        Selected: <span className="font-medium text-slate-700">{file.name}</span>
                    </p>
                )}
            </div>

            <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
                {MODEL_CARDS.map((card) => (
                    <ModelCard
                        key={card.key}
                        name={card.name}
                        live={card.live}
                        state={cardStates[card.key]}
                        onCreateExpense={handleCreateExpense}
                    />
                ))}
            </div>
        </div>
    );
}

// ------------------------------------------------------------------
// App shell
// ------------------------------------------------------------------

export default function App() {
    const [mode, setMode] = useState("benchmark");

    return (
        <div className="min-h-screen bg-slate-50">
            <header className="border-b border-slate-200 bg-white">
                <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                        <h1 className="text-lg font-bold text-slate-900">
                            Taxor Eval Framework
                        </h1>
                        <p className="text-xs text-slate-500">
                            Benchmark and live-test bill extraction models
                        </p>
                    </div>
                    <ModeToggle mode={mode} setMode={setMode} />
                </div>
            </header>

            <main className="mx-auto max-w-6xl px-6 py-8">
                {mode === "benchmark" ? <BenchmarkMode /> : <LiveTestingMode />}
            </main>
        </div>
    );
}