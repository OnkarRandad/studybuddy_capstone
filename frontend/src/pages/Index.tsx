import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BookOpen, Plus, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CourseCard } from "@/components/CourseCard";
import { DashboardCharts } from "@/components/DashboardCharts";
import { useSession } from "@/contexts/SessionContext";
import { useToast } from "@/hooks/use-toast";

const Index = () => {
  const navigate = useNavigate();
  const { userId, courses, setUserId, addCourse } = useSession();
  const { toast } = useToast();
  
  const [usernameInput, setUsernameInput] = useState("");
  const [courseNameInput, setCourseNameInput] = useState("");

  const handleSaveUsername = () => {
    if (!usernameInput.trim()) {
      toast({
        title: "Username required",
        description: "Please enter a username",
        variant: "destructive",
      });
      return;
    }
    setUserId(usernameInput.trim());
    toast({
      title: "Username saved",
      description: `Welcome, ${usernameInput}!`,
    });
  };

  const handleCreateCourse = () => {
    if (!userId) {
      toast({
        title: "Username required",
        description: "Please enter your username first",
        variant: "destructive",
      });
      return;
    }
    if (!courseNameInput.trim()) {
      toast({
        title: "Course name required",
        description: "Please enter a course name",
        variant: "destructive",
      });
      return;
    }
    
    const course = addCourse(courseNameInput.trim());
    toast({
      title: "Course created",
      description: `Created ${course.name}`,
    });
    setCourseNameInput("");
    navigate(`/course/${course.id}`);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
                <BookOpen className="h-6 w-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">Study Buddy AI</h1>
                <p className="text-sm text-muted-foreground">Agentic Learning Assistant</p>
              </div>
            </div>
            <Button variant="outline" size="sm">
              Settings
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {/* Username Section */}
        <section className="mb-8 rounded-xl border bg-card p-6">
          <div className="mb-4 flex items-center gap-2">
            <User className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">User Profile</h2>
          </div>
          {!userId ? (
            <div className="flex gap-2">
              <Input
                placeholder="Enter your username"
                value={usernameInput}
                onChange={(e) => setUsernameInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSaveUsername()}
              />
              <Button onClick={handleSaveUsername}>Save Username</Button>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <p className="text-foreground">
                Logged in as: <span className="font-semibold">{userId}</span>
              </p>
              <Button variant="outline" size="sm" onClick={() => setUserId("")}>
                Change Username
              </Button>
            </div>
          )}
        </section>

        {/* Create Course Section */}
        {userId && (
          <section className="mb-8 rounded-xl border bg-card p-6">
            <div className="mb-4 flex items-center gap-2">
              <Plus className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold text-foreground">Create New Course</h2>
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="Enter course name (e.g., Machine Learning)"
                value={courseNameInput}
                onChange={(e) => setCourseNameInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateCourse()}
              />
              <Button onClick={handleCreateCourse}>
                <Plus className="mr-2 h-4 w-4" />
                Create Course
              </Button>
            </div>
          </section>
        )}

        {/* Courses Section */}
        {userId && courses.length > 0 && (
          <section className="mb-12">
            <h2 className="mb-6 text-2xl font-bold text-foreground">Your Courses</h2>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {courses.map((course) => (
                <CourseCard
                  key={course.id}
                  course={{
                    id: course.id,
                    name: course.name,
                    color: "from-blue-500 to-purple-500",
                    studyHours: 0,
                    lastStudied: "Not yet",
                  }}
                  onClick={() => navigate(`/course/${course.id}`)}
                />
              ))}
            </div>
          </section>
        )}

        {/* Dashboard Analytics */}
        {userId && courses.length > 0 && <DashboardCharts />}
      </main>
    </div>
  );
};

export default Index;
