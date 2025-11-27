const API_BASE_URL = "http://localhost:8000";

export interface IngestParams {
  user_id: string;
  course_id: string;
  title: string;
  file: File;
}

export interface ChatParams {
  user_id: string;
  course_id: string;
  prompt: string;
  mode: string;
  difficulty?: string;
  num_items?: number;
}

export interface StatsResponse {
  [key: string]: any;
}

export const ingestFile = async (params: IngestParams): Promise<void> => {
  const formData = new FormData();
  formData.append("user_id", params.user_id);
  formData.append("course_id", params.course_id);
  formData.append("title", params.title);
  formData.append("file", params.file);

  const response = await fetch(`${API_BASE_URL}/ingest`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to ingest file: ${errorText}`);
  }
};

export const sendChatMessage = async (params: ChatParams): Promise<string> => {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Chat request failed: ${errorText}`);
  }

  const data = await response.json();
  return (
    data.content_md ||
    data.answer ||
    data.response ||
    data.output ||
    data.result ||
    JSON.stringify(data)
  );
};

export const getStats = async (
  userId: string,
  courseId: string
): Promise<StatsResponse> => {
  const response = await fetch(`${API_BASE_URL}/stats/${userId}/${courseId}`, {
    method: "GET",
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch stats: ${errorText}`);
  }

  return response.json();
};
