<template>
  <div class="markdown-view" v-html="renderedMarkdown"></div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import MarkdownIt from "markdown-it";

const props = defineProps<{
  content: string;
}>();

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
});

const renderedMarkdown = computed(() => {
  if (!props.content) return "";
  return md.render(props.content);
});
</script>

<style scoped>
.markdown-view {
  line-height: 1.6;
  word-wrap: break-word;
}

.markdown-view :deep(h1),
.markdown-view :deep(h2),
.markdown-view :deep(h3),
.markdown-view :deep(h4),
.markdown-view :deep(h5),
.markdown-view :deep(h6) {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-view :deep(h1) {
  font-size: 1.5rem;
}

.markdown-view :deep(h2) {
  font-size: 1.25rem;
}

.markdown-view :deep(h3) {
  font-size: 1.125rem;
}

.markdown-view :deep(p) {
  margin-bottom: 0.75rem;
}

.markdown-view :deep(code) {
  padding: 0.125rem 0.25rem;
  background-color: var(--el-fill-color-light);
  border-radius: 0.25rem;
  font-family: monospace;
  font-size: 0.875em;
}

.markdown-view :deep(pre) {
  padding: 1rem;
  overflow-x: auto;
  background-color: var(--el-bg-color-page);
  border-radius: 0.5rem;
  margin-bottom: 1rem;
}

.markdown-view :deep(pre code) {
  padding: 0;
  background-color: transparent;
}

.markdown-view :deep(ul),
.markdown-view :deep(ol) {
  padding-left: 1.5rem;
  margin-bottom: 0.75rem;
}

.markdown-view :deep(li) {
  margin-bottom: 0.25rem;
}

.markdown-view :deep(a) {
  color: #409eff;
  text-decoration: none;
}

.markdown-view :deep(a:hover) {
  text-decoration: underline;
}

.markdown-view :deep(blockquote) {
  padding: 0.5rem 1rem;
  margin-bottom: 1rem;
  border-left: 4px solid var(--el-border-color);
  color: var(--el-text-color-secondary);
}

.markdown-view :deep(table) {
  width: 100%;
  margin-bottom: 1rem;
  border-collapse: collapse;
}

.markdown-view :deep(th),
.markdown-view :deep(td) {
  padding: 0.5rem;
  border: 1px solid var(--el-border-color);
}

.markdown-view :deep(th) {
  background-color: var(--el-fill-color-light);
  font-weight: 600;
}

.markdown-view :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 0.5rem;
}

.markdown-view :deep(hr) {
  margin: 1.5rem 0;
  border: none;
  border-top: 1px solid var(--el-border-color);
}
</style>
