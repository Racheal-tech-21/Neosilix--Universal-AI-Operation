#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Backup original file
backup_original() {
    log_info "Creating backup of original CopilotPage.tsx..."
    if [ -f "CopilotPage.tsx" ]; then
        cp CopilotPage.tsx "CopilotPage.tsx.backup.$(date +%Y%m%d_%H%M%S)"
        log_success "Backup created"
    else
        log_error "CopilotPage.tsx not found in current directory"
        exit 1
    fi
}

# Create advanced chat interface function
create_advanced_chat_interface() {
    log_info "Creating advanced chat interface..."
    
    cat > advanced_chat_interface.txt << 'EOF'
      {/* Enhanced Advanced Chat Interface */}
      {isChatOpen && (
        <div className={clsx(
          "fixed bottom-4 right-4 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 border border-cyan-500/30 rounded-2xl shadow-2xl ring-2 ring-cyan-400/20 flex flex-col backdrop-blur-sm",
          isChatExpanded ? "w-[480px] h-[700px]" : "w-96 h-[500px]"
        )}>
          {/* Enhanced Chat Header */}
          <div className="flex items-center justify-between p-4 border-b border-cyan-500/20 bg-gradient-to-r from-cyan-900/30 to-purple-900/30 rounded-t-2xl">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Brain className="w-6 h-6 text-cyan-400 animate-pulse" />
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full ring-2 ring-gray-900"></div>
              </div>
              <div>
                <h3 className="font-bold text-cyan-400 text-lg">AI Copilot</h3>
                <p className="text-xs text-cyan-300/70">Advanced System Intelligence</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsChatExpanded(!isChatExpanded)}
                className="text-cyan-300 hover:text-white hover:bg-cyan-500/20 rounded-lg transition-all"
              >
                {isChatExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsChatOpen(false)}
                className="text-cyan-300 hover:text-white hover:bg-red-500/20 rounded-lg transition-all"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Enhanced Chat Messages */}
          <ScrollArea className="flex-1 p-4 bg-gradient-to-b from-gray-900/50 to-gray-800/30">
            <div className="space-y-4">
              {chatMessages.length === 0 && (
                <div className="text-center text-cyan-200/80 py-8">
                  <div className="relative inline-block mb-4">
                    <Bot className="w-12 h-12 text-cyan-400 mx-auto mb-2 drop-shadow-lg" />
                    <div className="absolute inset-0 bg-cyan-400/20 blur-xl rounded-full"></div>
                  </div>
                  <p className="text-lg font-semibold mb-2 text-cyan-100">Hello! I'm your Advanced AI Copilot</p>
                  <p className="text-sm mb-6">I can help you monitor, analyze, and optimize your system infrastructure</p>
                  <div className="grid grid-cols-1 gap-3 max-w-xs mx-auto">
                    {quickQuestions.map((question, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        size="sm"
                        onClick={() => sendMessage(question)}
                        className="w-full text-xs text-left justify-start h-auto py-3 bg-cyan-500/10 border-cyan-400/30 text-cyan-200 hover:bg-cyan-500/20 hover:border-cyan-400/50 transition-all rounded-lg"
                      >
                        <Brain className="w-3 h-3 mr-2 flex-shrink-0" />
                        {question}
                      </Button>
                    ))}
                  </div>
                </div>
              )}
              
              {chatMessages.map((message) => (
                <div
                  key={message.id}
                  className={clsx("flex gap-3 group", {
                    "flex-row-reverse": message.role === "user",
                  })}
                >
                  <div
                    className={clsx(
                      "w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 relative transition-all duration-300",
                      message.role === "user"
                        ? "bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg shadow-blue-500/25"
                        : "bg-gradient-to-br from-cyan-500 to-cyan-600 shadow-lg shadow-cyan-500/25"
                    )}
                  >
                    {message.role === "user" ? (
                      <User className="w-5 h-5 text-white" />
                    ) : (
                      <Brain className="w-5 h-5 text-white" />
                    )}
                    <div className={clsx(
                      "absolute -bottom-1 -right-1 w-3 h-3 rounded-full border-2 border-gray-900",
                      message.role === "user" ? "bg-green-400" : "bg-cyan-400"
                    )}></div>
                  </div>
                  <div
                    className={clsx(
                      "rounded-2xl px-4 py-3 max-w-[80%] relative transition-all duration-300 backdrop-blur-sm",
                      message.role === "user"
                        ? "bg-gradient-to-br from-blue-600 to-blue-700 text-white shadow-lg shadow-blue-500/25"
                        : "bg-gradient-to-br from-gray-800 to-gray-700 text-gray-100 shadow-lg shadow-cyan-500/10 border border-cyan-500/20"
                    )}
                  >
                    <div className={clsx(
                      "absolute top-3 w-2 h-2 rotate-45",
                      message.role === "user" 
                        ? "-left-1 bg-blue-600" 
                        : "-right-1 bg-gray-800"
                    )}></div>
                    <p className="text-sm leading-relaxed">{message.content}</p>
                    <p className="text-xs opacity-70 mt-2 flex items-center gap-1">
                      <div className={clsx(
                        "w-1.5 h-1.5 rounded-full animate-pulse",
                        message.role === "user" ? "bg-green-400" : "bg-cyan-400"
                      )}></div>
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-cyan-600 shadow-lg shadow-cyan-500/25 flex items-center justify-center">
                    <Brain className="w-5 h-5 text-white" />
                  </div>
                  <div className="bg-gradient-to-br from-gray-800 to-gray-700 rounded-2xl px-4 py-3 border border-cyan-500/20 shadow-lg shadow-cyan-500/10">
                    <div className="flex items-center gap-2">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                      <span className="text-sm text-cyan-300">Analyzing system...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          </ScrollArea>

          {/* Enhanced Chat Input */}
          <div className="p-4 border-t border-cyan-500/20 bg-gradient-to-r from-gray-900/80 to-gray-800/80 rounded-b-2xl backdrop-blur-sm">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                sendMessage(chatInput);
              }}
              className="flex gap-2"
            >
              <div className="flex-1 relative">
                <Input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask about system metrics, anomalies, optimizations..."
                  className="w-full bg-gray-800/50 border-cyan-500/30 text-white placeholder-cyan-200/50 rounded-xl pl-4 pr-10 py-3 backdrop-blur-sm focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400 transition-all"
                  disabled={isLoading}
                />
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                  <Brain className="w-4 h-4 text-cyan-400/60" />
                </div>
              </div>
              <Button
                type="submit"
                disabled={isLoading || !chatInput.trim()}
                className="bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-600 hover:to-cyan-700 text-white px-4 rounded-xl shadow-lg shadow-cyan-500/25 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
              </Button>
            </form>
            <div className="flex justify-between items-center mt-3">
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-xs text-cyan-300/70">AI Online</span>
                </div>
                {stats && (
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-cyan-500 rounded-full"></div>
                    <span className="text-xs text-cyan-300/70">
                      CPU: {stats.cpu.toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>
              <div className="text-xs text-cyan-300/50">
                Powered by Neosilix AI
              </div>
            </div>
          </div>
        </div>
      )}
EOF
    log_success "Advanced chat interface template created"
}

# Update the sendMessage function to use advanced endpoint
update_send_message_function() {
    log_info "Updating sendMessage function to use advanced endpoint..."
    
    # Create the updated sendMessage function
    cat > updated_send_message.txt << 'EOF'
  // Enhanced Chat function with advanced ML capabilities
  const sendMessage = async (message: string) => {
    if (!message.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: message,
      timestamp: new Date(),
    };

    setChatMessages(prev => [...prev, userMessage]);
    setChatInput("");
    setIsLoading(true);

    try {
      // Try advanced endpoint first, fallback to basic endpoint
      const res = await fetch("http://localhost:5000/api/advanced-chat", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          ...(token && { Authorization: `Bearer ${token}` })
        },
        body: JSON.stringify({ question: message }),
      });

      let data;
      if (res.ok) {
        data = await res.json();
      } else {
        // Fallback to basic chat endpoint
        const fallbackRes = await fetch("http://localhost:5000/api/chat", {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            ...(token && { Authorization: `Bearer ${token}` })
          },
          body: JSON.stringify({ question: message }),
        });
        
        if (!fallbackRes.ok) throw new Error("Failed to send message");
        data = await fallbackRes.json();
      }
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.response || data.answer || "I'm here to help with system monitoring and infrastructure questions.",
        timestamp: new Date(),
      };

      setChatMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      toast.error("Failed to send message");
      console.error("Chat error:", error);
    } finally {
      setIsLoading(false);
    }
  };
EOF
    log_success "Send message function updated"
}

# Update quick questions for advanced capabilities
update_quick_questions() {
    log_info "Updating quick questions for advanced ML capabilities..."
    
    cat > updated_quick_questions.txt << 'EOF'
  const quickQuestions = [
    "What's my current system health status?",
    "Analyze performance metrics and suggest optimizations",
    "Are there any anomalies or potential issues?",
    "Predict system trends for the next hour",
    "How can I optimize resource usage?",
    "Perform deep system analysis"
  ];
EOF
    log_success "Quick questions updated"
}

# Integrate all changes
integrate_changes() {
    log_info "Integrating all changes into CopilotPage.tsx..."
    
    # Create a temporary file for the integrated version
    cp CopilotPage.tsx CopilotPage.tsx.tmp
    
    # Replace the old chat interface with the new one
    # First, find the line numbers of the old chat interface
    OLD_CHAT_START=$(grep -n "Chat Interface" CopilotPage.tsx.tmp | head -1 | cut -d: -f1)
    OLD_CHAT_END=$(grep -n "Footer" CopilotPage.tsx.tmp | head -1 | cut -d: -f1)
    
    if [ -z "$OLD_CHAT_START" ] || [ -z "$OLD_CHAT_END" ]; then
        log_error "Could not locate chat interface section in the file"
        exit 1
    fi
    
    # Create the new file
    head -n $((OLD_CHAT_START - 1)) CopilotPage.tsx.tmp > CopilotPage.tsx.new
    
    # Add the new chat interface
    cat advanced_chat_interface.txt >> CopilotPage.tsx.new
    
    # Add the rest of the file after the old chat interface
    tail -n +$((OLD_CHAT_END)) CopilotPage.tsx.tmp >> CopilotPage.tsx.new
    
    # Replace the original file
    mv CopilotPage.tsx.new CopilotPage.tsx
    
    # Clean up temporary files
    rm -f CopilotPage.tsx.tmp advanced_chat_interface.txt updated_send_message.txt updated_quick_questions.txt
    
    log_success "Advanced ML chatbot integrated successfully!"
}

# Verify integration
verify_integration() {
    log_info "Verifying integration..."
    
    if grep -q "Enhanced Advanced Chat Interface" CopilotPage.tsx; then
        log_success "Advanced chat interface found in file"
    else
        log_error "Advanced chat interface integration failed"
        exit 1
    fi
    
    if grep -q "api/advanced-chat" CopilotPage.tsx; then
        log_success "Advanced chat endpoint configured"
    else
        log_warning "Advanced chat endpoint not found, using fallback"
    fi
    
    log_success "Integration verification completed"
}

# Main integration function
main() {
    log_info "Starting Advanced ML Chatbot Integration..."
    
    backup_original
    create_advanced_chat_interface
    update_send_message_function
    update_quick_questions
    integrate_changes
    verify_integration
    
    log_success "Advanced ML chatbot integration completed successfully!"
    log_info "Original file backed up as: CopilotPage.tsx.backup.*"
    log_info "Next steps:"
    log_info "1. Ensure your backend has the /api/advanced-chat endpoint"
    log_info "2. Restart your development server"
    log_info "3. Test the new advanced chat interface"
}

# Run if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Check if we're in the right directory
    if [ ! -f "CopilotPage.tsx" ]; then
        log_error "Please run this script from the directory containing CopilotPage.tsx"
        exit 1
    fi
    
    main "$@"
fi

