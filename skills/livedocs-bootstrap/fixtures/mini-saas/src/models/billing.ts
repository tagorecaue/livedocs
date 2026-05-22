// Subscription billing - simplified model for smoke-testing the skill
export interface Subscription {
  id: string;
  customerId: string;
  status: 'active' | 'paused' | 'cancelled';
  monthlyPriceCents: number;
  nextBillingDate: Date;
  cancelledAt: Date | null;
}

export interface Invoice {
  id: string;
  subscriptionId: string;
  status: 'draft' | 'open' | 'paid' | 'overdue' | 'void';
  amountCents: number;
  dueDate: Date;
  paidAt: Date | null;
}

export interface PaymentMethod {
  id: string;
  customerId: string;
  type: 'card' | 'bank_transfer' | 'pix';
  isDefault: boolean;
}
