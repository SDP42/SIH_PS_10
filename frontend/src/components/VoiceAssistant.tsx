import { useEffect, useRef, useState } from 'react';
import {
  Mic, MicOff, Send, Volume2, VolumeX, X, Sparkles, ShieldAlert,
  CheckCircle2, XCircle, Loader2, MessageSquare,
} from 'lucide-react';
import {
  askAssistant, confirmAssistantAction, getAssistantCapabilities,
  type AssistantReply, type AssistantPendingAction, type AssistantCapabilities,
} from '../api';

/**
 * Voice + text clinical terminology assistant.
 *
 * Speech-to-text and text-to-speech both run in the browser via the Web
 * Speech API — no external speech provider, no audio upload, no API key.
 * Voice and typing are two input methods for the same backend call, so the
 * assistant behaves identically either way and typing always remains
 * available even where speech recognition is unsupported.
 */

type AssistantState = 'READY' | 'LISTENING' | 'PROCESSING' | 'ANSWER' | 'ERROR';

// The Web Speech API is not in TypeScript's standard DOM lib, and is still
// vendor-prefixed in Chrome/Edge — declare only the surface we use.
interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start(): void;
  stop(): void;
  onresult: ((e: any) => void) | null;
  onerror: ((e: any) => void) | null;
  onend: (() => void) | null;
}

function getSpeechRecognition(): (new () => SpeechRecognitionLike) | null {
  if (typeof window === 'undefined') return null;
  const w = window as any;
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

const STATE_LABEL: Record<AssistantState, { text: string; color: string }> = {
  READY: { text: 'Ready', color: 'var(--text-muted)' },
  LISTENING: { text: 'Listening…', color: 'var(--danger)' },
  PROCESSING: { text: 'Processing…', color: 'var(--warning)' },
  ANSWER: { text: 'Answer', color: 'var(--success)' },
  ERROR: { text: 'Error', color: 'var(--danger)' },
};

const INTENT_LABEL: Record<string, string> = {
  PROJECT_FAQ: 'Project question',
  TERMINOLOGY_SEARCH: 'Terminology search',
  TRANSLATE_MAPPING: 'Mapping lookup',
  VALIDATE_CODE: 'Code validation',
  CLINICAL_TEXT: 'Clinical text',
  CREATE_CONDITION: 'Record action',
  UNKNOWN: 'Not understood',
};

export default function VoiceAssistant() {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<AssistantState>('READY');
  const [transcript, setTranscript] = useState('');
  const [input, setInput] = useState('');
  const [reply, setReply] = useState<AssistantReply | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [speaking, setSpeaking] = useState(false);
  const [caps, setCaps] = useState<AssistantCapabilities | null>(null);
  const [confirmResult, setConfirmResult] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const speechSupported = getSpeechRecognition() !== null;
  const synthSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  useEffect(() => {
    if (open && !caps) getAssistantCapabilities().then(setCaps).catch(() => {});
  }, [open, caps]);

  // Stop any in-flight speech when the panel closes, so a closed panel is
  // never still talking.
  useEffect(() => {
    if (!open && synthSupported) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
    }
  }, [open, synthSupported]);

  async function submit(text: string) {
    const q = text.trim();
    if (!q) return;
    setState('PROCESSING');
    setError(null);
    setReply(null);
    setConfirmResult(null);
    try {
      const r = await askAssistant(q);
      setReply(r);
      setState('ANSWER');
    } catch (e) {
      setError('Could not reach the assistant. Check that the backend is running.');
      setState('ERROR');
    }
  }

  function startListening() {
    const Recognition = getSpeechRecognition();
    if (!Recognition) return;

    const rec = new Recognition();
    rec.lang = 'en-IN';
    rec.interimResults = true;
    rec.continuous = false;
    recognitionRef.current = rec;

    setTranscript('');
    setError(null);
    setState('LISTENING');

    rec.onresult = (e: any) => {
      let text = '';
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript;
      setTranscript(text);
      // Only submit once the engine marks the utterance final, so we don't
      // fire a request on every interim word.
      if (e.results[e.results.length - 1].isFinal) {
        rec.stop();
        submit(text);
      }
    };
    rec.onerror = (e: any) => {
      setError(
        e?.error === 'not-allowed'
          ? 'Microphone permission was denied. You can still type your question below.'
          : 'Speech recognition failed. You can still type your question below.'
      );
      setState('ERROR');
    };
    rec.onend = () => {
      setState((s) => (s === 'LISTENING' ? 'READY' : s));
    };

    try {
      rec.start();
    } catch {
      setError('Could not start the microphone. You can still type your question below.');
      setState('ERROR');
    }
  }

  function stopListening() {
    recognitionRef.current?.stop();
    setState('READY');
  }

  function speak(text: string) {
    if (!synthSupported) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-IN';
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  }

  function stopSpeaking() {
    if (synthSupported) window.speechSynthesis.cancel();
    setSpeaking(false);
  }

  async function handleConfirm(action: AssistantPendingAction) {
    setConfirming(true);
    try {
      const r = await confirmAssistantAction(action);
      setConfirmResult(r.answer);
      setReply((prev) => (prev ? { ...prev, requires_confirmation: false } : prev));
    } catch {
      setConfirmResult('Could not save — you may need to sign in again.');
    } finally {
      setConfirming(false);
    }
  }

  function clearAll() {
    setTranscript('');
    setInput('');
    setReply(null);
    setError(null);
    setConfirmResult(null);
    setState('READY');
    stopSpeaking();
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        title="Ask the clinical terminology assistant"
        style={{
          position: 'fixed', right: 24, bottom: 24, zIndex: 900,
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'var(--gradient-brand, var(--accent))', color: '#fff',
          border: 'none', borderRadius: 999, padding: '13px 20px',
          fontSize: 14, fontWeight: 600, cursor: 'pointer',
          boxShadow: '0 6px 24px rgba(0,0,0,0.28)',
        }}
      >
        <Sparkles size={16} /> Ask the Assistant
      </button>
    );
  }

  const stateInfo = STATE_LABEL[state];

  return (
    <div
      style={{
        position: 'fixed', right: 24, bottom: 24, zIndex: 900,
        width: 'min(420px, calc(100vw - 48px))', maxHeight: 'min(680px, calc(100vh - 48px))',
        display: 'flex', flexDirection: 'column',
        background: 'var(--bg-card)', border: '1px solid var(--border)',
        borderRadius: 16, boxShadow: '0 12px 48px rgba(0,0,0,0.4)', overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 16px', borderBottom: '1px solid var(--border)' }}>
        <Sparkles size={16} style={{ color: 'var(--accent)' }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14 }}>Clinical Terminology Assistant</div>
          <div style={{ fontSize: 11, color: stateInfo.color, display: 'flex', alignItems: 'center', gap: 5 }}>
            {state === 'PROCESSING' && <Loader2 size={10} className="spin" />}
            {stateInfo.text}
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={clearAll} title="Clear"><X size={14} /></button>
        <button className="btn btn-ghost btn-sm" onClick={() => setOpen(false)} title="Close">✕</button>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px' }}>
        {!speechSupported && (
          <div className="demo-banner" style={{ marginBottom: 12, alignItems: 'flex-start', fontSize: 12 }}>
            <MicOff size={13} style={{ flexShrink: 0, marginTop: 2 }} />
            <span>
              Voice recognition is not supported in this browser. Please use Chrome or Edge, or type your question below.
            </span>
          </div>
        )}

        {transcript && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 10.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 4 }}>Transcript</div>
            <div style={{ fontSize: 13.5, fontStyle: 'italic', color: 'var(--text-secondary)' }}>“{transcript}”</div>
          </div>
        )}

        {error && (
          <div style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 10, padding: '10px 12px', fontSize: 12.5, color: 'var(--danger)', marginBottom: 12 }}>
            {error}
          </div>
        )}

        {reply && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
              <span className={`badge ${reply.intent === 'UNKNOWN' ? 'badge-pending' : 'badge-active'}`} style={{ fontSize: 10 }}>
                {INTENT_LABEL[reply.intent] || reply.intent}
              </span>
              <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>
                {reply.source === 'knowledge_base' ? 'from knowledge base' : reply.source === 'terminology_engine' ? 'from terminology engine' : ''}
              </span>
            </div>

            <div style={{ fontSize: 13.5, lineHeight: 1.6, marginBottom: 10 }}>{reply.answer}</div>

            {reply.suggestion && (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', background: 'var(--bg-input)', borderRadius: 8, padding: '9px 11px', marginBottom: 10 }}>
                {reply.suggestion}
              </div>
            )}

            {/* Clinical safety notice — shown whenever clinical text was interpreted */}
            {reply.intent === 'CLINICAL_TEXT' && (
              <div style={{ display: 'flex', gap: 8, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.28)', borderRadius: 8, padding: '9px 11px', marginBottom: 10 }}>
                <ShieldAlert size={13} style={{ color: 'var(--danger)', flexShrink: 0, marginTop: 2 }} />
                <span style={{ fontSize: 11.5, color: 'var(--text-secondary)' }}>
                  Symptoms only — no diagnosis is inferred. A clinician must confirm any coding.
                </span>
              </div>
            )}

            {/* Structured terminology results */}
            {Array.isArray(reply.data?.results) && reply.data.results.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                {reply.data.results.slice(0, 5).map((r: any, i: number) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                    <div style={{ fontSize: 12.5 }}>
                      {r.display}
                      {r.native_script && <span style={{ color: 'var(--accent)', marginLeft: 6 }}>{r.native_script}</span>}
                    </div>
                    <span className="td-code" style={{ fontSize: 11, whiteSpace: 'nowrap' }}>{r.code}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Dual-coding mapping results */}
            {Array.isArray(reply.data?.mappings) && reply.data.mappings.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                {reply.data.mappings.map((m: any, i: number) => (
                  <div key={i} style={{ padding: '7px 0', borderBottom: '1px solid var(--border)' }}>
                    <div style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>{m.target_system}</div>
                    {m.code ? (
                      <div style={{ fontSize: 12.5 }}>
                        <span className="td-code">{m.code}</span> — {m.display}
                        <span className={`badge badge-${m.equivalence === 'equivalent' ? 'equivalent' : 'related'}`} style={{ fontSize: 9.5, marginLeft: 6 }}>{m.equivalence}</span>
                      </div>
                    ) : (
                      <div style={{ fontSize: 12.5, color: 'var(--warning)' }}>No validated equivalent</div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Confirmation gate for data-changing actions */}
            {reply.requires_confirmation && reply.pending_action && (
              <div style={{ background: 'var(--bg-input)', border: '1px solid var(--warning)', borderRadius: 10, padding: '11px 12px', marginBottom: 10 }}>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 9 }}>
                  This will record clinical data. Nothing has been saved yet.
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-sm" style={{ background: '#16a34a', color: '#fff' }} disabled={confirming}
                    onClick={() => handleConfirm(reply.pending_action!)}>
                    <CheckCircle2 size={13} /> {confirming ? 'Saving…' : 'Confirm'}
                  </button>
                  <button className="btn btn-outline btn-sm" disabled={confirming}
                    onClick={() => { setReply({ ...reply, requires_confirmation: false }); setConfirmResult('Cancelled — nothing was saved.'); }}>
                    <XCircle size={13} /> Cancel
                  </button>
                </div>
              </div>
            )}

            {confirmResult && (
              <div style={{ fontSize: 12.5, color: 'var(--success)', marginBottom: 10 }}>{confirmResult}</div>
            )}

            {synthSupported && (
              <button className="btn btn-ghost btn-sm" onClick={() => (speaking ? stopSpeaking() : speak(reply.answer))}>
                {speaking ? <><VolumeX size={13} /> Stop</> : <><Volume2 size={13} /> Speak answer</>}
              </button>
            )}
          </div>
        )}

        {!reply && !error && caps && (
          <div>
            <div style={{ fontSize: 10.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 7 }}>Try asking</div>
            {[...caps.example_questions.slice(0, 3), ...caps.example_commands.slice(0, 3)].map((ex) => (
              <button key={ex} className="btn btn-ghost btn-sm"
                style={{ display: 'block', width: '100%', textAlign: 'left', marginBottom: 5, fontSize: 12 }}
                onClick={() => { setTranscript(ex); submit(ex); }}>
                {ex}
              </button>
            ))}
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10, lineHeight: 1.5 }}>
              {caps.safety_note}
            </div>
          </div>
        )}
      </div>

      {/* Footer: mic + text input, both always present */}
      <div style={{ borderTop: '1px solid var(--border)', padding: '12px 14px' }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button
            className="btn btn-sm"
            disabled={!speechSupported}
            title={speechSupported ? 'Start listening' : 'Speech recognition not supported in this browser'}
            onClick={state === 'LISTENING' ? stopListening : startListening}
            style={{
              background: state === 'LISTENING' ? 'var(--danger)' : 'var(--gradient-brand, var(--accent))',
              color: '#fff', flexShrink: 0, opacity: speechSupported ? 1 : 0.45,
            }}
          >
            {state === 'LISTENING' ? <MicOff size={14} /> : <Mic size={14} />}
          </button>
          <input
            className="input"
            placeholder="Ask anything, or type a command…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && input.trim()) { setTranscript(input); submit(input); setInput(''); } }}
            style={{ flex: 1, fontSize: 13 }}
          />
          <button className="btn btn-primary btn-sm" disabled={!input.trim()}
            onClick={() => { setTranscript(input); submit(input); setInput(''); }}>
            <Send size={13} />
          </button>
        </div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 7, display: 'flex', alignItems: 'center', gap: 5 }}>
          <MessageSquare size={10} />
          Speech runs in your browser — no audio leaves this device.
        </div>
      </div>
    </div>
  );
}
