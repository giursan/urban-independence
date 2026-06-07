export interface Snapshot {
  summary: string;
  mood_trend: string;
  emotional_valence: number;
  engagement_level: number;
  loneliness_signal: number;
  conversational_markers: string;
  topics_of_interest: string[];
  highlights: string[];
  gentle_followups: string[];
  suggested_topics: string[];
  crisis_flags: string[];
  confidence: number;
  disclaimer: string;
}

export interface CompanionFact {
  id: string;
  category: string;
  title: string;
  content: string;
  tags: string[];
  importance: number;
  updated_at: string;
}
