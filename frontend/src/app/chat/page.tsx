"use client";

import { useChat } from "@/hooks/use-chat";
import { ChatMessages } from "@/components/chat/chat-messages";
import { ChatInput } from "@/components/chat/chat-input";
import { QuickPrompts } from "@/components/chat/quick-prompts";
import { ContextPanel } from "@/components/chat/context-panel";
import { Button } from "@/components/ui/button";
import { PlusCircle } from "lucide-react";

export default function ChatPage() {
  const { messages, isLoading, sendMessage, evaluateMessage, retryMessage, clearChat } = useChat();

  // Lấy sources từ tin nhắn cuối cùng có chứa dữ liệu (bỏ qua pending/error không có source)
  const lastMessageWithSources = [...messages].reverse().find(m => m.role === "assistant" && m.sources);
  const currentSources = lastMessageWithSources?.sources || null;

  return (
    <div className="flex h-full overflow-hidden relative">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full bg-background relative z-0">
        
        <header className="px-4 py-3 border-b shrink-0 flex items-center justify-between bg-card/50 backdrop-blur-sm relative z-10">
          <div>
            <h1 className="text-lg font-bold tracking-tight">Trợ lý AI</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Phân tích thị trường vàng dựa trên dữ liệu giá &amp; tin tức thực tế
            </p>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={clearChat}
            disabled={messages.length === 0}
            className="h-8 border-border/50 bg-background/50 hover:bg-muted text-muted-foreground hover:text-foreground"
          >
            <PlusCircle className="h-4 w-4 mr-1.5" />
            Đoạn chat mới
          </Button>
        </header>

        <ChatMessages
          messages={messages}
          isLoading={isLoading}
          onEvaluate={evaluateMessage}
          onRetry={retryMessage}
          onFollowUp={sendMessage}
        />
        
        <div className="mt-auto shrink-0 relative z-10">
          {messages.length === 0 && (
            <QuickPrompts onSelect={sendMessage} />
          )}
          <ChatInput onSendMessage={sendMessage} isLoading={isLoading} />
        </div>
      </div>

      {/* Right Sidebar - Context Panel */}
      <div className="hidden lg:block w-64 shrink-0 h-full">
        <ContextPanel sources={currentSources} />
      </div>
    </div>
  );
}
