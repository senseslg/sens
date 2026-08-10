(() => {
  const root = document.getElementById("root");

  const state = {
    user: null,
    dashboard: null,
    users: [],
    userDrafts: {},
    loading: true,
    refreshing: false,
    usersLoading: false,
    authError: "",
    loginBusy: false,
    userBusyKey: "",
    userError: "",
    userMessage: "",
    newUser: {
      username: "",
      display_name: "",
      password: "",
      is_active: true,
    },
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function fmtState(stateValue) {
    if (stateValue === "healthy") return "健康";
    if (stateValue === "warning") return "关注";
    if (stateValue === "error") return "异常";
    return "未知";
  }

  function stateClass(stateValue) {
    if (stateValue === "healthy") return "state-healthy";
    if (stateValue === "warning") return "state-warning";
    if (stateValue === "error") return "state-error";
    return "state-neutral";
  }

  function formatDateTime(value) {
    if (!value) return "未填写";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return escapeHtml(value);
    return new Intl.DateTimeFormat("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(date);
  }

  function apiErrorMessage(detail, fallback) {
    const messages = {
      missing_credentials: "请填写账号和密码。",
      invalid_credentials: "账号或密码不正确。",
      missing_user_fields: "请填写账号、名称和密码。",
      user_fields_too_long: "账号或名称长度超出限制。",
      password_too_short: "密码至少需要 8 位。",
      username_exists: "该账号已存在。",
      missing_display_name: "请填写显示名称。",
      display_name_too_long: "显示名称长度超出限制。",
      cannot_disable_self: "不能停用当前登录账号。",
      cannot_delete_self: "不能删除当前登录账号。",
      last_active_user: "至少需要保留一个可用账号。",
      user_not_found: "账号不存在或已被删除。",
    };
    return messages[detail] || fallback;
  }

  async function requestJson(url, options = {}) {
    const resp = await fetch(url, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    let payload = {};
    try {
      payload = await resp.json();
    } catch (error) {
      payload = {};
    }
    if (!resp.ok) {
      return { ok: false, status: resp.status, ...payload };
    }
    return { ok: true, status: resp.status, ...payload };
  }

  function setDrafts(users) {
    state.userDrafts = Object.fromEntries(
      users.map((item) => [
        item.id,
        {
          display_name: item.display_name,
          is_active: item.is_active,
        },
      ]),
    );
  }

  async function loadDashboard() {
    const data = await requestJson("/api/dashboard");
    if (!data.ok && data.status) {
      throw new Error(data.detail || "dashboard_unavailable");
    }
    state.dashboard = data;
  }

  async function loadUsers() {
    state.usersLoading = true;
    render();
    const data = await requestJson("/api/users");
    state.usersLoading = false;
    if (!data.ok && data.status) {
      throw new Error(data.detail || "users_unavailable");
    }
    state.users = data.users || [];
    setDrafts(state.users);
  }

  async function loadAuthedData() {
    state.loading = true;
    state.authError = "";
    state.userError = "";
    render();
    try {
      const me = await requestJson("/api/me");
      if (!me.ok && me.status === 401) {
        state.user = null;
        state.dashboard = null;
        state.users = [];
        state.loading = false;
        render();
        bindEvents();
        return;
      }
      if (!me.ok) {
        throw new Error(me.detail || "me_unavailable");
      }
      state.user = me;
      await loadDashboard();
      await loadUsers();
    } catch (error) {
      state.authError = "后台数据加载失败，请稍后重试。";
    } finally {
      state.loading = false;
      render();
      bindEvents();
    }
  }

  async function handleLogin(username, password) {
    state.loginBusy = true;
    state.authError = "";
    render();
    try {
      const data = await requestJson("/api/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      if (!data.ok && data.status) {
        state.authError = apiErrorMessage(data.detail, "登录失败。");
        return;
      }
      await loadAuthedData();
    } catch (error) {
      state.authError = "登录请求失败。";
    } finally {
      state.loginBusy = false;
      render();
      bindEvents();
    }
  }

  async function handleLogout() {
    await requestJson("/api/logout", { method: "POST" });
    state.user = null;
    state.dashboard = null;
    state.users = [];
    state.userDrafts = {};
    state.userError = "";
    state.userMessage = "";
    render();
    bindEvents();
  }

  async function handleRefresh() {
    state.refreshing = true;
    render();
    try {
      await Promise.all([loadDashboard(), loadUsers()]);
    } catch (error) {
      state.userError = "刷新后台数据失败，请稍后再试。";
    } finally {
      state.refreshing = false;
      render();
      bindEvents();
    }
  }

  function updateNewUser(field, value) {
    state.newUser = { ...state.newUser, [field]: value };
    render();
    bindEvents();
  }

  function updateDraft(userId, field, value) {
    state.userDrafts = {
      ...state.userDrafts,
      [userId]: {
        ...(state.userDrafts[userId] || {}),
        [field]: value,
      },
    };
    render();
    bindEvents();
  }

  async function refreshUsers() {
    await loadUsers();
    render();
    bindEvents();
  }

  async function handleCreateUser(event) {
    event.preventDefault();
    state.userBusyKey = "create";
    state.userError = "";
    state.userMessage = "";
    render();
    try {
      const data = await requestJson("/api/users", {
        method: "POST",
        body: JSON.stringify(state.newUser),
      });
      if (!data.ok && data.status) {
        throw new Error(apiErrorMessage(data.detail, "创建账号失败。"));
      }
      state.newUser = {
        username: "",
        display_name: "",
        password: "",
        is_active: true,
      };
      state.userMessage = "账号已创建。";
      await refreshUsers();
    } catch (error) {
      state.userError = error.message || "创建账号失败。";
    } finally {
      state.userBusyKey = "";
      render();
      bindEvents();
    }
  }

  async function handleSaveUser(userId) {
    const draft = state.userDrafts[userId];
    if (!draft) return;
    state.userBusyKey = `save-${userId}`;
    state.userError = "";
    state.userMessage = "";
    render();
    try {
      const data = await requestJson(`/api/users/${userId}`, {
        method: "PUT",
        body: JSON.stringify(draft),
      });
      if (!data.ok && data.status) {
        throw new Error(apiErrorMessage(data.detail, "保存失败。"));
      }
      state.userMessage = "账号已更新。";
      await refreshUsers();
    } catch (error) {
      state.userError = error.message || "保存失败。";
    } finally {
      state.userBusyKey = "";
      render();
      bindEvents();
    }
  }

  async function handleResetPassword(userId) {
    const password = window.prompt("请输入新密码，至少 8 位：");
    if (!password) return;
    state.userBusyKey = `password-${userId}`;
    state.userError = "";
    state.userMessage = "";
    render();
    try {
      const data = await requestJson(`/api/users/${userId}/password`, {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      if (!data.ok && data.status) {
        throw new Error(apiErrorMessage(data.detail, "重置密码失败。"));
      }
      state.userMessage = "密码已重置。";
    } catch (error) {
      state.userError = error.message || "重置密码失败。";
    } finally {
      state.userBusyKey = "";
      render();
      bindEvents();
    }
  }

  async function handleDeleteUser(userId) {
    if (!window.confirm("确认删除该账号？此操作无法恢复。")) return;
    state.userBusyKey = `delete-${userId}`;
    state.userError = "";
    state.userMessage = "";
    render();
    try {
      const data = await requestJson(`/api/users/${userId}`, {
        method: "DELETE",
      });
      if (!data.ok && data.status) {
        throw new Error(apiErrorMessage(data.detail, "删除失败。"));
      }
      state.userMessage = "账号已删除。";
      await refreshUsers();
    } catch (error) {
      state.userError = error.message || "删除失败。";
    } finally {
      state.userBusyKey = "";
      render();
      bindEvents();
    }
  }

  function metric(label, value, note) {
    return `
      <div class="metric">
        <div class="metric-label">${escapeHtml(label)}</div>
        <div class="metric-value">${escapeHtml(value)}</div>
        ${note ? `<div class="metric-note">${escapeHtml(note)}</div>` : ""}
      </div>
    `;
  }

  function renderLogin() {
    return `
      <main class="auth-shell">
        <div class="auth-panel">
          <div class="auth-copy">
            <div class="brand-mark">S</div>
            <h1>SENS 管理后台</h1>
            <p>本机信息、健康状况、sens-server 服务目录和后台账号管理。</p>
            <div class="auth-badges">
              <span>Local Only</span>
              <span>MySQL</span>
              <span>Admin Users</span>
            </div>
          </div>
          <form class="auth-form" id="login-form">
            <label>
              <span>账号</span>
              <input name="username" value="sens" autocomplete="username" />
            </label>
            <label>
              <span>密码</span>
              <input name="password" type="password" autocomplete="current-password" />
            </label>
            ${state.authError ? `<div class="error-box">${escapeHtml(state.authError)}</div>` : ""}
            <button type="submit" class="primary-btn" ${state.loginBusy ? "disabled" : ""}>
              ${state.loginBusy ? "登录中..." : "登录"}
            </button>
            <div class="auth-hint">默认账号已预置为 sens。</div>
          </form>
        </div>
      </main>
    `;
  }

  function renderServiceCard(item) {
    const health = item.health || {};
    const status = health.state || "neutral";
    const device = item.device || {};
    const checks = item.checks || {};
    const excerpts = Array.isArray(item.excerpt)
      ? item.excerpt
      : String(item.excerpt || "")
          .split("\n")
          .filter(Boolean)
          .slice(0, 8);

    return `
      <article class="service-card">
        <div class="service-head">
          <div>
            <h3>${escapeHtml(item.title)}</h3>
            <div class="service-path">${escapeHtml(item.path)}</div>
          </div>
          <span class="pill ${stateClass(status)}">${escapeHtml(fmtState(status))}</span>
        </div>
        <div class="tag-row">
          ${item.archive ? '<span class="tag muted">归档</span>' : '<span class="tag">在线目录</span>'}
          ${(item.facts || [])
            .map((fact) => `<span class="tag">${escapeHtml(fact)}</span>`)
            .join("")}
        </div>
        ${
          device.items?.length
            ? `
              <div class="device-block">
                <div class="mini-title">设备信息</div>
                <div class="device-tags">
                  ${device.items
                    .map((entry) => `<span class="tag device-tag">${escapeHtml(entry.label)}：${escapeHtml(entry.value)}</span>`)
                    .join("")}
                </div>
              </div>
            `
            : ""
        }
        ${
          checks.items?.length
            ? `
              <div class="check-block">
                <div class="mini-title">基础检查</div>
                <div class="check-list">
                  ${checks.items
                    .map(
                      (check) => `
                        <div class="check-item ${stateClass(check.state)}">
                          <span class="check-label">${escapeHtml(check.label)}</span>
                          <span class="pill ${stateClass(check.state)}">${escapeHtml(fmtState(check.state))}</span>
                        </div>
                      `,
                    )
                    .join("")}
                </div>
              </div>
            `
            : ""
        }
        <div class="service-grid">
          <div>
            <div class="mini-title">健康检查</div>
            <div class="service-output">${escapeHtml(health.summary || health.output || "未采集到输出")}</div>
          </div>
          <div>
            <div class="mini-title">状态摘要</div>
            <div class="service-output">${escapeHtml(item.status?.summary || item.status?.output || "未采集到状态脚本输出")}</div>
          </div>
        </div>
        ${
          excerpts.length
            ? `<div class="excerpt">${excerpts.map((line) => `<div>${escapeHtml(line)}</div>`).join("")}</div>`
            : ""
        }
      </article>
    `;
  }

  function renderDashboard() {
    const local = state.dashboard?.local || {};
    const summary = state.dashboard?.summary || {};
    const mysql = local.mysql || {};
    const services = state.dashboard?.services || [];
    return `
      <main class="app-shell">
        <header class="topbar">
          <div>
            <div class="eyebrow">Local Control Plane</div>
            <h1>SENS 管理后台</h1>
            <p>本机与 sens-server 服务目录的统一健康视图。</p>
          </div>
          <div class="top-actions">
            <button class="ghost-btn" id="refresh-btn" ${state.refreshing ? "disabled" : ""}>
              ${state.refreshing ? "刷新中..." : "刷新"}
            </button>
            <button class="ghost-btn" id="logout-btn">退出</button>
          </div>
        </header>

        <section class="summary-grid">
          ${metric("本机状态", fmtState(local.health), local.hostname || "")}
          ${metric("MySQL", fmtState(mysql.state), mysql.version || mysql.error || "本地 socket")}
          ${metric(
            "服务目录",
            String(summary.service_count ?? 0),
            `${summary.healthy_count ?? 0} 健康 / ${summary.warning_count ?? 0} 关注 / ${summary.error_count ?? 0} 异常`,
          )}
          ${metric("归档目录", String(summary.archive_count ?? 0), state.dashboard?.device_record_path || "")}
        </section>

        <section class="content-grid">
          <section class="card">
            <div class="card-head">
              <div>
                <h2>本机信息与健康</h2>
                <p>当前主机、操作系统、CPU、内存、磁盘和 MySQL 状态。</p>
              </div>
            </div>
            <div class="local-grid">
              <div class="local-main">
                <div class="row"><span class="row-label">主机名</span><span class="row-value">${escapeHtml(local.hostname || "")}</span></div>
                <div class="row"><span class="row-label">FQDN</span><span class="row-value">${escapeHtml(local.fqdn || "")}</span></div>
                <div class="row"><span class="row-label">系统</span><span class="row-value">${escapeHtml(`${local.os || ""} ${local.os_version || ""} · ${local.kernel || ""}`)}</span></div>
                <div class="row"><span class="row-label">架构 / CPU</span><span class="row-value">${escapeHtml(`${local.architecture || ""} · ${local.cpu_count || 0} 核`)}</span></div>
                <div class="row"><span class="row-label">Load Avg</span><span class="row-value">${Array.isArray(local.load_averages) ? escapeHtml(local.load_averages.join(" / ")) : "N/A"}</span></div>
                <div class="row"><span class="row-label">Uptime</span><span class="row-value">${escapeHtml(local.uptime || "")}</span></div>
              </div>
              <div class="local-side">
                <div class="status-box">
                  <div class="status-title">磁盘</div>
                  <span class="pill ${stateClass(local.disk?.state)}">${escapeHtml(fmtState(local.disk?.state))}</span>
                  <div class="status-line">${escapeHtml(`${local.disk?.used_percent ?? 0}% used`)}</div>
                  <div class="status-line">${escapeHtml(`${local.disk?.used_gb ?? 0} / ${local.disk?.total_gb ?? 0} GB`)}</div>
                </div>
                <div class="status-box">
                  <div class="status-title">内存</div>
                  <span class="pill ${stateClass(local.memory?.state)}">${escapeHtml(fmtState(local.memory?.state))}</span>
                  <div class="status-line">${escapeHtml(`${local.memory?.available_mb ?? 0} MB 可用`)}</div>
                  <div class="status-line">${escapeHtml(`${local.memory?.available_percent ?? 0}% available`)}</div>
                </div>
                <div class="status-box">
                  <div class="status-title">MySQL</div>
                  <span class="pill ${stateClass(mysql.state)}">${escapeHtml(fmtState(mysql.state))}</span>
                  <div class="status-line">${escapeHtml(mysql.version || mysql.error || "未知版本")}</div>
                  <div class="status-line">${escapeHtml(`${mysql.database_count || 0} databases / ${mysql.user_count || 0} users`)}</div>
                </div>
              </div>
            </div>
          </section>

          <section class="card">
            <div class="card-head">
              <div>
                <h2>sens-server 服务健康</h2>
                <p>按目录读取现有运维文档，并调用本地只读健康脚本。</p>
              </div>
            </div>
            <div class="service-list">
              ${services.map((item) => renderServiceCard(item)).join("")}
            </div>
          </section>

          <section class="card">
            <div class="card-head">
              <div>
                <h2>用户管理</h2>
                <p>创建、停用、修改和重置本地登录账号。</p>
              </div>
            </div>
            <div class="user-panel">
              <form class="user-form" id="new-user-form">
                <div class="user-form-head">
                  <div>
                    <div class="mini-title">新增账号</div>
                    <div class="form-hint">账号名一旦创建后保持不变，后续只调整名称、状态和密码。</div>
                  </div>
                  <button class="primary-btn" type="submit" ${state.userBusyKey === "create" ? "disabled" : ""}>
                    ${state.userBusyKey === "create" ? "创建中..." : "创建账号"}
                  </button>
                </div>
                <div class="form-grid">
                  <label>
                    <span>账号</span>
                    <input name="username" value="${escapeHtml(state.newUser.username)}" placeholder="如 ops" autocomplete="off" />
                  </label>
                  <label>
                    <span>显示名称</span>
                    <input name="display_name" value="${escapeHtml(state.newUser.display_name)}" placeholder="如 运维账号" />
                  </label>
                  <label>
                    <span>初始密码</span>
                    <input name="password" type="password" value="${escapeHtml(state.newUser.password)}" placeholder="至少 8 位" autocomplete="new-password" />
                  </label>
                  <label>
                    <span>状态</span>
                    <select name="is_active">
                      <option value="1" ${state.newUser.is_active ? "selected" : ""}>启用</option>
                      <option value="0" ${state.newUser.is_active ? "" : "selected"}>停用</option>
                    </select>
                  </label>
                </div>
              </form>

              ${state.userError ? `<div class="error-box">${escapeHtml(state.userError)}</div>` : ""}
              ${state.userMessage ? `<div class="success-box">${escapeHtml(state.userMessage)}</div>` : ""}

              <div class="user-table-wrap">
                ${
                  state.usersLoading
                    ? '<div class="empty-state">正在加载账号列表...</div>'
                    : state.users.length
                      ? `
                        <table class="user-table" id="user-table">
                          <thead>
                            <tr>
                              <th>账号</th>
                              <th>显示名称</th>
                              <th>状态</th>
                              <th>上次登录</th>
                              <th>创建时间</th>
                              <th>更新时间</th>
                              <th>操作</th>
                            </tr>
                          </thead>
                          <tbody>
                            ${state.users
                              .map((item) => {
                                const draft = state.userDrafts[item.id] || {
                                  display_name: item.display_name,
                                  is_active: item.is_active,
                                };
                                const isCurrent = state.user && state.user.id === item.id;
                                return `
                                  <tr>
                                    <td>
                                      <div class="user-identity">
                                        <div class="user-name">${escapeHtml(item.username)}</div>
                                        ${isCurrent ? '<div class="user-meta">当前登录</div>' : ""}
                                      </div>
                                    </td>
                                    <td>
                                      <input class="inline-input" data-user-id="${item.id}" data-field="display_name" value="${escapeHtml(draft.display_name)}" />
                                    </td>
                                    <td>
                                      <select class="inline-select" data-user-id="${item.id}" data-field="is_active" ${isCurrent ? "disabled" : ""}>
                                        <option value="1" ${draft.is_active ? "selected" : ""}>启用</option>
                                        <option value="0" ${draft.is_active ? "" : "selected"}>停用</option>
                                      </select>
                                    </td>
                                    <td>${escapeHtml(formatDateTime(item.last_login_at))}</td>
                                    <td>${escapeHtml(formatDateTime(item.created_at))}</td>
                                    <td>${escapeHtml(formatDateTime(item.updated_at))}</td>
                                    <td>
                                      <div class="action-row">
                                        <button class="ghost-btn compact" data-action="save-user" data-id="${item.id}" ${state.userBusyKey === `save-${item.id}` ? "disabled" : ""}>${state.userBusyKey === `save-${item.id}` ? "保存中..." : "保存"}</button>
                                        <button class="ghost-btn compact" data-action="reset-password" data-id="${item.id}" ${state.userBusyKey === `password-${item.id}` ? "disabled" : ""}>${state.userBusyKey === `password-${item.id}` ? "重置中..." : "重置密码"}</button>
                                        ${isCurrent ? "" : `<button class="ghost-btn compact danger" data-action="delete-user" data-id="${item.id}" ${state.userBusyKey === `delete-${item.id}` ? "disabled" : ""}>${state.userBusyKey === `delete-${item.id}` ? "删除中..." : "删除"}</button>`}
                                      </div>
                                    </td>
                                  </tr>
                                `;
                              })
                              .join("")}
                          </tbody>
                        </table>
                      `
                      : '<div class="empty-state">暂无账号。</div>'
                }
              </div>
            </div>
          </section>
        </section>
      </main>
    `;
  }

  function render() {
    if (state.loading && !state.user) {
      root.innerHTML = '<main class="boot-screen"><div class="boot-card">正在加载后台状态...</div></main>';
      return;
    }
    if (!state.user || !state.dashboard) {
      root.innerHTML = renderLogin();
      return;
    }
    root.innerHTML = renderDashboard();
  }

  function bindEvents() {
    const loginForm = document.getElementById("login-form");
    if (loginForm) {
      loginForm.onsubmit = async (event) => {
        event.preventDefault();
        const formData = new FormData(loginForm);
        await handleLogin(String(formData.get("username") || ""), String(formData.get("password") || ""));
      };
    }

    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
      logoutBtn.onclick = handleLogout;
    }

    const refreshBtn = document.getElementById("refresh-btn");
    if (refreshBtn) {
      refreshBtn.onclick = handleRefresh;
    }

    const newUserForm = document.getElementById("new-user-form");
    if (newUserForm) {
      const usernameInput = newUserForm.querySelector('input[name="username"]');
      const displayNameInput = newUserForm.querySelector('input[name="display_name"]');
      const passwordInput = newUserForm.querySelector('input[name="password"]');
      const activeSelect = newUserForm.querySelector('select[name="is_active"]');
      if (usernameInput) usernameInput.oninput = (event) => updateNewUser("username", event.target.value);
      if (displayNameInput) displayNameInput.oninput = (event) => updateNewUser("display_name", event.target.value);
      if (passwordInput) passwordInput.oninput = (event) => updateNewUser("password", event.target.value);
      if (activeSelect) activeSelect.onchange = (event) => updateNewUser("is_active", event.target.value === "1");
      newUserForm.onsubmit = handleCreateUser;
    }

    const userTable = document.getElementById("user-table");
    if (userTable) {
      userTable.querySelectorAll("[data-user-id][data-field]").forEach((input) => {
        const userId = Number(input.getAttribute("data-user-id"));
        const field = input.getAttribute("data-field");
        const handler = (event) => updateDraft(userId, field, field === "is_active" ? event.target.value === "1" : event.target.value);
        input.oninput = handler;
        input.onchange = handler;
      });
      userTable.querySelectorAll("[data-action]").forEach((button) => {
        button.onclick = async (event) => {
          event.preventDefault();
          const action = button.getAttribute("data-action");
          const userId = Number(button.getAttribute("data-id"));
          if (action === "save-user") await handleSaveUser(userId);
          if (action === "reset-password") await handleResetPassword(userId);
          if (action === "delete-user") await handleDeleteUser(userId);
        };
      });
    }
  }

  render();
  bindEvents();
  loadAuthedData();
})();
