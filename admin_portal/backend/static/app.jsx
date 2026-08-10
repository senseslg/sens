const { useEffect, useState } = React;

function cls(...items) {
  return items.filter(Boolean).join(" ");
}

function fmtState(state) {
  if (state === "healthy") return "健康";
  if (state === "warning") return "关注";
  if (state === "error") return "异常";
  return "未知";
}

function stateClass(state) {
  if (state === "healthy") return "state-healthy";
  if (state === "warning") return "state-warning";
  if (state === "error") return "state-error";
  return "state-neutral";
}

function Card({ title, subtitle, children, className = "" }) {
  return (
    <section className={cls("card", className)}>
      <div className="card-head">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
      </div>
      {children}
    </section>
  );
}

function Pill({ state, label }) {
  return <span className={cls("pill", stateClass(state))}>{label}</span>;
}

function Metric({ label, value, note }) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {note ? <div className="metric-note">{note}</div> : null}
    </div>
  );
}

function formatDateTime(value) {
  if (!value) return "未填写";
  try {
    return new Date(value).toLocaleString("zh-CN", { hour12: false });
  } catch (error) {
    return value;
  }
}

function apiErrorMessage(detail, fallback) {
  const messages = {
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

function LoginScreen({ onLogin, error, busy }) {
  const [username, setUsername] = useState("sens");
  const [password, setPassword] = useState("");

  return (
    <main className="auth-shell">
      <div className="auth-panel">
        <div className="auth-copy">
          <div className="brand-mark">S</div>
          <h1>SENS 管理后台</h1>
          <p>本机信息、健康状况与 `sens-server` 下全部服务目录的运维概览。</p>
          <div className="auth-badges">
            <span>React</span>
            <span>Python</span>
            <span>MySQL</span>
          </div>
        </div>
        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault();
            onLogin(username, password);
          }}
        >
          <label>
            <span>账号</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label>
            <span>密码</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error ? <div className="error-box">{error}</div> : null}
          <button type="submit" className="primary-btn" disabled={busy}>
            {busy ? "登录中..." : "登录"}
          </button>
          <div className="auth-hint">默认账号已预置为 `sens`。</div>
        </form>
      </div>
    </main>
  );
}

function ServiceCard({ item }) {
  const health = item.health;
  const status = health ? health.state : "neutral";
  const statusLabel = health ? fmtState(health.state) : "未运行";
  const statusText = health?.summary || health?.output || "未采集到输出";
  const statusBlock = item.status;
  const excerpts = item.excerpt ? item.excerpt.split("\n").filter(Boolean).slice(0, 8) : [];

  return (
    <article className="service-card">
      <div className="service-head">
        <div>
          <h3>{item.title}</h3>
          <div className="service-path">{item.path}</div>
        </div>
        <Pill state={status} label={statusLabel} />
      </div>
      <div className="tag-row">
        {item.archive ? <span className="tag muted">归档</span> : <span className="tag">在线目录</span>}
        {item.facts?.map((fact) => (
          <span className="tag" key={fact}>
            {fact}
          </span>
        ))}
      </div>
      <div className="service-grid">
        <div>
          <div className="mini-title">健康检查</div>
          <div className="service-output">{statusText}</div>
        </div>
        <div>
          <div className="mini-title">状态摘要</div>
          <div className="service-output">
            {statusBlock?.summary || statusBlock?.output || "未采集到状态脚本输出"}
          </div>
        </div>
      </div>
      {excerpts.length ? (
        <div className="excerpt">
          {excerpts.map((line, index) => (
            <div key={index}>{line}</div>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function Dashboard({ data, onRefresh, onLogout, refreshing }) {
  const local = data.local;
  const summary = data.summary;
  const mysql = local.mysql || {};

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">Local Control Plane</div>
          <h1>SENS 管理后台</h1>
          <p>本机与 `sens-server` 服务目录的统一健康视图。</p>
        </div>
        <div className="top-actions">
          <button className="ghost-btn" onClick={onRefresh} disabled={refreshing}>
            {refreshing ? "刷新中..." : "刷新"}
          </button>
          <button className="ghost-btn" onClick={onLogout}>
            退出
          </button>
        </div>
      </header>

      <section className="summary-grid">
        <Metric label="本机状态" value={fmtState(local.health)} note={local.hostname} />
        <Metric label="MySQL" value={fmtState(mysql.state)} note={mysql.version || mysql.error || "本地 socket"} />
        <Metric label="服务目录" value={summary.service_count} note={`${summary.healthy_count} 健康 / ${summary.warning_count} 关注 / ${summary.error_count} 异常`} />
        <Metric label="归档目录" value={summary.archive_count} note={data.device_record_path} />
      </section>

      <section className="content-grid">
        <Card title="本机信息与健康" subtitle="当前主机、操作系统、CPU、内存、磁盘和 MySQL 状态。">
          <div className="local-grid">
            <div className="local-main">
              <div className="row">
                <span className="row-label">主机名</span>
                <span className="row-value">{local.hostname}</span>
              </div>
              <div className="row">
                <span className="row-label">FQDN</span>
                <span className="row-value">{local.fqdn}</span>
              </div>
              <div className="row">
                <span className="row-label">系统</span>
                <span className="row-value">{local.os} {local.os_version} · {local.kernel}</span>
              </div>
              <div className="row">
                <span className="row-label">架构 / CPU</span>
                <span className="row-value">{local.architecture} · {local.cpu_count} 核</span>
              </div>
              <div className="row">
                <span className="row-label">Load Avg</span>
                <span className="row-value">{local.load_averages ? local.load_averages.join(" / ") : "N/A"}</span>
              </div>
              <div className="row">
                <span className="row-label">Uptime</span>
                <span className="row-value">{local.uptime}</span>
              </div>
            </div>
            <div className="local-side">
              <div className="status-box">
                <div className="status-title">磁盘</div>
                <Pill state={local.disk.state} label={fmtState(local.disk.state)} />
                <div className="status-line">{local.disk.used_percent}% used</div>
                <div className="status-line">{local.disk.used_gb} / {local.disk.total_gb} GB</div>
              </div>
              <div className="status-box">
                <div className="status-title">内存</div>
                <Pill state={local.memory.state} label={fmtState(local.memory.state)} />
                <div className="status-line">{local.memory.available_mb} MB 可用</div>
                <div className="status-line">{local.memory.available_percent}% available</div>
              </div>
              <div className="status-box">
                <div className="status-title">MySQL</div>
                <Pill state={mysql.state} label={fmtState(mysql.state)} />
                <div className="status-line">{mysql.version || mysql.error || "未知版本"}</div>
                <div className="status-line">{mysql.database_count || 0} databases / {mysql.user_count || 0} users</div>
              </div>
            </div>
          </div>
        </Card>

        <Card title="sens-server 服务健康" subtitle="按目录读取现有运维文档，并调用本地只读健康脚本。">
          <div className="service-list">
            {data.services.map((item) => (
              <ServiceCard key={item.key} item={item} />
            ))}
          </div>
        </Card>
      </section>
    </main>
  );
}

function UserManagement({
  currentUser,
  users,
  drafts,
  newUser,
  onNewUserChange,
  onCreateUser,
  onDraftChange,
  onSaveUser,
  onResetPassword,
  onDeleteUser,
  loading,
  busyKey,
  error,
  message,
}) {
  return (
    <Card title="用户管理" subtitle="创建、停用、修改和重置本地登录账号。">
      <div className="user-panel">
        <form className="user-form" onSubmit={onCreateUser}>
          <div className="user-form-head">
            <div>
              <div className="mini-title">新增账号</div>
              <div className="form-hint">账号名一旦创建后保持不变，后续只调整名称、状态和密码。</div>
            </div>
            <button className="primary-btn" type="submit" disabled={busyKey === "create"}>
              {busyKey === "create" ? "创建中..." : "创建账号"}
            </button>
          </div>
          <div className="form-grid">
            <label>
              <span>账号</span>
              <input
                value={newUser.username}
                onChange={(event) => onNewUserChange("username", event.target.value)}
                placeholder="如 ops"
                autoComplete="off"
              />
            </label>
            <label>
              <span>显示名称</span>
              <input
                value={newUser.display_name}
                onChange={(event) => onNewUserChange("display_name", event.target.value)}
                placeholder="如 运维账号"
              />
            </label>
            <label>
              <span>初始密码</span>
              <input
                type="password"
                value={newUser.password}
                onChange={(event) => onNewUserChange("password", event.target.value)}
                placeholder="至少 8 位"
                autoComplete="new-password"
              />
            </label>
            <label>
              <span>状态</span>
              <select
                value={newUser.is_active ? "1" : "0"}
                onChange={(event) => onNewUserChange("is_active", event.target.value === "1")}
              >
                <option value="1">启用</option>
                <option value="0">停用</option>
              </select>
            </label>
          </div>
        </form>

        {error ? <div className="error-box">{error}</div> : null}
        {message ? <div className="success-box">{message}</div> : null}

        <div className="user-table-wrap">
          {loading ? (
            <div className="empty-state">正在加载账号列表...</div>
          ) : users.length ? (
            <table className="user-table">
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
                {users.map((user) => {
                  const draft = drafts[user.id] || {
                    display_name: user.display_name,
                    is_active: user.is_active,
                  };
                  const isCurrent = currentUser && currentUser.id === user.id;
                  return (
                    <tr key={user.id}>
                      <td>
                        <div className="user-identity">
                          <div className="user-name">{user.username}</div>
                          {isCurrent ? <div className="user-meta">当前登录</div> : null}
                        </div>
                      </td>
                      <td>
                        <input
                          className="inline-input"
                          value={draft.display_name}
                          onChange={(event) => onDraftChange(user.id, "display_name", event.target.value)}
                        />
                      </td>
                      <td>
                        <select
                          className="inline-select"
                          value={draft.is_active ? "1" : "0"}
                          onChange={(event) => onDraftChange(user.id, "is_active", event.target.value === "1")}
                          disabled={isCurrent}
                        >
                          <option value="1">启用</option>
                          <option value="0">停用</option>
                        </select>
                      </td>
                      <td>{formatDateTime(user.last_login_at)}</td>
                      <td>{formatDateTime(user.created_at)}</td>
                      <td>{formatDateTime(user.updated_at)}</td>
                      <td>
                        <div className="action-row">
                          <button
                            className="ghost-btn compact"
                            onClick={() => onSaveUser(user.id)}
                            disabled={busyKey === `save-${user.id}`}
                          >
                            {busyKey === `save-${user.id}` ? "保存中..." : "保存"}
                          </button>
                          <button
                            className="ghost-btn compact"
                            onClick={() => onResetPassword(user.id)}
                            disabled={busyKey === `password-${user.id}`}
                          >
                            {busyKey === `password-${user.id}` ? "重置中..." : "重置密码"}
                          </button>
                          {!isCurrent ? (
                            <button
                              className="ghost-btn compact danger"
                              onClick={() => onDeleteUser(user.id)}
                              disabled={busyKey === `delete-${user.id}`}
                            >
                              {busyKey === `delete-${user.id}` ? "删除中..." : "删除"}
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">暂无账号。</div>
          )}
        </div>
      </div>
    </Card>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [users, setUsers] = useState([]);
  const [userDrafts, setUserDrafts] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [usersLoading, setUsersLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const [loginBusy, setLoginBusy] = useState(false);
  const [userBusyKey, setUserBusyKey] = useState("");
  const [userError, setUserError] = useState("");
  const [userMessage, setUserMessage] = useState("");
  const [newUser, setNewUser] = useState({
    username: "",
    display_name: "",
    password: "",
    is_active: true,
  });

  async function loadUsers() {
    setUsersLoading(true);
    try {
      const usersResp = await fetch("/api/users");
      if (!usersResp.ok) {
        throw new Error("users_unavailable");
      }
      const usersData = await usersResp.json();
      const nextUsers = usersData.users || [];
      setUsers(nextUsers);
      setUserDrafts(
        Object.fromEntries(
          nextUsers.map((item) => [
            item.id,
            {
              display_name: item.display_name,
              is_active: item.is_active,
            },
          ]),
        ),
      );
      return nextUsers;
    } catch (error) {
      setUserError("用户列表加载失败，请重试。");
      throw error;
    } finally {
      setUsersLoading(false);
    }
  }

  async function loadDashboard() {
    const dashResp = await fetch("/api/dashboard");
    if (!dashResp.ok) {
      throw new Error("dashboard_unavailable");
    }
    const dashData = await dashResp.json();
    setDashboard(dashData);
    return dashData;
  }

  async function loadMeDashboardAndUsers() {
    setLoading(true);
    setAuthError("");
    setUserError("");
    try {
      const meResp = await fetch("/api/me");
      if (!meResp.ok) {
        setUser(null);
        setDashboard(null);
        setUsers([]);
        setLoading(false);
        return;
      }
      const meData = await meResp.json();
      setUser(meData);
      await loadDashboard();
      await loadUsers();
    } catch (error) {
      setAuthError("后台数据加载失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMeDashboardAndUsers();
  }, []);

  async function handleLogin(username, password) {
    setLoginBusy(true);
    setAuthError("");
    try {
      const resp = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!resp.ok) {
        setAuthError("账号或密码不正确。");
        return;
      }
      const meData = await resp.json();
      setUser(meData);
      await loadMeDashboardAndUsers();
    } catch (error) {
      setAuthError("登录请求失败。");
    } finally {
      setLoginBusy(false);
    }
  }

  async function handleLogout() {
    await fetch("/api/logout", { method: "POST" });
    setUser(null);
    setDashboard(null);
    setUsers([]);
    setUserDrafts({});
    setUserError("");
    setUserMessage("");
  }

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await Promise.all([loadDashboard(), loadUsers()]);
    } catch (error) {
      setUserError("刷新后台数据失败，请稍后再试。");
    } finally {
      setRefreshing(false);
    }
  }

  function updateNewUser(field, value) {
    setNewUser((prev) => ({ ...prev, [field]: value }));
  }

  function updateDraft(userId, field, value) {
    setUserDrafts((prev) => ({
      ...prev,
      [userId]: {
        ...(prev[userId] || {}),
        [field]: value,
      },
    }));
  }

  async function refreshUsers() {
    await loadUsers();
  }

  async function handleCreateUser(event) {
    event.preventDefault();
    setUserBusyKey("create");
    setUserError("");
    setUserMessage("");
    try {
      const resp = await fetch("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newUser),
      });
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(apiErrorMessage(body.detail, "创建账号失败。"));
      }
      setNewUser({
        username: "",
        display_name: "",
        password: "",
        is_active: true,
      });
      await refreshUsers();
      setUserMessage("账号已创建。");
    } catch (error) {
      setUserError(error.message || "创建账号失败。");
    } finally {
      setUserBusyKey("");
    }
  }

  async function handleSaveUser(userId) {
    const draft = userDrafts[userId];
    if (!draft) return;
    setUserBusyKey(`save-${userId}`);
    setUserError("");
    setUserMessage("");
    try {
      const resp = await fetch(`/api/users/${userId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(apiErrorMessage(body.detail, "保存失败。"));
      }
      await refreshUsers();
      setUserMessage("账号已更新。");
    } catch (error) {
      setUserError(error.message || "保存失败。");
    } finally {
      setUserBusyKey("");
    }
  }

  async function handleResetPassword(userId) {
    const password = window.prompt("请输入新密码，至少 8 位：");
    if (!password) return;
    setUserBusyKey(`password-${userId}`);
    setUserError("");
    setUserMessage("");
    try {
      const resp = await fetch(`/api/users/${userId}/password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(apiErrorMessage(body.detail, "重置密码失败。"));
      }
      setUserMessage("密码已重置。");
    } catch (error) {
      setUserError(error.message || "重置密码失败。");
    } finally {
      setUserBusyKey("");
    }
  }

  async function handleDeleteUser(userId) {
    if (!window.confirm("确认删除该账号？此操作无法恢复。")) return;
    setUserBusyKey(`delete-${userId}`);
    setUserError("");
    setUserMessage("");
    try {
      const resp = await fetch(`/api/users/${userId}`, { method: "DELETE" });
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(apiErrorMessage(body.detail, "删除失败。"));
      }
      await refreshUsers();
      setUserMessage("账号已删除。");
    } catch (error) {
      setUserError(error.message || "删除失败。");
    } finally {
      setUserBusyKey("");
    }
  }

  if (loading && !user) {
    return (
      <div className="boot-screen">
        <div className="boot-card">正在加载后台状态...</div>
      </div>
    );
  }

  if (!user || !dashboard) {
    return <LoginScreen onLogin={handleLogin} error={authError} busy={loginBusy} />;
  }

  return (
    <>
      <Dashboard
        data={dashboard}
        onRefresh={handleRefresh}
        onLogout={handleLogout}
        refreshing={refreshing}
      />
      <div className="app-shell">
        <UserManagement
          currentUser={user}
          users={users}
          drafts={userDrafts}
          newUser={newUser}
          onNewUserChange={updateNewUser}
          onCreateUser={handleCreateUser}
          onDraftChange={updateDraft}
          onSaveUser={handleSaveUser}
          onResetPassword={handleResetPassword}
          onDeleteUser={handleDeleteUser}
          loading={usersLoading}
          busyKey={userBusyKey}
          error={userError}
          message={userMessage}
        />
      </div>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
