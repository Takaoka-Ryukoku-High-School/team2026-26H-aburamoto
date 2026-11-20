(() => {
  const enabledKey = "daily-note-weather-notifications-enabled";
  const cursorKey = "daily-note-weather-notifications-cursor";
  const timeKey = "daily-note-weather-notification-time";
  const deliveredKey = "daily-note-weather-notification-delivered-date";
  const panel = document.createElement("div");
  const button = document.createElement("button");
  const timeLabel = document.createElement("label");
  const timeInput = document.createElement("input");

  panel.style.cssText = [
    "position:fixed",
    "top:10px",
    "right:10px",
    "z-index:10000",
    "padding:8px",
    "border:1px solid #d4ded5",
    "border-radius:8px",
    "background:#fffefa",
    "box-shadow:0 2px 8px #0002",
    "font:12px sans-serif",
  ].join(";");
  button.type = "button";
  button.style.cssText = [
    "border:0",
    "border-radius:6px",
    "padding:7px 10px",
    "background:#e2ede5",
    "color:#2e6654",
    "font:inherit",
    "cursor:pointer",
  ].join(";");
  panel.append(button);
  timeLabel.textContent = "通知時刻 ";
  timeLabel.style.cssText = "display:block;margin-top:6px;color:#77807b;";
  timeInput.type = "time";
  timeInput.value = localStorage.getItem(timeKey) || "07:30";
  timeInput.style.cssText = "border:1px solid #d4ded5;border-radius:5px;padding:3px;";
  timeLabel.append(timeInput);
  panel.append(timeLabel);
  document.body.append(panel);

  timeInput.addEventListener("change", () => {
    localStorage.setItem(timeKey, timeInput.value || "07:30");
  });

  function isScheduledTime() {
    const configured = localStorage.getItem(timeKey) || "07:30";
    const now = new Date();
    const current = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    const today = now.toISOString().slice(0, 10);
    return current >= configured && localStorage.getItem(deliveredKey) !== today;
  }

  function isEnabled() {
    return localStorage.getItem(enabledKey) === "true";
  }

  function updateButton() {
    if (!("Notification" in window)) {
      button.textContent = "このブラウザは通知に未対応";
      button.disabled = true;
      return;
    }
    if (Notification.permission === "denied") {
      button.textContent = "通知はブラウザ設定で許可";
      button.disabled = true;
    } else if (Notification.permission === "granted" && isEnabled()) {
      button.textContent = "天気通知 ON（停止）";
      button.disabled = false;
    } else if (Notification.permission === "granted") {
      button.textContent = "天気通知 OFF（有効化）";
      button.disabled = false;
    } else {
      button.textContent = "天気通知を許可";
      button.disabled = false;
    }
  }

  button.addEventListener("click", async () => {
    if (!("Notification" in window)) {
      updateButton();
      return;
    }
    if (Notification.permission === "granted") {
      localStorage.setItem(enabledKey, String(!isEnabled()));
      updateButton();
      return;
    }
    const permission = await Notification.requestPermission();
    if (permission === "granted") {
      localStorage.setItem(enabledKey, "true");
    }
    updateButton();
  });

  let lastId = Number(localStorage.getItem(cursorKey) || "0");

  async function pollNotifications() {
    if ("Notification" in window && Notification.permission === "granted" && isEnabled() && isScheduledTime()) {
      try {
        const response = await fetch(
          `/api/weather-notifications?after=${lastId}`,
          { cache: "no-store" },
        );
        if (!response.ok) {
          throw new Error(`Notification request failed: ${response.status}`);
        }
        const result = await response.json();
        for (const notification of result.notifications) {
          lastId = Math.max(lastId, notification.id);
          localStorage.setItem(cursorKey, String(lastId));
          if (Date.now() - notification.created_at <= 60_000) {
            new Notification(notification.title, { body: notification.body });
          }
        }
        localStorage.setItem(deliveredKey, new Date().toISOString().slice(0, 10));
      } catch (error) {
        console.error("Could not check weather notifications:", error);
      }
    }
    window.setTimeout(pollNotifications, 5000);
  }

  updateButton();
  pollNotifications();
})();
