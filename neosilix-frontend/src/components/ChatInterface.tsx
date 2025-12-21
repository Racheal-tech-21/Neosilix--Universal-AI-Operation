import React, { useRef, useEffect } from "react";
import { ScrollArea } from "./ui/scroll-area";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Send, Brain, User, Bot, X, Minimize2, Maximize2 } from "lucide-react";
import clsx from "clsx";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  intelligence_level?: string;
  confidence?: number;
  question_type?: string;
  system_health?: number;
  recommendations?: any[];
  predicted_issues?: any[];
  targets_analysis?: any;
  user_id?: string;
}

interface ChatInterfaceProps {
  isOpen: boolean;
  onClose: () => void;
  sendMessage: (message: string) => Promise<void>;
  chatMessages: ChatMessage[];
  chatInput: string;
  setChatInput: (input: string) => void;
  isLoading: boolean;
  isChatExpanded: boolean;
  isChatMinimized: boolean;
  handleMinimize: () => void;
  handleExpand: () => void;
  aiIntelligence: string;
  getIntelligenceColor: (level: string) => string;
  getIntelligenceText: (level: string) => string;
  quickQuestions: string[];
}

const ChatInterface = ({
  isOpen,
  onClose,
  sendMessage,
  chatMessages,
  chatInput,
  setChatInput,
  isLoading,
  isChatExpanded,
  isChatMinimized,
  handleMinimize,
  handleExpand,
  aiIntelligence,
  getIntelligenceColor,
  getIntelligenceText,
  quickQuestions
}: ChatInterfaceProps) => {
  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  if (!isOpen) return null;

  return (
    <div 
      ref={chatContainerRef}
      className={clsx(
        "fixed bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 border border-cyan-500/30 rounded-2xl shadow-2xl ring-2 ring-cyan-400/20 flex flex-col backdrop-blur-sm transition-all duration-500 z-50",
        isChatMinimized ? "w-80 h-16 bottom-4 right-4" : 
        isChatExpanded ? "w-[95vw] h-[95vh] top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" : 
        "w-96 h-[600px] bottom-4 right-4",
        aiIntelligence === 'advanced_neural' && "ring-purple-400/30 border-purple-500/20",
        aiIntelligence === 'degraded' && "ring-gray-400/30 border-gray-500/20"
      )}
    >
      {/* Header */}
      <div 
        className={clsx(
          "flex items-center justify-between p-4 border-b border-cyan-500/20 rounded-t-2xl transition-all duration-500 cursor-pointer flex-shrink-0",
          aiIntelligence === 'advanced_neural' 
            ? "bg-gradient-to-r from-purple-900/40 to-cyan-900/40 hover:from-purple-800/50 hover:to-cyan-800/50" 
            : aiIntelligence === 'degraded'
            ? "bg-gradient-to-r from-gray-900/40 to-gray-800/40 hover:from-gray-800/50 hover:to-gray-700/50"
            : "bg-gradient-to-r from-cyan-900/30 to-purple-900/30 hover:from-cyan-800/40 hover:to-purple-800/40"
        )} 
        onClick={() => isChatMinimized && handleMinimize()}
      >
        <div className="flex items-center gap-3">
          <div className="relative">
            <Brain className={clsx(
              "w-6 h-6 transition-all duration-500",
              aiIntelligence === 'advanced_neural' 
                ? "text-purple-400" 
                : aiIntelligence === 'degraded'
                ? "text-gray-400"
                : "text-cyan-400"
            )} />
          </div>
          <div>
            <h3 className={clsx(
              "font-bold text-lg transition-all duration-500",
              aiIntelligence === 'advanced_neural' 
                ? "text-purple-300" 
                : aiIntelligence === 'degraded'
                ? "text-gray-300"
                : "text-cyan-300"
            )}>
              Neosilix AI 
            </h3>
            {!isChatMinimized && (
              <p className={clsx(
                "text-xs transition-all duration-500",
                aiIntelligence === 'advanced_neural' 
                  ? "text-purple-400" 
                  : aiIntelligence === 'degraded'
                  ? "text-gray-400"
                  : "text-cyan-400"
              )}>
                {getIntelligenceText(aiIntelligence)}
              </p>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleMinimize();
            }}
            className={clsx(
              "transition-all duration-300 hover:scale-110 min-w-8 h-8 flex items-center justify-center",
              aiIntelligence === 'advanced_neural' 
                ? "text-purple-300 hover:bg-purple-500/20" 
                : aiIntelligence === 'degraded'
                ? "text-gray-300 hover:bg-gray-500/20"
                : "text-cyan-300 hover:bg-cyan-500/20"
            )}
            title={isChatMinimized ? "Restore Chat" : "Minimize Chat"}
          >
            {isChatMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
          </Button>

          {!isChatMinimized && (
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                handleExpand();
              }}
              className={clsx(
                "transition-all duration-300 hover:scale-110 min-w-8 h-8 flex items-center justify-center",
                aiIntelligence === 'advanced_neural' 
                  ? "text-purple-300 hover:bg-purple-500/20" 
                  : aiIntelligence === 'degraded'
                  ? "text-gray-300 hover:bg-gray-500/20"
                  : "text-cyan-300 hover:bg-cyan-500/20"
              )}
              title={isChatExpanded ? "Contract Chat" : "Expand Chat"}
            >
              {isChatExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </Button>
          )}
          
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onClose();
            }}
            className={clsx(
              "transition-all duration-300 hover:scale-110 min-w-8 h-8 flex items-center justify-center",
              aiIntelligence === 'advanced_neural' 
                ? "text-purple-300 hover:bg-purple-500/20" 
                : aiIntelligence === 'degraded'
                ? "text-gray-300 hover:bg-gray-500/20"
                : "text-cyan-300 hover:bg-cyan-500/20"
            )}
            title="Close Chat"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {!isChatMinimized && (
        <div className="flex-1 flex flex-col min-h-0">
          {/* Chat Messages Area with Proper Scroll */}
          <div className="flex-1 overflow-hidden">
            <ScrollArea className="h-full w-full">
              <div className="p-4 space-y-4">
                {chatMessages.length === 0 && (
                  <div className="text-center py-8">
                    <Brain className={clsx(
                      "w-12 h-12 mx-auto mb-3 transition-all duration-500",
                      aiIntelligence === 'advanced_neural' 
                        ? "text-purple-400" 
                        : aiIntelligence === 'degraded'
                        ? "text-gray-400"
                        : "text-cyan-400"
                    )} />
                    <h4 className={clsx(
                      "font-semibold mb-2 transition-all duration-500",
                      aiIntelligence === 'advanced_neural' 
                        ? "text-purple-300" 
                        : aiIntelligence === 'degraded'
                        ? "text-gray-300"
                        : "text-cyan-300"
                    )}>
                      Neosilix AI Assistant Ready
                    </h4>
                    <p className={clsx(
                      "text-sm transition-all duration-500",
                      aiIntelligence === 'advanced_neural' 
                        ? "text-purple-400" 
                        : aiIntelligence === 'degraded'
                        ? "text-gray-400"
                        : "text-cyan-400"
                    )}>
                      Ask me anything about your infrastructure
                    </p>
                  </div>
                )}
                
                {chatMessages.map((message) => (
                  <div
                    key={message.id}
                    className={clsx(
                      "flex gap-3 transition-all duration-500 group",
                      message.role === "user" ? "justify-end" : "justify-start"
                    )}
                  >
                    {message.role === "assistant" && (
                      <div className={clsx(
                        "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all duration-500",
                        aiIntelligence === 'advanced_neural' 
                          ? "bg-gradient-to-br from-purple-500 to-pink-500" 
                          : aiIntelligence === 'degraded'
                          ? "bg-gradient-to-br from-gray-500 to-gray-600"
                          : "bg-gradient-to-br from-cyan-500 to-blue-500"
                      )}>
                        <Brain className="w-4 h-4 text-white" />
                      </div>
                    )}
                    
                    <div
                      className={clsx(
                        "max-w-[80%] rounded-2xl p-4 transition-all duration-500 group-hover:shadow-lg",
                        message.role === "user"
                          ? "bg-gradient-to-br from-cyan-500 to-blue-500 text-white rounded-tr-none"
                          : aiIntelligence === 'advanced_neural'
                          ? "bg-gradient-to-br from-purple-900/50 to-pink-900/30 border border-purple-500/20 rounded-tl-none"
                          : aiIntelligence === 'degraded'
                          ? "bg-gradient-to-br from-gray-800/50 to-gray-700/30 border border-gray-500/20 rounded-tl-none"
                          : "bg-gradient-to-br from-cyan-900/30 to-blue-900/30 border border-cyan-500/20 rounded-tl-none"
                      )}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        {message.role === "user" ? (
                          <User className="w-4 h-4" />
                        ) : (
                          <Bot className="w-4 h-4" />
                        )}
                        <span className="text-xs font-semibold opacity-80">
                          {message.role === "user" ? "You" : "Neural AI"}
                        </span>
                        {message.confidence && (
                          <span className={clsx(
                            "text-xs px-2 py-1 rounded-full",
                            message.confidence > 0.7 
                              ? "bg-green-500/20 text-green-300" 
                              : message.confidence > 0.4
                              ? "bg-yellow-500/20 text-yellow-300"
                              : "bg-red-500/20 text-red-300"
                          )}>
                            {Math.round(message.confidence * 100)}% confidence
                          </span>
                        )}
                      </div>
                      <p className="text-sm leading-relaxed break-words">{message.content}</p>
                      <div className="text-xs opacity-60 mt-2">
                        {message.timestamp.toLocaleTimeString()}
                      </div>
                    </div>

                    {message.role === "user" && (
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-gray-600 to-gray-700 flex items-center justify-center">
                        <User className="w-4 h-4 text-gray-300" />
                      </div>
                    )}
                  </div>
                ))}
                
                {isLoading && (
                  <div className="flex gap-3">
                    <div className={clsx(
                      "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
                      aiIntelligence === 'advanced_neural' 
                        ? "bg-gradient-to-br from-purple-500 to-pink-500" 
                        : aiIntelligence === 'degraded'
                        ? "bg-gradient-to-br from-gray-500 to-gray-600"
                        : "bg-gradient-to-br from-cyan-500 to-blue-500"
                    )}>
                      <Brain className="w-4 h-4 text-white" />
                    </div>
                    <div className={clsx(
                      "rounded-2xl p-4 rounded-tl-none",
                      aiIntelligence === 'advanced_neural'
                        ? "bg-gradient-to-br from-purple-900/50 to-pink-900/30 border border-purple-500/20"
                        : aiIntelligence === 'degraded'
                        ? "bg-gradient-to-br from-gray-800/50 to-gray-700/30 border border-gray-500/20"
                        : "bg-gradient-to-br from-cyan-900/30 to-blue-900/30 border border-cyan-500/20"
                    )}>
                      <div className="flex space-x-2">
                        <div className={clsx(
                          "w-2 h-2 rounded-full animate-pulse",
                          aiIntelligence === 'advanced_neural' 
                            ? "bg-purple-400" 
                            : aiIntelligence === 'degraded'
                            ? "bg-gray-400"
                            : "bg-cyan-400"
                        )}></div>
                        <div className={clsx(
                          "w-2 h-2 rounded-full animate-pulse delay-150",
                          aiIntelligence === 'advanced_neural' 
                            ? "bg-purple-400" 
                            : aiIntelligence === 'degraded'
                            ? "bg-gray-400"
                            : "bg-cyan-400"
                        )}></div>
                        <div className={clsx(
                          "w-2 h-2 rounded-full animate-pulse delay-300",
                          aiIntelligence === 'advanced_neural' 
                            ? "bg-purple-400" 
                            : aiIntelligence === 'degraded'
                            ? "bg-gray-400"
                            : "bg-cyan-400"
                        )}></div>
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={chatEndRef} />
              </div>
            </ScrollArea>
          </div>

          {/* Input Area */}
          <div className="p-4 border-t border-cyan-500/20 flex-shrink-0">
            <div className="mb-3">
              <ScrollArea className="max-w-full">
                <div className="flex gap-2 pb-2">
                  {quickQuestions.map((question, index) => (
                    <button
                      key={index}
                      onClick={() => sendMessage(question)}
                      disabled={isLoading}
                      className={clsx(
                        "flex-shrink-0 px-3 py-2 text-xs rounded-xl transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap",
                        aiIntelligence === 'advanced_neural'
                          ? "bg-purple-900/40 text-purple-300 hover:bg-purple-800/60 border border-purple-500/30"
                          : aiIntelligence === 'degraded'
                          ? "bg-gray-800/40 text-gray-300 hover:bg-gray-700/60 border border-gray-500/30"
                          : "bg-cyan-900/30 text-cyan-300 hover:bg-cyan-800/50 border border-cyan-500/30"
                      )}
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </ScrollArea>
            </div>
            
            <div className="flex gap-2">
              <Input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage(chatInput)}
                placeholder="Ask Neural AI about your infrastructure..."
                disabled={isLoading}
                className={clsx(
                  "flex-1 transition-all duration-500 border-0 focus:ring-2",
                  aiIntelligence === 'advanced_neural'
                    ? "bg-purple-900/20 text-purple-100 placeholder-purple-400 focus:ring-purple-500"
                    : aiIntelligence === 'degraded'
                    ? "bg-gray-800/20 text-gray-100 placeholder-gray-400 focus:ring-gray-500"
                    : "bg-cyan-900/20 text-cyan-100 placeholder-cyan-400 focus:ring-cyan-500"
                )}
              />
              <Button
                onClick={() => sendMessage(chatInput)}
                disabled={isLoading || !chatInput.trim()}
                className={clsx(
                  "transition-all duration-500 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed",
                  aiIntelligence === 'advanced_neural'
                    ? "bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
                    : aiIntelligence === 'degraded'
                    ? "bg-gradient-to-r from-gray-500 to-gray-600 hover:from-gray-600 hover:to-gray-700"
                    : "bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600"
                )}
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {isChatMinimized && (
        <div className="flex items-center justify-between px-4 py-2 flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className={clsx(
              "w-2 h-2 rounded-full",
              aiIntelligence === 'advanced_neural' ? "bg-purple-400" :
              aiIntelligence === 'degraded' ? "bg-yellow-400" :
              "bg-cyan-400"
            )} />
            <span className={clsx(
              "text-sm font-medium",
              aiIntelligence === 'advanced_neural' ? "text-purple-300" :
              aiIntelligence === 'degraded' ? "text-gray-300" :
              "text-cyan-300"
            )}>
              {chatMessages.length} messages
            </span>
          </div>
          {isLoading && (
            <div className="flex space-x-1">
              <div className={clsx(
                "w-1.5 h-1.5 rounded-full animate-pulse",
                aiIntelligence === 'advanced_neural' ? "bg-purple-400" :
                aiIntelligence === 'degraded' ? "bg-gray-400" :
                "bg-cyan-400"
              )}></div>
              <div className={clsx(
                "w-1.5 h-1.5 rounded-full animate-pulse delay-150",
                aiIntelligence === 'advanced_neural' ? "bg-purple-400" :
                aiIntelligence === 'degraded' ? "bg-gray-400" :
                "bg-cyan-400"
              )}></div>
              <div className={clsx(
                "w-1.5 h-1.5 rounded-full animate-pulse delay-300",
                aiIntelligence === 'advanced_neural' ? "bg-purple-400" :
                aiIntelligence === 'degraded' ? "bg-gray-400" :
                "bg-cyan-400"
              )}></div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ChatInterface;
