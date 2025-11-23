import { Clock, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface CourseCardProps {
  course: {
    id: string;
    name: string;
    color: string;
    studyHours: number;
    lastStudied: string;
  };
  onClick: () => void;
}

export const CourseCard = ({ course, onClick }: CourseCardProps) => {
  return (
    <div className="group relative overflow-hidden rounded-xl border bg-card shadow-sm transition-all hover:shadow-lg">
      <div className={`absolute inset-0 bg-gradient-to-br ${course.color} opacity-10 transition-opacity group-hover:opacity-20`} />
      <div className="relative p-6">
        <div className="mb-4">
          <h4 className="mb-2 text-xl font-semibold text-card-foreground">
            {course.name}
          </h4>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>{course.studyHours} hours studied</span>
          </div>
        </div>
        <div className="mb-4 text-sm text-muted-foreground">
          Last studied: {course.lastStudied}
        </div>
        <Button
          className="w-full"
          onClick={onClick}
        >
          Go to Course
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};
