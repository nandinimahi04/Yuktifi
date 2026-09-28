"use client";
import React, { useState } from "react";
import { MessageSquare, X, Send, Bot, Loader2, Mic } from "lucide-react";
import { api } from "@/lib/api-client";
import { useStore } from "@/lib/store";
import { motion, AnimatePresence } from "framer-motion";

export function CopilotOverlay() {
  const state = useStore();
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [messages, setMessages] = useState<{role: "user"|"ai", content: string, source?: string}[]>([
    { role: "ai", content: "Hi! I'm your YuktiFi AI Assistant. Ask me anything about your business plan or financial numbers.", source: "template" }
  ]);
  const [loading, setLoading] = useState(false);

  const startListening = () => {
    // SpeechRecognition is not in all TypeScript DOM lib configs — safe cast via any
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SpeechRecognitionAPI =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognitionAPI) {
      alert("Your browser does not support voice input. Try Chrome on Android or desktop.");
      return;
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const recognition: any = new SpeechRecognitionAPI();
    recognition.lang = 'en-IN';
    recognition.interimResults = false;
    
    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event: { results: { [0]: { [0]: { transcript: string } } } }) => {
      const transcript = event.results[0][0].transcript;
      setQuery(transcript);
    };
    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);
    recognition.start();
  };

  const handleSend = async () => {
    if (!query.trim()) return;
    if (!state.sessionId) {
      setMessages(prev => [...prev, { role: "ai", content: "Please complete your profile setup first to use the AI Copilot.", source: "system" }]);
      return;
    }
    
    const userMsg = query;
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setQuery("");
    setLoading(true);

    /*
      Removed `location_id: state.locationId || "Solapur"`.

      The copilot is the one place where a wrong input is not merely a wrong
      number on a card - it becomes the subject of generated prose. With a
      hardcoded city, a user in Nagpur would ask "how competitive is this
      market?" and receive a fluent, specific, entirely invented answer about
      Solapur, with the model's own confidence, because the model was told Solapur
      and had no reason to doubt it. The backend's numeric guard passes, because
      a location name is not a number that can be checked.

      Without a confirmed location the copilot now says it needs one. Asking the
      user is the correct behaviour; the model was never a source of location
      truth to begin with.
    */
    if (!state.locationId || !state.categoryId) {
      setMessages(prev => [
        ...prev,
        {
          role: "ai",
          content:
            "I need a confirmed location and business category before I can answer that — without them anything I said would be invented. Complete your profile first.",
          source: "system",
        },
      ]);
      return;
    }

    try {
      const res = await api.copilotChat({
        message: userMsg,
        location_id: state.locationId,
        category_id: state.categoryId
      });
      setMessages(prev => [...prev, { role: "ai", content: res.reply, source: "copilot" }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: "ai", content: "I'm sorry, I encountered an error while analyzing that.", source: "error" }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-6 right-6 bg-warm-primary text-warm-text p-4 rounded-full shadow-xl hover:bg-orange-600 transition-colors z-50 flex items-center justify-center border-2 border-white/20"
          >
            <MessageSquare size={24} />
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.9 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed bottom-6 right-6 w-96 h-[500px] bg-white border border-warm-border shadow-2xl rounded-2xl flex flex-col z-50 overflow-hidden font-sans"
          >
            <div className="bg-warm-primary p-4 text-warm-text flex justify-between items-center shadow-sm z-10">
              <div className="flex items-center space-x-2">
                <img
                  src="/yukti-logo-transparent.png"
                  alt="YuktiFi Logo"
                  className="h-7 w-7 object-contain"
                />
                <div className="flex flex-col justify-center">
                  <span className="font-bold text-base leading-tight">YuktiFi Copilot</span>
                  <span className="text-[6px] font-bold uppercase tracking-[0.1em] opacity-80 mt-0.5">Government of India Initiative</span>
                </div>
              </div>
              <button onClick={() => setIsOpen(false)} className="text-warm-text/80 hover:text-warm-text transition-colors bg-white/10 hover:bg-white/20 p-1.5 rounded-full">
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-5 bg-warm-bg">
              {messages.map((msg, i) => (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  key={i} 
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div className={`max-w-[85%] p-4 shadow-sm rounded-2xl ${msg.role === "user" ? "bg-warm-primary text-warm-text rounded-tr-sm" : "bg-white border border-warm-border text-warm-text rounded-tl-sm"}`}>
                    <p className="text-sm font-medium whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                    {msg.source && msg.role === "ai" && msg.source !== "template" && (
                      <div className="mt-2.5 text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-100 inline-block px-2.5 py-1 rounded-full uppercase tracking-wider">
                        Source: {msg.source}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
              {loading && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                  <div className="bg-white border border-warm-border p-4 rounded-2xl rounded-tl-sm shadow-sm flex items-center space-x-3">
                    <Loader2 size={18} className="animate-spin text-warm-primary" />
                    <span className="text-xs font-bold text-warm-muted uppercase tracking-wider">Processing...</span>
                  </div>
                </motion.div>
              )}
            </div>

            <div className="bg-white border-t border-warm-border flex flex-col z-10">
              <div className="flex space-x-2 overflow-x-auto px-4 py-3 scrollbar-hide border-b border-warm-border bg-warm-bg/50">
                <button 
                  onClick={() => setQuery("Please explain my score in Hindi.")}
                  className="whitespace-nowrap text-xs font-bold px-3 py-1.5 bg-white text-warm-primary hover:bg-orange-50 hover:border-warm-primary transition-colors border border-warm-border rounded-full shadow-sm"
                >
                  Translate to Hindi
                </button>
                <button 
                  onClick={() => setQuery("How can I improve my Loan Repayment Capacity?")}
                  className="whitespace-nowrap text-xs font-bold px-3 py-1.5 bg-white text-emerald-600 hover:bg-emerald-50 hover:border-emerald-300 transition-colors border border-warm-border rounded-full shadow-sm"
                >
                  Improve Loan Repayment Capacity
                </button>
              </div>
              <div className="p-4 flex items-center space-x-3 bg-white">
                <button
                  onClick={startListening}
                  className={`p-3 rounded-full transition-colors flex items-center justify-center shadow-sm border ${isListening ? 'bg-red-50 text-red-500 border-red-200 animate-pulse' : 'bg-warm-surface text-warm-muted border-warm-border hover:bg-warm-border hover:text-warm-text'}`}
                  title="Voice Input"
                >
                  <Mic size={18} />
                </button>
                <input
                  type="text"
                  placeholder="Ask a question..."
                  className="flex-1 px-4 py-3 border border-warm-border rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-warm-primary focus:border-transparent bg-warm-surface text-warm-text placeholder-warm-muted transition-all"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                />
                <button
                  onClick={handleSend}
                  disabled={!query.trim() || loading}
                  className="bg-warm-primary text-warm-text font-bold p-3 rounded-xl hover:bg-orange-600 transition-all disabled:opacity-50 disabled:bg-warm-muted flex items-center justify-center shadow-sm"
                >
                  <Send size={18} />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
