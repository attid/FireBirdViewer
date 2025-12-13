<template>
  <Message severity="info" :closable="false" class="mt-4">
    <div class="flex flex-col gap-2">
      <span class="font-bold">Demo Access</span>
      <div class="text-sm">
        For access use:
        <ul class="list-disc list-inside mt-1">
          <li>Database: <b>firebird5:employee</b></li>
          <li>User: <b>demo</b></li>
          <li>Password: <b>demo</b></li>
        </ul>
      </div>
    </div>
  </Message>
</template>

<script setup>
import Message from 'primevue/message'
</script>
