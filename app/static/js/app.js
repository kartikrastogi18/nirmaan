/**
 * IMPORTANT: every permission check in this file (isManager(), canEditTask(),
 * hiding a "New task" button, etc.) is a UX convenience only -- it decides
 * what to *show*, never what to *allow*. The real enforcement is entirely
 * server-side (roles_required / project_access_required / the manager-vs-
 * assignee check in update_task). If this file got every check backwards,
 * the worst outcome is a confusing UI -- not a security hole -- because
 * the API re-checks everything itself regardless of what the UI sent.
 */

const state = {
  user: null,
  authMode: "login",
  projects: [],
  currentProject: null,
  tasks: [],
  team: [],
  allUsers: [],
  pendingUsers: [],
  messages: [],
  progressUpdates: [],
  files: [],
  activity: [],
  notifications: [],
  syncStatus: navigator.onLine ? "online" : "offline",
  lastSyncedAt: null,
};

const root = document.getElementById("app");

function isManager() {
  return !!state.user && (state.user.role === "boss" || state.user.role === "project_manager");
}

function isBoss() {
  return !!state.user && state.user.role === "boss";
}

function canPostProgress() {
  return !!state.user && ["boss", "project_manager", "contractor", "client"].includes(state.user.role);
}

function formatMoney(value) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value) || 0);
}

function roleLabel(role) {
  return {
    boss: "Boss / Director",
    project_manager: "Project Manager",
    architect: "Architect",
    contractor: "Contractor",
    client: "Client",
  }[role] || role;
}

/* ------------------------------- Rendering ------------------------------ */

function render() {
  mount(root, state.user ? renderShell() : renderAuthScreen());
}

function renderAuthScreen() {
  const isLogin = state.authMode === "login";
  return el("div", { class: "auth-screen" }, [
    el("div", { class: "auth-card" }, [
      el("div", { class: "brand" }, [
        el("div", { class: "brand-mark" }, ["N"]),
        el("div", {}, [
          el("p", { class: "brand-name" }, ["Nirmaan Software"]),
          el("p", { class: "brand-tag" }, ["Official Construction & Site Operations"]),
        ]),
      ]),
      el("div", { class: "instant-active-banner" }, [
        el("span", { class: "banner-icon" }, ["✓"]),
        el("span", {}, ["Clean Official Suite: Login with your assigned username and password."]),
      ]),
      el("div", { class: "auth-tabs" }, [
        el(
          "button",
          {
            class: isLogin ? "tab active" : "tab",
            type: "button",
            onclick: () => {
              state.authMode = "login";
              render();
            },
          },
          ["Log in"]
        ),
        el(
          "button",
          {
            class: !isLogin ? "tab active" : "tab",
            type: "button",
            onclick: () => {
              state.authMode = "register";
              render();
            },
          },
          ["Create Account"]
        ),
      ]),
      isLogin ? renderLoginForm() : renderRegisterForm(),
    ]),
  ]);
}

function renderLoginForm() {
  const usernameInput = el("input", {
    type: "text",
    placeholder: "Username (e.g. boss, kartik_pm, etc.)",
    autocomplete: "username",
    id: "login-username-input",
  });
  const passwordInput = el("input", {
    type: "password",
    placeholder: "Your password (default: 123456)",
    autocomplete: "current-password",
    id: "login-password-input",
  });

  const submit = async (e) => {
    e.preventDefault();
    const username = usernameInput.value.trim();
    const password = passwordInput.value;
    if (!username || !password) {
      showToast("Please enter both username and password.", "error");
      return;
    }
    try {
      const data = await apiRequest("/auth/login", {
        method: "POST",
        auth: false,
        body: { username, password },
      });
      setTokens(data);
      state.user = data.user;
      showToast(`Welcome back, ${data.user.name} (@${data.user.username || data.user.name}).`, "success");
      await loadProjects();
      if (state.projects.length) await selectProject(state.projects[0].id);
      else render();
      state.syncStatus = navigator.onLine ? "online" : "offline";
      state.lastSyncedAt = new Date();
      startAutoSync();
    } catch (_err) {
      // apiRequest displays real toast message
    }
  };

  const fillDemo = (user, pass) => {
    usernameInput.value = user;
    passwordInput.value = pass;
    usernameInput.focus();
  };

  return el("form", { class: "auth-form", onsubmit: submit }, [
    el("label", {}, ["Username", usernameInput]),
    el("label", {}, ["Password", passwordInput]),
    el("button", { class: "btn btn-primary", type: "submit", id: "login-submit-btn" }, ["Log in to Nirmaan"]),
    el("div", { class: "demo-section" }, [
      el("p", { class: "demo-heading" }, ["Quick Test Accounts (Click to autofill):"]),
      el("div", { class: "demo-pills" }, [
        el(
          "button",
          {
            type: "button",
            class: "demo-pill",
            id: "pill-boss",
            onclick: () => fillDemo("boss", "123456"),
          },
          [
            el("span", { class: "demo-pill-title" }, ["👑 Boss / Director"]),
            el("span", { class: "demo-pill-sub" }, ["boss · 123456"]),
          ]
        ),
        el(
          "button",
          {
            type: "button",
            class: "demo-pill",
            id: "pill-pm",
            onclick: () => fillDemo("kartik_pm", "123456"),
          },
          [
            el("span", { class: "demo-pill-title" }, ["👷 Kartik (Project Manager)"]),
            el("span", { class: "demo-pill-sub" }, ["kartik_pm · 123456"]),
          ]
        ),
        el(
          "button",
          {
            type: "button",
            class: "demo-pill",
            id: "pill-contractor",
            onclick: () => fillDemo("kartik_contractor", "123456"),
          },
          [
            el("span", { class: "demo-pill-title" }, ["🏗️ Kartik (Contractor)"]),
            el("span", { class: "demo-pill-sub" }, ["kartik_contractor · 123456"]),
          ]
        ),
        el(
          "button",
          {
            type: "button",
            class: "demo-pill",
            id: "pill-architect",
            onclick: () => fillDemo("kartik_arch", "123456"),
          },
          [
            el("span", { class: "demo-pill-title" }, ["📐 Kartik (Architect)"]),
            el("span", { class: "demo-pill-sub" }, ["kartik_arch · 123456"]),
          ]
        ),
        el(
          "button",
          {
            type: "button",
            class: "demo-pill",
            id: "pill-client",
            onclick: () => fillDemo("kartik_client", "123456"),
          },
          [
            el("span", { class: "demo-pill-title" }, ["🤝 Kartik (Client)"]),
            el("span", { class: "demo-pill-sub" }, ["kartik_client · 123456"]),
          ]
        ),
      ]),
    ]),
  ]);
}

function renderRegisterForm() {
  const nameInput = el("input", { type: "text", placeholder: "e.g. Rajesh Sharma", id: "reg-name" });
  const usernameInput = el("input", { type: "text", placeholder: "e.g. rajesh_pm (normal string)", id: "reg-username" });
  const phoneInput = el("input", { type: "tel", placeholder: "10-digit mobile number", id: "reg-phone" });
  const passwordInput = el("input", {
    type: "password",
    placeholder: "Choose password (min 6 chars)",
    id: "reg-password",
  });
  const roleSelect = el("select", { id: "reg-role" }, [
    el("option", { value: "project_manager" }, ["Project Manager"]),
    el("option", { value: "contractor" }, ["Contractor (Thekedar)"]),
    el("option", { value: "architect" }, ["Architect"]),
    el("option", { value: "client" }, ["Client"]),
    el("option", { value: "boss" }, ["Boss (Executive / Admin)"]),
  ]);

  const submit = async (e) => {
    e.preventDefault();
    const name = nameInput.value.trim();
    const username = usernameInput.value.trim().toLowerCase();
    const phone = phoneInput.value.trim();
    const password = passwordInput.value;
    const role = roleSelect.value;

    if (!name) {
      showToast("Please enter your name.", "error");
      return;
    }
    if (!username || username.length < 2) {
      showToast("Please enter a username (at least 2 characters).", "error");
      return;
    }
    if (!phone || phone.length < 8) {
      showToast("Please enter a valid phone number.", "error");
      return;
    }
    if (!password || password.length < 6) {
      showToast("Password must be at least 6 characters.", "error");
      return;
    }

    try {
      const data = await apiRequest("/auth/register", {
        method: "POST",
        auth: false,
        body: { name, username, phone, password, role },
      });
      // If tokens are returned, instantly log the user in
      if (data.access_token && data.user) {
        setTokens(data);
        state.user = data.user;
        showToast(`Account registered and activated! Welcome, ${data.user.name}.`, "success");
        await loadProjects();
        if (state.projects.length) await selectProject(state.projects[0].id);
        else render();
        state.syncStatus = navigator.onLine ? "online" : "offline";
        state.lastSyncedAt = new Date();
        startAutoSync();
      } else {
        showToast("Registration successful! You may now log in.", "success");
        state.authMode = "login";
        render();
      }
    } catch (_err) {
      /* apiRequest shows server toast */
    }
  };

  return el("form", { class: "auth-form", onsubmit: submit }, [
    el("label", {}, ["Full Name", nameInput]),
    el("label", {}, ["Username", usernameInput]),
    el("label", {}, ["Phone Number", phoneInput]),
    el("label", {}, ["Password", passwordInput]),
    el("label", {}, ["Role / Responsibility", roleSelect]),
    el("button", { class: "btn btn-primary", type: "submit", id: "register-submit-btn" }, ["Register & Activate Now"]),
    el("p", { class: "hint" }, ["All accounts activate immediately."]),
  ]);
}



function openDialog(title, content) {
  const close = () => { document.removeEventListener("keydown", onKey); backdrop.remove(); };
  const onKey = e => { if (e.key === "Escape") close(); };
  const closeBtn = el("button", { class: "btn btn-ghost", type: "button", onclick: close, "aria-label": "Close" }, ["×"]);
  const backdrop = el("div", { class: "dialog-backdrop" }, [el("div", { class: "dialog", role: "dialog", "aria-modal": "true", "aria-label": title }, [
    el("div", { class: "dialog-head" }, [el("h2", {}, [title]), closeBtn]), content
  ])]);
  document.addEventListener("keydown", onKey); document.body.appendChild(backdrop); closeBtn.focus();
}

function renderSyncStatus() {
  const labels = { online: "Online", syncing: "Syncing…", offline: "Offline" };
  const title = state.lastSyncedAt ? `Last synced ${state.lastSyncedAt.toLocaleTimeString()}` : "Internet synchronization status";
  return el("span", { class: `sync-status sync-${state.syncStatus}`, title, role: "status", "aria-live": "polite" }, [
    el("span", { class: "sync-dot", "aria-hidden": "true" }, []), labels[state.syncStatus] || "Online"
  ]);
}

function renderNotificationButton() {
  const unread = state.notifications.filter(n => !n.isRead).length;
  return el("button", { class: "btn btn-ghost notification-btn", title: "Notifications", "aria-label": `${unread} unread notifications`, onclick: openNotifications }, [unread ? `🔔 ${unread}` : "🔔"]);
}

function openNotifications() {
  const rows = state.notifications.length ? state.notifications.map(n => el("button", { class: `notification-row ${n.isRead ? "" : "unread"}`, onclick: async () => { if (!n.isRead) { await apiRequest(`/notifications/${n.id}/read`, { method: "PATCH" }); n.isRead=true; render(); } } }, [
    el("strong", {}, [n.text]), el("span", { class: "hint" }, [new Date(n.createdAt).toLocaleString()])
  ])) : [el("p", { class: "hint" }, ["No notifications yet."])];
  openDialog("Notifications", el("div", { class: "notification-list" }, rows));
}

async function loadNotifications() {
  try { const data = await apiRequest("/notifications"); state.notifications = data.notifications; } catch (_err) { state.notifications = []; }
}

function renderShell() {
  return el("div", { class: "shell" }, [
    el("header", { class: "topbar" }, [
      el("div", { class: "brand brand-compact" }, [
        el("div", { class: "brand-mark" }, ["N"]),
        el("div", {}, [
          el("p", { class: "brand-name" }, ["Nirmaan"]),
        ]),
      ]),
      el("div", { class: "topbar-user" }, [
        renderSyncStatus(),
        el("button", { class: "btn btn-ghost install-app-btn", type: "button", onclick: installNirmaan, title: "Install Nirmaan on this device" }, ["Install"]),
        renderNotificationButton(),
        el("div", { class: "user-pill" }, [
          el("span", { class: "user-name" }, [state.user.name]),
          state.user.username ? el("span", { class: "user-username-tag" }, [`@${state.user.username}`]) : null,
          el("span", { class: `badge role-badge role-badge-${state.user.role}` }, [roleLabel(state.user.role)]),
        ]),
        el(
          "button",
          {
            class: "btn btn-ghost logout-btn",
            id: "logout-btn",
            title: "Log out of Nirmaan",
            onclick: () => {
              clearTokens();
              stopAutoSync();
              state.user = null;
              state.projects = [];
              state.currentProject = null;
              render();
              showToast("You have been logged out successfully.", "info");
            },
          },
          ["Log out"]
        ),
      ]),
    ]),
    el("div", { class: "layout" }, [
      el("aside", { class: "sidebar" }, [renderSidebar()]),
      el("main", { class: "content" }, [
        state.currentProject ? renderProjectDetail() : renderEmptyState(),
      ]),
    ]),
  ]);
}

function renderSidebar() {
  const restricted = !isBoss();
  const children = [el("h2", { class: "sidebar-title" }, [restricted ? "Your Assigned Sites" : "All Project Sites"])];
  if (restricted) {
    children.push(el("p", { class: "hint assigned-sites-note" }, ["Only sites explicitly assigned to your username by the Boss are visible."]));
  }

  children.push(
    el(
      "div",
      { class: "project-list" },
      state.projects.map((p) => {
        const singleAssignedSite = restricted && state.projects.length === 1;
        const attrs = { class: "project-item" + (state.currentProject && state.currentProject.id === p.id ? " active" : "") + (singleAssignedSite ? " single-assigned" : "") };
        if (!singleAssignedSite) attrs.onclick = () => selectProject(p.id);
        if (singleAssignedSite) attrs.disabled = true;
        return el("button", attrs, [
          el("span", { class: "site-tag" }, [singleAssignedSite ? `Your Assigned Site · ${p.siteCode}` : `Site ${p.siteCode}`]),
          el("span", { class: "project-name" }, [p.name]),
          el("span", { class: `status-pill status-${p.status}` }, [p.status.replace("_", " ")]),
        ]);
      })
    )
  );

  if (state.projects.length === 0) {
    children.push(
      el("div", { class: "no-sites-card" }, [
        el("strong", {}, ["No Assigned Sites"]),
        el("p", { class: "hint" }, [
          restricted
            ? `Your username (@${state.user.username || state.user.name}) has not been assigned to any project sites yet. Please ask the Boss / Director to grant site access.`
            : "No project sites created yet. Use the form below to add your first site."
        ]),
      ])
    );
  }

  if (isBoss()) {
    children.push(
      el("div", { class: "boss-sidebar-actions" }, [
        el(
          "button",
          {
            class: "btn btn-primary btn-small provision-btn-sidebar",
            type: "button",
            id: "sidebar-provision-btn",
            onclick: openBossUserProvisionDialog,
          },
          ["+ Provision New User"]
        ),
      ])
    );
    children.push(renderCreateProjectForm());
    children.push(renderPendingApprovals());
  }

  return el("div", {}, children);
}

function renderCreateProjectForm() {
  const codeInput = el("input", { type: "text", placeholder: "Site code (e.g. GV-02)", maxlength: "10", id: "new-site-code" });
  const nameInput = el("input", { type: "text", placeholder: "Project name", id: "new-site-name" });
  const budgetInput = el("input", { type: "number", placeholder: "Budget (INR)", id: "new-site-budget" });

  const submit = async (e) => {
    e.preventDefault();
    try {
      const data = await apiRequest("/projects", {
        method: "POST",
        body: {
          siteCode: codeInput.value.trim(),
          name: nameInput.value.trim(),
          budget: Number(budgetInput.value) || 0,
        },
      });
      showToast(`Site ${data.project.siteCode} (${data.project.name}) created successfully.`, "success");
      codeInput.value = "";
      nameInput.value = "";
      budgetInput.value = "";
      await loadProjects();
      render();
    } catch (_err) {
      /* toasted already */
    }
  };

  return el("form", { class: "inline-form", onsubmit: submit }, [
    el("h3", {}, ["Add Project Site (Boss Exclusive)"]),
    codeInput,
    nameInput,
    budgetInput,
    el("button", { class: "btn btn-primary btn-small", type: "submit", id: "create-site-submit-btn" }, ["Create Site"]),
  ]);
}

function renderPendingApprovals() {
  const wrap = el("div", { class: "pending-section" }, [
    el("div", { class: "panel-header" }, [
      el("h3", {}, ["Pending approvals"]),
      el(
        "button",
        {
          class: "btn btn-small btn-ghost",
          type: "button",
          onclick: async () => {
            await loadPendingUsers();
            render();
          },
        },
        ["Refresh"]
      ),
    ]),
  ]);

  if (!state.pendingUsers || state.pendingUsers.length === 0) {
    wrap.appendChild(el("p", { class: "hint" }, ["Nobody waiting."]));
    return wrap;
  }

  for (const u of state.pendingUsers) {
    wrap.appendChild(
      el("div", { class: "pending-row" }, [
        el("div", {}, [
          el("p", { class: "pending-name" }, [u.name]),
          el("p", { class: "hint" }, [`${roleLabel(u.role)} · `, el("span", { class: "id-tag" }, [u.id])]),
        ]),
        el(
          "button",
          {
            class: "btn btn-small",
            onclick: async () => {
              try {
                await apiRequest(`/auth/users/${u.id}/approve`, { method: "POST" });
                showToast(`${u.name} approved.`, "success");
                await loadPendingUsers();
                render();
              } catch (_err) {
                /* toasted already */
              }
            },
          },
          ["Approve"]
        ),
      ])
    );
  }
  return wrap;
}

function openBossUserProvisionDialog() {
  const usernameInput = el("input", {
    type: "text",
    placeholder: "e.g. vikram_contractor (normal string)",
    id: "prov-username",
    required: true,
  });
  const nameInput = el("input", {
    type: "text",
    placeholder: "e.g. Vikram Sharma",
    id: "prov-name",
    required: true,
  });
  const passwordInput = el("input", {
    type: "password",
    placeholder: "Password (min 6 chars)",
    id: "prov-password",
    value: "123456",
    required: true,
  });
  const roleSelect = el("select", { id: "prov-role" }, [
    el("option", { value: "project_manager" }, ["Project Manager"]),
    el("option", { value: "contractor" }, ["Contractor (Thekedar)"]),
    el("option", { value: "architect" }, ["Architect"]),
    el("option", { value: "client" }, ["Client"]),
    el("option", { value: "boss" }, ["Boss (Executive / Director)"]),
  ]);
  const siteOptions = [
    el("option", { value: "" }, ["-- None (No site assigned yet) --"]),
    ...state.projects.map((p) =>
      el("option", { value: String(p.id) }, [`Site ${p.siteCode} · ${p.name}`])
    ),
  ];
  const siteSelect = el("select", { id: "prov-site" }, siteOptions);
  if (state.currentProject) {
    siteSelect.value = String(state.currentProject.id);
  }

  const submit = async (e) => {
    e.preventDefault();
    const username = usernameInput.value.trim().toLowerCase();
    const name = nameInput.value.trim() || username;
    const password = passwordInput.value;
    const role = roleSelect.value;
    const projectId = siteSelect.value ? Number(siteSelect.value) : null;

    if (!username || username.length < 2) {
      showToast("Username must be at least 2 characters.", "error");
      return;
    }
    if (!password || password.length < 6) {
      showToast("Password must be at least 6 characters.", "error");
      return;
    }

    try {
      const data = await apiRequest("/auth/users", {
        method: "POST",
        body: { username, name, password, role, projectId },
      });
      showToast(`User '${data.user.username}' provisioned and assigned successfully!`, "success");
      document.querySelector(".dialog-backdrop")?.remove();
      await loadAllUsers();
      if (state.currentProject) await loadTeam();
      render();
    } catch (_err) {
      /* apiRequest displays server toast */
    }
  };

  const form = el("form", { class: "auth-form", onsubmit: submit }, [
    el("label", {}, ["Username (Normal String)", usernameInput]),
    el("label", {}, ["Full Name", nameInput]),
    el("label", {}, ["Role / Responsibility", roleSelect]),
    el("label", {}, ["Password", passwordInput]),
    el("label", {}, ["Assign Project Site", siteSelect]),
    el("p", { class: "hint" }, [
      "The newly created user will only have access to the site selected above. Their UI and tools will be customized strictly for their role.",
    ]),
    el("div", { class: "dialog-actions" }, [
      el(
        "button",
        {
          class: "btn btn-ghost",
          type: "button",
          onclick: () => document.querySelector(".dialog-backdrop")?.remove(),
        },
        ["Cancel"]
      ),
      el("button", { class: "btn btn-primary", type: "submit", id: "prov-submit-btn" }, [
        "Provision User & Grant Site Access",
      ]),
    ]),
  ]);

  openDialog("👑 Provision New User & Assign Site", form);
}

function renderProvisionedUsersSection() {
  const users = state.allUsers || [];
  return el("section", { class: "panel boss-provision-panel" }, [
    el("div", { class: "panel-header" }, [
      el("div", {}, [
        el("h2", {}, ["Provisioned Users & Site Access"]),
        el("p", { class: "hint" }, ["Every user's assigned username, role, and authorized site(s)."]),
      ]),
      el("button", { class: "btn btn-primary btn-small", id: "boss-section-provision-btn", onclick: openBossUserProvisionDialog }, ["+ Provision New User"]),
    ]),
    users.length
      ? el("div", { class: "provisioned-users-grid" }, users.map((u) => {
          const assigned = (u.assignedProjects || []).map((p) => `Site ${p.siteCode}`).join(", ") || (u.role === "boss" ? "All Sites (Director)" : "No Site Assigned");
          return el("div", { class: "user-card" }, [
            el("div", { class: "user-card-head" }, [
              el("div", {}, [
                el("strong", { class: "user-card-name" }, [u.name]),
                el("p", { class: "user-card-username" }, [`@${u.username || u.id}`]),
              ]),
              el("span", { class: `badge role-badge role-badge-${u.role}` }, [roleLabel(u.role)]),
            ]),
            el("div", { class: "user-card-site" }, [
              el("span", { class: "hint" }, ["Assigned Site: "]),
              el("strong", { class: "site-code-badge" }, [assigned]),
            ]),
          ]);
        }))
      : el("p", { class: "hint" }, ["No provisioned users loaded yet."]),
  ]);
}

function renderProgressFeatureStrip() {
  if (!canPostProgress()) return null;
  return el(
    "div",
    {
      class: "progress-feature-strip",
      onclick: openProgressComposer,
      role: "button",
      tabindex: "0",
      onkeydown: (e) => {
        if (e.key === "Enter" || e.key === " ") openProgressComposer();
      },
    },
    [
      el("span", {}, ["📸 Live Camera"]),
      el("span", {}, ["🖼 Upload Photos"]),
      el("span", {}, ["🎙 Voice Note"]),
      el("span", {}, ["🗣 Speech-to-Text"]),
      el("span", {}, ["📍 GPS Geotag"]),
    ]
  );
}

function renderDrawingsUploadAndList() {
  const fileInput = el("input", {
    type: "file",
    accept: ".pdf,.png,.jpg,.jpeg,.webp,.dwg,.cad,.doc,.docx",
    id: "arch-file-input",
  });
  const uploadBtn = el("button", { class: "btn btn-primary btn-small", type: "submit" }, ["Upload Blueprint"]);

  const upload = async (e) => {
    e.preventDefault();
    if (!fileInput.files[0]) return showToast("Select a drawing or blueprint file first.", "error");
    const fd = new FormData();
    fd.append("file", fileInput.files[0]);
    uploadBtn.disabled = true;
    uploadBtn.textContent = "Uploading…";
    try {
      await apiFormRequest(`/projects/${state.currentProject.id}/files`, fd);
      fileInput.value = "";
      await loadFiles();
      render();
      showToast("Drawing uploaded successfully.", "success");
    } catch (_err) {
    } finally {
      uploadBtn.disabled = false;
      uploadBtn.textContent = "Upload Blueprint";
    }
  };

  const fileRows = state.files.length
    ? state.files.map((f) => {
        const isDrawing = /\.(pdf|png|jpe?g|dwg|cad)$/i.test(f.name);
        return el("div", { class: `file-row ${isDrawing ? "drawing-row" : ""}` }, [
          el("div", { class: "file-info" }, [
            el("span", { class: "file-icon" }, [isDrawing ? "📐" : "📄"]),
            el("div", {}, [
              el("strong", { class: "file-name" }, [f.name]),
              el("p", { class: "hint" }, [
                `${Math.max(1, Math.round(f.sizeBytes / 1024))} KB · Uploaded by ${f.uploadedBy ? f.uploadedBy.name : "Team"}`,
              ]),
            ]),
          ]),
          el(
            "button",
            {
              class: "btn btn-small",
              onclick: async () => {
                try {
                  const blob = await apiBlob(`/api/projects/${state.currentProject.id}/files/${f.id}`);
                  const u = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = u;
                  a.download = f.name;
                  a.click();
                  setTimeout(() => URL.revokeObjectURL(u), 1000);
                } catch (_e) {
                  showToast("Could not download file.", "error");
                }
              },
            },
            ["Download"]
          ),
        ]);
      })
    : [el("p", { class: "hint" }, ["No blueprints or drawings uploaded yet for this site."])];

  return el("div", { class: "drawings-vault" }, [
    el("form", { class: "file-upload inline-form-row", onsubmit: upload }, [fileInput, uploadBtn]),
    el("div", { class: "file-list" }, fileRows),
  ]);
}

function renderBossDashboard(p) {
  return el("div", { class: "project-detail boss-view" }, [
    el("div", { class: "project-header" }, [
      el("div", {}, [
        el("p", { class: "site-tag" }, [`Site ${p.siteCode}`]),
        el("h1", {}, [p.name]),
        el("p", { class: "hint" }, [p.location || "No location set"]),
      ]),
      el("div", { class: "header-actions" }, [
        el("span", { class: `status-pill status-${p.status}` }, [p.status.replace("_", " ")]),
        el("button", { class: "btn btn-primary btn-small", id: "boss-header-provision-btn", onclick: openBossUserProvisionDialog }, ["+ Provision User & Assign Site"]),
        el("button", { class: "btn btn-small", onclick: openFinanceEditor }, ["Edit Finances"]),
        el("button", { class: "btn btn-small", onclick: exportCurrentProject }, ["Export Backup"]),
      ]),
    ]),
    el("div", { class: "role-home-note role-note-boss" }, [
      el("span", { class: "role-note-icon" }, ["👑"]),
      el("span", {}, ["Director / Boss Workspace · Total executive authority, user provisioning, financials, and site command."]),
    ]),

    el("section", { class: "overview-grid overview-grid-4", "aria-label": "Project Financial Overview" }, [
      el("div", { class: "overview-card" }, [
        el("span", { class: "hint" }, ["Overall Progress"]),
        el("strong", {}, [`${Math.round(p.progressPercent || 0)}%`]),
      ]),
      el("div", { class: "overview-card" }, [
        el("span", { class: "hint" }, ["Total Budget"]),
        el("strong", { class: "text-green" }, [formatMoney(p.budget || 0)]),
      ]),
      el("div", { class: "overview-card" }, [
        el("span", { class: "hint" }, ["Amount Spent"]),
        el("strong", { class: "text-amber" }, [formatMoney(p.spent || 0)]),
      ]),
      el("div", { class: "overview-card" }, [
        el("span", { class: "hint" }, ["Remaining Funds"]),
        el("strong", { class: "text-blue" }, [formatMoney(Math.max(0, (p.budget || 0) - (p.spent || 0)))]),
      ]),
    ]),

    renderProvisionedUsersSection(),

    el("section", { class: "panel" }, [
      el("div", { class: "panel-header" }, [
        el("div", {}, [
          el("h2", {}, ["Tasks & Project Milestones"]),
          el("p", { class: "hint" }, ["Track deadlines, contractor assignments, and overall execution status."]),
        ]),
        renderCreateTaskButton(),
      ]),
      renderTaskList(),
    ]),

    el("section", { class: "panel progress-panel" }, [
      el("div", { class: "panel-header" }, [
        el("div", {}, [
          el("h2", {}, ["Site Updates & Field Logs"]),
          el("p", { class: "hint" }, ["Photos, voice notes, and daily work submitted from the construction site."]),
        ]),
        el("button", { class: "btn btn-small btn-primary", onclick: openProgressComposer }, ["+ Post Update"]),
      ]),
      renderProgressFeatureStrip(),
      renderProgressUpdates(),
    ]),

    el("section", { class: "panel" }, [
      el("div", { class: "panel-header" }, [
        el("h2", {}, ["Site Team Roster"]),
        renderGrantAccessForm(),
      ]),
      renderTeamList(),
    ]),

    renderPersonalTools(),

    el("section", { class: "panel" }, [
      el("div", { class: "panel-header" }, [el("h2", {}, ["Executive Feedback & Directives"])]),
      renderFeedbackPanel(),
    ]),
  ]);
}

function renderPMDashboard(p) {
  const pendingCount = state.tasks.filter((t) => t.status !== "done").length;
  const doneCount = state.tasks.filter((t) => t.status === "done").length;
  return el("div", { class: "project-detail pm-view" }, [
    el("div", { class: "project-header" }, [
      el("div", {}, [
        el("p", { class: "site-tag" }, [`Site ${p.siteCode}`]),
        el("h1", {}, [p.name]),
        el("p", { class: "hint" }, [p.location || "No location set"]),
      ]),
      el("div", { class: "header-actions" }, [
        el("span", { class: `status-pill status-${p.status}` }, [p.status.replace("_", " ")]),
        el("button", { class: "btn btn-primary btn-small", onclick: () => openTaskForm() }, ["+ New Task"]),
      ]),
    ]),
    el("div", { class: "role-home-note role-note-pm" }, [
      el("span", { class: "role-note-icon" }, ["👷"]),
      el("span", {}, ["Project Manager Workspace · Work scheduling, task assignments, team coordination & quality control."]),
    ]),

    el("section", { class: "overview-grid", "aria-label": "Operational metrics" }, [
      el("div", { class: "overview-card" }, [
        el("span", { class: "hint" }, ["Site Progress"]),
        el("strong", {}, [`${Math.round(p.progressPercent || 0)}%`]),
      ]),
      el("div", { class: "overview-card" }, [
        el("span", { class: "hint" }, ["Pending Tasks"]),
        el("strong", { class: "text-amber" }, [String(pendingCount)]),
      ]),
      el("div", { class: "overview-card" }, [
        el("span", { class: "hint" }, ["Completed Tasks"]),
        el("strong", { class: "text-green" }, [String(doneCount)]),
      ]),
    ]),

    el("section", { class: "panel highlight-panel" }, [
      el("div", { class: "panel-header" }, [
        el("div", {}, [
          el("h2", {}, ["Tasks, Deadlines & Assignees"]),
          el("p", { class: "hint" }, ["Assign tasks to contractors and track completion."]),
        ]),
        renderCreateTaskButton(),
      ]),
      renderTaskList(),
    ]),

    el("section", { class: "panel" }, [
      el("div", { class: "panel-header" }, [
        el("div", {}, [
          el("h2", {}, ["Site Team Members"]),
          el("p", { class: "hint" }, ["Team members with access to this site."]),
        ]),
        renderGrantAccessForm(),
      ]),
      renderTeamList(),
    ]),

    el("section", { class: "panel progress-panel" }, [
      el("div", { class: "panel-header" }, [
        el("div", {}, [
          el("h2", {}, ["Site Progress Updates"]),
          el("p", { class: "hint" }, ["Field reports, contractor photos & audio notes."]),
        ]),
        el("button", { class: "btn btn-small btn-primary", onclick: openProgressComposer }, ["+ Post Update"]),
      ]),
      renderProgressFeatureStrip(),
      renderProgressUpdates(),
    ]),

    renderPersonalTools(),

    el("section", { class: "panel" }, [
      el("div", { class: "panel-header" }, [el("h2", {}, ["Site Communication & Coordination"])]),
      renderFeedbackPanel(),
    ]),
  ]);
}

function renderContractorDashboard(p) {
  return el("div", { class: "project-detail contractor-view" }, [
    el("div", { class: "project-header" }, [
      el("div", {}, [
        el("p", { class: "site-tag" }, [`Site ${p.siteCode}`]),
        el("h1", {}, [p.name]),
        el("p", { class: "hint" }, [p.location || "No location set"]),
      ]),
      el("span", { class: `status-pill status-${p.status}` }, [p.status.replace("_", " ")]),
    ]),
    el("div", { class: "role-home-note role-note-contractor" }, [
      el("span", { class: "role-note-icon" }, ["🏗️"]),
      el("span", {}, ["Contractor (Thekedar) Field Operations · Record daily work, photos, camera, voice notes & task status."]),
    ]),

    el("div", { class: "contractor-hero-card" }, [
      el("div", { class: "contractor-hero-info" }, [
        el("h2", {}, ["Daily Site Work & Reporting"]),
        el("p", {}, ["Take live photos, record voice notes in Hindi/English, and submit today's work report for the Boss & Project Manager."]),
      ]),
      el(
        "button",
        {
          class: "btn btn-primary btn-large contractor-report-btn",
          type: "button",
          onclick: openProgressComposer,
        },
        ["📸 Submit Daily Work Report (Photos / Camera / Voice)"]
      ),
    ]),

    renderProgressFeatureStrip(),

    el("section", { class: "panel highlight-panel" }, [
      el("div", { class: "panel-header" }, [
        el("div", {}, [
          el("h2", {}, ["My Assigned Work & Day-wise Tasks"]),
          el("p", { class: "hint" }, ["Update status (Pending / In Progress / Done) as work progresses on site."]),
        ]),
      ]),
      renderTaskList(),
    ]),

    el("section", { class: "panel progress-panel" }, [
      el("div", { class: "panel-header" }, [
        el("div", {}, [
          el("h2", {}, ["Recent Daily Work Reports"]),
          el("p", { class: "hint" }, ["Your submitted site photos, audio recordings, and work logs."]),
        ]),
        el("button", { class: "btn btn-small btn-primary", onclick: openProgressComposer }, ["+ Add Daily Log"]),
      ]),
      renderProgressUpdates(),
    ]),

    el("section", { class: "panel" }, [
      el("div", { class: "panel-header" }, [
        el("h2", {}, ["Field Queries / Note to Project Manager"]),
      ]),
      renderFeedbackPanel(),
    ]),
  ]);
}

function renderArchitectDashboard(p) {
  return el("div", { class: "project-detail architect-view" }, [
    el("div", { class: "project-header" }, [
      el("div", {}, [
        el("p", { class: "site-tag" }, [`Site ${p.siteCode}`]),
        el("h1", {}, [p.name]),
        el("p", { class: "hint" }, [p.location || "No location set"]),
      ]),
      el("span", { class: `status-pill status-${p.status}` }, [p.status.replace("_", " ")]),
    ]),
    el("div", { class: "role-home-note role-note-architect" }, [
      el("span", { class: "role-note-icon" }, ["📐"]),
      el("span", {}, ["Architectural Workspace · Blueprints, CAD/PDF drawings repository, design tasks & visual site inspection."]),
    ]),

    el("section", { class: "panel highlight-panel drawings-panel" }, [
      el("div", { class: "panel-header" }, [
        el("div", {}, [
          el("h2", {}, ["Architectural Drawings & Blueprint Repository"]),
          el("p", { class: "hint" }, ["Upload and manage project plans, elevation drawings, structural details (PDF, CAD, PNG, JPG)."]),
        ]),
      ]),
      renderDrawingsUploadAndList(),
    ]),

    el("section", { class: "panel progress-panel" }, [
      el("div", { class: "panel-header" }, [
        el("div", {}, [
          el("h2", {}, ["Visual Site Inspection Feed"]),
          el("p", { class: "hint" }, ["Verify contractor execution against architectural drawings using site photos."]),
        ]),
      ]),
      renderProgressUpdates(),
    ]),

    el("section", { class: "panel" }, [
      el("div", { class: "panel-header" }, [
        el("div", {}, [
          el("h2", {}, ["Design Review Tasks & Approvals"]),
          el("p", { class: "hint" }, ["Tasks requiring architectural review or drawing approval."]),
        ]),
      ]),
      renderTaskList(),
    ]),

    el("section", { class: "panel" }, [
      el("div", { class: "panel-header" }, [
        el("h2", {}, ["Architectural Notes & Queries"]),
      ]),
      renderFeedbackPanel(),
    ]),
  ]);
}

function renderClientDashboard(p) {
  const pct = Math.round(p.progressPercent || 0);
  const fill = el("div", { class: "client-progress-fill" });
  fill.style.width = `${Math.max(5, Math.min(100, pct))}%`;

  return el("div", { class: "project-detail client-view" }, [
    el("div", { class: "project-header" }, [
      el("div", {}, [
        el("p", { class: "site-tag" }, [`Site ${p.siteCode}`]),
        el("h1", {}, [p.name]),
        el("p", { class: "hint" }, [p.location || "No location set"]),
      ]),
      el("span", { class: `status-pill status-${p.status}` }, [p.status.replace("_", " ")]),
    ]),
    el("div", { class: "role-home-note role-note-client" }, [
      el("span", { class: "role-note-icon" }, ["🤝"]),
      el("span", {}, ["Client Portal · Live construction progress, high-resolution photo gallery & direct communication."]),
    ]),

    el("div", { class: "client-showcase-card" }, [
      el("div", { class: "client-showcase-info" }, [
        el("span", { class: "client-welcome-tag" }, ["Project Status"]),
        el("h2", {}, [`${p.name} · Site ${p.siteCode}`]),
        el("p", { class: "client-showcase-desc" }, [
          p.description || "Construction is underway according to schedule. View live photos and progress below.",
        ]),
        el("div", { class: "client-progress-bar-wrap" }, [
          el("div", { class: "client-progress-bar" }, [fill]),
          el("div", { class: "client-progress-text" }, [
            el("strong", {}, [`${pct}% Complete`]),
            el("span", { class: "hint" }, [p.status.replace("_", " ").toUpperCase()]),
          ]),
        ]),
      ]),
    ]),

    el("section", { class: "panel progress-panel" }, [
      el("div", { class: "panel-header" }, [
        el("div", {}, [
          el("h2", {}, ["Site Photo Gallery & Visual Updates"]),
          el("p", { class: "hint" }, ["Click on any photo to open full-screen high-resolution viewer."]),
        ]),
        canPostProgress() ? el("button", { class: "btn btn-small btn-primary", onclick: openProgressComposer }, ["+ Add Photo / Note"]) : null,
      ]),
      renderProgressUpdates(),
    ]),

    el("section", { class: "panel" }, [
      el("div", { class: "panel-header" }, [
        el("div", {}, [
          el("h2", {}, ["Message Project Director & Site Team"]),
          el("p", { class: "hint" }, ["Ask questions or request updates directly from your site team."]),
        ]),
      ]),
      renderFeedbackPanel(),
    ]),
  ]);
}

function renderProjectDetail() {
  const p = state.currentProject;
  if (!p) return renderEmptyState();

  if (state.user.role === "boss") {
    return renderBossDashboard(p);
  } else if (state.user.role === "project_manager") {
    return renderPMDashboard(p);
  } else if (state.user.role === "contractor") {
    return renderContractorDashboard(p);
  } else if (state.user.role === "architect") {
    return renderArchitectDashboard(p);
  } else if (state.user.role === "client") {
    return renderClientDashboard(p);
  }
  return renderPMDashboard(p);
}


function openFinanceEditor() {
  if (!isBoss()) return;
  const budget=el("input",{type:"number",min:"0",value:String(state.currentProject.budget||0)});
  const spent=el("input",{type:"number",min:"0",value:String(state.currentProject.spent||0)});
  const form=el("form",{class:"auth-form",onsubmit:async e=>{e.preventDefault(); try { const d=await apiRequest(`/projects/${state.currentProject.id}`,{method:"PATCH",body:{budget:Number(budget.value),spent:Number(spent.value)}}); state.currentProject=d.project; await loadProjects(); render(); document.querySelector(".dialog-backdrop")?.remove(); showToast("Financials updated.","success"); } catch(_e){} }},[el("label",{},["Budget (INR)",budget]),el("label",{},["Spent (INR)",spent]),el("button",{class:"btn btn-primary",type:"submit"},["Save"])]);
  openDialog("Boss financial controls",form);
}

function renderPersonalTools() {
  const searchInput = el("input", { type: "search", placeholder: "Search tasks, updates, feedback, files…", "aria-label": "Search this project" });
  const results = el("div", { class: "search-results" });
  const doSearch = async (e) => {
    e.preventDefault();
    const q = searchInput.value.trim();
    if (q.length < 2) { results.replaceChildren(el("p", { class: "hint" }, ["Type at least 2 characters."])); return; }
    try {
      const data = await apiRequest(`/projects/${state.currentProject.id}/search?q=${encodeURIComponent(q)}`);
      results.replaceChildren(...(data.results.length ? data.results.map(r => el("div", { class: "search-result" }, [
        el("span", { class: "badge" }, [r.type]), el("strong", {}, [r.title]), el("p", { class: "hint" }, [r.text || ""])
      ])) : [el("p", { class: "hint" }, ["No matches."])]));
    } catch (_err) {}
  };

  const fileInput = el("input", { type: "file", accept: ".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx,.csv,.txt" });
  const upload = async (e) => {
    e.preventDefault();
    if (!fileInput.files[0]) return showToast("Choose a file first.", "error");
    const fd = new FormData(); fd.append("file", fileInput.files[0]);
    try { await apiFormRequest(`/projects/${state.currentProject.id}/files`, fd); fileInput.value = ""; await loadFiles(); render(); showToast("File uploaded.", "success"); } catch (_err) {}
  };
  const fileRows = state.files.length ? state.files.map(f => el("div", { class: "file-row" }, [
    el("div", {}, [el("strong", {}, [f.name]), el("p", { class: "hint" }, [`${Math.max(1, Math.round(f.sizeBytes/1024))} KB · ${f.uploadedBy ? f.uploadedBy.name : "Unknown"}`])]),
    el("button", { class: "btn btn-small", onclick: async () => { try { const blob = await apiBlob(`/api/projects/${state.currentProject.id}/files/${f.id}`); const u=URL.createObjectURL(blob); const a=document.createElement("a"); a.href=u; a.download=f.name; a.click(); setTimeout(()=>URL.revokeObjectURL(u),1000); } catch(_e){ showToast("Could not download file.","error"); } } }, ["Download"])
  ])) : [el("p", { class: "hint" }, ["No project files yet."])];

  const activityRows = state.activity.length ? state.activity.slice(0,10).map(a => el("div", { class: "activity-row" }, [
    el("strong", {}, [a.actor ? a.actor.name : "System"]), el("span", {}, [a.detail || a.action]), el("span", { class: "hint" }, [new Date(a.createdAt).toLocaleString()])
  ])) : [el("p", { class: "hint" }, ["Activity will appear as files and other tracked actions are added."])];

  return el("section", { class: "panel" }, [
    el("div", { class: "panel-header" }, [el("h2", {}, ["Tools & files"]), el("button", { class: "btn btn-small", onclick: exportCurrentProject }, ["Export backup"])]),
    el("form", { class: "tool-search", onsubmit: doSearch }, [searchInput, el("button", { class: "btn btn-small", type: "submit" }, ["Search"])]), results,
    el("h3", {}, ["Project files"]), el("form", { class: "file-upload", onsubmit: upload }, [fileInput, el("button", { class: "btn btn-small btn-primary", type: "submit" }, ["Upload file"])]),
    el("div", { class: "file-list" }, fileRows),
    el("h3", {}, ["Recent activity"]), el("div", { class: "activity-list" }, activityRows),
  ]);
}

async function exportCurrentProject() {
  try {
    const blob = await apiBlob(`/api/projects/${state.currentProject.id}/export`);
    const url = URL.createObjectURL(blob); const a = document.createElement("a");
    a.href = url; a.download = `${state.currentProject.siteCode}-backup.json`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (_err) { showToast("Could not export this project.", "error"); }
}

function renderFeedbackPanel() {
  const list = el(
    "div",
    { class: "message-list" },
    state.messages.length
      ? state.messages.map(renderMessage)
      : [el("p", { class: "hint" }, ["No feedback yet. Anyone on this site's team can post here."])]
  );

  const bodyInput = el("textarea", { placeholder: "Share an update, a question, or feedback...", rows: "2" });
  const submit = async (e) => {
    e.preventDefault();
    const body = bodyInput.value.trim();
    if (!body) return;
    try {
      await apiRequest(`/projects/${state.currentProject.id}/messages`, {
        method: "POST",
        body: { body },
      });
      bodyInput.value = "";
      await loadMessages();
      render();
      const el2 = document.querySelector(".message-list");
      if (el2) el2.scrollTop = el2.scrollHeight;
    } catch (_err) {
      /* toasted already */
    }
  };

  return el("div", {}, [
    list,
    el("form", { class: "feedback-form", onsubmit: submit }, [
      bodyInput,
      el("button", { class: "btn btn-small btn-primary", type: "submit" }, ["Post"]),
    ]),
  ]);
}

function renderMessage(m) {
  const when = new Date(m.createdAt);
  const timeLabel = isNaN(when.getTime())
    ? ""
    : when.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  return el("div", { class: "message-row" }, [
    el("div", { class: "message-meta" }, [
      el("span", { class: "message-sender" }, [m.sender ? m.sender.name : "Unknown"]),
      m.sender ? el("span", { class: "badge role-badge" }, [roleLabel(m.sender.role)]) : null,
      el("span", { class: "hint" }, [timeLabel]),
    ]),
    el("p", { class: "message-body" }, [m.body]),
  ]);
}

function renderGrantAccessForm() {
  const idInput = el("input", { type: "text", placeholder: "User ID, e.g. TW-TK-1234" });
  const submit = async (e) => {
    e.preventDefault();
    try {
      await apiRequest(`/projects/${state.currentProject.id}/access`, {
        method: "POST",
        body: { userId: idInput.value.trim() },
      });
      showToast("Access granted.", "success");
      idInput.value = "";
      await loadTeam();
      render();
    } catch (_err) {
      /* toasted already */
    }
  };
  return el("form", { class: "inline-form inline-form-row", onsubmit: submit }, [
    idInput,
    el("button", { class: "btn btn-small", type: "submit" }, ["Grant access"]),
  ]);
}

function renderTeamList() {
  if (state.team.length === 0) {
    return el("p", { class: "hint" }, ["Nobody's been granted access to this site yet."]);
  }
  return el(
    "div",
    { class: "team-list" },
    state.team.map((u) =>
      el("div", { class: "team-row" }, [
        el("div", {}, [
          el("span", {}, [u.name]),
          el("p", { class: "hint" }, [el("span", { class: "id-tag" }, [u.id])]),
        ]),
        el("div", { class: "team-actions" }, [
          el("span", { class: "badge role-badge" }, [roleLabel(u.role)]),
          isBoss() ? el("button", { class: "btn btn-small btn-danger", type: "button", onclick: async () => {
            if (!window.confirm(`Revoke ${u.name}'s access to this project?`)) return;
            try { await apiRequest(`/projects/${state.currentProject.id}/access/${u.id}`, { method: "DELETE" }); showToast("Access revoked.", "success"); await loadTeam(); render(); } catch (_err) {}
          } }, ["Revoke"]) : null,
        ]),
      ])
    )
  );
}

function renderCreateTaskButton() {
  return el("button", { class: "btn btn-small btn-primary", onclick: () => openTaskForm() }, ["+ New task"]);
}

let taskFormOpen = false;

function openTaskForm() {
  taskFormOpen = true;
  render();
  const input = document.querySelector(".task-form input[type=text]");
  if (input) input.focus();
}

let taskViewFilter = "all";

function renderTaskList() {
  const body = [];
  if (taskFormOpen) body.push(renderTaskForm());
  const today = new Date(); today.setHours(0,0,0,0);
  const groups = { Overdue:[], Today:[], Upcoming:[], Completed:[] };
  for (const task of state.tasks) {
    if (task.status === "done") groups.Completed.push(task);
    else if (!task.dueDate) groups.Upcoming.push(task);
    else { const d=new Date(task.dueDate+"T00:00:00"); if (d<today) groups.Overdue.push(task); else if (d.getTime()===today.getTime()) groups.Today.push(task); else groups.Upcoming.push(task); }
  }
  const keys=["Overdue","Today","Upcoming","Completed"];
  const tabs=el("div",{class:"task-filter-tabs",role:"tablist","aria-label":"Filter tasks"},keys.map(k=>el("button",{type:"button",class:`task-filter-tab ${taskViewFilter===k.toLowerCase()?"active":""}`,onclick:()=>{taskViewFilter=k.toLowerCase();render()}},[el("span",{},[k]),el("b",{},[String(groups[k].length)])])));
  body.push(tabs);
  if (!state.tasks.length && !taskFormOpen) body.push(el("div",{class:"task-empty"},[el("strong",{},["No tasks yet"]),el("p",{class:"hint"},["New work and deadlines will appear here."])]));
  for (const label of keys) {
    if (taskViewFilter!=="all" && taskViewFilter!==label.toLowerCase()) continue;
    if (!groups[label].length) continue;
    body.push(el("div",{class:"task-group-head"},[el("span",{},[label]),el("span",{class:"hint"},[`${groups[label].length} task${groups[label].length===1?"":"s"}`])]));
    for (const task of groups[label]) body.push(renderTaskCard(task,label==="Overdue"));
  }
  if (taskViewFilter!=="all" && !(groups[keys.find(k=>k.toLowerCase()===taskViewFilter)]||[]).length) body.push(el("div",{class:"task-empty"},[el("p",{class:"hint"},[`No ${taskViewFilter} tasks.`])]));
  return el("div", { class: "task-list" }, body);
}

function renderTaskForm() {
  const titleInput = el("input", { type: "text", placeholder: "Task title" });
  const assigneeInput = el("input", { type: "text", placeholder: "Assignee user ID (optional)" });
  const dueDateInput = el("input", { type: "date", required: true });
  const dueTimeInput = el("input", { type: "time" });

  const submit = async (e) => {
    e.preventDefault();
    try {
      await apiRequest(`/projects/${state.currentProject.id}/tasks`, {
        method: "POST",
        body: {
          title: titleInput.value.trim(),
          assigneeId: assigneeInput.value.trim() || undefined,
          dueDate: dueDateInput.value, dueTime: dueTimeInput.value || undefined,
        },
      });
      showToast("Task created.", "success");
      taskFormOpen = false;
      await loadTasks();
      render();
    } catch (_err) {
      /* toasted already */
    }
  };

  return el("form", { class: "task-form inline-form", onsubmit: submit }, [
    titleInput,
    assigneeInput,
    el("label", {}, ["Deadline date", dueDateInput]), el("label", {}, ["Deadline time", dueTimeInput]),
    el("div", { class: "form-actions" }, [
      el("button", { class: "btn btn-small btn-primary", type: "submit" }, ["Add task"]),
      el(
        "button",
        {
          class: "btn btn-small btn-ghost",
          type: "button",
          onclick: () => {
            taskFormOpen = false;
            render();
          },
        },
        ["Cancel"]
      ),
    ]),
  ]);
}

function renderTaskCard(task, overdue = false) {
  const isAssignee = !!(task.assignee && state.user && task.assignee.id === state.user.id);
  const canEditFully = isManager();
  const canEditStatus = canEditFully || isAssignee;

  const statusSelect = el(
    "select",
    { disabled: !canEditStatus },
    ["pending", "in_progress", "delayed", "done"].map((s) =>
      el("option", { value: s, selected: s === task.status }, [s.replace("_", " ")])
    )
  );

  const progressInput = el("input", {
    type: "number",
    min: "0",
    max: "100",
    value: String(task.progressPercent),
    disabled: !canEditStatus,
  });

  const saveStatus = async () => {
    const pct = Number(progressInput.value);
    if (!Number.isFinite(pct) || pct < 0 || pct > 100) { showToast("Progress must be between 0 and 100.", "error"); progressInput.focus(); return; }
    try {
      await apiRequest(`/projects/${state.currentProject.id}/tasks/${task.id}`, {
        method: "PATCH",
        body: { status: statusSelect.value, progressPercent: pct },
      });
      showToast("Task updated.", "success");
      await loadTasks();
      render();
    } catch (_err) {
      /* toasted already, including the real "you can only update status
         and progressPercent" message if a non-manager somehow sends more */
    }
  };

  const deleteTask = async () => {
    if (!window.confirm(`Delete task "${task.title}"? This cannot be undone.`)) return;
    try {
      await apiRequest(`/projects/${state.currentProject.id}/tasks/${task.id}`, { method: "DELETE" });
      showToast("Task deleted.", "success");
      await loadTasks();
      render();
    } catch (_err) {
      /* toasted already */
    }
  };

  const due = task.dueDate ? new Date(task.dueDate+"T"+(task.dueTime||"23:59")) : null;
  const dueText = due ? due.toLocaleString([], { month:"short", day:"numeric", hour: task.dueTime?"2-digit":undefined, minute:task.dueTime?"2-digit":undefined }) : "No deadline";
  const statusText = String(task.status||"pending").replace("_"," ");
  return el("article", { class: `task-card mobile-task-card${overdue ? " overdue" : ""}` }, [
    el("div", { class: "task-card-header" }, [
      el("div",{class:"task-title-wrap"},[el("p", { class: "task-title" }, [task.title]),el("p",{class:"task-meta"},[task.assignee?`👤 ${task.assignee.name}`:"👤 Unassigned",`  ·  ${overdue?"⚠️":"🕒"} ${overdue?"Overdue · ":"Due "}${dueText}`])]),
      el("span", { class: `status-pill status-${task.status}` }, [statusText]),
    ]),
    el("div",{class:"task-progress-row"},[el("div",{class:"task-progress-track"},[el("span",{style:`width:${Math.max(0,Math.min(100,Number(task.progressPercent)||0))}%`})]),el("strong",{},[`${task.progressPercent}%`])]),
    canEditStatus ? el("div", { class: "task-mobile-actions" }, [
      el("label", { class: "task-status-control" }, [el("span",{},["Status"]), statusSelect]),
      task.status === "in_progress" ? el("label", { class: "task-progress-control" }, [el("span",{},["Progress"]), progressInput]) : null,
      el("button", { class: "btn btn-small btn-primary", onclick: saveStatus }, ["Save"]),
      canEditFully ? el("button", { class: "btn btn-small btn-danger task-delete", onclick: deleteTask, "aria-label":`Delete ${task.title}` }, ["Delete"]) : null,
    ]) : el("div",{class:"task-readonly-note"},["View only"]),
  ]);
}


/* --------------------------- Site progress media ------------------------- */
let progressDialog = null;
let activeRecorder = null;
let activeStream = null;
let cameraStream = null;
let recordedAudio = null;
let speechRecognizer = null;
let lightboxUrls = [];
let progressPreviewUrls = [];
let recordingTimer = null;

function renderProgressUpdates() {
  if (!state.progressUpdates.length) return el("p", { class: "hint" }, ["No site updates posted yet."]);
  return el("div", { class: "progress-feed" }, state.progressUpdates.map(renderProgressCard));
}

function renderProgressCard(update) {
  const card = el("article", { class: "progress-card" });
  const when = new Date(update.createdAt || update.logDate);
  card.appendChild(el("div", { class: "progress-card-head" }, [
    el("div", {}, [el("h3", {}, [update.title]), el("p", { class: "hint" }, [`${update.author.name} · ${isNaN(when) ? update.logDate : when.toLocaleString()}`])]),
  ]));
  if (update.description) card.appendChild(el("p", { class: "progress-copy" }, [update.description]));
  if (update.photos && update.photos.length) {
    const grid = el("div", { class: "photo-grid" });
    update.photos.forEach((photo, index) => {
      const button = el("button", { class: "photo-tile", type: "button", "aria-label": `Open photo ${index + 1}` }, [el("span", { class: "photo-loading" }, ["Loading photo…"])]);
      hydrateImageButton(button, photo.url, update.photos, index); grid.appendChild(button);
    });
    card.appendChild(grid);
    const tagged = update.photos.find(p => p.latitude != null && p.longitude != null);
    if (tagged) card.appendChild(el("p", { class: "geo-tag" }, [`📍 ${tagged.latitude.toFixed(5)}, ${tagged.longitude.toFixed(5)}${tagged.accuracyM ? ` · ±${Math.round(tagged.accuracyM)}m` : ""}`]));
  }
  if (update.audioUrl) { const audioWrap = el("div", { class: "voice-note" }, [el("strong", {}, ["Voice note"]), el("span", { class: "hint" }, ["Loading audio…"])]); hydrateAudio(audioWrap, update.audioUrl); card.appendChild(audioWrap); }
  if (update.audioTranscript) card.appendChild(el("div", { class: "transcript" }, [el("strong", {}, ["Transcript"]), el("p", {}, [update.audioTranscript])]));
  return card;
}

async function hydrateImageButton(button, mediaPath, allPhotos, index) {
  try { const blob = await apiBlob(mediaPath); const url = URL.createObjectURL(blob); button._objectUrl = url; button.replaceChildren(el("img", { src: url, alt: allPhotos[index].caption || `Site progress photo ${index + 1}` })); button.onclick = () => openLightbox(allPhotos, index); }
  catch (_err) { button.replaceChildren(el("span", { class: "hint" }, ["Photo unavailable"])); }
}
async function hydrateAudio(wrap, mediaPath) {
  try { const blob = await apiBlob(mediaPath); const url = URL.createObjectURL(blob); wrap.replaceChildren(el("strong", {}, ["Voice note"]), el("audio", { controls: true, preload: "metadata", src: url })); }
  catch (_err) { wrap.replaceChildren(el("span", { class: "hint" }, ["Voice note unavailable"])); }
}
async function openLightbox(photos, startIndex) {
  lightboxUrls.forEach(URL.revokeObjectURL); lightboxUrls = [];
  try {
    const urls = await Promise.all(photos.map(async p => { const u = URL.createObjectURL(await apiBlob(p.url)); lightboxUrls.push(u); return u; }));
    let index = startIndex; const image = el("img", { class: "lightbox-image", alt: "Site progress photo" }); const counter = el("span", { class: "lightbox-counter" }); const overlay = el("div", { class: "lightbox", role: "dialog", "aria-modal": "true", "aria-label": "Photo viewer" });
    const show = () => { image.src = urls[index]; image.alt = photos[index].caption || `Site progress photo ${index + 1}`; counter.textContent = `${index + 1} / ${urls.length}`; };
    const close = () => { document.removeEventListener("keydown", keys); overlay.remove(); lightboxUrls.forEach(URL.revokeObjectURL); lightboxUrls = []; };
    const keys = e => { if (e.key === "Escape") close(); if (e.key === "ArrowLeft") { index = (index - 1 + urls.length) % urls.length; show(); } if (e.key === "ArrowRight") { index = (index + 1) % urls.length; show(); } };
    overlay.append(el("div", { class: "lightbox-toolbar" }, [counter, el("button", { class: "lightbox-close", onclick: close, "aria-label": "Close photo viewer" }, ["×"])]), image);
    if (urls.length > 1) overlay.append(el("button", { class: "lightbox-nav lightbox-prev", onclick: () => { index = (index - 1 + urls.length) % urls.length; show(); }, "aria-label": "Previous photo" }, ["‹"]), el("button", { class: "lightbox-nav lightbox-next", onclick: () => { index = (index + 1) % urls.length; show(); }, "aria-label": "Next photo" }, ["›"]));
    overlay.addEventListener("click", e => { if (e.target === overlay) close(); }); document.body.appendChild(overlay); document.addEventListener("keydown", keys); show(); overlay.querySelector(".lightbox-close").focus();
  } catch (_err) { showToast("Could not open this photo.", "error"); }
}

function openProgressComposer() {
  if (progressDialog) return;
  const title = el("input", { type: "text", placeholder: "e.g. Ground floor slab completed", maxlength: "200" });
  const description = el("textarea", { rows: "3", placeholder: "What changed on site today?" });
  const progress = el("input", { type: "number", min: "0", max: "100", placeholder: "Overall progress %" });
  const galleryInput = el("input", { type: "file", accept: "image/jpeg,image/png,image/webp,image/heic", multiple: true, class: "visually-hidden" });
  const fallbackCameraInput = el("input", { type: "file", accept: "image/*", capture: "environment", class: "visually-hidden" });
  const selectedPhotos = [];
  const preview = el("div", { class: "media-preview-grid", "aria-live": "polite" });
  const photoStatus = el("span", { class: "hint" }, ["No photos attached."]);
  const cameraPanel = el("div", { class: "camera-panel hidden" });
  const cameraVideo = el("video", { class: "camera-video", autoplay: true, playsinline: true, muted: true });
  const cameraCanvas = el("canvas", { class: "hidden" });
  const captureButton = el("button", { class: "btn btn-primary", type: "button" }, ["Capture photo"]);
  const switchButton = el("button", { class: "btn", type: "button" }, ["Switch camera"]);
  const closeCameraButton = el("button", { class: "btn", type: "button" }, ["Close camera"]);
  cameraPanel.append(cameraVideo, cameraCanvas, el("div", { class: "camera-actions" }, [captureButton, switchButton, closeCameraButton]));
  let facingMode = "environment";
  const transcript = el("textarea", { rows: "4", placeholder: "Live transcript appears here. You can edit it before posting." });
  const recordStatus = el("span", { class: "hint", "aria-live": "polite" }, ["No voice note recorded."]);
  const audioPreview = el("audio", { controls: true, class: "hidden", preload: "metadata" });
  const recordButton = el("button", { class: "media-action", type: "button" }, ["🎙 Record voice note"]);
  const deleteRecording = el("button", { class: "btn btn-small hidden", type: "button" }, ["Delete recording"]);
  const speechButton = el("button", { class: "media-action", type: "button" }, ["🗣 Start speech-to-text"]);
  const galleryButton = el("button", { class: "media-action", type: "button" }, ["🖼 Upload photos"]);
  const cameraButton = el("button", { class: "media-action", type: "button" }, ["📸 Open camera"]);
  const locationButton = el("button", { class: "media-action", type: "button" }, ["📍 Add location"]);
  const capability = el("p", { class: "capability-note" }, [window.isSecureContext ? "Camera and microphone are available when you grant browser permission." : "Camera and microphone require HTTPS or localhost. Photo upload still works here."]);
  const form = el("form", { class: "progress-form" }); const cancel = el("button", { class: "btn", type: "button" }, ["Cancel"]); const submit = el("button", { class: "btn btn-primary", type: "submit" }, ["Post update"]);
  const dialog = el("div", { class: "dialog-backdrop" }, [el("div", { class: "dialog", role: "dialog", "aria-modal": "true", "aria-labelledby": "progress-dialog-title" }, [el("div", { class: "dialog-head" }, [el("div", {}, [el("p", { class: "site-tag" }, [`Site ${state.currentProject.siteCode}`]), el("h2", { id: "progress-dialog-title" }, ["Post site update"])]), el("button", { class: "btn btn-ghost", type: "button", onclick: closeProgressComposer, "aria-label": "Close" }, ["×"])]), form])]);

  function refreshPhotos() {
    progressPreviewUrls.forEach(URL.revokeObjectURL); progressPreviewUrls = []; preview.replaceChildren();
    selectedPhotos.forEach((file, index) => { const url = URL.createObjectURL(file); progressPreviewUrls.push(url); const remove = el("button", { type: "button", class: "media-preview-remove", "aria-label": `Remove photo ${index + 1}` }, ["×"]); remove.onclick = () => { selectedPhotos.splice(index, 1); refreshPhotos(); }; preview.append(el("div", { class: "media-preview-item" }, [el("img", { src: url, alt: `Selected photo ${index + 1}` }), remove])); });
    photoStatus.textContent = selectedPhotos.length ? `${selectedPhotos.length} photo${selectedPhotos.length === 1 ? "" : "s"} attached.` : "No photos attached.";
  }
  function addFiles(files) { for (const file of files) { if (selectedPhotos.length >= 12) { showToast("You can attach up to 12 photos per update.", "error"); break; } if (!file.type.startsWith("image/")) { showToast("Only image files can be attached as photos.", "error"); continue; } selectedPhotos.push(file); } refreshPhotos(); }
  async function startCamera() {
    if (!supportsCamera()) { fallbackCameraInput.click(); return; }
    stopMediaStream(cameraStream); cameraStream = null;
    try { cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: facingMode } }, audio: false }); cameraVideo.srcObject = cameraStream; cameraPanel.classList.remove("hidden"); await cameraVideo.play(); }
    catch (_err) { showToast("Camera permission was not available. You can upload a photo instead.", "error"); }
  }
  function stopCamera() { stopMediaStream(cameraStream); cameraStream = null; cameraVideo.srcObject = null; cameraPanel.classList.add("hidden"); }
  galleryButton.onclick = () => galleryInput.click(); galleryInput.onchange = () => { addFiles([...galleryInput.files]); galleryInput.value = ""; };
  fallbackCameraInput.onchange = () => { addFiles([...fallbackCameraInput.files]); fallbackCameraInput.value = ""; };
  locationButton.onclick = () => { if (!navigator.geolocation) return showToast("Location is not supported on this device.", "error"); locationButton.textContent="📍 Locating…"; navigator.geolocation.getCurrentPosition(pos => { geo={latitude:pos.coords.latitude, longitude:pos.coords.longitude, accuracyM:pos.coords.accuracy}; locationButton.textContent="📍 Location added"; showToast("Location will be attached to photos.", "success"); }, err => { locationButton.textContent="📍 Add location"; showToast(err.code===1 ? "Location permission was denied. Photos can still be posted without it." : "Could not get location.", "error"); }, {enableHighAccuracy:true, timeout:10000}); };
  cameraButton.onclick = startCamera; closeCameraButton.onclick = stopCamera; switchButton.onclick = async () => { facingMode = facingMode === "environment" ? "user" : "environment"; await startCamera(); };
  captureButton.onclick = () => { if (!cameraVideo.videoWidth) return showToast("Camera is still starting.", "error"); cameraCanvas.width = cameraVideo.videoWidth; cameraCanvas.height = cameraVideo.videoHeight; cameraCanvas.getContext("2d").drawImage(cameraVideo, 0, 0); addFiles([dataUrlToFile(cameraCanvas.toDataURL("image/jpeg", .9), `camera-${Date.now()}.jpg`)]); };
  recordButton.onclick = () => toggleRecording(recordButton, recordStatus, audioPreview, deleteRecording);
  deleteRecording.onclick = () => { recordedAudio = null; if (audioPreview.src) URL.revokeObjectURL(audioPreview.src); audioPreview.removeAttribute("src"); audioPreview.classList.add("hidden"); deleteRecording.classList.add("hidden"); recordStatus.textContent = "No voice note recorded."; recordButton.textContent = "🎙 Record voice note"; };
  speechButton.onclick = () => toggleSpeech(speechButton, transcript);
  form.append(el("label", {}, ["Title", title]), el("label", {}, ["Details", description]), capability, el("div", { class: "media-action-grid" }, [galleryButton, cameraButton, locationButton, recordButton, speechButton]), galleryInput, fallbackCameraInput, cameraPanel, photoStatus, preview, el("div", { class: "record-preview" }, [recordStatus, audioPreview, deleteRecording]), el("label", {}, ["Transcript / site note", transcript]), el("div", { class: "dialog-actions" }, [cancel, submit]));
  cancel.onclick = closeProgressComposer;
  form.onsubmit = async e => { e.preventDefault(); if (!title.value.trim()) { showToast("Add a title for this update.", "error"); title.focus(); return; } if (activeRecorder && activeRecorder.state === "recording") return showToast("Stop the voice recording before posting.", "error"); const totalBytes = selectedPhotos.reduce((sum, f) => sum + f.size, 0) + (recordedAudio ? recordedAudio.size : 0); if (totalBytes > 24 * 1024 * 1024) return showToast("Attachments are too large. Keep photos and audio under 24 MB total.", "error"); const fd = new FormData(); fd.append("title", title.value.trim()); fd.append("description", description.value.trim()); fd.append("transcript", transcript.value.trim()); if (geo) { fd.append("latitude", geo.latitude); fd.append("longitude", geo.longitude); fd.append("accuracyM", geo.accuracyM); } selectedPhotos.forEach(f => fd.append("photos", f)); if (recordedAudio) fd.append("audio", recordedAudio, `voice-note.${audioExtension(recordedAudio.type)}`); submit.disabled = true; submit.textContent = "Posting…"; try { await apiFormRequest(`/projects/${state.currentProject.id}/progress`, fd); showToast("Site update posted.", "success"); closeProgressComposer(); await loadProgress(); render(); } catch (_err) { submit.disabled = false; submit.textContent = "Post update"; } };
  const escape = e => { if (e.key === "Escape") closeProgressComposer(); }; dialog._escape = escape; dialog._stopCamera = stopCamera; document.addEventListener("keydown", escape); document.body.appendChild(dialog); progressDialog = dialog; recordedAudio = null; cancel.focus();
}

function closeProgressComposer() {
  if (!progressDialog) return;
  if (progressDialog._escape) document.removeEventListener("keydown", progressDialog._escape); if (progressDialog._stopCamera) progressDialog._stopCamera();
  if (activeRecorder && activeRecorder.state !== "inactive") activeRecorder.stop(); stopMediaStream(activeStream); activeStream = null;
  if (speechRecognizer) { try { speechRecognizer.stop(); } catch (_err) {} } speechRecognizer = null;
  if (recordingTimer) { clearInterval(recordingTimer); recordingTimer = null; }
  progressPreviewUrls.forEach(URL.revokeObjectURL); progressPreviewUrls = []; activeRecorder = null; progressDialog.remove(); progressDialog = null;
}

async function toggleRecording(button, status, audioPreview, deleteButton) {
  if (activeRecorder && activeRecorder.state === "recording") { activeRecorder.stop(); button.textContent = "🎙 Record again"; return; }
  if (!supportsRecording()) { showToast("Voice recording requires a supported browser over HTTPS or localhost.", "error"); return; }
  try {
    stopMediaStream(activeStream); activeStream = await navigator.mediaDevices.getUserMedia({ audio: true }); const chunks = []; const mimeType = preferredAudioMimeType(); activeRecorder = mimeType ? new MediaRecorder(activeStream, { mimeType }) : new MediaRecorder(activeStream); const started = Date.now();
    activeRecorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
    activeRecorder.onerror = () => showToast("The voice recording stopped unexpectedly.", "error");
    activeRecorder.onstop = () => { if (recordingTimer) clearInterval(recordingTimer); recordingTimer = null; recordedAudio = new Blob(chunks, { type: activeRecorder.mimeType || "audio/webm" }); stopMediaStream(activeStream); activeStream = null; if (audioPreview.src) URL.revokeObjectURL(audioPreview.src); audioPreview.src = URL.createObjectURL(recordedAudio); audioPreview.classList.remove("hidden"); deleteButton.classList.remove("hidden"); status.textContent = `Voice note ready · ${Math.max(1, Math.round((Date.now()-started)/1000))}s`; };
    activeRecorder.start(500); button.textContent = "■ Stop recording"; status.textContent = "Recording · 0:00"; recordingTimer = setInterval(() => { const sec = Math.floor((Date.now()-started)/1000); status.textContent = `Recording · ${Math.floor(sec/60)}:${String(sec%60).padStart(2,"0")}`; }, 500);
  } catch (_err) { stopMediaStream(activeStream); activeStream = null; showToast("Microphone permission was not available.", "error"); }
}

function toggleSpeech(button, transcript) {
  if (speechRecognizer) { speechRecognizer.stop(); speechRecognizer = null; button.textContent = "🗣 Start speech-to-text"; return; }
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition; if (!Recognition) { showToast("Live speech-to-text is not supported here. You can still type or edit the transcript.", "error"); return; }
  const r = new Recognition(); r.continuous = true; r.interimResults = true; r.lang = "en-IN"; let committed = transcript.value.trim();
  r.onresult = e => { let interim = ""; for (let i=e.resultIndex; i<e.results.length; i++) { const text=e.results[i][0].transcript; if (e.results[i].isFinal) committed = `${committed} ${text}`.trim(); else interim += text; } transcript.value = `${committed}${interim ? ` ${interim}` : ""}`.trim(); };
  r.onerror = e => { if (e.error !== "aborted") showToast(`Speech recognition stopped: ${e.error}.`, "error"); };
  r.onend = () => { speechRecognizer = null; button.textContent = "🗣 Start speech-to-text"; };
  try { r.start(); speechRecognizer = r; button.textContent = "■ Stop speech-to-text"; } catch (_err) { showToast("Could not start speech recognition.", "error"); }
}

async function loadProgress() { const data = await apiRequest(`/projects/${state.currentProject.id}/progress`); state.progressUpdates = data.updates; }


window.addEventListener("pagehide", () => {
  stopMediaStream(activeStream); stopMediaStream(cameraStream);
  lightboxUrls.forEach(URL.revokeObjectURL); progressPreviewUrls.forEach(URL.revokeObjectURL);
});

/* ------------------------------ Data loading ----------------------------- */

async function loadProjects() {
  try {
    const data = await apiRequest("/projects");
    state.projects = data.projects;
    if (isBoss()) {
      await Promise.all([loadPendingUsers(), loadAllUsers()]);
    }
  } catch (_err) {
    /* toasted already */
  }
}

async function loadAllUsers() {
  if (!isBoss()) return;
  try {
    const data = await apiRequest("/auth/users");
    state.allUsers = data.users || [];
  } catch (_err) {
    state.allUsers = [];
  }
}

async function loadPendingUsers() {
  try {
    const data = await apiRequest("/auth/pending");
    state.pendingUsers = data.users;
  } catch (_err) {
    /* toasted already */
  }
}

async function selectProject(projectId) {
  try {
    const [projectData, teamData, tasksData, messagesData, progressData, filesData, activityData] = await Promise.all([
      apiRequest(`/projects/${projectId}`),
      apiRequest(`/projects/${projectId}/team`),
      apiRequest(`/projects/${projectId}/tasks`),
      apiRequest(`/projects/${projectId}/messages`),
      apiRequest(`/projects/${projectId}/progress`),
      apiRequest(`/projects/${projectId}/files`),
      apiRequest(`/projects/${projectId}/activity`),
    ]);
    state.currentProject = projectData.project;
    state.team = teamData.team;
    state.tasks = tasksData.tasks;
    state.messages = messagesData.messages;
    state.progressUpdates = progressData.updates;
    state.files = filesData.files;
    state.activity = activityData.activity;
    taskFormOpen = false;
    render();
  } catch (_err) {
    /* toasted already */
  }
}

async function loadTeam() {
  const data = await apiRequest(`/projects/${state.currentProject.id}/team`);
  state.team = data.team;
}

async function loadTasks() {
  const data = await apiRequest(`/projects/${state.currentProject.id}/tasks`);
  state.tasks = data.tasks;
}

async function loadFiles() {
  const data = await apiRequest(`/projects/${state.currentProject.id}/files`);
  state.files = data.files;
}

async function loadMessages() {
  const data = await apiRequest(`/projects/${state.currentProject.id}/messages`);
  state.messages = data.messages;
}

/* ------------------------- Internet synchronization ---------------------- */
const SYNC_INTERVAL_MS = 15000;
let syncTimer = null;
let syncInFlight = false;

async function syncFromServer({ forceRender = true } = {}) {
  if (!state.user || syncInFlight || !navigator.onLine) {
    if (!navigator.onLine && state.syncStatus !== "offline") { state.syncStatus = "offline"; if (forceRender) render(); }
    return;
  }
  syncInFlight = true;
  state.syncStatus = "syncing";
  if (forceRender) render();
  try {
    const selectedId = state.currentProject?.id;
    await Promise.all([loadProjects(), loadNotifications()]);
    if (selectedId && state.projects.some(p => p.id === selectedId)) await selectProject(selectedId);
    else if (state.projects.length) await selectProject(state.projects[0].id);
    state.syncStatus = "online";
    state.lastSyncedAt = new Date();
  } catch (_err) {
    state.syncStatus = navigator.onLine ? "online" : "offline";
  } finally {
    syncInFlight = false;
    if (forceRender) render();
  }
}

function startAutoSync() {
  if (syncTimer) clearInterval(syncTimer);
  syncTimer = setInterval(() => syncFromServer({ forceRender: true }), SYNC_INTERVAL_MS);
}
function stopAutoSync() { if (syncTimer) clearInterval(syncTimer); syncTimer = null; }

window.addEventListener("online", () => { state.syncStatus = "online"; render(); syncFromServer(); });
window.addEventListener("offline", () => { state.syncStatus = "offline"; render(); });
window.addEventListener("nirmaan:network", e => {
  const next = e.detail?.state;
  if (next === "offline") { state.syncStatus = "offline"; render(); }
  else if (next === "online" && state.syncStatus === "offline") { state.syncStatus = "online"; render(); }
});

/* --------------------------------- Boot ---------------------------------- */

async function boot() {
  if (!isLoggedIn()) { render(); return; }
  try {
    const me = await apiRequest("/auth/me", { silent: true });
    state.user = me.user;
    await Promise.all([loadProjects(), loadNotifications()]);
    if (state.projects.length) await selectProject(state.projects[0].id);
    else render();
    state.syncStatus = navigator.onLine ? "online" : "offline";
    state.lastSyncedAt = new Date();
    startAutoSync();
    render();
  } catch (_err) { clearTokens(); state.user = null; stopAutoSync(); render(); }
}

boot();

/* ------------------------------ PWA install ------------------------------ */
let deferredInstallPrompt = null;
window.addEventListener("beforeinstallprompt", event => {
  event.preventDefault();
  deferredInstallPrompt = event;
  window.dispatchEvent(new CustomEvent("nirmaan:pwa-installable"));
});
window.addEventListener("appinstalled", () => { deferredInstallPrompt = null; showToast("Nirmaan installed on this device.", "success"); });
async function installNirmaan() {
  if (!deferredInstallPrompt) { showToast("Use your browser menu and choose Add to Home Screen / Install App.", "info"); return; }
  deferredInstallPrompt.prompt();
  await deferredInstallPrompt.userChoice;
  deferredInstallPrompt = null;
}
if ("serviceWorker" in navigator) window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
