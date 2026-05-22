<template>
  <div class="settings-page">
    <h1>Settings</h1>
    <section>
      <h2>Payment method</h2>
      <select v-model="defaultMethod">
        <option v-for="m in methods" :key="m.id" :value="m.id">
          {{ m.type }}
        </option>
      </select>
    </section>
  </div>
</template>
