import React, { useState, useEffect, useRef } from 'react';
import { 
  Shield, 
  ShieldAlert, 
  UploadCloud, 
  FileText, 
  Send, 
  RefreshCw, 
  AlertTriangle, 
  Search, 
  CheckCircle2, 
  ChevronDown, 
  ChevronUp,
  Sparkles,
  BookOpen,
  Info,
  ExternalLink,
  Flame,
  Eye,
  Archive,
  Droplet,
  Trash2,
  X,
  Layers
} from 'lucide-react';
import { 
  uploadSDS, 
  listDocuments, 
  searchSDS, 
  checkBackendHealth 
} from './services/api';

// ============================================================================
// RICH MARKDOWN RENDERER COMPONENT
// ============================================================================
function MarkdownRenderer({ text }) {
  if (!text) return null;

  // Split content into lines for structured block and inline parsing
  const lines = text.split('\n');
  const elements = [];
  let tableBuffer = [];
  let inList = false;

  const flushTable = (key) => {
    if (tableBuffer.length === 0) return null;
    const rows = [...tableBuffer];
    tableBuffer = [];

    // Separator row check without bracket-colon pattern to avoid Tailwind class scanning
    const isSeparatorRow = (r) => {
      const clean = r.replace(/\|/g, '').trim();
      return clean.length > 0 && clean.split('').every(ch => ch === '-' || ch === ':' || ch === ' ');
    };

    const parsedRows = rows
      .filter(r => !isSeparatorRow(r.trim()))
      .map(r => r.split('|').map(c => c.trim()).filter((c, idx, arr) => !(idx === 0 && c === '') && !(idx === arr.length - 1 && c === '')));

    if (parsedRows.length === 0) return null;

    const [header, ...body] = parsedRows;

    return (
      <div key={key} className="overflow-x-auto my-3 border border-slate-200 rounded-lg">
        <table className="min-w-full divide-y divide-slate-200 text-sm text-left">
          {header && (
            <thead className="bg-slate-50 text-slate-700 font-semibold">
              <tr>
                {header.map((col, cIdx) => (
                  <th key={cIdx} className="px-3 py-2 border-r border-slate-200 last:border-r-0">{col}</th>
                ))}
              </tr>
            </thead>
          )}
          <tbody className="divide-y divide-slate-100 bg-white">
            {body.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-slate-50">
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className="px-3 py-2 border-r border-slate-100 last:border-r-0 text-slate-800">{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const renderInline = (str) => {
    if (!str) return '';
    // Parse bold (**text**)
    const boldRegex = /\*\*(.*?)\*\*/g;
    const parts = [];
    let lastIdx = 0;
    let match;

    while ((match = boldRegex.exec(str)) !== null) {
      if (match.index > lastIdx) {
        parts.push(str.substring(lastIdx, match.index));
      }
      parts.push(
        <strong key={match.index} className="font-semibold text-slate-900">
          {match[1]}
        </strong>
      );
      lastIdx = boldRegex.lastIndex;
    }
    if (lastIdx < str.length) {
      parts.push(str.substring(lastIdx));
    }
    return parts.length > 0 ? parts : str;
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    // Table line detection
    if (line.startsWith('|') && line.endsWith('|')) {
      tableBuffer.push(line);
      continue;
    } else if (tableBuffer.length > 0) {
      elements.push(flushTable(`table-${i}`));
    }

    // Empty line
    if (!line) {
      elements.push(<div key={`space-${i}`} className="h-2" />);
      continue;
    }

    // Source Citation Line
    if (line.toLowerCase().startsWith('source:') || line.toLowerCase().startsWith('**source:**') || line.toLowerCase().startsWith('source :')) {
      elements.push(
        <div key={`source-${i}`} className="mt-4 pt-3 border-t border-slate-200 flex items-start gap-2 text-sm font-medium text-slate-600">
          <BookOpen className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
          <div className="text-slate-700">
            {renderInline(line)}
          </div>
        </div>
      );
      continue;
    }

    // Safety Alert / Callout line (Important, Warning, Caution, Hazard)
    if (line.startsWith('⚠️') || line.toLowerCase().startsWith('warning:') || line.toLowerCase().startsWith('caution:') || line.toLowerCase().startsWith('hazard:')) {
      elements.push(
        <div key={`alert-${i}`} className="my-2.5 p-3 bg-amber-50/80 border-l-4 border-amber-500 rounded-r-lg text-amber-950 text-sm leading-relaxed flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
          <div>{renderInline(line)}</div>
        </div>
      );
      continue;
    }

    // Headings (###, ##, #)
    if (line.startsWith('### ')) {
      elements.push(
        <h3 key={`h3-${i}`} className="text-base md:text-lg font-bold text-slate-900 mt-4 mb-2 first:mt-0 tracking-tight">
          {renderInline(line.substring(4))}
        </h3>
      );
      continue;
    }
    if (line.startsWith('## ')) {
      elements.push(
        <h2 key={`h2-${i}`} className="text-lg md:text-xl font-bold text-slate-900 mt-5 mb-2.5 first:mt-0 tracking-tight">
          {renderInline(line.substring(3))}
        </h2>
      );
      continue;
    }
    if (line.startsWith('# ')) {
      elements.push(
        <h1 key={`h1-${i}`} className="text-xl md:text-2xl font-extrabold text-slate-900 mt-6 mb-3 first:mt-0 tracking-tight">
          {renderInline(line.substring(2))}
        </h1>
      );
      continue;
    }

    // Bullet List (- or * or •)
    if (line.startsWith('- ') || line.startsWith('* ') || line.startsWith('• ')) {
      const bulletText = line.replace(/^[-*•]\s+/, '');
      elements.push(
        <div key={`bullet-${i}`} className="pl-2 py-1 flex items-start gap-2.5 text-[15px] leading-relaxed text-slate-800">
          <span className="h-2 w-2 rounded-full bg-blue-600 shrink-0 mt-2" />
          <div className="flex-1">{renderInline(bulletText)}</div>
        </div>
      );
      continue;
    }

    // Numbered List (1., 2., etc.)
    const numMatch = line.match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      const num = numMatch[1];
      const itemText = numMatch[2];
      elements.push(
        <div key={`num-${i}`} className="pl-2 py-1 flex items-start gap-2.5 text-[15px] leading-relaxed text-slate-800">
          <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-blue-800 text-xs font-bold shrink-0 mt-0.5">
            {num}
          </span>
          <div className="flex-1">{renderInline(itemText)}</div>
        </div>
      );
      continue;
    }

    // Regular Paragraph
    elements.push(
      <p key={`p-${i}`} className="text-[15px] leading-relaxed text-slate-800 py-1">
        {renderInline(rawLine)}
      </p>
    );
  }

  // Flush any trailing table
  if (tableBuffer.length > 0) {
    elements.push(flushTable('table-end'));
  }

  return <div className="space-y-0.5">{elements}</div>;
}

// ============================================================================
// MAIN APPLICATION
// ============================================================================
export default function App() {
  // Backend & Document State
  const [backendStatus, setBackendStatus] = useState('checking');
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Upload State
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadedDocInfo, setUploadedDocInfo] = useState(null);

  // Chat Conversation State
  const [messages, setMessages] = useState([]);
  const [inputQuestion, setInputQuestion] = useState('');
  const [lastQuestion, setLastQuestion] = useState('');
  const [loadingAnswer, setLoadingAnswer] = useState(false);
  const [chatError, setChatError] = useState('');
  const [expandedSources, setExpandedSources] = useState({});

  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loadingAnswer]);

  // Initial startup: check backend health and fetch documents
  useEffect(() => {
    checkHealth();
    fetchDocuments();
  }, []);

  const checkHealth = async () => {
    setBackendStatus('checking');
    const health = await checkBackendHealth();
    setBackendStatus(health.status);
  };

  const fetchDocuments = async () => {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
      if (docs.length > 0 && !selectedDocId) {
        setSelectedDocId(docs[0].id.toString());
      }
    } catch (e) {
      console.error("Failed to load documents list", e);
    }
  };

  const activeDocument = documents.find(d => d.id.toString() === selectedDocId);

  const handleDocChange = (docId) => {
    setSelectedDocId(docId);
    setMessages([]);
    setChatError('');
  };

  // Drag and Drop for Upload
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.toLowerCase().endsWith('.pdf')) {
        setSelectedFile(file);
        setUploadError('');
      } else {
        setUploadError('Only PDF files are supported.');
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.name.toLowerCase().endsWith('.pdf')) {
        setSelectedFile(file);
        setUploadError('');
      } else {
        setUploadError('Only PDF files are supported.');
      }
    }
  };

  const handleUploadSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!selectedFile) {
      setUploadError('Please choose a PDF file first.');
      return;
    }

    setUploading(true);
    setUploadError('');
    setUploadSuccess(false);

    try {
      const result = await uploadSDS(selectedFile);
      setUploadedDocInfo(result);
      setUploadSuccess(true);
      await fetchDocuments();
      setSelectedDocId(result.document_id.toString());
      setSelectedFile(null);
      setTimeout(() => {
        setShowUploadModal(false);
        setUploadSuccess(false);
      }, 1500);
    } catch (err) {
      setUploadError(err.message || 'Error uploading file.');
    } finally {
      setUploading(false);
    }
  };

  // Asking Questions
  const handleAsk = async (questionText) => {
    if (!questionText || !questionText.trim()) return;
    if (!selectedDocId) {
      setChatError('Please upload or select an active SDS document first.');
      return;
    }

    const cleanQuestion = questionText.trim();
    setLastQuestion(cleanQuestion);
    setInputQuestion('');
    setChatError('');

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: cleanQuestion,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages(prev => [...prev, userMsg]);
    setLoadingAnswer(true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, 300000); // 300s timeout (5 minutes for local CPU inference)

    try {
      const response = await fetch(`http://127.0.0.1:8000/api/v1/sds/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: parseInt(selectedDocId, 10),
          question: cleanQuestion,
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to query the RAG pipeline.');
      }

      const data = await response.json();
      const aiMsg = {
        id: Date.now() + 1,
        sender: 'ai',
        text: data.answer,
        foundInSds: data.found_in_sds,
        sources: data.sources || [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      clearTimeout(timeoutId);
      let errMsg = 'Failed to retrieve response.';
      if (err.name === 'AbortError') {
        errMsg = 'Response Timeout: The local Ollama server took longer than 5 minutes. Please check system resources.';
      } else {
        errMsg = err.message || 'Something went wrong while contacting ChemSafe AI.';
      }

      setChatError(errMsg);
      const errorMsg = {
        id: Date.now() + 1,
        sender: 'ai',
        text: `Error: ${errMsg}`,
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoadingAnswer(false);
    }
  };

  const handleRetry = () => {
    if (lastQuestion) {
      setMessages(prev => {
        if (prev.length > 0 && prev[prev.length - 1].sender === 'ai' && prev[prev.length - 1].isError) {
          return prev.slice(0, prev.length - 1);
        }
        return prev;
      });
      handleAsk(lastQuestion);
    }
  };

  const toggleSourceExpand = (msgId) => {
    setExpandedSources(prev => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  // Example questions for the empty state
  const exampleQuestions = [
    { label: "What are the main hazards?", icon: ShieldAlert },
    { label: "What PPE should I wear?", icon: Shield },
    { label: "What should I do if it gets in my eyes?", icon: Eye },
    { label: "How should this chemical be stored?", icon: Archive },
    { label: "Is this chemical flammable?", icon: Flame },
    { label: "What should I do if there is a spill?", icon: Droplet },
    { label: "How should I dispose of it?", icon: Trash2 },
    { label: "Can I store it near other chemicals?", icon: Layers },
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      
      {/* ==================================================================== */}
      {/* TOP NAVIGATION BAR */}
      {/* ==================================================================== */}
      <header className="sticky top-0 z-30 bg-white border-b border-slate-200 shadow-xs">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-xs">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-slate-900 tracking-tight leading-tight">ChemSafe AI</h1>
                <span className="px-2 py-0.5 text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 rounded-md">
                  SDS Assistant
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium hidden sm:block">
                Grounded Chemical Safety & Incident Intelligence
              </p>
            </div>
          </div>

          {/* Right Controls: Backend Status & Upload Button */}
          <div className="flex items-center gap-3">
            {/* Backend connection pill */}
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-600">
              <span className={`w-2 h-2 rounded-full ${backendStatus === 'healthy' ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
              <span>{backendStatus === 'healthy' ? 'Qwen3:1.7b Online' : 'Connecting...'}</span>
            </div>

            {/* Document Switcher or Upload Button */}
            <button
              onClick={() => setShowUploadModal(true)}
              className="flex items-center gap-2 px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg shadow-xs transition"
            >
              <UploadCloud className="w-4 h-4" />
              <span className="hidden sm:inline">Upload SDS</span>
            </button>
          </div>
        </div>
      </header>

      {/* ==================================================================== */}
      {/* ACTIVE SDS INDICATOR BANNER */}
      {/* ==================================================================== */}
      <section className="bg-white border-b border-slate-200 py-2.5 px-4">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-3 text-sm">
          
          {/* Active SDS Details */}
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-7 h-7 rounded-md bg-emerald-50 text-emerald-600 border border-emerald-200">
              <FileText className="w-4 h-4" />
            </div>
            {activeDocument ? (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active SDS:</span>
                <span className="font-semibold text-slate-900">{activeDocument.filename}</span>
                <span className="text-slate-300">•</span>
                <span className="text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md font-medium">
                  {activeDocument.pages_count} pages
                </span>
                <span className="text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md font-medium">
                  {activeDocument.sections_count} sections
                </span>
                <span className="text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md font-medium">
                  {activeDocument.chunks_count} chunks indexed
                </span>
              </div>
            ) : (
              <span className="text-slate-500 text-sm">No SDS active. Please upload an SDS to begin.</span>
            )}
          </div>

          {/* Quick Document Selector Dropdown */}
          {documents.length > 1 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 font-medium">Switch SDS:</span>
              <select
                value={selectedDocId}
                onChange={(e) => handleDocChange(e.target.value)}
                className="text-xs font-semibold bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {documents.map(d => (
                  <option key={d.id} value={d.id.toString()}>{d.filename}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      </section>

      {/* ==================================================================== */}
      {/* MAIN CHAT CONVERSATION AREA */}
      {/* ==================================================================== */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-4 md:p-6 flex flex-col justify-between">
        
        {/* Message Stream */}
        <div className="flex-1 space-y-6 pb-6">
          
          {/* EMPTY STATE: Welcoming intro + Suggested questions */}
          {messages.length === 0 && (
            <div className="pt-6 md:pt-12 text-center max-w-2xl mx-auto space-y-6">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-50 border border-blue-100 text-blue-600 mb-2">
                <Sparkles className="w-8 h-8" />
              </div>
              <div className="space-y-2">
                <h2 className="text-2xl md:text-3xl font-bold text-slate-900 tracking-tight">
                  Ask anything about your SDS
                </h2>
                <p className="text-sm md:text-base text-slate-600 leading-relaxed max-w-lg mx-auto">
                  ChemSafe AI retrieves verified context from your active document and explains critical safety precautions in clear, natural language.
                </p>
              </div>

              {/* Suggestions Grid */}
              <div className="pt-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
                  Suggested Safety Questions
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left">
                  {exampleQuestions.map((q, idx) => {
                    const IconComponent = q.icon;
                    return (
                      <button
                        key={idx}
                        onClick={() => handleAsk(q.label)}
                        disabled={loadingAnswer || !activeDocument}
                        className="p-3 bg-white hover:bg-blue-50/50 border border-slate-200 hover:border-blue-300 rounded-xl text-left text-sm font-medium text-slate-800 transition flex items-center gap-3 shadow-xs group disabled:opacity-50"
                      >
                        <div className="p-2 rounded-lg bg-slate-50 group-hover:bg-blue-100 text-slate-600 group-hover:text-blue-700 transition">
                          <IconComponent className="w-4 h-4" />
                        </div>
                        <span className="flex-1 text-slate-700 group-hover:text-slate-900">{q.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* CHAT MESSAGES STREAM */}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
            >
              {/* User Message Bubble */}
              {msg.sender === 'user' && (
                <div className="max-w-[85%] sm:max-w-[75%] bg-blue-600 text-white rounded-2xl rounded-br-xs px-4 py-3 shadow-xs">
                  <p className="text-[15px] leading-relaxed font-normal">{msg.text}</p>
                  <span className="text-[11px] text-blue-100 font-medium block text-right mt-1">
                    {msg.timestamp}
                  </span>
                </div>
              )}

              {/* AI Assistant Message Card */}
              {msg.sender === 'ai' && (
                <div className="w-full bg-white border border-slate-200 rounded-2xl rounded-tl-xs p-5 md:p-6 shadow-xs space-y-4">
                  
                  {/* Top Status Bar: AI Label + Grounding Badge */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-md bg-blue-600 text-white flex items-center justify-center text-xs font-bold">
                        <Shield className="w-3.5 h-3.5" />
                      </div>
                      <span className="text-sm font-bold text-slate-900">ChemSafe AI</span>
                      <span className="text-xs text-slate-400">• {msg.timestamp}</span>
                    </div>

                    {/* Grounding Status Pill */}
                    {!msg.isError && (
                      <div>
                        {msg.foundInSds ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                            Grounded in uploaded SDS
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                            Information not found in SDS
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* AI Response Text (Formatted Markdown) */}
                  <div className="text-slate-800 leading-relaxed">
                    {msg.isError ? (
                      <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-900 space-y-2">
                        <div className="flex items-center gap-2 font-semibold">
                          <AlertTriangle className="w-4 h-4 text-rose-600" />
                          <span>Generation Error</span>
                        </div>
                        <p className="text-sm text-rose-800">{msg.text.replace(/^Error:\s*/, '')}</p>
                        <button
                          onClick={handleRetry}
                          className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-medium rounded-lg transition"
                        >
                          <RefreshCw className="w-3.5 h-3.5" />
                          Retry Question
                        </button>
                      </div>
                    ) : (
                      <MarkdownRenderer text={msg.text} />
                    )}
                  </div>

                  {/* Collapsible Retrieved SDS Evidence Drawer */}
                  {!msg.isError && msg.sources && msg.sources.length > 0 && (
                    <div className="pt-2">
                      <button
                        onClick={() => toggleSourceExpand(msg.id)}
                        className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-blue-600 transition"
                      >
                        <span>View Retrieved SDS Evidence ({msg.sources.length} chunks)</span>
                        {expandedSources[msg.id] ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {expandedSources[msg.id] && (
                        <div className="mt-3 space-y-2.5 pt-2">
                          {msg.sources.map((src, sIdx) => (
                            <div
                              key={sIdx}
                              className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1.5"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2 font-semibold text-slate-700">
                                <span>Section {src.section_number}: {src.section_title}</span>
                                <span className="text-slate-500 font-normal">Page {src.page_number}</span>
                              </div>
                              <p className="text-slate-600 leading-relaxed font-mono bg-white p-2.5 rounded-lg border border-slate-200/80 whitespace-pre-wrap">
                                {src.text}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {/* AI Loading State Indicator */}
          {loadingAnswer && (
            <div className="w-full bg-white border border-slate-200 rounded-2xl rounded-tl-xs p-5 shadow-xs space-y-3">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-blue-600 text-white flex items-center justify-center text-xs font-bold">
                  <Shield className="w-3.5 h-3.5" />
                </div>
                <span className="text-sm font-bold text-slate-900">ChemSafe AI</span>
              </div>
              <div className="flex items-center gap-3 py-2 text-slate-600 text-sm">
                <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
                <span>ChemSafe AI is analyzing the SDS...</span>
                <span className="inline-flex gap-1 text-blue-600 font-extrabold text-lg leading-none">
                  <span className="animate-bounce">●</span>
                  <span className="animate-bounce" style={{ animationDelay: '0.2s' }}>●</span>
                  <span className="animate-bounce" style={{ animationDelay: '0.4s' }}>●</span>
                </span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* ==================================================================== */}
        {/* PINNED CHAT INPUT BAR */}
        {/* ==================================================================== */}
        <div className="sticky bottom-0 pt-2 pb-3 bg-slate-50/95 backdrop-blur-xs">
          {chatError && (
            <div className="mb-3 p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{chatError}</span>
              </div>
              {lastQuestion && (
                <button
                  onClick={handleRetry}
                  className="px-2.5 py-1 bg-rose-600 text-white font-medium rounded-md hover:bg-rose-700 transition"
                >
                  Retry
                </button>
              )}
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAsk(inputQuestion);
            }}
            className="flex items-center gap-2 bg-white border border-slate-300 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100 rounded-xl p-1.5 shadow-xs transition"
          >
            <input
              type="text"
              value={inputQuestion}
              onChange={(e) => setInputQuestion(e.target.value)}
              placeholder="Ask anything about your SDS (e.g. 'What PPE is required?', 'What are the main hazards?')..."
              disabled={loadingAnswer || !activeDocument}
              className="flex-1 px-3 py-2 text-[15px] text-slate-800 placeholder-slate-400 bg-transparent focus:outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loadingAnswer || !inputQuestion.trim() || !activeDocument}
              className="w-10 h-10 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white flex items-center justify-center transition shadow-xs shrink-0"
              title="Send question"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          <p className="text-center text-[11px] text-slate-500 mt-2">
            ChemSafe AI answers are strictly grounded in your active SDS. Always follow verified safety protocols and consult your safety officer.
          </p>
        </div>
      </main>

      {/* ==================================================================== */}
      {/* UPLOAD & DOCUMENT MANAGEMENT MODAL */}
      {/* ==================================================================== */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-lg w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                  <UploadCloud className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-base">Upload Safety Data Sheet</h3>
                  <p className="text-xs text-slate-500">Extracts 16 GHS sections, generates embeddings & indexes in FAISS</p>
                </div>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4">
              
              {/* Drag and drop zone */}
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition flex flex-col items-center justify-center gap-2.5 ${
                  dragActive
                    ? 'border-blue-500 bg-blue-50/50'
                    : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-slate-800">
                    {selectedFile ? selectedFile.name : 'Click to select or drag & drop SDS PDF'}
                  </p>
                  <p className="text-xs text-slate-500">Standard 16-section Safety Data Sheet (PDF format)</p>
                </div>
              </div>

              {/* Status messages */}
              {uploadError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}

              {uploadSuccess && uploadedDocInfo && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 space-y-1">
                  <div className="flex items-center gap-1.5 font-bold text-emerald-800">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>SDS Processed Successfully!</span>
                  </div>
                  <p className="text-emerald-700">
                    {uploadedDocInfo.filename} • {uploadedDocInfo.pages_count} pages • {uploadedDocInfo.sections_count} sections • {uploadedDocInfo.chunks_count} chunks indexed.
                  </p>
                </div>
              )}

              {/* Submit button */}
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleUploadSubmit}
                  disabled={uploading || !selectedFile}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-lg shadow-xs transition flex items-center gap-2"
                >
                  {uploading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Indexing SDS...</span>
                    </>
                  ) : (
                    <span>Process & Index PDF</span>
                  )}
                </button>
              </div>

              {/* Document Library Listing */}
              {documents.length > 0 && (
                <div className="pt-4 border-t border-slate-100 space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Existing Indexed Documents ({documents.length})
                  </p>
                  <div className="max-h-36 overflow-y-auto divide-y divide-slate-100 border border-slate-200 rounded-lg">
                    {documents.map((doc) => (
                      <div
                        key={doc.id}
                        className={`p-2.5 flex items-center justify-between text-xs transition ${
                          selectedDocId === doc.id.toString() ? 'bg-blue-50/70 font-semibold' : 'hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-center gap-2 truncate">
                          <FileText className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                          <span className="truncate text-slate-800">{doc.filename}</span>
                        </div>
                        <button
                          onClick={() => {
                            handleDocChange(doc.id.toString());
                            setShowUploadModal(false);
                          }}
                          className={`px-2 py-1 rounded text-[11px] font-medium transition ${
                            selectedDocId === doc.id.toString()
                              ? 'bg-blue-600 text-white'
                              : 'bg-slate-200 hover:bg-slate-300 text-slate-700'
                          }`}
                        >
                          {selectedDocId === doc.id.toString() ? 'Active' : 'Select'}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
