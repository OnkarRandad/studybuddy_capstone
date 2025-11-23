import { useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function QuizPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const quiz = location.state?.quiz;

  if (!quiz) {
    return (
      <div className="p-6">
        <h2 className="text-xl font-semibold">Error</h2>
        <p>No quiz data found.</p>
        <Button className="mt-4" onClick={() => navigate(-1)}>
          Go Back
        </Button>
      </div>
    );
  }

  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);

  const handleChange = (qIndex, value) => {
    setAnswers((prev) => ({ ...prev, [qIndex]: value }));
  };

  const handleSubmit = () => {
    setSubmitted(true);
  };

  const score = quiz.questions.reduce((acc, q, i) => {
    if (q.correct_answer && answers[i] === q.correct_answer) return acc + 1;
    return acc;
  }, 0);

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">{quiz.title || "Quiz"}</h1>

      {quiz.questions.map((q, index) => (
        <Card key={index} className="p-4 mb-4">
          <h2 className="font-medium mb-2">
            {index + 1}. {q.question}
          </h2>

          {/* Multiple choice */}
          {q.options ? (
            <div className="space-y-2">
              {q.options.map((opt, optIndex) => (
                <label key={optIndex} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name={`q-${index}`}
                    value={opt}
                    onChange={() => handleChange(index, opt)}
                    disabled={submitted}
                  />
                  {opt}
                </label>
              ))}
            </div>
          ) : (
            /* Short Answer */
            <input
              type="text"
              className="border p-2 w-full rounded mt-2"
              placeholder="Type your answer"
              onChange={(e) => handleChange(index, e.target.value)}
              disabled={submitted}
            />
          )}

          {/* If submitted, show correct answer */}
          {submitted && (
            <p className="mt-3 text-sm">
              <strong>Correct answer:</strong> {q.correct_answer}
            </p>
          )}
        </Card>
      ))}

      {!submitted ? (
        <Button className="mt-4" onClick={handleSubmit}>
          Submit Quiz
        </Button>
      ) : (
        <div className="mt-6 text-xl font-semibold">
          Score: {score} / {quiz.questions.length}
        </div>
      )}
    </div>
  );
}
