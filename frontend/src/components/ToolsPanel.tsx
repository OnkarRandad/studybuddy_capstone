import { Brain, FileText, Sparkles } from "lucide-react";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";
import { sendChatMessage } from "@/lib/api";

interface ToolsPanelProps {
  userId: string;
  courseId: string;
  onOpenQuizModal: () => void;
  onAddMessage: (content: string, role?: "user" | "assistant") => void;
}

export const ToolsPanel = ({
  userId,
  courseId,
  onOpenQuizModal,
  onAddMessage,
}: ToolsPanelProps) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const { toast } = useToast();

  const generateCheatSheet = async () => {
    if (isGenerating) return;
    setIsGenerating(true);

    try {
      const content = await sendChatMessage({
        user_id: userId,
        course_id: courseId,
        prompt: "Generate a cheat sheet from my uploaded materials.",
        mode: "guide",
      });
      onAddMessage(content);
    } catch (error) {
      toast({
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to generate cheat sheet",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const summarizeNotes = async () => {
    if (isGenerating) return;
    setIsGenerating(true);

    try {
      const content = await sendChatMessage({
        user_id: userId,
        course_id: courseId,
        prompt: "Summarize my uploaded course notes.",
        mode: "summary",
      });
      onAddMessage(content);
    } catch (error) {
      toast({
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to summarize notes",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const tools = [
    {
      id: "quiz",
      name: "Create Quiz",
      description: "Generate a practice quiz from your materials",
      icon: Brain,
      action: onOpenQuizModal, // updated
    },
    {
      id: "cheatsheet",
      name: "Generate Cheat Sheet",
      description: "Create a one-page summary for exam prep",
      icon: FileText,
      action: generateCheatSheet,
    },
    {
      id: "summarize",
      name: "Summarize Notes",
      description: "Get key points from your uploaded files",
      icon: Sparkles,
      action: summarizeNotes,
    },
  ];

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4">
        <h2 className="font-semibold text-foreground">Study Tools</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          AI-powered tools to enhance your learning
        </p>
      </div>

      {/* Tools List */}
      <div className="flex-1 space-y-3 p-4">
        {tools.map((tool) => (
          <button
            key={tool.id}
            onClick={tool.action}
            disabled={isGenerating}
            className="group w-full rounded-lg border bg-card p-4 text-left transition-all hover:border-primary hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 transition-colors group-hover:bg-primary/20">
              <tool.icon className="h-5 w-5 text-primary" />
            </div>
            <h3 className="mb-1 font-semibold text-card-foreground">
              {tool.name}
            </h3>
            <p className="text-sm text-muted-foreground">{tool.description}</p>
          </button>
        ))}
      </div>

      {/* Tips Section */}
      <div className="border-t bg-muted/30 p-4">
        <h3 className="mb-2 text-sm font-semibold text-foreground">
          Quick Tips
        </h3>
        <ul className="space-y-1 text-xs text-muted-foreground">
          <li>• Upload files to enhance AI responses</li>
          <li>• Create quizzes to test your knowledge</li>
          <li>• Generate cheat sheets before exams</li>
        </ul>
      </div>
    </div>
  );
};

