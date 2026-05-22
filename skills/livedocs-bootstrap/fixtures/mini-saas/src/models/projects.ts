// Project management - simplified model
export interface Project {
  id: string;
  ownerId: string;
  title: string;
  status: 'draft' | 'active' | 'archived';
  createdAt: Date;
}

export interface Task {
  id: string;
  projectId: string;
  title: string;
  status: 'todo' | 'in_progress' | 'done';
  assigneeId: string | null;
  dueDate: Date | null;
}
