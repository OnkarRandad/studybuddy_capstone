import { useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { API_BASE } from "@/config/api";
import { useNavigate } from "react-router-dom";

interface QuizModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId: string;
  courseId: string;
  onAddMessage: (content: string, role?: "user" | "assistant") => void;
}

export const QuizModal = ({ isOpen, onClose, userId, courseId, onAddMessage }: QuizModalProps) => {
  const [numQuestions, setNumQuestions] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [error, setError] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const navigate = useNavigate();

  const handleCreate = async () => {
    // Validate number of questions
    const count = parseInt(numQuestions);
    if (!numQuestions || isNaN(count) || count < 1) {
      setError("Please enter a valid number of questions (at least 1)");
      return;
    }

    setError("");
    setIsGenerating(true);

    try {
      const response = await fetch(`${API_BASE}/generate_quiz`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId,
          course_id: courseId,
          num_questions: count,
          difficulty: difficulty,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to generate quiz");
      }

      const data = await response.json();
      navigate(`/course/${courseId}/quiz`, { state: { quiz: data } });
    } catch (error) {
      setError(error instanceof Error ? error.message : "Failed to generate quiz");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create Quiz</DialogTitle>
          <DialogDescription>
            Customize your practice quiz based on your course materials
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Number of Questions */}
          <div className="space-y-2">
            <Label htmlFor="num-questions">Number of Questions</Label>
            <Input
              id="num-questions"
              type="number"
              min="1"
              placeholder="How many questions?"
              value={numQuestions}
              onChange={(e) => {
                setNumQuestions(e.target.value);
                setError("");
              }}
            />
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
          </div>

          {/* Difficulty Level */}
          <div className="space-y-2">
            <Label>Difficulty Level</Label>
            <RadioGroup value={difficulty} onValueChange={setDifficulty}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="easy" id="easy" />
                <Label htmlFor="easy" className="font-normal">
                  Easy
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="medium" id="medium" />
                <Label htmlFor="medium" className="font-normal">
                  Medium
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="hard" id="hard" />
                <Label htmlFor="hard" className="font-normal">
                  Hard
                </Label>
              </div>
            </RadioGroup>
          </div>
        </div>

        <div className="flex gap-3">
          <Button variant="outline" onClick={onClose} className="flex-1" disabled={isGenerating}>
            Cancel
          </Button>
          <Button onClick={handleCreate} className="flex-1" disabled={isGenerating}>
            {isGenerating ? "Generating..." : "Generate Quiz"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
