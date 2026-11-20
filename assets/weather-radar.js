(() => {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "🌧 雨雲レーダー";
  button.style.cssText = [
    "position:fixed",
    "top:88px",
    "right:12px",
    "z-index:10000",
    "border:0",
    "border-radius:8px",
    "padding:11px 14px",
    "background:#2e6654",
    "color:#fff",
    "box-shadow:0 3px 10px #0003",
    "font: bold 14px sans-serif",
    "cursor:pointer",
  ].join(";");

  const overlay = document.createElement("div");
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-label", "雨雲レーダー");
  overlay.style.cssText = [
    "position:fixed",
    "inset:0",
    "z-index:10001",
    "display:none",
    "align-items:center",
    "justify-content:center",
    "padding:12px",
    "background:#0008",
    "font:14px sans-serif",
  ].join(";");

  const panel = document.createElement("section");
  panel.style.cssText = [
    "width:min(900px,100%)",
    "max-height:94vh",
    "overflow:auto",
    "padding:14px",
    "border:1px solid #d4ded5",
    "border-radius:12px",
    "background:#fffefa",
    "box-shadow:0 8px 32px #0003",
  ].join(";");

  const heading = document.createElement("div");
  heading.style.cssText = "display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px;";
  const title = document.createElement("strong");
  title.textContent = "雨雲レーダー";
  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.textContent = "閉じる";
  closeButton.style.cssText = "border:0;border-radius:6px;padding:7px 10px;background:#e2ede5;color:#2e6654;cursor:pointer;";
  heading.append(title, closeButton);

  const mapElement = document.createElement("div");
  mapElement.style.cssText = "width:100%;height:min(58vh,560px);min-height:280px;border-radius:8px;background:#e9eee9;";

  const controls = document.createElement("div");
  controls.style.cssText = "display:flex;align-items:center;gap:10px;margin-top:10px;";
  const playButton = document.createElement("button");
  playButton.type = "button";
  playButton.textContent = "再生";
  playButton.style.cssText = closeButton.style.cssText;
  const slider = document.createElement("input");
  slider.type = "range";
  slider.min = "0";
  slider.max = "0";
  slider.value = "0";
  slider.disabled = true;
  slider.style.cssText = "flex:1;min-width:0;";
  const timestamp = document.createElement("span");
  timestamp.style.cssText = "min-width:76px;color:#77807b;text-align:right;font-size:12px;";
  controls.append(playButton, slider, timestamp);

  const status = document.createElement("div");
  status.setAttribute("role", "status");
  status.style.cssText = "min-height:18px;margin-top:7px;color:#77807b;font-size:12px;";
  const attribution = document.createElement("div");
  attribution.style.cssText = "margin-top:5px;color:#77807b;font-size:11px;";
  attribution.innerHTML = 'Weather data by <a href="https://www.rainviewer.com/" target="_blank" rel="noopener noreferrer">RainViewer</a>';

  panel.append(heading, mapElement, controls, status, attribution);
  overlay.append(panel);
  document.body.append(button, overlay);

  let map;
  let radarLayer;
  let frames = [];
  let animationTimer;
  let isLoading = false;

  function stopAnimation() {
    if (animationTimer) {
      window.clearInterval(animationTimer);
      animationTimer = undefined;
    }
    playButton.textContent = "再生";
  }

  function showFrame(index) {
    const frame = frames[index];
    if (!frame || !map) {
      return;
    }
    if (radarLayer) {
      map.removeLayer(radarLayer);
    }
    radarLayer = L.tileLayer(
      `${frame.host}${frame.path}/256/{z}/{x}/{y}/2/1_1.png`,
      {
        maxNativeZoom: 7,
        maxZoom: 12,
        opacity: 0.68,
        attribution: '<a href="https://www.rainviewer.com/" target="_blank" rel="noopener noreferrer">Weather data by RainViewer</a>',
      },
    ).addTo(map);
    timestamp.textContent = new Date(frame.time * 1000).toLocaleTimeString(
      [],
      { hour: "2-digit", minute: "2-digit" },
    );
    slider.value = String(index);
    status.textContent = `日本全国を移動・拡大して雨雲を確認できます（${index + 1}/${frames.length}）`;
  }

  async function loadRadar() {
    if (frames.length || isLoading) {
      if (frames.length) {
        showFrame(frames.length - 1);
      }
      return;
    }
    if (typeof L === "undefined") {
      status.textContent = "地図を読み込めません。ページを再読み込みしてください。";
      return;
    }

    isLoading = true;
    status.textContent = "雨雲データを読み込んでいます...";
    try {
      const response = await fetch(
        "https://api.rainviewer.com/public/weather-maps.json",
        { cache: "no-store" },
      );
      if (!response.ok) {
        throw new Error(`RainViewer request failed: ${response.status}`);
      }
      const result = await response.json();
      const radarFrames = result.radar?.past;
      if (!result.host || !Array.isArray(radarFrames) || radarFrames.length === 0) {
        throw new Error("RainViewer returned no radar frames");
      }
      frames = radarFrames.map((frame) => ({
        host: result.host,
        path: frame.path,
        time: frame.time,
      }));
      slider.max = String(frames.length - 1);
      slider.disabled = false;
      showFrame(frames.length - 1);
    } catch (error) {
      console.error("Could not load weather radar:", error);
      status.textContent = "雨雲データを取得できませんでした。時間をおいて再度お試しください。";
    } finally {
      isLoading = false;
    }
  }

  function openRadar() {
    overlay.style.display = "flex";
    if (!map && typeof L !== "undefined") {
      map = L.map(mapElement, { minZoom: 4, maxZoom: 12 }).setView([36.2, 138.2], 5);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map);
    }
    void loadRadar();
    window.setTimeout(() => map?.invalidateSize(), 0);
  }

  function closeRadar() {
    stopAnimation();
    overlay.style.display = "none";
  }

  button.addEventListener("click", openRadar);
  closeButton.addEventListener("click", closeRadar);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) {
      closeRadar();
    }
  });
  slider.addEventListener("input", () => {
    stopAnimation();
    showFrame(Number(slider.value));
  });
  playButton.addEventListener("click", () => {
    if (animationTimer) {
      stopAnimation();
      return;
    }
    if (frames.length < 2) {
      return;
    }
    playButton.textContent = "停止";
    animationTimer = window.setInterval(() => {
      const next = (Number(slider.value) + 1) % frames.length;
      showFrame(next);
    }, 700);
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && overlay.style.display !== "none") {
      closeRadar();
    }
  });
})();
