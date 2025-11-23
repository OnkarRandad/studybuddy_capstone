import { createContext, useContext, useState, ReactNode } from "react";

interface Course {
  id: string;
  name: string;
}

interface SessionContextType {
  userId: string | null;
  courses: Course[];
  setUserId: (userId: string) => void;
  addCourse: (name: string) => Course;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

const slugify = (text: string): string => {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
};

export const SessionProvider = ({ children }: { children: ReactNode }) => {
  const [userId, setUserIdState] = useState<string | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);

  const setUserId = (newUserId: string) => {
    setUserIdState(newUserId);
  };

  const addCourse = (name: string): Course => {
    const id = slugify(name);
    const newCourse: Course = { id, name };
    setCourses((prev) => [...prev, newCourse]);
    return newCourse;
  };

  return (
    <SessionContext.Provider value={{ userId, courses, setUserId, addCourse }}>
      {children}
    </SessionContext.Provider>
  );
};

export const useSession = () => {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
};
