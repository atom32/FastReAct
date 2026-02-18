/**
 * Vue Router configuration
 */

import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/chat",
  },
  {
    path: "/chat",
    name: "Chat",
    component: () => import("../views/ChatView.vue"),
    meta: {
      title: "Chat - FastReAct",
    },
  },
  {
    path: "/admin",
    name: "Admin",
    component: () => import("../views/AdminView.vue"),
    meta: {
      title: "Admin - FastReAct",
    },
  },
  {
    path: "/marketplace",
    name: "Marketplace",
    component: () => import("../views/MCPMarketplaceView.vue"),
    meta: {
      title: "MCP Marketplace - FastReAct",
    },
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach((to, _from, next) => {
  // Set page title
  if (to.meta.title) {
    document.title = to.meta.title as string;
  }
  next();
});

export default router;
