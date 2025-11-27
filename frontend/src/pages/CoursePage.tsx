import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, BookOpen, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FileUpload } from "@/components/FileUpload";
import { ChatInterface } from "@/components/ChatInterface";
import { ToolsPanel } from "@/components/ToolsPanel";
import { QuizModal } from "@/components/QuizModal";
import { useSession } from "@/contexts/SessionContext";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

const CoursePage = () => {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const { userId, courses } = useSession();
  const [isQuizModalOpen, setIsQuizModalOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);

  const course = courses.find((c) => c.id === courseId);

  const addMessage = (content: string, role: "user" | "assistant" = "assistant") => {
    const newMessage: Message = {
      id: Date.now().toString(),
      role,
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newMessage]);
  };

  if (!userId) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-background p-6">
        <Alert className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Please return to the home page and enter your username first.
          </AlertDescription>
        </Alert>
        <Button className="mt-4" onClick={() => navigate("/")}>
          Go to Home
        </Button>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-background p-6">
        <Alert className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Course not found. Please create this course from the home page.
          </AlertDescription>
        </Alert>
        <Button className="mt-4" onClick={() => navigate("/")}>
          Go to Home
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate("/")}
              >
                <ArrowLeft className="h-5 w-5" />
              </Button>
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                  <BookOpen className="h-5 w-5 text-primary-foreground" />
                </div>
                <h1 className="text-xl font-bold text-foreground">{course.name}</h1>
              </div>
            </div>
            <Button variant="outline" size="sm">
              Course Settings
            </Button>
          </div>
        </div>
      </header>

      {/* Three-pane layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Pane - Course Materials */}
        <div className="w-80 border-r bg-card">
          <FileUpload userId={userId} courseId={courseId!} />
        </div>

        {/* Middle Pane - Chatbot */}
        <div className="flex-1">
          <ChatInterface 
            userId={userId} 
            courseId={courseId!} 
            messages={messages}
            setMessages={setMessages}
          />
        </div>

        {/* Right Pane - Tools */}
        <div className="w-80 border-l bg-card">
          <ToolsPanel 
            userId={userId}
            courseId={courseId!}
            onOpenQuizModal={() => setIsQuizModalOpen(true)}
            onAddMessage={addMessage}
          />
        </div>
      </div>

      {/* Quiz Modal */}
      <QuizModal
        isOpen={isQuizModalOpen}
        onClose={() => setIsQuizModalOpen(false)}
        userId={userId}
        courseId={courseId!}
        onAddMessage={addMessage}
      />
    </div>
  );
};

export default CoursePage;
