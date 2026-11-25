export interface MeetingSummary {
  id: string;
  title: string;
  date: string;
  duration: string;
  participants: number;
  status: 'Processed' | 'Scheduled' | 'Draft';
}

export interface TaskItem {
  id: string;
  title: string;
  dueDate: string;
  priority: 'High' | 'Medium' | 'Low';
  sourceMeeting: string;
  completed: boolean;
}

export interface CalendarEvent {
  id: string;
  title: string;
  time: string;
  platform: string;
  attendees: number;
}
