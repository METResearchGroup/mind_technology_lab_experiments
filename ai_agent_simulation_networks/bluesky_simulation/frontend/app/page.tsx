'use client';

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Play, RotateCcw, Loader2 } from 'lucide-react';

interface SimulationState {
  current_turn: number;
  is_running: boolean;
  total_rounds: number;
  session_id: string;
}

interface Like {
  turn: number;
  agent_handle: string;
  liked_post_uri: string;
  reason: string;
}

interface Post {
  author_handle: string;
  text: string;
  created_at: string;
}

interface SimulationHistory {
  likes: Like[];
  posts: Post[];
}

export default function Home() {
  const [state, setState] = useState<SimulationState | null>(null);
  const [history, setHistory] = useState<SimulationHistory>({ likes: [], posts: [] });
  const [totalRounds, setTotalRounds] = useState(10);
  const [loading, setLoading] = useState(false);
  const [expandedTurns, setExpandedTurns] = useState<Set<number>>(new Set([0]));
  const [expandedAgents, setExpandedAgents] = useState<Record<number, Set<string>>>({});
  const [logs, setLogs] = useState<string[]>([]);
  const [logsExpanded, setLogsExpanded] = useState(true);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);

  const API_BASE = 'http://localhost:8000';

  useEffect(() => {
    fetchState();
    fetchHistory();

    // Cleanup event source on unmount
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, []);

  const fetchState = async () => {
    try {
      const res = await fetch(`${API_BASE}/simulation/state`);
      const data = await res.json();
      setState(data);
    } catch (error) {
      console.error('Error fetching state:', error);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/simulation/history`);
      const data = await res.json();
      setHistory(data);
    } catch (error) {
      console.error('Error fetching history:', error);
    }
  };

  const resetSimulation = async () => {
    setLoading(true);
    try {
      await fetch(`${API_BASE}/simulation/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ total_rounds: totalRounds }),
      });
      await fetchState();
      await fetchHistory();
      setExpandedTurns(new Set([0]));
      setExpandedAgents({});
      setLogs([]);
    } catch (error) {
      console.error('Error resetting simulation:', error);
    }
    setLoading(false);
  };

  const addLog = (message: string) => {
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  const runStep = async () => {
    setLoading(true);
    setLogs([]);

    try {
      // Start the simulation step
      const res = await fetch(`${API_BASE}/simulation/step`, { method: 'POST' });
      const data = await res.json();

      if (data.running) {
        addLog('⚠️ Simulation already running');
        setLoading(false);
        return;
      }

      addLog(`🚀 Starting Turn ${data.turn}`);

      // Connect to SSE endpoint for real-time updates
      const es = new EventSource(`${API_BASE}/simulation/events`);
      setEventSource(es);

      es.onmessage = (event) => {
        if (event.data.startsWith(':')) return; // Ignore heartbeat

        try {
          const eventData = JSON.parse(event.data);

          switch (eventData.type) {
            case 'turn_start':
              addLog(`📍 Turn ${eventData.data.turn} started`);
              break;

            case 'agent_start':
              addLog(`🤖 ${eventData.data.agent} - Starting turn ${eventData.data.turn}`);
              break;

            case 'agent_complete':
              addLog(`✅ ${eventData.data.agent} - Completed (${eventData.data.likes_count} likes, ${eventData.data.posts_count} posts)`);
              if (eventData.data.log) {
                addLog(`   Log: ${eventData.data.log.trim()}`);
              }
              // Fetch updated history incrementally
              fetchHistory();
              break;

            case 'agent_error':
              addLog(`❌ ${eventData.data.agent} - Error: ${eventData.data.error}`);
              break;

            case 'turn_complete':
              addLog(`🎉 Turn ${eventData.data.turn} completed`);
              fetchState();
              fetchHistory();
              // Auto-expand the new turn
              setExpandedTurns(prev => new Set([...prev, eventData.data.turn]));
              break;

            case 'simulation_complete':
              addLog(`🏁 Simulation complete at turn ${eventData.data.turn}`);
              break;

            case 'error':
              addLog(`💥 Error: ${eventData.data.error}`);
              break;
          }
        } catch (e) {
          console.error('Error parsing event:', e);
        }
      };

      es.onerror = () => {
        es.close();
        setEventSource(null);
        setLoading(false);
        addLog('📡 Event stream closed');
      };

    } catch (error) {
      console.error('Error running step:', error);
      addLog(`💥 Error: ${error}`);
      setLoading(false);
    }
  };

  const toggleTurn = (turn: number) => {
    setExpandedTurns(prev => {
      const newSet = new Set(prev);
      if (newSet.has(turn)) {
        newSet.delete(turn);
      } else {
        newSet.add(turn);
      }
      return newSet;
    });
  };

  const toggleAgent = (turn: number, agent: string) => {
    setExpandedAgents(prev => {
      const turnAgents = prev[turn] || new Set();
      const newTurnAgents = new Set(turnAgents);
      if (newTurnAgents.has(agent)) {
        newTurnAgents.delete(agent);
      } else {
        newTurnAgents.add(agent);
      }
      return { ...prev, [turn]: newTurnAgents };
    });
  };

  // Group history by turn
  const turnData: Record<number, { likes: Like[]; posts: Post[] }> = {};

  history.likes.forEach(like => {
    if (!turnData[like.turn]) {
      turnData[like.turn] = { likes: [], posts: [] };
    }
    turnData[like.turn].likes.push(like);
  });

  // Group agent data per turn
  const agentDataPerTurn: Record<number, Record<string, { likes: Like[]; posts: Post[] }>> = {};

  Object.entries(turnData).forEach(([turn, data]) => {
    const turnNum = parseInt(turn);
    agentDataPerTurn[turnNum] = {};

    data.likes.forEach(like => {
      if (!agentDataPerTurn[turnNum][like.agent_handle]) {
        agentDataPerTurn[turnNum][like.agent_handle] = { likes: [], posts: [] };
      }
      agentDataPerTurn[turnNum][like.agent_handle].likes.push(like);
    });
  });

  const turns = state ? Array.from({ length: state.current_turn }, (_, i) => i) : [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8">
          <h1 className="text-5xl font-bold text-white mb-2 bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-pink-400">
            Bluesky AI Agent Simulation
          </h1>
          <p className="text-slate-300">Social Science Research Platform</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Control Panel */}
          <div className="lg:col-span-1">
            <div className="bg-slate-800/50 backdrop-blur-lg rounded-2xl p-6 border border-slate-700 shadow-2xl">
              <h2 className="text-2xl font-semibold text-white mb-6">Control Panel</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Total Rounds
                  </label>
                  <input
                    type="number"
                    value={totalRounds}
                    onChange={(e) => setTotalRounds(parseInt(e.target.value))}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    min="1"
                    max="100"
                  />
                </div>

                <button
                  onClick={resetSimulation}
                  disabled={loading}
                  className="w-full px-4 py-3 bg-gradient-to-r from-red-500 to-pink-500 hover:from-red-600 hover:to-pink-600 text-white font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <RotateCcw size={20} />
                  Reset Simulation
                </button>

                <button
                  onClick={runStep}
                  disabled={loading || (state !== null && state.current_turn >= state.total_rounds)}
                  className="w-full px-4 py-3 bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {loading ? <Loader2 size={20} className="animate-spin" /> : <Play size={20} />}
                  {loading ? 'Running...' : 'Run Next Turn'}
                </button>
              </div>

              {state && (
                <div className="mt-6 p-4 bg-slate-700/50 rounded-lg">
                  <div className="text-sm text-slate-300 space-y-2">
                    <div className="flex justify-between">
                      <span>Current Turn:</span>
                      <span className="font-semibold text-white">{state.current_turn}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Total Rounds:</span>
                      <span className="font-semibold text-white">{state.total_rounds}</span>
                    </div>
                    <div className="w-full bg-slate-600 rounded-full h-2 mt-3">
                      <div
                        className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${(state.current_turn / state.total_rounds) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Logs Panel */}
              <div className="mt-6 bg-slate-700/50 rounded-lg overflow-hidden">
                <button
                  onClick={() => setLogsExpanded(!logsExpanded)}
                  className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-700 transition-colors"
                >
                  <span className="font-semibold text-white">Execution Logs</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">{logs.length} entries</span>
                    {logsExpanded ? <ChevronUp size={20} className="text-slate-300" /> : <ChevronDown size={20} className="text-slate-300" />}
                  </div>
                </button>

                {logsExpanded && (
                  <div className="px-4 pb-4 max-h-96 overflow-y-auto">
                    {logs.length === 0 ? (
                      <div className="text-center py-8 text-slate-400 text-sm">
                        No logs yet. Run a simulation step to see progress.
                      </div>
                    ) : (
                      <div className="space-y-1 font-mono text-xs">
                        {logs.map((log, idx) => (
                          <div
                            key={idx}
                            className={`p-2 rounded ${log.includes('❌') || log.includes('💥')
                                ? 'bg-red-900/20 text-red-300'
                                : log.includes('✅')
                                  ? 'bg-green-900/20 text-green-300'
                                  : log.includes('🚀') || log.includes('🎉')
                                    ? 'bg-blue-900/20 text-blue-300'
                                    : 'bg-slate-800/50 text-slate-300'
                              }`}
                          >
                            {log}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Simulation History */}
          <div className="lg:col-span-2">
            <div className="bg-slate-800/50 backdrop-blur-lg rounded-2xl p-6 border border-slate-700 shadow-2xl">
              <h2 className="text-2xl font-semibold text-white mb-6">Simulation History</h2>

              <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
                {turns.length === 0 ? (
                  <div className="text-center py-12 text-slate-400">
                    <p>No simulation data yet. Click "Run Next Turn" to start.</p>
                  </div>
                ) : (
                  turns.map(turn => {
                    const agents = Object.keys(agentDataPerTurn[turn] || {});
                    const isExpanded = expandedTurns.has(turn);

                    return (
                      <div key={turn} className="bg-slate-700/50 rounded-lg overflow-hidden">
                        <button
                          onClick={() => toggleTurn(turn)}
                          className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-700 transition-colors"
                        >
                          <span className="font-semibold text-white">Turn {turn}</span>
                          <div className="flex items-center gap-3">
                            <span className="text-sm text-slate-300">
                              {agents.length} agents active
                            </span>
                            {isExpanded ? <ChevronUp size={20} className="text-slate-300" /> : <ChevronDown size={20} className="text-slate-300" />}
                          </div>
                        </button>

                        {isExpanded && (
                          <div className="px-4 pb-4 space-y-2">
                            {agents.map(agent => {
                              const agentData = agentDataPerTurn[turn][agent];
                              const isAgentExpanded = expandedAgents[turn]?.has(agent);

                              return (
                                <div key={agent} className="bg-slate-600/50 rounded-lg overflow-hidden">
                                  <button
                                    onClick={() => toggleAgent(turn, agent)}
                                    className="w-full px-3 py-2 flex items-center justify-between hover:bg-slate-600 transition-colors"
                                  >
                                    <span className="text-sm font-medium text-purple-300">{agent}</span>
                                    <div className="flex items-center gap-2">
                                      <span className="text-xs text-slate-400">
                                        {agentData.likes.length} likes
                                      </span>
                                      {isAgentExpanded ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
                                    </div>
                                  </button>

                                  {isAgentExpanded && (
                                    <div className="px-3 pb-3 space-y-2">
                                      {agentData.likes.map((like, idx) => (
                                        <div key={idx} className="bg-slate-700/50 rounded p-2 text-xs">
                                          <div className="text-slate-300 mb-1">
                                            <span className="font-semibold text-blue-300">Liked:</span> {like.liked_post_uri.substring(0, 40)}...
                                          </div>
                                          <div className="text-slate-400 italic">
                                            "{like.reason}"
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
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
    </div>
  );
}
