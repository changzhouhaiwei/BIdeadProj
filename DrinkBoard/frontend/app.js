(() => {
  const DEVICE_LABEL = { phone: "手机", tablet: "平板", desktop: "电脑", unknown: "" };
  const HOST_KEY = "drinkboard.host.v1";

  const ui = {
    roomId: "",
    joinKey: "",
    hostMode: false,
    tab: "log",
    drinkKey: "",
    selectedId: "",
    boardDate: "",
    dateTouched: false,
    cache: null,
    me: null,
    view: "home",
    lock: 0,
    timer: 0,
    qrUrl: "",
    ticket: 0,
  };

  function apiBase() {
    return new URL("api/", window.location.href).toString();
  }

  function storageGet(key) {
    try {
      return localStorage.getItem(key);
    } catch (_err) {
      return null;
    }
  }

  function storageSet(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (_err) {
      /* 隐私模式就只留在这一页 */
    }
  }

  function loadHosts() {
    try {
      const parsed = JSON.parse(storageGet(HOST_KEY) || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch (_err) {
      return [];
    }
  }

  function saveHost(entry) {
    const hosts = loadHosts().filter((item) => item.roomId !== entry.roomId);
    hosts.unshift(entry);
    storageSet(HOST_KEY, JSON.stringify(hosts.slice(0, 8)));
  }

  function adminFor(roomId) {
    const found = loadHosts().find((item) => item.roomId === roomId);
    return found ? found.adminToken : "";
  }

  function whoKey(roomId) {
    return `drinkboard.who.v1.${roomId}`;
  }

  function loadWho(roomId) {
    try {
      const parsed = JSON.parse(storageGet(whoKey(roomId)) || "null");
      if (parsed && parsed.token && parsed.id) return parsed;
    } catch (_err) {
      /* 继续走填昵称 */
    }
    return null;
  }

  function saveWho(roomId, who) {
    storageSet(whoKey(roomId), JSON.stringify(who));
  }

  function clearWho(roomId) {
    try {
      localStorage.removeItem(whoKey(roomId));
    } catch (_err) {
      /* 忽略 */
    }
  }

  function h(tag, attrs, children) {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([key, value]) => {
      if (value == null || value === false) return;
      if (key === "class") node.className = value;
      else if (key === "onClick") node.addEventListener("click", value);
      else if (key === "onSubmit") node.addEventListener("submit", value);
      else if (key === "onInput") node.addEventListener("input", value);
      else if (key === "onChange") node.addEventListener("change", value);
      else if (key === "disabled") node.disabled = true;
      else node.setAttribute(key, String(value));
    });
    const list = Array.isArray(children) ? children : children == null ? [] : [children];
    list.flat().forEach((child) => {
      if (child == null || child === false) return;
      node.append(child.nodeType ? child : document.createTextNode(String(child)));
    });
    return node;
  }

  function toast(message) {
    const box = document.getElementById("toast");
    box.textContent = message;
    box.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => box.classList.remove("show"), 2200);
  }

  function deviceInfo() {
    const width = window.screen ? window.screen.width : 0;
    const height = window.screen ? window.screen.height : 0;
    const ua = navigator.userAgent || "";
    const shortSide = Math.min(width || 9999, height || 9999);
    let deviceType = "desktop";
    if (/Mobi|Android|iPhone|iPod/i.test(ua) || shortSide < 600) deviceType = "phone";
    else if (/iPad|Tablet/i.test(ua) || shortSide < 1024) deviceType = "tablet";
    return {
      user_agent: ua.slice(0, 300),
      platform: navigator.platform || "",
      screen: `${width}x${height}`,
      language: navigator.language || "",
      device_type: deviceType,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
    };
  }

  async function api(path, options) {
    const opts = options || {};
    const headers = Object.assign({ Accept: "application/json" }, opts.headers || {});
    if (ui.joinKey) headers["X-Join-Key"] = ui.joinKey;
    if (opts.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
    let response;
    try {
      response = await fetch(apiBase() + path, {
        method: opts.method || "GET",
        headers,
        body: opts.body || null,
      });
    } catch (_err) {
      const error = new Error("没连上，看下网络");
      error.status = 0;
      throw error;
    }
    const text = await response.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (_err) {
        data = text;
      }
    }
    if (!response.ok) {
      const detail = data && data.detail ? data.detail : "没办成";
      const error = new Error(detail);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function parseRoute() {
    const query = new URLSearchParams(window.location.search);
    ui.roomId = query.get("room") || "";
    ui.joinKey = query.get("k") || "";
    ui.hostMode = query.get("host") === "1";
  }

  function setRoute(params, replace) {
    const url = new URL(window.location.href);
    url.search = "";
    url.hash = "";
    Object.entries(params).forEach(([key, value]) => {
      if (value) url.searchParams.set(key, value);
    });
    if (replace) history.replaceState({}, "", url);
    else history.pushState({}, "", url);
    parseRoute();
    show();
  }

  function joinPageUrl() {
    const url = new URL(window.location.href);
    url.searchParams.set("room", ui.roomId);
    url.searchParams.set("k", ui.joinKey);
    url.searchParams.delete("host");
    url.hash = "";
    return url.toString();
  }

  function mount(node) {
    const y = window.scrollY;
    document.getElementById("app").replaceChildren(node);
    window.scrollTo(0, y);
  }

  function grams(value) {
    const number = Number(value) || 0;
    return (Math.round(number * 100) / 100).toFixed(2);
  }

  function signedMl(value) {
    const number = Number(value) || 0;
    return number > 0 ? `+${number} ml` : `${number} ml`;
  }

  function clock(iso) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat("zh-CN", {
      timeZone: "Asia/Shanghai",
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).format(date);
  }

  function shiftDate(iso, days) {
    const parts = iso.split("-").map(Number);
    const date = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
    date.setUTCDate(date.getUTCDate() + days);
    return date.toISOString().slice(0, 10);
  }

  function localHostWarning(url) {
    try {
      const host = new URL(url).hostname;
      if (host === "localhost" || host === "127.0.0.1" || host === "::1") {
        return "这是本机地址，旁边的手机扫不开。用电脑的局域网 IP 打开这个页，再给别人扫。";
      }
    } catch (_err) {
      return "";
    }
    return "";
  }

  function stopPoll() {
    if (ui.timer) clearInterval(ui.timer);
    ui.timer = 0;
  }

  function startPoll() {
    stopPoll();
    ui.timer = setInterval(() => {
      if (ui.view === "board") refresh(true);
    }, 3000);
  }

  async function withLock(fn) {
    ui.lock += 1;
    try {
      return await fn();
    } finally {
      ui.lock -= 1;
    }
  }

  function show() {
    parseRoute();
    stopPoll();
    ui.ticket += 1;
    if (!ui.roomId || !ui.joinKey) {
      ui.view = "home";
      renderHome();
      return;
    }
    if (ui.hostMode) {
      ui.view = "host";
      renderHost(ui.ticket);
      return;
    }
    ui.me = loadWho(ui.roomId);
    if (!ui.me) {
      ui.view = "nick";
      renderNick();
      return;
    }
    ui.view = "board";
    renderBoardLoading();
    refresh(false).then(() => {
      if (ui.view === "board") startPoll();
    });
  }

  function renderHome() {
    document.title = "酒局记账";
    const hosts = loadHosts();
    const paste = h("input", {
      id: "paste-link",
      type: "url",
      placeholder: "把链接贴这里",
      autocomplete: "off",
    });
    const resume = hosts.map((item) =>
      h(
        "button",
        {
          type: "button",
          class: "btn btn-line",
          onClick: () =>
            setRoute({ room: item.roomId, k: item.joinKey, host: "1" }, false),
        },
        item.title || "继续主持"
      )
    );
    mount(
      h("div", {}, [
        h("h1", {}, "酒局记账"),
        h("p", { class: "lede" }, "开一局，把码亮出来。扫进来的人都记在同一张牌上，谁都能改谁的量。"),
        h("div", { class: "card stack" }, [
          h(
            "button",
            { type: "button", class: "btn btn-primary", onClick: createRoom },
            "创建酒局"
          ),
          resume.length ? h("p", { class: "muted" }, "这台设备主持过") : null,
          resume,
        ]),
        h("form", {
          class: "card stack",
          onSubmit: (event) => {
            event.preventDefault();
            openPasted(paste.value);
          },
        }, [
          h("label", { for: "paste-link" }, "手里已经有链接"),
          paste,
          h("button", { type: "submit", class: "btn btn-green" }, "打开"),
        ]),
      ])
    );
  }

  async function createRoom() {
    await withLock(async () => {
      try {
        const created = await api("rooms", { method: "POST" });
        saveHost({
          roomId: created.room_id,
          joinKey: created.join_key,
          adminToken: created.admin_token,
          title: created.title,
        });
        toast("局开好了");
        setRoute({ room: created.room_id, k: created.join_key, host: "1" }, false);
      } catch (error) {
        toast(error.message);
      }
    });
  }

  function openPasted(text) {
    const raw = (text || "").trim();
    if (!raw) {
      toast("先贴链接");
      return;
    }
    try {
      const url = new URL(raw, window.location.origin);
      const room = url.searchParams.get("room");
      const key = url.searchParams.get("k");
      if (!room || !key) throw new Error("链接里没有房间");
      setRoute({ room, k: key }, false);
    } catch (_err) {
      toast("这链接不像这一局的");
    }
  }

  async function renderHost(ticket) {
    document.title = "亮码 · 酒局记账";
    mount(h("p", { class: "lede" }, "正在把码画出来…"));
    let state;
    try {
      state = await api(`rooms/${encodeURIComponent(ui.roomId)}/state`);
    } catch (error) {
      if (ticket !== ui.ticket) return;
      mount(h("div", { class: "card" }, [
        h("h1", {}, "链接无效"),
        h("p", { class: "muted" }, error.message),
        h("button", { type: "button", class: "btn btn-line", onClick: () => setRoute({}, false) }, "回首页"),
      ]));
      return;
    }
    if (ticket !== ui.ticket) return;
    const pageUrl = joinPageUrl();
    const img = h("img", { class: "qr", alt: "加入这局的二维码", width: "240", height: "240" });
    try {
      const response = await fetch(apiBase() + `rooms/${encodeURIComponent(ui.roomId)}/qr`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "image/svg+xml",
          "X-Join-Key": ui.joinKey,
        },
        body: JSON.stringify({ page_url: pageUrl }),
      });
      if (!response.ok) throw new Error("二维码没出来");
      const svg = await response.text();
      if (ui.qrUrl) URL.revokeObjectURL(ui.qrUrl);
      ui.qrUrl = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
      img.src = ui.qrUrl;
    } catch (_err) {
      img.alt = "二维码没出来，用下面的链接也行";
    }
    if (ticket !== ui.ticket) return;
    const warning = localHostWarning(pageUrl);
    const admin = adminFor(ui.roomId);
    const link = h("input", { class: "linkbox", readonly: "readonly", value: pageUrl });
    mount(
      h("div", {}, [
        h("h1", {}, state.title || "酒局"),
        h("p", { class: "lede" }, "扫这个码，进的是同一局。"),
        warning ? h("p", { class: "warn" }, warning) : null,
        h("div", { class: "card stack" }, [
          img,
          link,
          h("div", { class: "row" }, [
            h("button", { type: "button", class: "btn btn-line", onClick: () => copyText(pageUrl) }, "复制链接"),
            h(
              "button",
              {
                type: "button",
                class: "btn btn-primary",
                onClick: () => setRoute({ room: ui.roomId, k: ui.joinKey }, false),
              },
              "进入记账"
            ),
          ]),
        ]),
        adminPanel(state, admin),
      ])
    );
  }

  function adminPanel(state, admin) {
    if (!admin) {
      return h("div", { class: "card" }, [
        h("p", {}, "这台设备没有局主口令，酒单改不了。"),
        h("p", { class: "muted" }, "口令只在创建那台设备上留着。"),
      ]);
    }
    const titleInput = h("input", { id: "room-title", type: "text", value: state.title, maxlength: "40" });
    const list = h("div", {});
    state.drinks.forEach((drink) => list.append(drinkEditor(drink)));
    const tokenBox = h("input", { class: "linkbox", readonly: "readonly", value: admin });
    return h("div", { class: "card stack" }, [
      h("h2", {}, "局主"),
      h("p", { class: "muted" }, "口令存在这台设备里。换手机就找不回来了，自己抄一份。"),
      tokenBox,
      h("button", { type: "button", class: "btn btn-line tiny", onClick: () => copyText(admin) }, "复制口令"),
      h("label", { for: "room-title" }, "房间名"),
      titleInput,
      h("p", {}, "酒单"),
      list,
      h(
        "button",
        {
          type: "button",
          class: "btn btn-line",
          onClick: () => {
            list.append(
              drinkEditor({
                key: `c${Math.random().toString(36).slice(2, 8)}`,
                name: "",
                abv: 10,
                step_ml: 50,
                presets_ml: [],
              })
            );
          },
        },
        "再加一种酒"
      ),
      h(
        "button",
        {
          type: "button",
          class: "btn btn-primary",
          onClick: () => saveSettings(titleInput.value, list),
        },
        "保存酒单"
      ),
      h(
        "button",
        { type: "button", class: "btn btn-line", onClick: reloadDrinks },
        "按服务器上的配置重载"
      ),
      h(
        "button",
        { type: "button", class: "btn btn-danger", onClick: () => confirmReset(state.shanghai_today) },
        "清空今天"
      ),
    ]);
  }

  function drinkEditor(drink) {
    const presets = (drink.presets_ml || []).join(",");
    return h("fieldset", { class: "drink-edit", "data-key": drink.key }, [
      h("legend", {}, drink.name || "新的酒"),
      h("label", {}, ["名字", h("input", { type: "text", "data-field": "name", value: drink.name, maxlength: "20" })]),
      h("div", { class: "grid-2" }, [
        h("label", {}, ["度数", h("input", { type: "number", "data-field": "abv", value: drink.abv, min: "0.1", max: "100", step: "0.1" })]),
        h("label", {}, ["每次加减 ml", h("input", { type: "number", "data-field": "step", value: drink.step_ml, min: "1", max: "2000", step: "1" })]),
      ]),
      h("label", {}, [
        "快捷毫升，用逗号分开",
        h("input", { type: "text", "data-field": "presets", value: presets, placeholder: "330,500" }),
      ]),
      h(
        "button",
        {
          type: "button",
          class: "btn btn-line tiny",
          onClick: (event) => {
            const box = event.currentTarget.closest(".card") || document;
            if (box.querySelectorAll(".drink-edit").length <= 1) {
              toast("至少留一种酒");
              return;
            }
            event.currentTarget.closest(".drink-edit").remove();
          },
        },
        "从酒单拿掉"
      ),
    ]);
  }

  function readDrinks(list) {
    const drinks = [];
    list.querySelectorAll(".drink-edit").forEach((node) => {
      const presets = node.querySelector('[data-field="presets"]').value
        .split(/[,，\s]+/)
        .map((item) => item.trim())
        .filter(Boolean)
        .map((item) => Number(item));
      drinks.push({
        key: node.getAttribute("data-key"),
        name: node.querySelector('[data-field="name"]').value.trim(),
        abv: Number(node.querySelector('[data-field="abv"]').value),
        step_ml: Number(node.querySelector('[data-field="step"]').value),
        presets_ml: presets,
      });
    });
    return drinks;
  }

  async function saveSettings(title, list) {
    const admin = adminFor(ui.roomId);
    await withLock(async () => {
      try {
        await api(`rooms/${encodeURIComponent(ui.roomId)}/settings`, {
          method: "PUT",
          headers: { "X-Admin-Token": admin },
          body: JSON.stringify({ title: title.trim(), drinks: readDrinks(list) }),
        });
        const hosts = loadHosts();
        const current = hosts.find((item) => item.roomId === ui.roomId);
        if (current) {
          current.title = title.trim();
          saveHost(current);
        }
        toast("酒单存好了");
        renderHost();
      } catch (error) {
        toast(error.message);
      }
    });
  }

  async function reloadDrinks() {
    const admin = adminFor(ui.roomId);
    await withLock(async () => {
      try {
        await api(`rooms/${encodeURIComponent(ui.roomId)}/drinks/reload`, {
          method: "POST",
          headers: { "X-Admin-Token": admin },
        });
        toast("按配置重载了");
        renderHost();
      } catch (error) {
        toast(error.message);
      }
    });
  }

  function confirmReset(day) {
    const panel = h("div", { class: "card stack" }, [
      h("p", {}, `清空 ${day} 的记录？历史里其他天还在。`),
      h("div", { class: "row" }, [
        h("button", { type: "button", class: "btn btn-line", onClick: () => panel.remove() }, "再想想"),
        h(
          "button",
          {
            type: "button",
            class: "btn btn-danger",
            onClick: async () => {
              try {
                await api(`rooms/${encodeURIComponent(ui.roomId)}/reset-day`, {
                  method: "POST",
                  headers: { "X-Admin-Token": adminFor(ui.roomId) },
                  body: JSON.stringify({ date: day }),
                });
                toast("今天清空了");
                panel.remove();
              } catch (error) {
                toast(error.message);
              }
            },
          },
          "清空"
        ),
      ]),
    ]);
    document.getElementById("app").append(panel);
    panel.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function renderNick() {
    document.title = "进局 · 酒局记账";
    const input = h("input", {
      id: "nick",
      type: "text",
      maxlength: "16",
      required: "required",
      autocomplete: "nickname",
      placeholder: "例如老王",
    });
    mount(
      h("form", {
        class: "card stack",
        onSubmit: (event) => {
          event.preventDefault();
          doJoin(input.value);
        },
      }, [
        h("h1", {}, "先起个昵称"),
        h("p", { class: "muted" }, "今晚别人就这么叫你。不用登录。"),
        h("label", { for: "nick" }, "昵称"),
        input,
        h("button", { type: "submit", class: "btn btn-primary" }, "进入"),
      ])
    );
    api(`rooms/${encodeURIComponent(ui.roomId)}/state`)
      .then((state) => {
        const title = document.querySelector("form h1");
        if (title && state.title) title.textContent = state.title;
      })
      .catch(() => {
        /* 进局时再报链接无效 */
      });
  }

  async function doJoin(nickname) {
    await withLock(async () => {
      try {
        const joined = await api(`rooms/${encodeURIComponent(ui.roomId)}/join`, {
          method: "POST",
          body: JSON.stringify({ nickname, device: deviceInfo() }),
        });
        ui.me = {
          id: joined.participant_id,
          token: joined.participant_token,
          nickname: joined.nickname,
        };
        saveWho(ui.roomId, ui.me);
        toast(`进来了，${joined.nickname}`);
        show();
      } catch (error) {
        if (error.status === 404) {
          mount(h("div", { class: "card" }, [
            h("h1", {}, "链接无效"),
            h("p", { class: "muted" }, "让局主重新发一个码。"),
          ]));
          return;
        }
        toast(error.message);
      }
    });
  }

  function renderBoardLoading() {
    mount(h("p", { class: "lede" }, "正在打开这局…"));
  }

  async function refresh(silent) {
    if (ui.lock && silent) return;
    const query = ui.boardDate ? `?board_date=${encodeURIComponent(ui.boardDate)}` : "";
    try {
      const headers = {};
      if (ui.me && ui.me.token) headers["X-Participant-Token"] = ui.me.token;
      const data = await api(`rooms/${encodeURIComponent(ui.roomId)}/state${query}`, { headers });
      ui.cache = data;
      if (ui.me && !data.me) {
        clearWho(ui.roomId);
        ui.me = null;
        ui.view = "nick";
        stopPoll();
        renderNick();
        return;
      }
      if (!ui.dateTouched) ui.boardDate = data.board_date || data.shanghai_today;
      if (!ui.drinkKey && data.drinks[0]) ui.drinkKey = data.drinks[0].key;
      if (!data.drinks.some((drink) => drink.key === ui.drinkKey) && data.drinks[0]) {
        ui.drinkKey = data.drinks[0].key;
      }
      const people = data.participants || [];
      if (!people.some((person) => person.id === ui.selectedId)) {
        const mine = ui.me && people.find((person) => person.id === ui.me.id);
        ui.selectedId = mine ? mine.id : people[0] ? people[0].id : "";
      }
      if (ui.view === "board" && !editing()) renderBoard();
    } catch (error) {
      if (error.status === 401) {
        clearWho(ui.roomId);
        ui.me = null;
        ui.view = "nick";
        stopPoll();
        renderNick();
        return;
      }
      if (!silent) {
        if (error.status === 404) {
          ui.view = "dead";
          stopPoll();
          mount(h("div", { class: "card" }, [
            h("h1", {}, "链接无效"),
            h("p", { class: "muted" }, "让局主重新发一个码。"),
          ]));
          return;
        }
        toast(error.message);
      }
    }
  }

  function editing() {
    const el = document.activeElement;
    if (!el) return false;
    const tag = el.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
  }

  function renderBoard() {
    const data = ui.cache;
    if (!data) return;
    document.title = `${data.title} · 酒局记账`;
    const drink = data.drinks.find((item) => item.key === ui.drinkKey) || data.drinks[0];
    const selected = data.participants.find((person) => person.id === ui.selectedId);
    mount(
      h("div", {}, [
        headerBlock(data),
        ui.tab === "log" ? logTab(data, drink, selected) : null,
        ui.tab === "today" ? rankTab(data.leaderboard_today, "今天还没人记") : null,
        ui.tab === "all" ? rankTab(data.leaderboard_all, "这局还没有记录") : null,
        ui.tab === "audit" ? auditTab(data) : null,
        tabbar(),
      ])
    );
  }

  function headerBlock(data) {
    return h("div", { class: "topstick" }, [
      h("div", { class: "person-name" }, [
        h("h1", { class: "page-title" }, data.title),
        h(
          "button",
          { type: "button", class: "chip", onClick: () => setRoute({ room: ui.roomId, k: ui.joinKey, host: "1" }, false) },
          "亮码"
        ),
      ]),
      h("p", { class: "sub" }, `${data.shanghai_today} · 上海时间 · 每几秒自动刷新`),
    ]);
  }

  function logTab(data, drink, selected) {
    const mine = ui.me && data.participants.find((person) => person.id === ui.me.id);
    const blocks = [
      drink ? drinkChips(data.drinks) : h("p", { class: "warn" }, "酒单是空的"),
      data.board_date !== data.shanghai_today
        ? h("p", { class: "warn" }, `正在补记 ${data.board_date}。今天的榜不动，历史榜会计上。`)
        : null,
      dateField(data),
      drink && selected ? actionBar(drink, selected) : null,
      data.participants.length
        ? data.participants.map((person) => personCard(person, drink, mine))
        : h("div", { class: "card" }, "还没人进局。把码发给旁边的人。"),
      formulaNote(data),
    ];
    return h("div", {}, blocks);
  }

  function drinkChips(drinks) {
    return h(
      "div",
      { class: "chips" },
      drinks.map((drink) =>
        h(
          "button",
          {
            type: "button",
            class: "chip",
            "aria-pressed": drink.key === ui.drinkKey ? "true" : "false",
            onClick: () => {
              ui.drinkKey = drink.key;
              renderBoard();
            },
          },
          drink.name
        )
      )
    );
  }

  function dateField(data) {
    return h("label", { class: "sub" }, [
      "记在哪一天",
      h("input", {
        type: "date",
        value: data.board_date,
        min: shiftDate(data.shanghai_today, -60),
        max: data.shanghai_today,
        onChange: (event) => {
          ui.dateTouched = true;
          ui.boardDate = event.target.value;
          refresh(false);
        },
      }),
    ]);
  }

  function actionBar(drink, selected) {
    const ml = Number(selected.board.ml_by_drink[drink.key] || 0);
    const presets = (drink.presets_ml || []).filter((value) => value !== drink.step_ml);
    const setInput = h("input", {
      type: "number",
      inputmode: "numeric",
      min: "0",
      max: "20000",
      placeholder: "毫升",
    });
    return h("div", { class: "card stack" }, [
      h("p", {}, `给 ${selected.nickname} 的 ${drink.name}`),
      h("p", { class: "amount" }, [String(ml), h("span", { class: "muted" }, " ml")]),
      h("div", { class: "actions" }, [
        h(
          "button",
          {
            type: "button",
            class: "step minus",
            disabled: ml <= 0,
            onClick: () => postLog({ set_ml: Math.max(0, ml - drink.step_ml) }),
          },
          ml <= drink.step_ml ? "减掉" : `−${drink.step_ml}`
        ),
        h(
          "button",
          { type: "button", class: "step", onClick: () => postLog({ delta_ml: drink.step_ml }) },
          `+${drink.step_ml}`
        ),
        presets.map((value) =>
          h(
            "button",
            { type: "button", class: "step", onClick: () => postLog({ delta_ml: value }) },
            `+${value}`
          )
        ),
      ]),
      h("div", { class: "row" }, [
        setInput,
        h(
          "button",
          {
            type: "button",
            class: "step set",
            onClick: () => {
              if (setInput.value === "") {
                toast("先写毫升");
                return;
              }
              postLog({ set_ml: Number(setInput.value) });
            },
          },
          "改成"
        ),
      ]),
    ]);
  }

  async function postLog(extra) {
    if (!ui.me) {
      toast("先填昵称");
      return;
    }
    await withLock(async () => {
      try {
        await api(`rooms/${encodeURIComponent(ui.roomId)}/logs`, {
          method: "POST",
          headers: { "X-Participant-Token": ui.me.token },
          body: JSON.stringify(
            Object.assign(
              {
                participant_id: ui.selectedId,
                drink_key: ui.drinkKey,
                date: ui.boardDate || undefined,
              },
              extra
            )
          ),
        });
        toast("记下了");
        await refresh(false);
      } catch (error) {
        toast(error.message);
      }
    });
  }

  function personCard(person, drink, mine) {
    const bits = [];
    if (drink) {
      const ml = Number(person.board.ml_by_drink[drink.key] || 0);
      bits.push(`${drink.name} ${ml} ml`);
    }
    Object.entries(person.board.ml_by_drink || {}).forEach(([key, ml]) => {
      if (!drink || key === drink.key || !ml) return;
      const named = (ui.cache.drinks || []).find((item) => item.key === key);
      bits.push(`${named ? named.name : key} ${ml} ml`);
    });
    (person.board.extras || []).forEach((extra) => {
      if (extra.ml) bits.push(`${extra.drink_name} ${extra.ml} ml`);
    });
    const device = DEVICE_LABEL[person.device_type] || "";
    const who = mine && mine.id === person.id ? `${person.nickname} · 我` : person.nickname;
    return h(
      "button",
      {
        type: "button",
        class: person.id === ui.selectedId ? "person selected" : "person",
        onClick: () => {
          ui.selectedId = person.id;
          renderBoard();
        },
      },
      [
        h("div", { class: "person-name" }, [
          h("span", {}, who),
          h("span", { class: "grams" }, `${grams(person.board.pure_alcohol_g)} 克`),
        ]),
        device ? h("div", { class: "muted" }, device) : null,
        h("div", { class: "ml-line" }, bits.join(" · ") || "还没记"),
      ]
    );
  }

  function rankTab(board, emptyText) {
    const rows = (board && board.rows) || [];
    const heading = board && board.scope === "all" ? "历史排行榜" : "今日排行榜";
    if (!rows.length) {
      return h("div", {}, [h("h2", { class: "page-title" }, heading), h("div", { class: "card" }, emptyText)]);
    }
    const top = rows[0].pure_alcohol_g || 1;
    return h("div", {}, [
      h("h2", { class: "page-title" }, heading),
      rows.map((row) =>
        h("div", { class: "rank" }, [
          h("div", { class: "rank-name" }, [
            h("span", {}, [h("span", { class: "rank-no" }, String(row.rank)), row.nickname]),
            h("span", { class: "grams" }, `${grams(row.pure_alcohol_g)} 克`),
          ]),
          h("div", { class: "bar" }, [
            h("span", { style: `width:${Math.max(6, Math.round((row.pure_alcohol_g / top) * 100))}%` }),
          ]),
          h(
            "div",
            { class: "ml-line" },
            row.volumes.map((volume) => `${volume.drink_name} ${volume.ml} ml`).join(" · ")
          ),
        ])
      ),
      formulaNote(ui.cache),
    ]);
  }

  function auditTab(data) {
    const items = data.audit || [];
    if (!items.length) return h("div", { class: "card" }, "还没有改动");
    return h(
      "div",
      {},
      items.map((item) => {
        let text = item.text;
        if (item.kind !== "reset") {
          const who =
            item.editor_nickname === item.subject_nickname
              ? `${item.editor_nickname} 把自己的`
              : `${item.editor_nickname} 给 ${item.subject_nickname} 的`;
          text = `${who} ${item.drink_name} ${signedMl(item.delta_ml)}`;
          if (item.shanghai_date && item.shanghai_date !== data.shanghai_today) {
            text += `（${item.shanghai_date}）`;
          }
        }
        return h("div", { class: "audit-item" }, [
          h("div", { class: "muted" }, clock(item.at)),
          h("div", {}, text),
        ]);
      })
    );
  }

  function formulaNote(data) {
    const density = data && data.formula ? data.formula.density_g_per_ml : 0.789;
    return h(
      "p",
      { class: "sub" },
      `按毫升乘酒精度得到纯酒精，再乘 ${density} 算成克。今天按上海时间的日期切。`
    );
  }

  function tabbar() {
    const tabs = [
      ["log", "记账"],
      ["today", "今日"],
      ["all", "历史"],
      ["audit", "改动"],
    ];
    return h(
      "nav",
      { class: "tabbar" },
      tabs.map(([id, label]) =>
        h(
          "button",
          {
            type: "button",
            class: "tab",
            "aria-current": ui.tab === id ? "page" : "false",
            onClick: () => {
              ui.tab = id;
              renderBoard();
            },
          },
          label
        )
      )
    );
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      toast("复制了");
    } catch (_err) {
      const area = h("textarea", { readonly: "readonly" }, text);
      document.body.append(area);
      area.select();
      try {
        document.execCommand("copy");
        toast("复制了");
      } catch (_error) {
        toast("复制失败，长按链接自己拷");
      }
      area.remove();
    }
  }

  window.addEventListener("popstate", show);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stopPoll();
    else if (ui.view === "board") {
      refresh(true);
      startPoll();
    }
  });
  parseRoute();
  show();
})();
