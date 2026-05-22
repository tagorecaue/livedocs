<template>
  <div class="billing-page">
    <h1>Billing</h1>
    <table>
      <thead>
        <tr>
          <th>Invoice</th>
          <th>Status</th>
          <th>Amount</th>
          <th>Due date</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="inv in invoices" :key="inv.id">
          <td>{{ inv.id }}</td>
          <td>{{ statusLabel(inv.status) }}</td>
          <td>{{ formatCents(inv.amountCents) }}</td>
          <td>{{ inv.dueDate }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
const statusLabel = (s: string) => ({
  draft: 'Draft',
  open: 'Open',
  paid: 'Paid',
  overdue: 'Overdue',
  void: 'Void',
}[s])
</script>
