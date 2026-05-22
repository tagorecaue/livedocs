<template>
  <div class="projects-page">
    <h1>Projects</h1>
    <button @click="createProject">New project</button>
    <ul>
      <li v-for="p in projects" :key="p.id">
        {{ p.title }} — {{ p.status }}
      </li>
    </ul>
  </div>
</template>
