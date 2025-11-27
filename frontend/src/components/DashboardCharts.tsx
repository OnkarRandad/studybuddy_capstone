import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const timeData = [
  { name: "ML Fundamentals", value: 24 },
  { name: "Data Structures", value: 18 },
  { name: "Database Systems", value: 15 },
  { name: "Business Analytics", value: 21 },
];

const quizDataByCourse: Record<string, Array<{ week: string; score: number }>> = {
  "ML Fundamentals": [
    { week: "Week 1", score: 75 },
    { week: "Week 2", score: 82 },
    { week: "Week 3", score: 88 },
    { week: "Week 4", score: 91 },
    { week: "Week 5", score: 87 },
    { week: "Week 6", score: 93 },
  ],
  "Data Structures": [
    { week: "Week 1", score: 68 },
    { week: "Week 2", score: 73 },
    { week: "Week 3", score: 79 },
    { week: "Week 4", score: 85 },
    { week: "Week 5", score: 88 },
    { week: "Week 6", score: 90 },
  ],
  "Database Systems": [
    { week: "Week 1", score: 80 },
    { week: "Week 2", score: 85 },
    { week: "Week 3", score: 83 },
    { week: "Week 4", score: 89 },
    { week: "Week 5", score: 92 },
    { week: "Week 6", score: 95 },
  ],
  "Business Analytics": [
    { week: "Week 1", score: 72 },
    { week: "Week 2", score: 78 },
    { week: "Week 3", score: 84 },
    { week: "Week 4", score: 87 },
    { week: "Week 5", score: 91 },
    { week: "Week 6", score: 94 },
  ],
};

const streakData = [
  { name: "Completed", value: 12 },
  { name: "Remaining", value: 18 },
];

const COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
];

export const DashboardCharts = () => {
  const [selectedCourse, setSelectedCourse] = useState<string>("ML Fundamentals");
  const quizData = quizDataByCourse[selectedCourse];

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Time Distribution Chart - Now Pie Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Study Time Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={timeData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value}h`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {timeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px"
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Quiz Performance Chart - Now with Course Filter */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Quiz Performance Over Time</CardTitle>
            <Select value={selectedCourse} onValueChange={setSelectedCourse}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Select course" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ML Fundamentals">ML Fundamentals</SelectItem>
                <SelectItem value="Data Structures">Data Structures</SelectItem>
                <SelectItem value="Database Systems">Database Systems</SelectItem>
                <SelectItem value="Business Analytics">Business Analytics</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={quizData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis 
                dataKey="week" 
                tick={{ fill: "hsl(var(--muted-foreground))" }}
              />
              <YAxis 
                domain={[0, 100]} 
                tick={{ fill: "hsl(var(--muted-foreground))" }}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px"
                }}
              />
              <Line 
                type="monotone" 
                dataKey="score" 
                stroke="hsl(var(--chart-1))" 
                strokeWidth={3}
                dot={{ fill: "hsl(var(--chart-1))", r: 5 }}
                activeDot={{ r: 7 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Study Streak Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Study Streak Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={streakData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value} days`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {streakData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px"
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Study Completion Rate */}
      <Card>
        <CardHeader>
          <CardTitle>Weekly Study Completion</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].map((day, index) => {
              const completion = [100, 80, 100, 60, 100][index];
              return (
                <div key={day}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="text-muted-foreground">{day}</span>
                    <span className="font-medium text-foreground">{completion}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full bg-primary transition-all"
                      style={{ width: `${completion}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
